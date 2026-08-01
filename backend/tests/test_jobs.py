from __future__ import annotations

import unittest
from uuid import uuid4

from pydantic import ValidationError
from fastapi.testclient import TestClient

from app.api.admin_jobs import DiagnosticJobRequest
from app.api.admin_jobs import _serialize_job
from app.jobs.contracts import ClaimedJob, HandlerRegistry
from app.jobs.errors import PermanentJobError
from app.jobs.handlers import DIAGNOSTIC_JOB_TYPE, build_handler_registry, diagnostic_handler
from app.jobs.repository import bounded_backoff
from app.jobs.worker import JobWorker


def claimed(job_type=DIAGNOSTIC_JOB_TYPE, payload=None, attempt=1, maximum=3):
    return ClaimedJob(
        id=uuid4(),
        job_type=job_type,
        payload=payload or {"mode": "success", "failures_before_success": 0},
        attempt_number=attempt,
        max_attempts=maximum,
        lease_token=uuid4(),
    )


class MemoryRepository:
    def __init__(self, item):
        self.item = item
        self.successes = []
        self.failures = []

    def claim(self, _worker_id, _lease_seconds):
        item, self.item = self.item, None
        return item

    def renew_lease(self, _job_id, _lease_token, _lease_seconds):
        return True

    def succeed(self, item, result):
        self.successes.append((item, result))
        return True

    def fail(self, item, code, message, retryable, backoff):
        self.failures.append((item, code, message, retryable, backoff))
        return "retry_wait" if retryable and item.attempt_number < item.max_attempts else "failed"


def worker(repository, registry=None):
    return JobWorker(
        repository=repository,
        registry=registry or build_handler_registry(),
        worker_id="test-worker",
        lease_seconds=3600,
        poll_interval_seconds=1,
        backoff_base_seconds=5,
        backoff_max_seconds=12,
    )


class DiagnosticHandlerTests(unittest.TestCase):
    def test_job_serialization_hides_payload_and_lease_token(self):
        from app.models import Job

        item = Job(
            id=uuid4(),
            job_type=DIAGNOSTIC_JOB_TYPE,
            status="running",
            payload={"prompt": "must-not-be-returned"},
            priority=0,
            attempt_count=1,
            max_attempts=3,
            lease_token=uuid4(),
        )
        serialized = _serialize_job(item)
        self.assertNotIn("payload", serialized)
        self.assertNotIn("lease_token", serialized)

    def test_fixed_success_returns_only_summary(self):
        result = diagnostic_handler(claimed())
        self.assertEqual({"diagnostic": "ok", "attempt_number": 1}, result)

    def test_retry_then_success_uses_attempt_number(self):
        payload = {"mode": "retry_then_success", "failures_before_success": 1}
        with self.assertRaisesRegex(Exception, "进入重试"):
            diagnostic_handler(claimed(payload=payload, attempt=1))
        self.assertEqual("ok", diagnostic_handler(claimed(payload=payload, attempt=2))["diagnostic"])

    def test_invalid_payload_is_safe_permanent_failure(self):
        with self.assertRaises(PermanentJobError) as caught:
            diagnostic_handler(claimed(payload={"mode": "success", "secret": "must-not-echo"}))
        self.assertEqual("invalid_job_payload", caught.exception.code)
        self.assertNotIn("must-not-echo", caught.exception.message)

    def test_api_contract_rejects_free_form_and_invalid_retry_mode(self):
        with self.assertRaises(ValidationError):
            DiagnosticJobRequest.model_validate({
                "mode": "custom-code",
                "idempotency_key": "diagnostic-1",
            })

    def test_http_validation_response_does_not_echo_rejected_prompt(self):
        from app.main import app

        response = TestClient(app).post("/api/admin/jobs/diagnostics", json={
            "mode": "success",
            "idempotency_key": "diagnostic-1",
            "prompt": "sensitive-prompt-must-not-echo",
        })
        self.assertEqual(422, response.status_code)
        self.assertNotIn("sensitive-prompt-must-not-echo", response.text)
        with self.assertRaises(ValidationError):
            DiagnosticJobRequest.model_validate({
                "mode": "success",
                "failures_before_success": 1,
                "idempotency_key": "diagnostic-1",
            })


class WorkerTests(unittest.TestCase):
    def test_success_is_persisted(self):
        repository = MemoryRepository(claimed())
        self.assertTrue(worker(repository).run_once())
        self.assertEqual(1, len(repository.successes))
        self.assertEqual([], repository.failures)

    def test_retryable_failure_uses_bounded_backoff(self):
        item = claimed(payload={"mode": "retry_then_success", "failures_before_success": 3}, attempt=3, maximum=4)
        repository = MemoryRepository(item)
        worker(repository).run_once()
        self.assertEqual("diagnostic_retryable_failure", repository.failures[0][1])
        self.assertTrue(repository.failures[0][3])
        self.assertEqual(12, repository.failures[0][4])

    def test_unknown_type_fails_without_executing_arbitrary_input(self):
        repository = MemoryRepository(claimed(job_type="unknown.type", payload={"code": "print('no')"}))
        worker(repository).run_once()
        self.assertEqual("unknown_job_type", repository.failures[0][1])
        self.assertFalse(repository.failures[0][3])

    def test_unmapped_handler_error_is_not_leaked(self):
        registry = HandlerRegistry()

        def broken(_job):
            raise RuntimeError("database-password-must-not-leak")

        registry.register("broken", broken)
        repository = MemoryRepository(claimed(job_type="broken"))
        worker(repository, registry).run_once()
        self.assertEqual("handler_internal_error", repository.failures[0][1])
        self.assertNotIn("database-password", repository.failures[0][2])

    def test_empty_queue_returns_false(self):
        self.assertFalse(worker(MemoryRepository(None)).run_once())


class BackoffTests(unittest.TestCase):
    def test_backoff_is_exponential_and_bounded(self):
        self.assertEqual(5, bounded_backoff(1, 5, 12))
        self.assertEqual(10, bounded_backoff(2, 5, 12))
        self.assertEqual(12, bounded_backoff(3, 5, 12))


if __name__ == "__main__":
    unittest.main()
