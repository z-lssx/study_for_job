from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .internship_models import (
    Internship,
    InternshipExpressionVersion,
    InternshipFact,
    InternshipIntelligenceLink,
    InternshipMaterial,
)


def iso(value) -> str | None:
    return value.isoformat() if value else None


def get_internship(db: Session, internship_id: UUID, *, lock: bool = False) -> Internship:
    statement = select(Internship).where(Internship.id == internship_id)
    if lock:
        statement = statement.with_for_update()
    internship = db.scalars(statement).first()
    if internship is None:
        raise HTTPException(status_code=404, detail="实习经历不存在")
    return internship


def get_owned(db: Session, model, entity_id: UUID, internship_id: UUID, detail: str):
    entity = db.get(model, entity_id)
    if entity is None or entity.internship_id != internship_id:
        raise HTTPException(status_code=404, detail=detail)
    return entity


def touch(internship: Internship) -> None:
    internship.updated_at = datetime.now().astimezone()


def serialize_fact(item: InternshipFact) -> dict:
    return {
        "id": str(item.id), "category": item.category, "statement": item.statement,
        "source_kind": item.source_kind, "source_reference": item.source_reference,
        "origin": item.origin, "confirmation_status": item.confirmation_status,
        "created_at": iso(item.created_at), "updated_at": iso(item.updated_at),
    }


def serialize_version(item: InternshipExpressionVersion) -> dict:
    return {
        "id": str(item.id), "version_number": item.version_number, "label": item.label,
        "situation": item.situation, "task": item.task, "action": item.action,
        "result": item.result, "quantified_pitch": item.quantified_pitch,
        "follow_up_tree": item.follow_up_tree or [], "origin": item.origin,
        "confirmation_status": item.confirmation_status,
        "based_on_version_id": str(item.based_on_version_id) if item.based_on_version_id else None,
        "confirmed_at": iso(item.confirmed_at), "created_at": iso(item.created_at),
        "updated_at": iso(item.updated_at),
    }


def serialize_material(item: InternshipMaterial) -> dict:
    return {
        "id": str(item.id), "material_type": item.material_type, "label": item.label,
        "locator": item.locator, "notes": item.notes, "preparation_status": item.preparation_status,
        "created_at": iso(item.created_at), "updated_at": iso(item.updated_at),
    }


def intelligence_links(db: Session, internship_id: UUID) -> list[dict]:
    links = db.scalars(
        select(InternshipIntelligenceLink)
        .where(InternshipIntelligenceLink.internship_id == internship_id)
        .order_by(InternshipIntelligenceLink.created_at.desc())
    )
    result = []
    for link in links:
        canonical = db.execute(text("""
            SELECT cq.canonical_text, COUNT(qom.occurrence_id)::int AS occurrence_count
            FROM canonical_questions cq
            LEFT JOIN question_occurrence_mappings qom ON qom.canonical_question_id = cq.id
            WHERE cq.id = :id GROUP BY cq.id, cq.canonical_text
        """), {"id": link.canonical_question_id}).mappings().first()
        occurrences = db.execute(text("""
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
        """), {"id": link.canonical_question_id}).mappings().all()
        linked_fact = db.get(InternshipFact, link.internship_fact_id) if link.internship_fact_id else None
        result.append({
            "id": str(link.id), "canonical_question_id": str(link.canonical_question_id),
            "canonical_text": canonical["canonical_text"] if canonical else None,
            "occurrence_count": canonical["occurrence_count"] if canonical else 0,
            "frequency_is_reference_only": True, "relevance_note": link.relevance_note,
            "internship_fact": serialize_fact(linked_fact) if linked_fact else None,
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


def serialize_internship(db: Session, internship: Internship) -> dict:
    facts = db.scalars(select(InternshipFact).where(InternshipFact.internship_id == internship.id).order_by(InternshipFact.updated_at.desc()))
    versions = db.scalars(select(InternshipExpressionVersion).where(InternshipExpressionVersion.internship_id == internship.id).order_by(InternshipExpressionVersion.version_number.desc()))
    materials = db.scalars(select(InternshipMaterial).where(InternshipMaterial.internship_id == internship.id).order_by(InternshipMaterial.updated_at.desc()))
    return {
        "id": str(internship.id), "organization": internship.organization,
        "role_title": internship.role_title, "started_on": iso(internship.started_on),
        "ended_on": iso(internship.ended_on), "summary": internship.summary,
        "status": internship.status, "created_at": iso(internship.created_at),
        "updated_at": iso(internship.updated_at),
        "facts": [serialize_fact(item) for item in facts],
        "versions": [serialize_version(item) for item in versions],
        "materials": [serialize_material(item) for item in materials],
        "intelligence_links": intelligence_links(db, internship.id),
    }
