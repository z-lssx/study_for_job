from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .project_models import Project, ProjectEvidence, ProjectExpressionVersion, ProjectIntelligenceLink


def iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def get_project(db: Session, project_id: UUID, *, lock: bool = False) -> Project:
    statement = select(Project).where(Project.id == project_id)
    if lock:
        statement = statement.with_for_update()
    project = db.scalars(statement).first()
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


def get_owned(db: Session, model, entity_id: UUID, project_id: UUID, detail: str):
    entity = db.get(model, entity_id)
    if entity is None or entity.project_id != project_id:
        raise HTTPException(status_code=404, detail=detail)
    return entity


def touch_project(project: Project) -> None:
    project.updated_at = datetime.now().astimezone()


def serialize_evidence(item: ProjectEvidence) -> dict:
    return {
        "id": str(item.id), "category": item.category, "statement": item.statement,
        "source_kind": item.source_kind, "source_reference": item.source_reference,
        "origin": item.origin, "confirmation_status": item.confirmation_status,
        "created_at": iso(item.created_at), "updated_at": iso(item.updated_at),
    }


def serialize_version(item: ProjectExpressionVersion) -> dict:
    return {
        "id": str(item.id), "version_number": item.version_number, "label": item.label,
        "pitch_30s": item.pitch_30s, "pitch_2m": item.pitch_2m,
        "follow_up_tree": item.follow_up_tree or [], "origin": item.origin,
        "confirmation_status": item.confirmation_status,
        "based_on_version_id": str(item.based_on_version_id) if item.based_on_version_id else None,
        "confirmed_at": iso(item.confirmed_at), "created_at": iso(item.created_at),
        "updated_at": iso(item.updated_at),
    }


def intelligence_links(db: Session, project_id: UUID) -> list[dict]:
    links = db.scalars(
        select(ProjectIntelligenceLink)
        .where(ProjectIntelligenceLink.project_id == project_id)
        .order_by(ProjectIntelligenceLink.created_at.desc())
    )
    result = []
    for link in links:
        canonical = db.execute(
            text("""
                SELECT cq.canonical_text, COUNT(qom.occurrence_id)::int AS occurrence_count
                FROM canonical_questions cq
                LEFT JOIN question_occurrence_mappings qom ON qom.canonical_question_id = cq.id
                WHERE cq.id = :id GROUP BY cq.id, cq.canonical_text
            """), {"id": link.canonical_question_id},
        ).mappings().first()
        occurrences = db.execute(
            text("""
                SELECT qo.id, qo.round_ordinal, qo.field_kind, es.start_char, es.end_char,
                       d.id AS document_id, s.id AS submission_id, src.source_url,
                       SUBSTRING(d.cleaned_content FROM es.start_char + 1 FOR es.end_char - es.start_char) AS quote
                FROM question_occurrence_mappings qom
                JOIN question_occurrences qo ON qo.id = qom.occurrence_id
                JOIN evidence_spans es ON es.id = qo.evidence_span_id
                JOIN interview_documents d ON d.id = qo.document_id
                LEFT JOIN LATERAL (
                  SELECT candidate.* FROM interview_submissions candidate
                  WHERE candidate.document_id = d.id ORDER BY candidate.submitted_at DESC LIMIT 1
                ) s ON TRUE
                LEFT JOIN interview_sources src ON src.id = s.source_id
                WHERE qom.canonical_question_id = :id
                ORDER BY qo.created_at DESC LIMIT 3
            """), {"id": link.canonical_question_id},
        ).mappings().all()
        linked_evidence = db.get(ProjectEvidence, link.project_evidence_id) if link.project_evidence_id else None
        result.append({
            "id": str(link.id), "canonical_question_id": str(link.canonical_question_id),
            "canonical_text": canonical["canonical_text"] if canonical else None,
            "occurrence_count": canonical["occurrence_count"] if canonical else 0,
            "frequency_is_reference_only": True, "relevance_note": link.relevance_note,
            "project_evidence": serialize_evidence(linked_evidence) if linked_evidence else None,
            "occurrence_evidence": [{
                "occurrence_id": str(row["id"]), "round_ordinal": row["round_ordinal"],
                "field_kind": row["field_kind"], "quote": row["quote"],
                "start_char": row["start_char"], "end_char": row["end_char"],
                "document_id": str(row["document_id"]),
                "submission_id": str(row["submission_id"]) if row["submission_id"] else None,
                "source_url": row["source_url"],
            } for row in occurrences],
            "created_at": iso(link.created_at),
        })
    return result


def serialize_project(db: Session, project: Project) -> dict:
    evidence = db.scalars(
        select(ProjectEvidence).where(ProjectEvidence.project_id == project.id)
        .order_by(ProjectEvidence.updated_at.desc())
    )
    versions = db.scalars(
        select(ProjectExpressionVersion).where(ProjectExpressionVersion.project_id == project.id)
        .order_by(ProjectExpressionVersion.version_number.desc())
    )
    return {
        "id": str(project.id), "title": project.title, "target_role": project.target_role,
        "summary": project.summary, "status": project.status,
        "created_at": iso(project.created_at), "updated_at": iso(project.updated_at),
        "evidence": [serialize_evidence(item) for item in evidence],
        "versions": [serialize_version(item) for item in versions],
        "intelligence_links": intelligence_links(db, project.id),
    }
