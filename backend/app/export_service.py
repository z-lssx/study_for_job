import hashlib
import json
from collections import Counter
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session


SCHEMA_VERSION = "study-for-job.fact-relations.v1"
EXPORT_VERSION = "mvp.export.v1"
EVIDENCE_EXCERPT_LIMIT = 240

COLLECTION_LABELS = {
    "target_profiles": "目标画像",
    "applications": "投递记录",
    "interview_sources": "面经来源",
    "interview_documents": "面经文档元数据",
    "interview_submissions": "面经提交元数据",
    "extraction_runs": "结构化抽取运行",
    "interview_rounds": "面试轮次",
    "document_chunks": "结构化内容块",
    "chunk_annotations": "用户标注修订",
    "question_candidates": "问题候选",
    "evidence_refs": "有界证据引用",
    "canonical_questions": "规范题",
    "question_occurrences": "题目出现事实",
    "question_occurrence_mappings": "出现与规范题映射",
    "question_mapping_revisions": "映射修订历史",
    "knowledge_cards": "知识卡片",
    "knowledge_evidence_links": "知识卡证据关联",
    "algorithm_problems": "算法题与用户状态",
    "projects": "项目",
    "project_facts": "项目事实与草稿",
    "project_expression_versions": "项目表达版本",
    "project_intelligence_links": "项目情报关联",
    "internships": "实习",
    "internship_facts": "实习事实与草稿",
    "internship_expression_versions": "实习表达版本",
    "internship_materials": "实习材料",
    "internship_intelligence_links": "实习情报关联",
}

