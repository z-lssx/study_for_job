from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import case, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from ..db import SessionLocal
from ..models import Job, JobAttempt
from .contracts import ClaimedJob
from .errors import IdempotencyConflict, InvalidManualRetry, JobNotFound


class JobRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session] = SessionLocal,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def create(
        self,
        job_type: str,
        payload: dict,
        priority: int,
        max_attempts: int,
        idempotency_key: str | None,
    ) -> tuple[Job, bool]:
        now = self.clock()
        values = {
            "job_type": job_type,
            "status": "queued",
            "payload": payload,
            "priority": priority,
            "attempt_count": 0,
            "max_attempts": max_attempts,
            "next_run_at": now,
            "idempotency_key": idempotency_key,
            "created_at": now,
            "updated_at": now,
        }
        with self.session_factory.begin() as session:
            statement = insert(Job).values(**values)
            if idempotency_key is not None:
                statement = statement.on_conflict_do_nothing(
                    index_elements=[Job.job_type, Job.idempotency_key],
                    index_where=Job.idempotency_key.is_not(None),
                )
            job_id = session.execute(statement.returning(Job.id)).scalar_one_or_none()
            if job_id is not None:
                job = session.get(Job, job_id)
                return job, True

            existing = session.scalar(
                select(Job).where(Job.job_type == job_type, Job.idempotency_key == idempotency_key)
            )
            if existing is None:
                raise RuntimeError("Idempotent insert did not return or find a job")
            if (
                dict(existing.payload) != payload
                or existing.priority != priority
                or existing.max_attempts != max_attempts
            ):
                raise IdempotencyConflict("同一幂等键已用于不同的任务参数")
            return existing, False

    def list(self, limit: int, status: str | None = None) -> list[Job]:
        statement = select(Job)
        if status:
            statement = statement.where(Job.status == status)
        statement = statement.order_by(Job.created_at.desc(), Job.id.desc()).limit(limit)
        with self.session_factory() as session:
            return list(session.scalars(statement))

    def get(self, job_id: UUID) -> Job | None:
        with self.session_factory() as session:
            return session.get(Job, job_id)

    def attempts(self, job_id: UUID) -> list[JobAttempt]:
        statement = (
            select(JobAttempt)
            .where(JobAttempt.job_id == job_id)
            .order_by(JobAttempt.attempt_number, JobAttempt.created_at)
        )
        with self.session_factory() as session:
            return list(session.scalars(statement))

    def claim(self, worker_id: str, lease_seconds: int) -> ClaimedJob | None:
        while True:
            terminalized = False
            with self.session_factory.begin() as session:
                now = self.clock()
                due_time = case(
                    (Job.status == "running", Job.lease_expires_at),
                    else_=Job.next_run_at,
                )
                statement = (
                    select(Job)
                    .where(
                        or_(
                            (Job.status.in_(("queued", "retry_wait"))) & (Job.next_run_at <= now),
                            (Job.status == "running") & (Job.lease_expires_at <= now),
                        )
                    )
                    .order_by(Job.priority.desc(), due_time, Job.created_at, Job.id)
                    .with_for_update(skip_locked=True)
                    .limit(1)
                )
                job = session.scalar(statement)
                if job is None:
                    return None

                if job.status == "running":
                    self._mark_expired_attempt(session, job, now)
                if job.attempt_count >= job.max_attempts:
                    self._terminalize_exhausted(job, now)
                    terminalized = True
                else:
                    lease_token = uuid4()
                    job.status = "running"
                    job.attempt_count += 1
                    job.next_run_at = None
                    job.claimed_by = worker_id
                    job.lease_token = lease_token
                    job.lease_expires_at = now + timedelta(seconds=lease_seconds)
                    job.started_at = now
                    job.completed_at = None
                    job.updated_at = now
                    session.add(JobAttempt(
                        job_id=job.id,
                        attempt_number=job.attempt_count,
                        worker_id=worker_id,
                        lease_token=lease_token,
                        status="running",
                        started_at=now,
                        created_at=now,
                    ))
                    session.flush()
                    claimed = ClaimedJob(
                        id=job.id,
                        job_type=job.job_type,
                        payload=dict(job.payload),
                        attempt_number=job.attempt_count,
                        max_attempts=job.max_attempts,
                        lease_token=lease_token,
                    )
            if not terminalized:
                return claimed

    def renew_lease(self, job_id: UUID, lease_token: UUID, lease_seconds: int) -> bool:
        now = self.clock()
        with self.session_factory.begin() as session:
            result = session.execute(
                update(Job)
                .where(Job.id == job_id, Job.status == "running", Job.lease_token == lease_token)
                .values(lease_expires_at=now + timedelta(seconds=lease_seconds), updated_at=now)
            )
            return result.rowcount == 1

    def succeed(self, claimed: ClaimedJob, result_summary: dict) -> bool:
        now = self.clock()
        with self.session_factory.begin() as session:
            result = session.execute(
                update(Job)
                .where(Job.id == claimed.id, Job.status == "running", Job.lease_token == claimed.lease_token)
                .values(
                    status="succeeded",
                    result_summary=result_summary,
                    next_run_at=None,
                    claimed_by=None,
                    lease_token=None,
                    lease_expires_at=None,
                    completed_at=now,
                    last_error_code=None,
                    last_error_message=None,
                    updated_at=now,
                )
            )
            if result.rowcount != 1:
                return False
            self._finish_attempt(session, claimed.lease_token, "succeeded", now, result_summary=result_summary)
            return True

    def fail(
        self,
        claimed: ClaimedJob,
        error_code: str,
        error_message: str,
        retryable: bool,
        backoff_seconds: int,
    ) -> str | None:
        now = self.clock()
        will_retry = retryable and claimed.attempt_number < claimed.max_attempts
        next_status = "retry_wait" if will_retry else "failed"
        next_run_at = now + timedelta(seconds=backoff_seconds) if will_retry else None
        with self.session_factory.begin() as session:
            result = session.execute(
                update(Job)
                .where(Job.id == claimed.id, Job.status == "running", Job.lease_token == claimed.lease_token)
                .values(
                    status=next_status,
                    result_summary=None,
                    next_run_at=next_run_at,
                    claimed_by=None,
                    lease_token=None,
                    lease_expires_at=None,
                    completed_at=None if will_retry else now,
                    last_error_code=error_code[:120],
                    last_error_message=error_message[:1000],
                    updated_at=now,
                )
            )
            if result.rowcount != 1:
                return None
            self._finish_attempt(
                session,
                claimed.lease_token,
                "retry_scheduled" if will_retry else "failed",
                now,
                error_code=error_code,
                error_message=error_message,
            )
            return next_status

    def manual_retry(self, job_id: UUID) -> Job:
        now = self.clock()
        with self.session_factory.begin() as session:
            job = session.scalar(select(Job).where(Job.id == job_id).with_for_update())
            if job is None:
                raise JobNotFound("任务不存在")
            if job.status != "failed" or job.attempt_count >= job.max_attempts:
                raise InvalidManualRetry("仅允许重试尚有剩余尝试次数的失败任务")
            job.status = "queued"
            job.next_run_at = now
            job.completed_at = None
            job.result_summary = None
            job.last_error_code = None
            job.last_error_message = None
            job.updated_at = now
            session.flush()
            session.refresh(job)
            return job

    @staticmethod
    def _mark_expired_attempt(session: Session, job: Job, now: datetime) -> None:
        if job.lease_token is None:
            return
        session.execute(
            update(JobAttempt)
            .where(JobAttempt.lease_token == job.lease_token, JobAttempt.status == "running")
            .values(
                status="lease_expired",
                finished_at=now,
                error_code="lease_expired",
                error_message="Worker 租约到期，任务将恢复或终止",
            )
        )

    @staticmethod
    def _terminalize_exhausted(job: Job, now: datetime) -> None:
        job.status = "failed"
        job.next_run_at = None
        job.claimed_by = None
        job.lease_token = None
        job.lease_expires_at = None
        job.completed_at = now
        job.last_error_code = "lease_expired_max_attempts"
        job.last_error_message = "Worker 租约到期且已达到最大尝试次数"
        job.updated_at = now

    @staticmethod
    def _finish_attempt(
        session: Session,
        lease_token: UUID,
        status: str,
        now: datetime,
        result_summary: dict | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        session.execute(
            update(JobAttempt)
            .where(JobAttempt.lease_token == lease_token, JobAttempt.status == "running")
            .values(
                status=status,
                result_summary=result_summary,
                error_code=error_code[:120] if error_code else None,
                error_message=error_message[:1000] if error_message else None,
                finished_at=now,
            )
        )


def bounded_backoff(attempt_number: int, base_seconds: int, max_seconds: int) -> int:
    return min(max_seconds, base_seconds * (2 ** max(0, attempt_number - 1)))
