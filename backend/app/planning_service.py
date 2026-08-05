import hashlib
import json
import re
from collections import defaultdict
from datetime import date
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session


RULE_VERSION = "planning.rules.v1"
MODE_LIMITS = {"daily": 5, "weekly": 12, "pre_interview": 8}
TIER_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
MODE_ACTION_RANK = {
    "daily": {"review": 0, "practice": 1, "verify_fact": 2, "prepare_material": 3, "confirm_expression": 4, "map_evidence": 5},
    "weekly": {"verify_fact": 0, "map_evidence": 1, "review": 2, "practice": 3, "confirm_expression": 4, "prepare_material": 5},
    "pre_interview": {"confirm_expression": 0, "map_evidence": 1, "verify_fact": 2, "prepare_material": 3, "review": 4, "practice": 5},
}
ACTION_LABELS = {
    "review": "复习并口述",
    "practice": "练习并复盘",
    "verify_fact": "核实并补充事实证据",
    "prepare_material": "补齐材料",
    "confirm_expression": "核对事实后确认表达版本",
    "map_evidence": "为考点关联已确认事实",
}


def _rows(db: Session, statement: str, params: dict | None = None) -> list[dict]:
    return [dict(row) for row in db.execute(text(statement), params or {}).mappings().all()]


def _group(rows: list[dict], key: str) -> dict:
    result = defaultdict(list)
    for row in rows:
        result[row[key]].append(row)
    return result


def _normalized(value: str | None) -> str:
    return re.sub(r"[^\w]+", "", (value or "").casefold())


def _role_matches(value: str | None, candidates: list[str | None]) -> bool:
    left = _normalized(value)
    if len(left) < 2:
        return False
    for candidate in candidates:
        right = _normalized(candidate)
        if len(right) >= 2 and (left in right or right in left):
            return True
    return False


def _frequency_rank(count: int) -> int:
    if count >= 5:
        return 0
    if count >= 2:
        return 1
    if count == 1:
        return 2
    return 3


def _reason(code: str, message: str) -> dict:
    return {"code": code, "message": message}


def _base_item(
    *,
    item_id: str,
    track: str,
    action_type: str,
    entity_id: UUID,
    entity_label: str,
    entity_role: str | None,
    target: dict | None,
    tier: str,
    state_rank: int,
    source_types: list[str],
    business_ids: dict,
    reasons: list[dict],
    canonical_ids: list[UUID] | None = None,
    local_refs: list[dict] | None = None,
    limitations: list[str] | None = None,
) -> dict:
    target_match = bool(target and _role_matches(entity_role, [target["title"], target.get("focus")]))
    if target_match:
        reasons.append(_reason("TARGET_ROLE_EXPLICIT_MATCH", "经历中填写的目标岗位与所选目标画像存在确定性文本匹配。"))
    if target:
        source_types.append("target_profile")
    return {
        "id": item_id,
        "track": track,
        "action_type": action_type,
        "recommendation": f"{ACTION_LABELS[action_type]}：{entity_label}",
        "target": {
            "profile_id": str(target["id"]) if target else None,
            "profile_label": target["title"] if target else "未指定目标画像",
            "entity_id": str(entity_id),
            "entity_label": entity_label,
        },
        "priority": {"tier": tier, "tier_rank": TIER_RANK[tier], "order": None},
        "reason_codes": [item["code"] for item in reasons],
        "reasons": reasons,
        "source_types": list(dict.fromkeys(source_types)),
        "business_ids": business_ids,
        "evidence_status": "pending_resolution",
        "evidence_refs": [],
        "frequency_signal": None,
        "application_signal": {"applied": False, "effect": "none"},
        "limitations": limitations or [],
        "_entity_role": entity_role,
        "_state_rank": state_rank,
        "_target_rank": 0 if target_match else 1,
        "_canonical_ids": list(dict.fromkeys(canonical_ids or [])),
        "_local_refs": local_refs or [],
    }