COLLECTION_QUERIES = {
    "target_profiles": "SELECT to_jsonb(t) AS value FROM target_profiles t ORDER BY t.id",
    "applications": "SELECT to_jsonb(t) AS value FROM applications t ORDER BY t.id",
    "interview_sources": "SELECT to_jsonb(t) AS value FROM interview_sources t ORDER BY t.id",
    "interview_documents": """
        SELECT (to_jsonb(t) - 'raw_content' - 'cleaned_content')
               || jsonb_build_object('content_omitted', true) AS value
        FROM interview_documents t ORDER BY t.id
    """,
    "interview_submissions": """
        SELECT (to_jsonb(t) - 'raw_content' - 'current_job_id')
               || jsonb_build_object(
                    'raw_input_omitted', true,
                    'processing_status', CASE
                        WHEN t.document_id IS NOT NULL THEN 'succeeded'
                        WHEN j.status IS NOT NULL THEN j.status
                        WHEN t.last_error_code IS NOT NULL THEN 'failed'
                        ELSE 'unresolved'
                    END
                  ) AS value
        FROM interview_submissions t
        LEFT JOIN jobs j ON j.id = t.current_job_id
        ORDER BY t.id
    """,
    "extraction_runs": "SELECT to_jsonb(t) - 'job_id' AS value FROM extraction_runs t ORDER BY t.id",
    "interview_rounds": "SELECT to_jsonb(t) AS value FROM interview_rounds t ORDER BY t.id",
    "document_chunks": "SELECT to_jsonb(t) AS value FROM document_chunks t ORDER BY t.id",
    "chunk_annotations": "SELECT to_jsonb(t) AS value FROM extraction_chunk_annotations t ORDER BY t.chunk_id",
    "question_candidates": "SELECT to_jsonb(t) AS value FROM question_candidates t ORDER BY t.id",
    "canonical_questions": """
        SELECT to_jsonb(t)
               || jsonb_build_object(
                    'occurrence_count', (
                        SELECT COUNT(*)::int FROM question_occurrence_mappings m
                        WHERE m.canonical_question_id = t.id
                    ),
                    'frequency_semantics', 'structured_demand_signal_only'
                  ) AS value
        FROM canonical_questions t ORDER BY t.id
    """,
    "question_occurrences": "SELECT to_jsonb(t) AS value FROM question_occurrences t ORDER BY t.id",
    "question_occurrence_mappings": "SELECT to_jsonb(t) AS value FROM question_occurrence_mappings t ORDER BY t.occurrence_id",
    "question_mapping_revisions": "SELECT to_jsonb(t) AS value FROM question_mapping_revisions t ORDER BY t.id",
    "knowledge_cards": "SELECT to_jsonb(t) AS value FROM knowledge_cards t ORDER BY t.id",
    "knowledge_evidence_links": """
        SELECT to_jsonb(t)
               || jsonb_build_object('relation_id', 'knowledge_evidence:' || t.card_id::text || ':' || t.evidence_span_id::text) AS value
        FROM knowledge_card_evidence t ORDER BY t.card_id, t.evidence_span_id
    """,
    "algorithm_problems": """
        SELECT to_jsonb(t)
               || jsonb_build_object(
                    'occurrence_count', (
                        SELECT COUNT(*)::int FROM question_occurrence_mappings m
                        WHERE m.canonical_question_id = t.canonical_question_id
                    ),
                    'frequency_semantics', 'structured_demand_signal_only'
                  ) AS value
        FROM algorithm_problems t ORDER BY t.id
    """,
    "projects": "SELECT to_jsonb(t) AS value FROM projects t ORDER BY t.id",
    "project_facts": "SELECT to_jsonb(t) AS value FROM project_evidence t ORDER BY t.id",
    "project_expression_versions": """
        SELECT to_jsonb(t) AS value FROM project_expression_versions t
        ORDER BY t.project_id, t.version_number, t.id
    """,
    "project_intelligence_links": """
        SELECT to_jsonb(t)
               || jsonb_build_object(
                    'occurrence_count', (
                        SELECT COUNT(*)::int FROM question_occurrence_mappings m
                        WHERE m.canonical_question_id = t.canonical_question_id
                    ),
                    'frequency_semantics', 'structured_demand_signal_only'
                  ) AS value
        FROM project_intelligence_links t ORDER BY t.id
    """,
    "internships": "SELECT to_jsonb(t) AS value FROM internships t ORDER BY t.id",
    "internship_facts": "SELECT to_jsonb(t) AS value FROM internship_facts t ORDER BY t.id",
    "internship_expression_versions": """
        SELECT to_jsonb(t) AS value FROM internship_expression_versions t
        ORDER BY t.internship_id, t.version_number, t.id
    """,
    "internship_materials": "SELECT to_jsonb(t) AS value FROM internship_materials t ORDER BY t.id",
    "internship_intelligence_links": """
        SELECT to_jsonb(t)
               || jsonb_build_object(
                    'occurrence_count', (
                        SELECT COUNT(*)::int FROM question_occurrence_mappings m
                        WHERE m.canonical_question_id = t.canonical_question_id
                    ),
                    'frequency_semantics', 'structured_demand_signal_only'
                  ) AS value
        FROM internship_intelligence_links t ORDER BY t.id
    """,
}


def _json_rows(db: Session, statement: str) -> list[dict]:
    return [dict(row["value"]) for row in db.execute(text(statement)).mappings().all()]


def _evidence_refs(db: Session) -> list[dict]:
    statement = text(f"""
        SELECT to_jsonb(es)
               || jsonb_build_object(
                    'document_id', er.document_id,
                    'quote', substring(d.cleaned_content FROM es.start_char + 1
                        FOR LEAST(es.end_char - es.start_char, {EVIDENCE_EXCERPT_LIMIT})),
                    'quote_is_bounded', true,
                    'quote_max_chars', {EVIDENCE_EXCERPT_LIMIT},
                    'submission_id', origin.submission_id,
                    'source_id', origin.source_id,
                    'source_url', origin.source_url,
                    'source_host', origin.source_host,
                    'supports_objective_capability', false
                  ) AS value
        FROM evidence_spans es
        JOIN extraction_runs er ON er.id = es.run_id
        JOIN interview_documents d ON d.id = er.document_id
        LEFT JOIN LATERAL (
            SELECT s.id AS submission_id, s.source_id, src.source_url, src.host AS source_host
            FROM interview_submissions s
            LEFT JOIN interview_sources src ON src.id = s.source_id
            WHERE s.document_id = er.document_id
            ORDER BY (s.source_id IS NULL), s.submitted_at, s.id
            LIMIT 1
        ) origin ON true
        ORDER BY es.id
    """)
    return _json_rows(db, str(statement))


