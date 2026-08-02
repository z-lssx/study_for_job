from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..intelligence.extraction.repository import ExtractionRepository
from ..models import DocumentChunk, ExtractionChunkAnnotation, ExtractionRun, InterviewDocument, InterviewRound, Job, QuestionCandidate


def serialize_extraction(db: Session, document: InterviewDocument, run: ExtractionRun) -> dict:
    job = db.get(Job, run.job_id) if run.job_id else None
    rounds = list(db.scalars(select(InterviewRound).where(InterviewRound.run_id == run.id).order_by(InterviewRound.ordinal)))
    chunks = list(db.scalars(select(DocumentChunk).where(DocumentChunk.run_id == run.id).order_by(DocumentChunk.ordinal)))
    candidates = list(db.scalars(select(QuestionCandidate).where(QuestionCandidate.run_id == run.id).order_by(QuestionCandidate.start_char, QuestionCandidate.id)))
    annotations = {
        item.chunk_id: item for item in db.scalars(
            select(ExtractionChunkAnnotation).join(DocumentChunk, DocumentChunk.id == ExtractionChunkAnnotation.chunk_id).where(DocumentChunk.run_id == run.id)
        )
    }
    round_labels = {item.id: item.label for item in rounds}
    candidates_by_chunk: dict[UUID, list[QuestionCandidate]] = {}
    for candidate in candidates:
        candidates_by_chunk.setdefault(candidate.chunk_id, []).append(candidate)
    effective_status = {"running": "processing", "retry_wait": "retry_wait", "failed": "failed", "succeeded": "succeeded", "queued": "queued"}.get(
        job.status if job and run.status != "succeeded" else run.status, run.status
    )
    return {
        "id": str(run.id), "document_id": str(run.document_id), "status": effective_status,
        "method": run.extraction_method, "schema_version": run.schema_version, "processor_version": run.processor_version,
        "input_fingerprint": run.input_fingerprint, "trigger_revision": run.trigger_revision,
        "generated_at": run.generated_at.isoformat() if run.generated_at else None,
        "error": {"code": run.error_code, "message": run.error_message} if run.error_code else None,
        "can_retry": effective_status == "failed",
        "rounds": [
            {"id": str(item.id), "ordinal": item.ordinal, "label": item.label, "start_char": item.start_char, "end_char": item.end_char, "validation_status": item.validation_status}
            for item in rounds
        ],
        "chunks": [
            {
                "id": str(item.id), "ordinal": item.ordinal, "round_id": str(item.round_id) if item.round_id else None,
                "round_label": round_labels.get(item.round_id), "block_type": item.block_type,
                "start_char": item.start_char, "end_char": item.end_char,
                "evidence_text": document.cleaned_content[item.start_char:item.end_char],
                "validation_status": item.validation_status,
                "annotation": ({"note_text": annotations[item.id].note_text, "review_status": annotations[item.id].review_status} if item.id in annotations else None),
                "candidates": [
                    {
                        "id": str(candidate.id), "candidate_key": candidate.candidate_key, "field_kind": candidate.field_kind,
                        "text": candidate.extracted_text, "topic_candidate": candidate.topic_candidate,
                        "start_char": candidate.start_char, "end_char": candidate.end_char,
                        "evidence_text": document.cleaned_content[candidate.start_char:candidate.end_char],
                        "validation_status": candidate.validation_status,
                    }
                    for candidate in candidates_by_chunk.get(item.id, [])
                ],
            }
            for item in chunks
        ],
    }
