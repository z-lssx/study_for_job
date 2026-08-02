from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from ...db import SessionLocal
from ...models import (
    DocumentChunk,
    EvidenceSpan,
    ExtractionChunkAnnotation,
    ExtractionRun,
    InterviewDocument,
    InterviewRound,
    Job,
    QuestionCandidate,
)
from .extractor import PROCESSOR_VERSION, SCHEMA_VERSION, ExtractionResult, input_fingerprint

EXTRACTION_JOB_TYPE = "interview.extract"
EXTRACTION_MAX_ATTEMPTS = 3


@dataclass(frozen=True)
class ExtractionSnapshot:
    run_id: UUID
    document_id: UUID
    job_id: UUID
    input_fingerprint: str
    trigger_revision: int
    content_hash: str
    cleaning_version: str
    cleaned_content: str


class ExtractionRepository:
    def __init__(self, session_factory: sessionmaker[Session] = SessionLocal) -> None:
        self.session_factory = session_factory

    @staticmethod
    def latest(session: Session, document_id: UUID) -> ExtractionRun | None:
        return session.scalar(
            select(ExtractionRun).where(ExtractionRun.document_id == document_id).order_by(ExtractionRun.created_at.desc(), ExtractionRun.id.desc()).limit(1)
        )

    @staticmethod
    def chunk_for_document(session: Session, chunk_id: UUID, document_id: UUID | None) -> DocumentChunk | None:
        if document_id is None:
            return None
        return session.scalar(
            select(DocumentChunk).join(ExtractionRun, ExtractionRun.id == DocumentChunk.run_id).where(DocumentChunk.id == chunk_id, ExtractionRun.document_id == document_id)
        )

    @staticmethod
    def trigger(session: Session, document_id: UUID) -> tuple[ExtractionRun, bool]:
        document = session.get(InterviewDocument, document_id)
        if document is None:
            raise LookupError("document_not_found")
        fingerprint = input_fingerprint(document.content_hash, document.cleaning_version)
        now = datetime.now(timezone.utc)
        run_id = session.execute(
            insert(ExtractionRun)
            .values(
                document_id=document.id,
                input_fingerprint=fingerprint,
                extraction_method="deterministic",
                schema_version=SCHEMA_VERSION,
                processor_version=PROCESSOR_VERSION,
                status="queued",
                trigger_revision=1,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_nothing(index_elements=[ExtractionRun.document_id, ExtractionRun.input_fingerprint])
            .returning(ExtractionRun.id)
        ).scalar_one_or_none()
        created = run_id is not None
        if run_id is None:
            run = session.scalar(
                select(ExtractionRun)
                .where(ExtractionRun.document_id == document.id, ExtractionRun.input_fingerprint == fingerprint)
                .with_for_update()
            )
            if run is None:
                raise RuntimeError("extraction run conflict did not resolve")
            if run.status in {"queued", "running", "succeeded"}:
                return run, False
            run.trigger_revision += 1
            run.status = "queued"
            run.error_code = None
            run.error_message = None
            run.started_at = None
            run.generated_at = None
            run.updated_at = now
        else:
            run = session.get(ExtractionRun, run_id)
        ExtractionRepository._enqueue(session, run, now)
        return run, created

    @staticmethod
    def _enqueue(session: Session, run: ExtractionRun, now: datetime) -> None:
        job = Job(
            job_type=EXTRACTION_JOB_TYPE,
            status="queued",
            payload={
                "run_id": str(run.id),
                "document_id": str(run.document_id),
                "input_fingerprint": run.input_fingerprint,
                "trigger_revision": run.trigger_revision,
            },
            priority=0,
            attempt_count=0,
            max_attempts=EXTRACTION_MAX_ATTEMPTS,
            next_run_at=now,
            idempotency_key=f"interview.extract:{run.id}:r{run.trigger_revision}",
            created_at=now,
            updated_at=now,
        )
        session.add(job)
        session.flush()
        run.job_id = job.id

    def load_snapshot(self, run_id: UUID) -> ExtractionSnapshot | None:
        with self.session_factory() as session:
            row = session.execute(
                select(ExtractionRun, InterviewDocument)
                .join(InterviewDocument, InterviewDocument.id == ExtractionRun.document_id)
                .where(ExtractionRun.id == run_id)
            ).one_or_none()
            if row is None or row[0].job_id is None:
                return None
            run, document = row
            return ExtractionSnapshot(
                run_id=run.id,
                document_id=document.id,
                job_id=run.job_id,
                input_fingerprint=run.input_fingerprint,
                trigger_revision=run.trigger_revision,
                content_hash=document.content_hash,
                cleaning_version=document.cleaning_version,
                cleaned_content=document.cleaned_content,
            )

    def mark_running(self, snapshot: ExtractionSnapshot) -> str:
        now = datetime.now(timezone.utc)
        with self.session_factory.begin() as session:
            run = session.scalar(select(ExtractionRun).where(ExtractionRun.id == snapshot.run_id).with_for_update())
            if run is None:
                return "missing"
            if run.status == "succeeded":
                return "succeeded"
            if not self._matches(run, snapshot):
                return "drift"
            run.status = "running"
            run.started_at = now
            run.error_code = None
            run.error_message = None
            run.updated_at = now
            return "running"

    def complete(self, snapshot: ExtractionSnapshot, result: ExtractionResult) -> dict:
        now = datetime.now(timezone.utc)
        with self.session_factory.begin() as session:
            run = session.scalar(select(ExtractionRun).where(ExtractionRun.id == snapshot.run_id).with_for_update())
            if run is None or not self._matches(run, snapshot):
                raise RuntimeError("extraction_snapshot_drift")
            if run.status == "succeeded":
                return self._counts(session, run.id) | {"replayed": True}

            session.execute(delete(EvidenceSpan).where(EvidenceSpan.run_id == run.id))
            session.execute(delete(QuestionCandidate).where(QuestionCandidate.run_id == run.id))
            session.execute(delete(DocumentChunk).where(DocumentChunk.run_id == run.id))
            session.execute(delete(InterviewRound).where(InterviewRound.run_id == run.id))

            round_ids: dict[int, UUID] = {}
            for mark in result.rounds:
                row = InterviewRound(id=uuid4(), run_id=run.id, ordinal=mark.ordinal, label=mark.label, start_char=mark.start_char, end_char=mark.end_char)
                session.add(row)
                round_ids[mark.ordinal] = row.id
            session.flush()

            chunk_ids: dict[int, UUID] = {}
            chunks: dict[int, DocumentChunk] = {}
            for mark in result.chunks:
                row = DocumentChunk(
                    id=uuid4(),
                    run_id=run.id,
                    round_id=round_ids.get(mark.round_ordinal),
                    ordinal=mark.ordinal,
                    block_type=mark.block_type,
                    start_char=mark.start_char,
                    end_char=mark.end_char,
                    validation_status="needs_review" if mark.block_type == "unknown" else "pending_review",
                )
                session.add(row)
                chunk_ids[mark.ordinal] = row.id
                chunks[mark.ordinal] = row
            session.flush()

            for mark in result.chunks:
                chunk_id = chunk_ids[mark.ordinal]
                quote = snapshot.cleaned_content[mark.start_char:mark.end_char]
                session.add(EvidenceSpan(
                    run_id=run.id,
                    chunk_id=chunk_id,
                    candidate_id=None,
                    field_name="content_block",
                    start_char=mark.start_char,
                    end_char=mark.end_char,
                    quote_hash=hashlib.sha256(quote.encode("utf-8")).hexdigest(),
                ))

            for mark in result.candidates:
                candidate = QuestionCandidate(
                    id=uuid4(),
                    run_id=run.id,
                    chunk_id=chunk_ids[mark.chunk_ordinal],
                    round_id=round_ids.get(mark.round_ordinal),
                    candidate_key=mark.candidate_key,
                    field_kind=mark.field_kind,
                    extracted_text=mark.extracted_text,
                    topic_candidate=mark.topic_candidate,
                    start_char=mark.start_char,
                    end_char=mark.end_char,
                )
                session.add(candidate)
                session.flush()
                quote = snapshot.cleaned_content[mark.start_char:mark.end_char]
                session.add(EvidenceSpan(
                    run_id=run.id,
                    chunk_id=candidate.chunk_id,
                    candidate_id=candidate.id,
                    field_name="follow_up_text" if mark.field_kind == "follow_up" else "question_text",
                    start_char=mark.start_char,
                    end_char=mark.end_char,
                    quote_hash=hashlib.sha256(quote.encode("utf-8")).hexdigest(),
                ))

            run.status = "succeeded"
            run.generated_at = now
            run.error_code = None
            run.error_message = None
            run.updated_at = now
            session.flush()
            return self._counts(session, run.id) | {"replayed": False}

    def fail(self, snapshot: ExtractionSnapshot, code: str, message: str) -> None:
        now = datetime.now(timezone.utc)
        with self.session_factory.begin() as session:
            session.execute(
                update(ExtractionRun)
                .where(
                    ExtractionRun.id == snapshot.run_id,
                    ExtractionRun.job_id == snapshot.job_id,
                    ExtractionRun.input_fingerprint == snapshot.input_fingerprint,
                    ExtractionRun.trigger_revision == snapshot.trigger_revision,
                    ExtractionRun.status != "succeeded",
                )
                .values(status="failed", error_code=code[:120], error_message=message[:1000], generated_at=None, updated_at=now)
            )

    @staticmethod
    def save_annotation(session: Session, chunk_id: UUID, note_text: str | None, review_status: str) -> ExtractionChunkAnnotation:
        chunk = session.get(DocumentChunk, chunk_id)
        if chunk is None:
            raise LookupError("chunk_not_found")
        now = datetime.now(timezone.utc)
        session.execute(
            insert(ExtractionChunkAnnotation)
            .values(chunk_id=chunk_id, note_text=note_text, review_status=review_status, created_at=now, updated_at=now)
            .on_conflict_do_update(index_elements=[ExtractionChunkAnnotation.chunk_id], set_={"note_text": note_text, "review_status": review_status, "updated_at": now})
        )
        session.flush()
        return session.get(ExtractionChunkAnnotation, chunk_id)

    @staticmethod
    def _matches(run: ExtractionRun, snapshot: ExtractionSnapshot) -> bool:
        return (
            run.document_id == snapshot.document_id
            and run.job_id == snapshot.job_id
            and run.input_fingerprint == snapshot.input_fingerprint
            and run.trigger_revision == snapshot.trigger_revision
        )

    @staticmethod
    def _counts(session: Session, run_id: UUID) -> dict:
        return {
            "round_count": session.scalar(select(func.count()).select_from(InterviewRound).where(InterviewRound.run_id == run_id)) or 0,
            "chunk_count": session.scalar(select(func.count()).select_from(DocumentChunk).where(DocumentChunk.run_id == run_id)) or 0,
            "candidate_count": session.scalar(select(func.count()).select_from(QuestionCandidate).where(QuestionCandidate.run_id == run_id)) or 0,
        }