def _boundary_class(collection: str, record: dict) -> str:
    if collection in {"target_profiles", "applications", "projects", "internships"}:
        return "user_maintained_fact"
    if collection in {"knowledge_cards", "algorithm_problems"}:
        return "user_maintained_state"
    if collection in {"project_facts", "internship_facts"}:
        if record["confirmation_status"] == "confirmed":
            return "confirmed_fact_with_ai_draft_origin" if record["origin"] == "ai_draft" else "confirmed_fact"
        return "ai_draft" if record["origin"] == "ai_draft" else "draft"
    if collection in {"project_expression_versions", "internship_expression_versions"}:
        prefix = "confirmed_expression" if record["confirmation_status"] == "confirmed" else "draft_expression"
        return f"{prefix}_with_ai_draft_origin" if record["origin"] == "ai_draft" else prefix
    if collection == "internship_materials":
        return "material_state"
    if collection in {
        "canonical_questions", "question_candidates", "question_occurrences",
        "question_occurrence_mappings", "project_intelligence_links", "internship_intelligence_links",
    }:
        return "structured_intelligence_signal"
    if collection in {"question_mapping_revisions", "chunk_annotations"}:
        return "user_revision"
    if collection == "evidence_refs":
        return "source_evidence"
    if collection in {"knowledge_evidence_links", "interview_rounds", "document_chunks", "extraction_runs"}:
        return "evidence_structure"
    return "source_metadata"


def _load_collections(db: Session) -> dict[str, list[dict]]:
    collections = {}
    for name in COLLECTION_LABELS:
        rows = _evidence_refs(db) if name == "evidence_refs" else _json_rows(db, COLLECTION_QUERIES[name])
        for row in rows:
            row["boundary_class"] = _boundary_class(name, row)
            if name in {"knowledge_cards", "algorithm_problems"}:
                row["supports_objective_capability"] = False
            if name in {"project_expression_versions", "internship_expression_versions"}:
                row["supports_objective_capability"] = False
        collections[name] = rows
    return collections


def _relationship(
    relationship_id: str,
    relationship_type: str,
    from_collection: str,
    from_id,
    to_collection: str,
    to_id,
    **attributes,
) -> dict | None:
    if not from_id or not to_id:
        return None
    return {
        "id": relationship_id,
        "type": relationship_type,
        "from": {"collection": from_collection, "id": str(from_id)},
        "to": {"collection": to_collection, "id": str(to_id)},
        "attributes": attributes,
    }


def _add_relationship(result: list[dict], *args, **kwargs) -> None:
    relation = _relationship(*args, **kwargs)
    if relation:
        result.append(relation)


