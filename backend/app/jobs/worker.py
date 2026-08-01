from __future__ import annotations

import logging
import os
import signal
import socket
import threading
from uuid import UUID

from ..config import Settings, get_settings
from ..migrations import apply_migrations
from .contracts import ClaimedJob, HandlerRegistry
from .errors import JobExecutionError, PermanentJobError
from .handlers import build_handler_registry
from .repository import JobRepository, bounded_backoff

logger = logging.getLogger("study_for_job.worker")


class LeaseHeartbeat:
    def __init__(self, repository: JobRepository, job_id: UUID, lease_token: UUID, lease_seconds: int):
        self.repository = repository
        self.job_id = job_id
        self.lease_token = lease_token
        self.lease_seconds = lease_seconds
        self.stop_event = threading.Event()
        self.lost_lease = False
        self.thread = threading.Thread(target=self._run, name=f"lease-{job_id}", daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        self.stop_event.set()
        self.thread.join(timeout=max(1, self.lease_seconds / 3 + 1))

    def _run(self) -> None:
        interval = max(1.0, self.lease_seconds / 3)
        while not self.stop_event.wait(interval):
            try:
                if not self.repository.renew_lease(self.job_id, self.lease_token, self.lease_seconds):
                    self.lost_lease = True
                    return
            except Exception:
                logger.exception("Lease heartbeat failed for job %s", self.job_id)


class JobWorker:
    def __init__(
        self,
        repository: JobRepository,
        registry: HandlerRegistry,
        worker_id: str,
        lease_seconds: int,
        poll_interval_seconds: float,
        backoff_base_seconds: int,
        backoff_max_seconds: int,
    ) -> None:
        self.repository = repository
        self.registry = registry
        self.worker_id = worker_id
        self.lease_seconds = lease_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.backoff_base_seconds = backoff_base_seconds
        self.backoff_max_seconds = backoff_max_seconds

    def run_once(self) -> bool:
        claimed = self.repository.claim(self.worker_id, self.lease_seconds)
        if claimed is None:
            return False

        logger.info(
            "Claimed job id=%s type=%s attempt=%s/%s",
            claimed.id,
            claimed.job_type,
            claimed.attempt_number,
            claimed.max_attempts,
        )
        with LeaseHeartbeat(self.repository, claimed.id, claimed.lease_token, self.lease_seconds):
            try:
                result = self._execute(claimed)
            except JobExecutionError as exc:
                backoff = bounded_backoff(
                    claimed.attempt_number,
                    self.backoff_base_seconds,
                    self.backoff_max_seconds,
                )
                status = self.repository.fail(
                    claimed,
                    exc.code,
                    exc.message,
                    exc.retryable,
                    backoff,
                )
                if status is None:
                    logger.warning("Discarded stale failure for job %s", claimed.id)
                else:
                    logger.info("Job %s transitioned to %s", claimed.id, status)
            else:
                if self.repository.succeed(claimed, result):
                    logger.info("Job %s succeeded", claimed.id)
                else:
                    logger.warning("Discarded stale success for job %s", claimed.id)
        return True

    def run_forever(self, stop_event: threading.Event) -> None:
        logger.info("Worker %s started", self.worker_id)
        while not stop_event.is_set():
            try:
                processed = self.run_once()
            except Exception:
                logger.exception("Worker cycle failed; the lease will be recovered if needed")
                processed = False
            if not processed:
                stop_event.wait(self.poll_interval_seconds)
        logger.info("Worker %s stopped", self.worker_id)

    def _execute(self, claimed: ClaimedJob) -> dict:
        handler = self.registry.get(claimed.job_type)
        if handler is None:
            raise PermanentJobError("unknown_job_type", "任务类型没有注册处理器")
        try:
            result = handler(claimed)
        except JobExecutionError:
            raise
        except Exception as exc:
            raise PermanentJobError("handler_internal_error", "任务处理器发生未映射错误") from exc
        if not isinstance(result, dict):
            raise PermanentJobError("invalid_handler_result", "任务处理器必须返回对象摘要")
        return result


def resolved_worker_id(settings: Settings) -> str:
    configured = settings.worker_id.strip()
    return configured or f"{socket.gethostname()}-{os.getpid()}"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    apply_migrations()
    settings = get_settings()
    stop_event = threading.Event()

    def request_stop(signum, _frame) -> None:
        logger.info("Received signal %s; stopping after current job", signum)
        stop_event.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    worker = JobWorker(
        repository=JobRepository(),
        registry=build_handler_registry(),
        worker_id=resolved_worker_id(settings),
        lease_seconds=settings.worker_lease_seconds,
        poll_interval_seconds=settings.worker_poll_interval_seconds,
        backoff_base_seconds=settings.worker_backoff_base_seconds,
        backoff_max_seconds=settings.worker_backoff_max_seconds,
    )
    worker.run_forever(stop_event)


if __name__ == "__main__":
    main()
