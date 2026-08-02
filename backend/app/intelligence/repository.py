from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from ..db import SessionLocal
from ..models import (
    InterviewDocument,
    InterviewDocumentSource,
    InterviewSource,
    InterviewSubmission,
    Job,
)
from .content import CLEANING_VERSION, content_hash, normalize_plain_text, validate_manual_content
from .errors import InvalidSubmissionAction, SubmissionNotFound
from .sources import SourceAddress, url_fingerprint

INGEST_JOB_TYPE = "interview.ingest"
INGEST_MAX_ATTEMPTS = 3


@dataclass(frozen=True)
class SubmissionCreateResult:
    submission_id: UUID
    created: bool
    duplicate_reason: str | None


@dataclass(frozen=True)
class SubmissionBundle:
    submission: InterviewSubmission
    source: InterviewSource | None
    document: InterviewDocument | None
    job: Job | None


@dataclass(frozen=True)
class SubmissionSnapshot:
    id: UUID
    current_job_id: UUID
    current_method: str
    source_id: UUID | None
    normalized_url: str | None
    raw_content: str | None
    raw_content_type: str | None
    input_fingerprint: str
    revision: int
    document_id: UUID | None


class IntelligenceRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session] = SessionLocal,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def submit_url(self, session: Session, address: SourceAddress) -> SubmissionCreateResult:
        now = self.clock()
        source_id = session.execute(
            insert(InterviewSource)
            .values(
                source_url=address.source_url,
                normalized_url=address.normalized_url,
                host=address.host,
                first_submitted_at=now,
                last_submitted_at=now,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_update(
                index_elements=[InterviewSource.normalized_url],
                set_={"last_submitted_at": now, "updated_at": now},
            )
            .returning(InterviewSource.id)
        ).scalar_one()
        fingerprint = url_fingerprint(address.normalized_url)
        submission_id = session.execute(
            insert(InterviewSubmission)
            .values(
                initial_method="url",
                current_method="url_fetch",
                source_id=source_id,
                input_fingerprint=fingerprint,
                revision=1,
                submitted_at=now,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_nothing(
                index_elements=[InterviewSubmission.source_id],
                index_where=InterviewSubmission.source_id.is_not(None),
            )
            .returning(InterviewSubmission.id)
        ).scalar_one_or_none()
        if submission_id is None:
            existing = session.scalar(select(InterviewSubmission).where(InterviewSubmission.source_id == source_id))
            if existing is None:
                raise RuntimeError("URL submission conflict did not resolve to an existing fact")
            return SubmissionCreateResult(existing.id, False, "normalized_url")
        submission = session.get(InterviewSubmission, submission_id)
        self._enqueue(session, submission, now)
        return SubmissionCreateResult(submission_id, True, None)

    def submit_content(self, session: Session, raw_content: str) -> SubmissionCreateResult:
        _cleaned, fingerprint = validate_manual_content(raw_content)
        now = self.clock()
        submission_id = session.execute(
            insert(InterviewSubmission)
            .values(
                initial_method="manual_text",
                current_method="manual_text",
                raw_content=raw_content.strip(),
                raw_content_type="text/plain",
                input_fingerprint=fingerprint,
                revision=1,
                submitted_at=now,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_nothing(
                index_elements=[InterviewSubmission.input_fingerprint],
                index_where=text("initial_method = 'manual_text'"),
            )
            .returning(InterviewSubmission.id)
        ).scalar_one_or_none()
        if submission_id is None:
            existing = session.scalar(
                select(InterviewSubmission).where(
                    InterviewSubmission.initial_method == "manual_text",
                    InterviewSubmission.input_fingerprint == fingerprint,
                )
            )
            if existing is None:
                raise RuntimeError("Manual submission conflict did not resolve to an existing fact")
            return SubmissionCreateResult(existing.id, False, "content_hash")
        submission = session.get(InterviewSubmission, submission_id)
        self._enqueue(session, submission, now)
        return SubmissionCreateResult(submission_id, True, None)

    def supplement(self, session: Session, submission_id: UUID, raw_content: str) -> SubmissionCreateResult:
        _cleaned, fingerprint = validate_manual_content(raw_content)
        now = self.clock()
        submission = session.scalar(
            select(InterviewSubmission).where(InterviewSubmission.id == submission_id).with_for_update()
        )
        if submission is None:
            raise SubmissionNotFound()
        job = session.get(Job, submission.current_job_id) if submission.current_job_id else None
        if submission.document_id is not None:
            raise InvalidSubmissionAction("successful_content_immutable", "已成功入库的原文不会被补正文覆盖", False)
        if job is None or job.status != "failed":
            raise InvalidSubmissionAction("submission_not_failed", "仅处理失败的面经可以补充正文", False)
        submission.current_method = "manual_fallback" if submission.source_id else "manual_text"
        submission.raw_content = raw_content.strip()
        submission.raw_content_type = "text/plain"
        submission.input_fingerprint = fingerprint
        submission.revision += 1
        submission.last_error_code = None
        submission.last_error_message = None
        submission.last_error_retryable = None
        submission.processing_started_at = None
        submission.updated_at = now
        self._enqueue(session, submission, now)
        return SubmissionCreateResult(submission.id, True, None)

    def retry(self, session: Session, submission_id: UUID) -> SubmissionCreateResult:
        now = self.clock()
        submission = session.scalar(
            select(InterviewSubmission).where(InterviewSubmission.id == submission_id).with_for_update()
        )
        if submission is None:
            raise SubmissionNotFound()
        job = session.get(Job, submission.current_job_id) if submission.current_job_id else None
        if submission.document_id is not None:
            raise InvalidSubmissionAction("already_succeeded", "该面经已成功入库，无需重新处理", False)
        if job is None or job.status != "failed":
            raise InvalidSubmissionAction("submission_not_failed", "仅处理失败的面经可以重新触发", False)
        if submission.last_error_retryable is False:
            raise InvalidSubmissionAction("failure_not_retryable", "该失败不能通过重试恢复，请补充正文", False)
        submission.revision += 1
        submission.last_error_code = None
        submission.last_error_message = None
        submission.last_error_retryable = None
        submission.processing_started_at = None
        submission.updated_at = now
        self._enqueue(session, submission, now)
        return SubmissionCreateResult(submission.id, True, None)

    @staticmethod
    def list_bundles(session: Session, limit: int = 100) -> list[SubmissionBundle]:
        statement = (
            select(InterviewSubmission, InterviewSource, InterviewDocument, Job)
            .outerjoin(InterviewSource, InterviewSource.id == InterviewSubmission.source_id)
            .outerjoin(InterviewDocument, InterviewDocument.id == InterviewSubmission.document_id)
            .outerjoin(Job, Job.id == InterviewSubmission.current_job_id)
            .order_by(InterviewSubmission.updated_at.desc(), InterviewSubmission.id.desc())
            .limit(limit)
        )
        return [SubmissionBundle(*row) for row in session.execute(statement).all()]

    @staticmethod
    def get_bundle(session: Session, submission_id: UUID) -> SubmissionBundle | None:
        statement = (
            select(InterviewSubmission, InterviewSource, InterviewDocument, Job)
            .outerjoin(InterviewSource, InterviewSource.id == InterviewSubmission.source_id)
            .outerjoin(InterviewDocument, InterviewDocument.id == InterviewSubmission.document_id)
            .outerjoin(Job, Job.id == InterviewSubmission.current_job_id)
            .where(InterviewSubmission.id == submission_id)
        )
        row = session.execute(statement).one_or_none()
        return SubmissionBundle(*row) if row else None

    def load_snapshot(self, submission_id: UUID) -> SubmissionSnapshot | None:
        with self.session_factory() as session:
            statement = (
                select(InterviewSubmission, InterviewSource)
                .outerjoin(InterviewSource, InterviewSource.id == InterviewSubmission.source_id)
                .where(InterviewSubmission.id == submission_id)
            )
            row = session.execute(statement).one_or_none()
            if row is None:
                return None
            submission, source = row
            if submission.current_job_id is None:
                return None
            return SubmissionSnapshot(
                id=submission.id,
                current_job_id=submission.current_job_id,
                current_method=submission.current_method,
                source_id=submission.source_id,
                normalized_url=source.normalized_url if source else None,
                raw_content=submission.raw_content,
                raw_content_type=submission.raw_content_type,
                input_fingerprint=submission.input_fingerprint,
                revision=submission.revision,
                document_id=submission.document_id,
            )

    def mark_processing(self, snapshot: SubmissionSnapshot) -> bool:
        now = self.clock()
        with self.session_factory.begin() as session:
            result = session.execute(
                update(InterviewSubmission)
                .where(
                    InterviewSubmission.id == snapshot.id,
                    InterviewSubmission.current_job_id == snapshot.current_job_id,
                    InterviewSubmission.revision == snapshot.revision,
                    InterviewSubmission.input_fingerprint == snapshot.input_fingerprint,
                    InterviewSubmission.document_id.is_(None),
                )
                .values(processing_started_at=now, updated_at=now)
            )
            return result.rowcount == 1

    def complete(
        self,
        snapshot: SubmissionSnapshot,
        raw_content: str,
        raw_content_type: str,
        cleaned_content: str,
        title: str | None,
    ) -> tuple[UUID, bool]:
        now = self.clock()
        digest = content_hash(cleaned_content)
        with self.session_factory.begin() as session:
            submission = session.scalar(
                select(InterviewSubmission)
                .where(InterviewSubmission.id == snapshot.id)
                .with_for_update()
            )
            if submission is None:
                raise SubmissionNotFound()
            if submission.document_id is not None:
                return submission.document_id, True
            if (
                submission.current_job_id != snapshot.current_job_id
                or submission.revision != snapshot.revision
                or submission.input_fingerprint != snapshot.input_fingerprint
            ):
                raise InvalidSubmissionAction(
                    "input_snapshot_drift",
                    "任务输入快照已经变化，已拒绝旧结果",
                    False,
                )
            document_id = session.execute(
                insert(InterviewDocument)
                .values(
                    content_hash=digest,
                    title=title,
                    raw_content=raw_content,
                    raw_content_type=raw_content_type,
                    cleaned_content=cleaned_content,
                    cleaning_version=CLEANING_VERSION,
                    acquisition_method=snapshot.current_method,
                    first_source_id=snapshot.source_id,
                    collected_at=now,
                    created_at=now,
                    updated_at=now,
                )
                .on_conflict_do_nothing(index_elements=[InterviewDocument.content_hash])
                .returning(InterviewDocument.id)
            ).scalar_one_or_none()
            deduplicated = document_id is None
            if document_id is None:
                document_id = session.scalar(
                    select(InterviewDocument.id).where(InterviewDocument.content_hash == digest)
                )
            if document_id is None:
                raise RuntimeError("Document upsert did not resolve a content fact")
            if snapshot.source_id is not None:
                session.execute(
                    insert(InterviewDocumentSource)
                    .values(
                        document_id=document_id,
                        source_id=snapshot.source_id,
                        first_submission_id=snapshot.id,
                        linked_at=now,
                    )
                    .on_conflict_do_nothing(
                        index_elements=[InterviewDocumentSource.document_id, InterviewDocumentSource.source_id]
                    )
                )
            submission.document_id = document_id
            submission.raw_content = raw_content
            submission.raw_content_type = raw_content_type
            submission.last_error_code = None
            submission.last_error_message = None
            submission.last_error_retryable = None
            submission.completed_at = now
            submission.updated_at = now
            return document_id, deduplicated

    def record_failure(self, snapshot: SubmissionSnapshot, code: str, message: str, retryable: bool) -> None:
        now = self.clock()
        with self.session_factory.begin() as session:
            session.execute(
                update(InterviewSubmission)
                .where(
                    InterviewSubmission.id == snapshot.id,
                    InterviewSubmission.current_job_id == snapshot.current_job_id,
                    InterviewSubmission.revision == snapshot.revision,
                    InterviewSubmission.input_fingerprint == snapshot.input_fingerprint,
                    InterviewSubmission.document_id.is_(None),
                )
                .values(
                    last_error_code=code[:120],
                    last_error_message=message[:1000],
                    last_error_retryable=retryable,
                    updated_at=now,
                )
            )

    @staticmethod
    def _enqueue(session: Session, submission: InterviewSubmission, now: datetime) -> Job:
        payload = {
            "submission_id": str(submission.id),
            "revision": submission.revision,
            "input_fingerprint": submission.input_fingerprint,
        }
        job = Job(
            job_type=INGEST_JOB_TYPE,
            status="queued",
            payload=payload,
            priority=0,
            attempt_count=0,
            max_attempts=INGEST_MAX_ATTEMPTS,
            next_run_at=now,
            idempotency_key=f"interview.ingest:{submission.id}:r{submission.revision}",
            created_at=now,
            updated_at=now,
        )
        session.add(job)
        session.flush()
        submission.current_job_id = job.id
        return job


def manual_title(cleaned_content: str) -> str | None:
    first_line = normalize_plain_text(cleaned_content).split("\n", 1)[0].strip()
    return first_line[:300] or None