def _build_relationships(db: Session, collections: dict[str, list[dict]]) -> list[dict]:
    result = []
    document_sources = _json_rows(db, """
        SELECT to_jsonb(t)
               || jsonb_build_object('relation_id', 'document_source:' || t.document_id::text || ':' || t.source_id::text) AS value
        FROM interview_document_sources t ORDER BY t.document_id, t.source_id
    """)
    for link in document_sources:
        _add_relationship(
            result, link["relation_id"], "document_has_source", "interview_documents", link["document_id"],
            "interview_sources", link["source_id"], first_submission_id=link["first_submission_id"], linked_at=link["linked_at"],
        )
    for item in collections["interview_submissions"]:
        _add_relationship(result, f"submission_source:{item['id']}", "submission_uses_source", "interview_submissions", item["id"], "interview_sources", item.get("source_id"))
        _add_relationship(result, f"submission_document:{item['id']}", "submission_resolved_to_document", "interview_submissions", item["id"], "interview_documents", item.get("document_id"))
    for item in collections["extraction_runs"]:
        _add_relationship(result, f"extraction_document:{item['id']}", "extraction_reads_document", "extraction_runs", item["id"], "interview_documents", item["document_id"])
    for item in collections["interview_rounds"]:
        _add_relationship(result, f"round_run:{item['id']}", "round_belongs_to_extraction", "interview_rounds", item["id"], "extraction_runs", item["run_id"])
    for item in collections["document_chunks"]:
        _add_relationship(result, f"chunk_run:{item['id']}", "chunk_belongs_to_extraction", "document_chunks", item["id"], "extraction_runs", item["run_id"])
        _add_relationship(result, f"chunk_round:{item['id']}", "chunk_belongs_to_round", "document_chunks", item["id"], "interview_rounds", item.get("round_id"))
    for item in collections["chunk_annotations"]:
        _add_relationship(result, f"chunk_annotation:{item['chunk_id']}", "annotation_revises_chunk", "chunk_annotations", item["chunk_id"], "document_chunks", item["chunk_id"])
    for item in collections["question_candidates"]:
        _add_relationship(result, f"candidate_run:{item['id']}", "candidate_belongs_to_extraction", "question_candidates", item["id"], "extraction_runs", item["run_id"])
        _add_relationship(result, f"candidate_chunk:{item['id']}", "candidate_extracted_from_chunk", "question_candidates", item["id"], "document_chunks", item["chunk_id"])
        _add_relationship(result, f"candidate_round:{item['id']}", "candidate_belongs_to_round", "question_candidates", item["id"], "interview_rounds", item.get("round_id"))
    for item in collections["evidence_refs"]:
        _add_relationship(result, f"evidence_run:{item['id']}", "evidence_belongs_to_extraction", "evidence_refs", item["id"], "extraction_runs", item["run_id"])
        _add_relationship(result, f"evidence_chunk:{item['id']}", "evidence_points_to_chunk", "evidence_refs", item["id"], "document_chunks", item["chunk_id"])
        _add_relationship(result, f"evidence_candidate:{item['id']}", "evidence_supports_candidate", "evidence_refs", item["id"], "question_candidates", item.get("candidate_id"))
        _add_relationship(result, f"evidence_document:{item['id']}", "evidence_points_to_document", "evidence_refs", item["id"], "interview_documents", item["document_id"])
        _add_relationship(result, f"evidence_submission:{item['id']}", "evidence_resolves_through_submission", "evidence_refs", item["id"], "interview_submissions", item.get("submission_id"))
        _add_relationship(result, f"evidence_source:{item['id']}", "evidence_resolves_to_source", "evidence_refs", item["id"], "interview_sources", item.get("source_id"))
    for item in collections["question_occurrences"]:
        for target, key, relation_type in [
            ("question_candidates", "candidate_id", "occurrence_comes_from_candidate"),
            ("interview_documents", "document_id", "occurrence_appears_in_document"),
            ("extraction_runs", "run_id", "occurrence_belongs_to_extraction"),
            ("interview_rounds", "round_id", "occurrence_belongs_to_round"),
            ("document_chunks", "chunk_id", "occurrence_comes_from_chunk"),
            ("evidence_refs", "evidence_span_id", "occurrence_has_evidence"),
        ]:
            _add_relationship(result, f"occurrence_{key}:{item['id']}", relation_type, "question_occurrences", item["id"], target, item.get(key))
    for item in collections["question_occurrence_mappings"]:
        _add_relationship(
            result, f"occurrence_mapping:{item['occurrence_id']}", "occurrence_maps_to_canonical_question",
            "question_occurrences", item["occurrence_id"], "canonical_questions", item["canonical_question_id"],
            mapping_origin=item["mapping_origin"], mapping_status=item["mapping_status"], revision=item["revision"],
        )
    for item in collections["question_mapping_revisions"]:
        _add_relationship(result, f"mapping_revision_occurrence:{item['id']}", "mapping_revision_revises_occurrence", "question_mapping_revisions", item["id"], "question_occurrences", item["occurrence_id"])
        _add_relationship(result, f"mapping_revision_from:{item['id']}", "mapping_revision_from_canonical", "question_mapping_revisions", item["id"], "canonical_questions", item.get("from_canonical_question_id"))
        _add_relationship(result, f"mapping_revision_to:{item['id']}", "mapping_revision_to_canonical", "question_mapping_revisions", item["id"], "canonical_questions", item["to_canonical_question_id"])
    for item in collections["knowledge_evidence_links"]:
        _add_relationship(result, item["relation_id"], "knowledge_card_has_evidence", "knowledge_cards", item["card_id"], "evidence_refs", item["evidence_span_id"], note_text=item.get("note_text"))
    for item in collections["algorithm_problems"]:
        _add_relationship(result, f"algorithm_canonical:{item['id']}", "algorithm_problem_links_canonical_question", "algorithm_problems", item["id"], "canonical_questions", item.get("canonical_question_id"), meaning="structured demand reference only")
    for item in collections["project_facts"]:
        _add_relationship(result, f"project_fact_owner:{item['id']}", "project_has_fact", "projects", item["project_id"], "project_facts", item["id"])
    for item in collections["project_expression_versions"]:
        _add_relationship(result, f"project_expression_owner:{item['id']}", "project_has_expression_version", "projects", item["project_id"], "project_expression_versions", item["id"])
        _add_relationship(result, f"project_expression_base:{item['id']}", "expression_based_on_version", "project_expression_versions", item["id"], "project_expression_versions", item.get("based_on_version_id"))
    for item in collections["project_intelligence_links"]:
        _add_relationship(result, f"project_intelligence_owner:{item['id']}", "project_has_intelligence_link", "projects", item["project_id"], "project_intelligence_links", item["id"])
        _add_relationship(result, f"project_intelligence_question:{item['id']}", "project_intelligence_link_targets_question", "project_intelligence_links", item["id"], "canonical_questions", item["canonical_question_id"], occurrence_count=item["occurrence_count"], meaning="demand signal only")
        _add_relationship(result, f"project_intelligence_fact:{item['id']}", "project_intelligence_link_binds_fact", "project_intelligence_links", item["id"], "project_facts", item.get("project_evidence_id"), meaning="does not confirm the fact")
    for item in collections["internship_facts"]:
        _add_relationship(result, f"internship_fact_owner:{item['id']}", "internship_has_fact", "internships", item["internship_id"], "internship_facts", item["id"])
    for item in collections["internship_expression_versions"]:
        _add_relationship(result, f"internship_expression_owner:{item['id']}", "internship_has_expression_version", "internships", item["internship_id"], "internship_expression_versions", item["id"])
        _add_relationship(result, f"internship_expression_base:{item['id']}", "expression_based_on_version", "internship_expression_versions", item["id"], "internship_expression_versions", item.get("based_on_version_id"))
    for item in collections["internship_materials"]:
        _add_relationship(result, f"internship_material_owner:{item['id']}", "internship_has_material", "internships", item["internship_id"], "internship_materials", item["id"])
    for item in collections["internship_intelligence_links"]:
        _add_relationship(result, f"internship_intelligence_owner:{item['id']}", "internship_has_intelligence_link", "internships", item["internship_id"], "internship_intelligence_links", item["id"])
        _add_relationship(result, f"internship_intelligence_question:{item['id']}", "internship_intelligence_link_targets_question", "internship_intelligence_links", item["id"], "canonical_questions", item["canonical_question_id"], occurrence_count=item["occurrence_count"], meaning="demand signal only")
        _add_relationship(result, f"internship_intelligence_fact:{item['id']}", "internship_intelligence_link_binds_fact", "internship_intelligence_links", item["id"], "internship_facts", item.get("internship_fact_id"), meaning="does not confirm the fact")
    return sorted(result, key=lambda item: (item["type"], item["id"]))