def _target_profile(db: Session, profile_id: UUID | None) -> dict | None:
    if profile_id is None:
        return None
    row = db.execute(
        text("SELECT id, title, location, focus, summary FROM target_profiles WHERE id = :id"),
        {"id": profile_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="目标岗位画像不存在")
    return dict(row)


def _application_context(db: Session, mode: str, context: dict | None, as_of_date: date) -> tuple[dict, list[dict]]:
    warnings = []
    result = {
        "requested": context is not None,
        "reliable": False,
        "application_id": str(context["application_id"]) if context else None,
        "interview_date": context["interview_date"].isoformat() if context else None,
        "persisted_key_date_used": False,
        "maximum_effect": "same-tier tie-break only",
        "reason_code": "INTERVIEW_CONTEXT_NOT_PROVIDED",
    }
    if context is None:
        if mode == "pre_interview":
            warnings.append(_reason("INTERVIEW_CONTEXT_NOT_PROVIDED", "未提供明确面试日期，面试前模式仍可生成，但投递信息不参与排序。"))
        return result, warnings
    if mode != "pre_interview":
        raise HTTPException(status_code=422, detail="interview_context 只允许用于 pre_interview 模式")
    application = db.execute(
        text("SELECT id, company, role, stage, key_date FROM applications WHERE id = :id"),
        {"id": context["application_id"]},
    ).mappings().first()
    if application is None:
        raise HTTPException(status_code=404, detail="投递记录不存在")
    result.update({"company": application["company"], "role": application["role"], "stage": application["stage"]})
    days_until = (context["interview_date"] - as_of_date).days
    result["days_until_interview"] = days_until
    if application["stage"] != "interview":
        result["reason_code"] = "APPLICATION_NOT_IN_INTERVIEW_STAGE"
        warnings.append(_reason("APPLICATION_NOT_IN_INTERVIEW_STAGE", "所选投递不处于 interview 阶段，未启用投递弱信号。"))
    elif not 0 <= days_until <= 14:
        result["reason_code"] = "INTERVIEW_DATE_OUTSIDE_RELIABLE_WINDOW"
        warnings.append(_reason("INTERVIEW_DATE_OUTSIDE_RELIABLE_WINDOW", "明确面试日期不在 0 至 14 天窗口内，未启用投递弱信号。"))
    else:
        result["reliable"] = True
        result["reason_code"] = "RELIABLE_NEAR_TERM_INTERVIEW"
    warnings.append(_reason("APPLICATION_KEY_DATE_NOT_USED", "投递 key_date 未标注日期类型，未被当作面试日期或排序依据。"))
    return result, warnings


def _knowledge_candidates(db: Session, as_of: date, target: dict | None, stats: dict) -> list[dict]:
    cards = _rows(db, "SELECT id, title, mastery_status, origin, next_review_at FROM knowledge_cards ORDER BY id")
    links = _rows(db, """
        SELECT DISTINCT kce.card_id, qom.canonical_question_id,
               (SELECT COUNT(*)::int FROM question_occurrence_mappings all_mappings
                WHERE all_mappings.canonical_question_id = qom.canonical_question_id) AS occurrence_count
        FROM knowledge_card_evidence kce
        LEFT JOIN question_occurrences qo ON qo.evidence_span_id = kce.evidence_span_id
        LEFT JOIN question_occurrence_mappings qom ON qom.occurrence_id = qo.id
        ORDER BY kce.card_id, qom.canonical_question_id
    """)
    link_map = _group(links, "card_id")
    result = []
    stats["scanned_by_track"]["knowledge"] = len(cards)
    stats["excluded_by_track"]["knowledge"] += 0
    for card in cards:
        due = card["next_review_at"] is not None and card["next_review_at"] <= as_of
        if card["mastery_status"] == "mastered" and not due:
            stats["excluded_by_track"]["knowledge"] += 1
            continue
        tier = {"not_started": "high", "learning": "high", "familiar": "medium", "mastered": "low"}[card["mastery_status"]]
        reasons = [_reason(f"KNOWLEDGE_{card['mastery_status'].upper()}", f"知识卡当前状态为 {card['mastery_status']}，按知识轨道语义安排复习。")]
        if due and card["mastery_status"] != "mastered":
            tier = "critical" if card["mastery_status"] in {"not_started", "learning"} else "high"
            reasons.append(_reason("REVIEW_DUE", "下一复习日期已到，提升到更高的稳定优先级档位。"))
        elif due:
            reasons.append(_reason("MASTERED_MAINTENANCE_DUE", "已掌握内容仅因维护复习到期进入低优先级，不表示能力下降。"))
        elif card["next_review_at"] is None:
            reasons.append(_reason("REVIEW_DATE_MISSING", "未设置下一复习日期，不推断紧迫度。"))
        rows = link_map.get(card["id"], [])
        canonical_ids = [row["canonical_question_id"] for row in rows if row["canonical_question_id"]]
        occurrence_count = max([row["occurrence_count"] for row in rows if row["canonical_question_id"]] or [0])
        if occurrence_count:
            reasons.append(_reason("STRUCTURED_DEMAND_OBSERVED", "关联规范题存在结构化 occurrence；频率只用于需求排序，不表示掌握度。"))
        result.append(_base_item(
            item_id=f"knowledge:{card['id']}:review", track="knowledge", action_type="review",
            entity_id=card["id"], entity_label=card["title"], entity_role=None, target=target, tier=tier,
            state_rank={"not_started": 0, "learning": 1, "familiar": 2, "mastered": 3}[card["mastery_status"]],
            source_types=["user_mastery_state"]
            + (["intelligence_suggestion_origin"] if card["origin"] == "intelligence_suggestion" else [])
            + (["structured_intelligence_frequency"] if occurrence_count else []),
            business_ids={"knowledge_card_id": str(card["id"])}, reasons=reasons, canonical_ids=canonical_ids,
            limitations=["情报频率是需求信号，不是用户能力评分。"],
        ) | {"_frequency_count": occurrence_count})
    return result


def _algorithm_candidates(db: Session, as_of: date, target: dict | None, stats: dict) -> list[dict]:
    items = _rows(db, """
        SELECT ap.id, ap.title, ap.status, ap.origin, ap.source_url, ap.canonical_question_id,
               ap.next_review_at, COUNT(qom.occurrence_id)::int AS occurrence_count
        FROM algorithm_problems ap
        LEFT JOIN question_occurrence_mappings qom ON qom.canonical_question_id = ap.canonical_question_id
        GROUP BY ap.id ORDER BY ap.id
    """)
    result = []
    stats["scanned_by_track"]["algorithm"] = len(items)
    stats["excluded_by_track"]["algorithm"] += 0
    for item in items:
        due = item["next_review_at"] is not None and item["next_review_at"] <= as_of
        if item["status"] == "solved" and not due:
            stats["excluded_by_track"]["algorithm"] += 1
            continue
        tier = {"revisit": "critical", "in_progress": "high", "not_started": "medium", "solved": "low"}[item["status"]]
        reasons = [_reason(f"ALGORITHM_{item['status'].upper()}", f"算法题当前状态为 {item['status']}，按算法轨道语义安排练习。")]
        if due and item["status"] != "solved":
            tier = "critical" if item["status"] in {"revisit", "in_progress"} else "high"
            reasons.append(_reason("PRACTICE_DUE", "下一复盘日期已到，提升到更高的稳定优先级档位。"))
        elif due:
            reasons.append(_reason("SOLVED_MAINTENANCE_DUE", "已解决题目仅作为到期维护项进入低优先级。"))
        if item["occurrence_count"]:
            reasons.append(_reason("STRUCTURED_DEMAND_OBSERVED", "关联规范题存在结构化 occurrence；频率不作为难度或能力评分。"))
        local_refs = []
        if item["source_url"]:
            local_refs.append({"kind": "external_problem", "url": item["source_url"], "supports_capability": False})
        result.append(_base_item(
            item_id=f"algorithm:{item['id']}:practice", track="algorithm", action_type="practice",
            entity_id=item["id"], entity_label=item["title"], entity_role=None, target=target, tier=tier,
            state_rank={"revisit": 0, "in_progress": 1, "not_started": 2, "solved": 3}[item["status"]],
            source_types=["user_algorithm_state"]
            + (["intelligence_suggestion_origin"] if item["origin"] == "intelligence_suggestion" else [])
            + (["structured_intelligence_frequency"] if item["occurrence_count"] else []),
            business_ids={"algorithm_problem_id": str(item["id"]), "canonical_question_id": str(item["canonical_question_id"]) if item["canonical_question_id"] else None},
            reasons=reasons, canonical_ids=[item["canonical_question_id"]] if item["canonical_question_id"] else [], local_refs=local_refs,
            limitations=["题目状态由用户维护；规范题频率只表示面经需求。"],
        ) | {"_frequency_count": item["occurrence_count"]})
    return result


def _experience_candidates(db: Session, mode: str, target: dict | None, stats: dict) -> list[dict]:
    projects = _rows(db, "SELECT id, title, target_role FROM projects WHERE status = 'active' ORDER BY id")
    project_facts = _group(_rows(db, "SELECT id, project_id AS owner_id, source_kind, source_reference, origin, confirmation_status FROM project_evidence ORDER BY project_id, id"), "owner_id")
    project_versions = _group(_rows(db, "SELECT id, project_id AS owner_id, origin, confirmation_status, version_number FROM project_expression_versions ORDER BY project_id, version_number DESC"), "owner_id")
    internships = _rows(db, "SELECT id, organization, role_title FROM internships WHERE status = 'active' ORDER BY id")
    internship_facts = _group(_rows(db, "SELECT id, internship_id AS owner_id, source_kind, source_reference, origin, confirmation_status FROM internship_facts ORDER BY internship_id, id"), "owner_id")
    internship_versions = _group(_rows(db, "SELECT id, internship_id AS owner_id, origin, confirmation_status, version_number FROM internship_expression_versions ORDER BY internship_id, version_number DESC"), "owner_id")
    materials = _group(_rows(db, "SELECT id, internship_id AS owner_id, label, preparation_status, locator FROM internship_materials ORDER BY internship_id, id"), "owner_id")
    links = _rows(db, """
        SELECT 'project' AS track, pil.id, pil.project_id AS owner_id, p.title AS owner_label,
               p.target_role AS entity_role, pil.canonical_question_id, pil.project_evidence_id AS fact_id,
               pe.confirmation_status AS fact_status, pe.origin AS fact_origin,
               COUNT(qom.occurrence_id)::int AS occurrence_count
        FROM project_intelligence_links pil
        JOIN projects p ON p.id = pil.project_id AND p.status = 'active'
        LEFT JOIN project_evidence pe ON pe.id = pil.project_evidence_id
        LEFT JOIN question_occurrence_mappings qom ON qom.canonical_question_id = pil.canonical_question_id
        GROUP BY pil.id, p.title, p.target_role, pe.confirmation_status, pe.origin
        UNION ALL
        SELECT 'internship', iil.id, iil.internship_id, i.organization, i.role_title,
               iil.canonical_question_id, iil.internship_fact_id,
               inf.confirmation_status, inf.origin, COUNT(qom.occurrence_id)::int
        FROM internship_intelligence_links iil
        JOIN internships i ON i.id = iil.internship_id AND i.status = 'active'
        LEFT JOIN internship_facts inf ON inf.id = iil.internship_fact_id
        LEFT JOIN question_occurrence_mappings qom ON qom.canonical_question_id = iil.canonical_question_id
        GROUP BY iil.id, i.organization, i.role_title, inf.confirmation_status, inf.origin
        ORDER BY track, id
    """)
    result = []
    stats["scanned_by_track"].update({"project": len(projects), "internship": len(internships)})
    stats["excluded_by_track"].update({"project": 0, "internship": 0})

    def add_owner(track: str, owner: dict, label: str, role: str | None, facts: list[dict], versions: list[dict]):
        confirmed = [fact for fact in facts if fact["confirmation_status"] == "confirmed"]
        drafts = [fact for fact in facts if fact["confirmation_status"] == "draft"]
        confirmed_versions = [version for version in versions if version["confirmation_status"] == "confirmed"]
        if not confirmed or drafts:
            tier = "critical" if mode == "pre_interview" and not confirmed else "high"
            reasons = []
            if not confirmed:
                reasons.append(_reason("CONFIRMED_FACT_MISSING", "没有已确认事实；草稿或表达版本不能证明经历能力。"))
            if drafts:
                reasons.append(_reason("UNVERIFIED_FACT_DRAFT_PRESENT", "存在待核实事实草稿，只生成核实/补证据任务。"))
            local_refs = [{
                "kind": f"{track}_fact", "id": str(fact["id"]), "origin": fact["origin"],
                "confirmation_status": fact["confirmation_status"], "source_kind": fact["source_kind"],
                "source_reference": fact["source_reference"], "supports_capability": fact["confirmation_status"] == "confirmed",
            } for fact in (drafts + confirmed)[:3]]
            result.append(_base_item(
                item_id=f"{track}:{owner['id']}:verify-facts", track=track, action_type="verify_fact",
                entity_id=owner["id"], entity_label=label, entity_role=role, target=target, tier=tier,
                state_rank=0 if not confirmed else 1,
                source_types=["confirmed_fact"] * bool(confirmed)
                + ["unverified_draft"] * bool(drafts)
                + ["ai_draft_origin"] * any(fact["origin"] == "ai_draft" for fact in facts)
                + ["missing_confirmed_fact"] * (not facts),
                business_ids={f"{track}_id": str(owner["id"]), "fact_ids": [str(fact["id"]) for fact in facts]},
                reasons=reasons, local_refs=local_refs,
                limitations=["draft/ai_draft 只表示待核实内容，不证明能力已完成。"],
            ) | {"_frequency_count": 0})
        if not confirmed_versions:
            draft_versions = [version for version in versions if version["confirmation_status"] == "draft"]
            reasons = [_reason("CONFIRMED_EXPRESSION_MISSING", "没有已确认表达版本；表达准备度与客观事实分开处理。")]
            if draft_versions:
                reasons.append(_reason("EXPRESSION_DRAFT_REVIEW_REQUIRED", "已有表达草稿，建议核对事实边界后再确认。"))
            result.append(_base_item(
                item_id=f"{track}:{owner['id']}:confirm-expression", track=track, action_type="confirm_expression",
                entity_id=owner["id"], entity_label=label, entity_role=role, target=target,
                tier="high" if mode == "pre_interview" else "medium", state_rank=0 if not versions else 1,
                source_types=(["expression_version"] if versions else ["missing_expression_version"])
                + (["unverified_draft"] if draft_versions else [])
                + (["ai_draft_origin"] if any(version["origin"] == "ai_draft" for version in draft_versions) else []),
                business_ids={f"{track}_id": str(owner["id"]), "expression_version_ids": [str(version["id"]) for version in versions]},
                reasons=reasons,
                local_refs=[{"kind": f"{track}_expression_version", "id": str(version["id"]), "origin": version["origin"], "confirmation_status": version["confirmation_status"], "supports_capability": False} for version in draft_versions[:3]],
                limitations=["表达版本不是客观事实；即使确认也不自动证明能力。"],
            ) | {"_frequency_count": 0})

    for project in projects:
        add_owner("project", project, project["title"], project["target_role"], project_facts.get(project["id"], []), project_versions.get(project["id"], []))
    for internship in internships:
        add_owner("internship", internship, internship["organization"], internship["role_title"], internship_facts.get(internship["id"], []), internship_versions.get(internship["id"], []))
        for material in materials.get(internship["id"], []):
            if material["preparation_status"] in {"ready", "verified"}:
                stats["excluded_by_track"]["internship"] += 1
                continue
            result.append(_base_item(
                item_id=f"internship-material:{material['id']}:prepare", track="internship", action_type="prepare_material",
                entity_id=material["id"], entity_label=material["label"], entity_role=internship["role_title"], target=target,
                tier="high" if mode == "pre_interview" and material["preparation_status"] == "missing" else "medium",
                state_rank=0 if material["preparation_status"] == "missing" else 1,
                source_types=["user_material_state"],
                business_ids={"internship_id": str(internship["id"]), "internship_material_id": str(material["id"])},
                reasons=[_reason(f"MATERIAL_{material['preparation_status'].upper()}", f"材料状态为 {material['preparation_status']}，不视为已准备完成。")],
                local_refs=[{"kind": "internship_material", "id": str(material["id"]), "locator": material["locator"], "preparation_status": material["preparation_status"], "supports_capability": False}],
            ) | {"_frequency_count": 0})
    for link in links:
        if link["fact_status"] == "confirmed":
            continue
        reasons = [_reason("INTELLIGENCE_LINK_WITHOUT_CONFIRMED_FACT", "考点关联没有绑定已确认事实，只能生成补证据任务。")]
        if link["occurrence_count"]:
            reasons.append(_reason("STRUCTURED_DEMAND_OBSERVED", "规范题存在结构化 occurrence；频率只表示需求，不证明经历能力。"))
        result.append(_base_item(
            item_id=f"{link['track']}-intelligence:{link['id']}:map-evidence", track=link["track"], action_type="map_evidence",
            entity_id=link["owner_id"], entity_label=link["owner_label"], entity_role=link["entity_role"], target=target,
            tier="high" if mode == "pre_interview" else "medium", state_rank=0,
            source_types=["structured_intelligence_link"]
            + (["structured_intelligence_frequency"] if link["occurrence_count"] else [])
            + (["unverified_draft"] if link["fact_id"] else ["missing_confirmed_fact"]),
            business_ids={f"{link['track']}_id": str(link["owner_id"]), "intelligence_link_id": str(link["id"]), "canonical_question_id": str(link["canonical_question_id"]), "fact_id": str(link["fact_id"]) if link["fact_id"] else None},
            reasons=reasons, canonical_ids=[link["canonical_question_id"]],
            limitations=["关联与 occurrence 频率都不是经历真实性或能力评分。"],
        ) | {"_frequency_count": link["occurrence_count"]})
    return result


def _canonical_evidence(db: Session, canonical_id: UUID, limit: int) -> list[dict]:
    rows = _rows(db, """
        SELECT qo.id AS occurrence_id, qo.document_id, qo.evidence_span_id,
               s.id AS submission_id, src.source_url, es.start_char, es.end_char,
               SUBSTRING(d.cleaned_content FROM es.start_char + 1 FOR LEAST(es.end_char - es.start_char, 240)) AS quote
        FROM question_occurrence_mappings qom
        JOIN question_occurrences qo ON qo.id = qom.occurrence_id
        JOIN evidence_spans es ON es.id = qo.evidence_span_id
        JOIN interview_documents d ON d.id = qo.document_id
        LEFT JOIN LATERAL (
          SELECT candidate.id, candidate.source_id FROM interview_submissions candidate
          WHERE candidate.document_id = d.id ORDER BY candidate.submitted_at DESC, candidate.id LIMIT 1
        ) s ON TRUE
        LEFT JOIN interview_sources src ON src.id = s.source_id
        WHERE qom.canonical_question_id = :id
        ORDER BY qo.created_at DESC, qo.id LIMIT :limit
    """, {"id": canonical_id, "limit": limit})
    return [{
        "kind": "interview_occurrence", "canonical_question_id": str(canonical_id),
        "occurrence_id": str(row["occurrence_id"]), "evidence_span_id": str(row["evidence_span_id"]),
        "document_id": str(row["document_id"]), "submission_id": str(row["submission_id"]) if row["submission_id"] else None,
        "source_url": row["source_url"], "start_char": row["start_char"], "end_char": row["end_char"],
        "quote": row["quote"], "supports_capability": False,
    } for row in rows]


def _knowledge_evidence(db: Session, card_id: UUID) -> list[dict]:
    rows = _rows(db, """
        SELECT kce.evidence_span_id, er.document_id, s.id AS submission_id, src.source_url,
               es.start_char, es.end_char,
               SUBSTRING(d.cleaned_content FROM es.start_char + 1 FOR LEAST(es.end_char - es.start_char, 240)) AS quote
        FROM knowledge_card_evidence kce
        JOIN evidence_spans es ON es.id = kce.evidence_span_id
        JOIN extraction_runs er ON er.id = es.run_id
        JOIN interview_documents d ON d.id = er.document_id
        LEFT JOIN LATERAL (
          SELECT candidate.id, candidate.source_id FROM interview_submissions candidate
          WHERE candidate.document_id = d.id ORDER BY candidate.submitted_at DESC, candidate.id LIMIT 1
        ) s ON TRUE
        LEFT JOIN interview_sources src ON src.id = s.source_id
        WHERE kce.card_id = :id ORDER BY kce.evidence_span_id LIMIT 3
    """, {"id": card_id})
    return [{
        "kind": "interview_evidence_span", "evidence_span_id": str(row["evidence_span_id"]),
        "document_id": str(row["document_id"]), "submission_id": str(row["submission_id"]) if row["submission_id"] else None,
        "source_url": row["source_url"], "start_char": row["start_char"], "end_char": row["end_char"],
        "quote": row["quote"], "supports_capability": False,
    } for row in rows]


def generate_assessment(
    db: Session,
    *,
    mode: str,
    as_of_date: date,
    target_profile_id: UUID | None,
    interview_context: dict | None,
) -> dict:
    db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
    target = _target_profile(db, target_profile_id)
    application, warnings = _application_context(db, mode, interview_context, as_of_date)
    if target is None:
        warnings.append(_reason("TARGET_PROFILE_NOT_SELECTED", "未选择目标画像，结果保持通用准备建议且不推断岗位相关性。"))
    stats = {"scanned_by_track": defaultdict(int), "excluded_by_track": defaultdict(int)}
    items = []
    items.extend(_knowledge_candidates(db, as_of_date, target, stats))
    items.extend(_algorithm_candidates(db, as_of_date, target, stats))
    items.extend(_experience_candidates(db, mode, target, stats))
    for track in ("knowledge", "algorithm", "project", "internship"):
        if stats["scanned_by_track"][track] == 0:
            warnings.append(_reason(f"{track.upper()}_NO_DATA", f"{track} 轨道没有业务数据，系统不会为该轨道编造建议。"))
    app_role = application.get("role") if application["reliable"] else None
    for item in items:
        item["_application_rank"] = 1
        if app_role and _role_matches(item["_entity_role"], [app_role]):
            item["_application_rank"] = 0
            item["application_signal"] = {"applied": True, "effect": "same-tier tie-break only", "application_id": application["application_id"]}
            item["reasons"].append(_reason("NEAR_TERM_INTERVIEW_ROLE_MATCH", "可信临近面试上下文与经历岗位字段确定性匹配，仅用于同档位次级排序。"))
            item["reason_codes"].append("NEAR_TERM_INTERVIEW_ROLE_MATCH")
            item["source_types"].append("reliable_application_context")
        item["_mode_rank"] = MODE_ACTION_RANK[mode][item["action_type"]]
        item["_frequency_rank"] = _frequency_rank(item["_frequency_count"])
    items.sort(key=lambda item: (
        item["priority"]["tier_rank"], item["_mode_rank"], item["_target_rank"], item["_state_rank"],
        item["_application_rank"], item["_frequency_rank"], item["id"],
    ))
    selected = items[:MODE_LIMITS[mode]]
    for order, item in enumerate(selected, start=1):
        refs = list(item["_local_refs"])
        if item["track"] == "knowledge":
            refs.extend(_knowledge_evidence(db, UUID(item["business_ids"]["knowledge_card_id"])))
        else:
            for canonical_id in item["_canonical_ids"]:
                remaining = 3 - len(refs)
                if remaining <= 0:
                    break
                refs.extend(_canonical_evidence(db, canonical_id, remaining))
        refs = refs[:3]
        item["evidence_refs"] = refs
        if any(ref["kind"].startswith("interview_") for ref in refs):
            item["evidence_status"] = "linked_interview_evidence"
        elif any(ref.get("supports_capability") for ref in refs):
            item["evidence_status"] = "confirmed_business_fact"
        elif refs:
            item["evidence_status"] = "reference_only_or_unverified"
        else:
            item["evidence_status"] = "no_linked_evidence"
            item["limitations"].append("没有可回链证据；建议依据仅限当前业务状态，不能外推能力事实。")
        if item["_frequency_count"]:
            item["frequency_signal"] = {"occurrence_count": item["_frequency_count"], "meaning": "structured_demand_only", "is_capability_score": False}
        item["source_types"] = list(dict.fromkeys(item["source_types"]))
        item["priority"]["order"] = order
        for private_key in [key for key in item if key.startswith("_")]:
            del item[private_key]
    if not selected:
        warnings.append(_reason("NO_ACTIONABLE_ITEMS", "当前事实快照没有可操作建议；系统不会为填满列表而编造任务。"))
    response = {
        "rule_version": RULE_VERSION,
        "mode": mode,
        "as_of_date": as_of_date.isoformat(),
        "trigger": "explicit_request",
        "target_profile": ({key: (str(value) if key == "id" else value) for key, value in target.items()} if target else None),
        "application_context": application,
        "sorting_contract": {
            "priority_tiers": ["critical", "high", "medium", "low"],
            "tie_break": ["priority_tier", "mode_action_rank", "explicit_target_role_match", "track_state_rank", "bounded_application_rank", "frequency_band", "stable_item_id"],
            "application_effect_cap": "never changes priority tier; same-tier role-matched tie-break only",
            "frequency_meaning": "structured demand only; never a capability score",
            "item_limit": MODE_LIMITS[mode],
        },
        "input_summary": {
            "scanned_by_track": dict(stats["scanned_by_track"]),
            "excluded_completed_by_track": dict(stats["excluded_by_track"]),
            "candidate_count": len(items),
            "returned_count": len(selected),
        },
        "warnings": warnings,
        "items": selected,
    }
    response["snapshot_fingerprint"] = hashlib.sha256(
        json.dumps(response, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return response