def _classification_counts(collections: dict[str, list[dict]]) -> dict:
    facts = Counter(item["boundary_class"] for name in ("project_facts", "internship_facts") for item in collections[name])
    expressions = Counter(item["boundary_class"] for name in ("project_expression_versions", "internship_expression_versions") for item in collections[name])
    materials = Counter(item["preparation_status"] for item in collections["internship_materials"])
    mappings = Counter(item["mapping_status"] for item in collections["question_occurrence_mappings"])
    return {
        "experience_facts": dict(sorted(facts.items())),
        "expression_versions": dict(sorted(expressions.items())),
        "internship_materials": dict(sorted(materials.items())),
        "intelligence_mappings": dict(sorted(mappings.items())),
    }


def _warnings(collections: dict[str, list[dict]]) -> list[dict]:
    warnings = [{
        "code": "NO_EXPLICIT_APPLICATION_TARGET_RELATION",
        "message": "投递与目标画像之间没有持久化关联；导出不会依据公司、岗位或文本相似度猜测关系。",
    }]
    major = {
        "NO_TARGET_PROFILES": "没有目标画像事实。",
        "NO_APPLICATIONS": "没有投递事实。",
        "NO_STRUCTURED_INTELLIGENCE": "没有规范题或 occurrence 结构化情报。",
        "NO_KNOWLEDGE_CARDS": "知识轨道没有用户维护数据。",
        "NO_ALGORITHM_PROBLEMS": "算法轨道没有用户维护数据。",
        "NO_PROJECTS": "项目轨道没有数据。",
        "NO_INTERNSHIPS": "实习轨道没有数据。",
    }
    checks = {
        "NO_TARGET_PROFILES": not collections["target_profiles"],
        "NO_APPLICATIONS": not collections["applications"],
        "NO_STRUCTURED_INTELLIGENCE": not collections["canonical_questions"] and not collections["question_occurrences"],
        "NO_KNOWLEDGE_CARDS": not collections["knowledge_cards"],
        "NO_ALGORITHM_PROBLEMS": not collections["algorithm_problems"],
        "NO_PROJECTS": not collections["projects"],
        "NO_INTERNSHIPS": not collections["internships"],
    }
    warnings.extend({"code": code, "message": major[code]} for code, missing in checks.items() if missing)
    if not collections["evidence_refs"]:
        warnings.append({"code": "NO_EVIDENCE_REFS", "message": "没有可导出的证据引用；不会补写或推断证据。"})
    elif any(not item.get("source_url") for item in collections["evidence_refs"]):
        warnings.append({"code": "EVIDENCE_WITHOUT_SOURCE_URL", "message": "部分证据来自手动正文或缺少来源 URL，仍保留文档、提交、片段和字符区间回链。"})
    return warnings


def _counts(collections: dict[str, list[dict]], relationships: list[dict]) -> dict:
    relationship_types = Counter(item["type"] for item in relationships)
    collection_counts = {name: len(rows) for name, rows in collections.items()}
    return {
        "collections": collection_counts,
        "relationships": dict(sorted(relationship_types.items())),
        "total_records": sum(collection_counts.values()),
        "total_relationships": len(relationships),
        "classifications": _classification_counts(collections),
    }


def _canonical_json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _record_label(record: dict) -> str:
    for key in ("title", "canonical_text", "organization", "label", "company", "extracted_text", "id", "relation_id", "occurrence_id", "chunk_id"):
        if record.get(key):
            return str(record[key]).replace("\n", " ")[:120]
    return "未命名记录"


def _render_markdown(snapshot: dict) -> str:
    lines = [
        "# study_for_job 事实关系快照",
        "",
        f"- Schema：`{snapshot['schema_version']}`",
        f"- Export：`{snapshot['export_version']}`",
        f"- Trigger：`{snapshot['trigger']}`",
        f"- As of date：`{snapshot['as_of_date']}`",
        f"- Fingerprint：`{snapshot['snapshot_fingerprint']}`",
        f"- 记录数：`{snapshot['counts']['total_records']}`",
        f"- 关系数：`{snapshot['counts']['total_relationships']}`",
        "",
        "## 事实边界",
        "",
        "- PostgreSQL 当前业务状态是唯一事实源；此日期是显式声明的快照基准，不构成历史时点重建。",
        "- 投递 `key_date` 保持未标注日期语义，不解释为面试日期。",
        "- confirmed、draft、AI 起草来源、表达版本、材料状态和情报信号通过 `boundary_class`/原始状态分别保留。",
        "- 表达版本即使 confirmed 也不证明客观能力；occurrence、association 和 frequency 仅表示结构化需求信号。",
        f"- 证据片段最多 {EVIDENCE_EXCERPT_LIMIT} 字符；不包含 raw_content 或完整 cleaned_content。",
        "",
        "## Warnings",
        "",
    ]
    lines.extend(f"- **{item['code']}**：{item['message']}" for item in snapshot["warnings"])
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in snapshot["limitations"])
    lines.extend(["", "## 分类计数", "", "```json", json.dumps(snapshot["counts"]["classifications"], ensure_ascii=False, sort_keys=True, indent=2), "```", ""])
    for name, records in snapshot["collections"].items():
        lines.extend([f"## {COLLECTION_LABELS[name]}", "", f"集合：`{name}` · {len(records)} 条", ""])
        if not records:
            lines.extend(["_无数据；未补写或推断。_", ""])
            continue
        for index, record in enumerate(records, 1):
            lines.extend([f"### {index}. {_record_label(record)}", "", "```json", json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2), "```", ""])
    lines.extend(["## 必要关系", "", f"共 {len(snapshot['relationships'])} 条；所有端点使用集合名与稳定业务 ID。", ""])
    if not snapshot["relationships"]:
        lines.extend(["_无可导出的显式关系；未基于文本猜测。_", ""])
    for index, relation in enumerate(snapshot["relationships"], 1):
        lines.extend([f"### {index}. {relation['type']}", "", "```json", json.dumps(relation, ensure_ascii=False, sort_keys=True, indent=2), "```", ""])
    return "\n".join(lines).rstrip() + "\n"


def generate_export(db: Session, *, export_format: str, as_of_date: date) -> dict:
    db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
    collections = _load_collections(db)
    relationships = _build_relationships(db, collections)
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "export_version": EXPORT_VERSION,
        "trigger": "explicit_request",
        "as_of_date": as_of_date.isoformat(),
        "snapshot_scope": "current_postgresql_state_declared_against_explicit_date",
        "fact_boundaries": {
            "source_of_truth": "postgresql_business_facts",
            "application_key_date_semantics": "untyped_key_date",
            "application_target_relation": "not_persisted_not_inferred",
            "intelligence_semantics": "demand_signal_only",
            "expression_semantics": "expression_not_objective_capability_proof",
            "ai_draft_semantics": "origin_retained_confirmation_required",
            "missing_data_semantics": "empty_not_inferred",
            "raw_content_included": False,
            "full_cleaned_content_included": False,
            "evidence_excerpt_max_chars": EVIDENCE_EXCERPT_LIMIT,
        },
        "collections": collections,
        "relationships": relationships,
        "counts": _counts(collections, relationships),
        "warnings": _warnings(collections),
        "limitations": [
            "这是用户显式请求时生成的同步只读快照，不是持久化备份、自动报告或恢复点。",
            "as_of_date 是显式声明基准；当前表没有完整时态历史，因此不能据此重建过去状态。",
            "没有持久化的投递—目标画像关系，导出不会通过文本相似度创建关系。",
            "情报映射、occurrence、association 与频率不证明用户掌握度、经历真实性或客观能力。",
            "项目/实习表达版本与底层事实分离；确认表达只表示表达版本确认。",
            "证据仅包含既有有界片段和引用；缺证据时保持缺失，不读取或扩张为全量面经正文。",
            "T014 assessment 是规则投影，不是本快照的底层事实源，未包含在导出主体中。",
        ],
    }
    fingerprint = hashlib.sha256(_canonical_json(snapshot).encode("utf-8")).hexdigest()
    snapshot["snapshot_fingerprint"] = fingerprint
    extension = "json" if export_format == "json" else "md"
    media_type = "application/json" if export_format == "json" else "text/markdown"
    content = snapshot if export_format == "json" else _render_markdown(snapshot)
    return {
        "format": export_format,
        "file_name": f"study-for-job-facts-{as_of_date.isoformat()}.{extension}",
        "media_type": media_type,
        "manifest": {
            "schema_version": SCHEMA_VERSION,
            "export_version": EXPORT_VERSION,
            "trigger": "explicit_request",
            "as_of_date": as_of_date.isoformat(),
            "snapshot_fingerprint": fingerprint,
            "counts": snapshot["counts"],
            "warnings": snapshot["warnings"],
            "limitations": snapshot["limitations"],
        },
        "content": content,
    }
