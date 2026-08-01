from __future__ import annotations

import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import delete

from app.db import SessionLocal
from app.jobs.errors import IdempotencyConflict, InvalidManualRetry
from app.jobs.handlers import DIAGNOSTIC_JOB_TYPE
from app.jobs.repository import JobRepository
from app.models import Job, JobAttempt


@unittest.skipUnless(os.getenv("RUN_POSTGRES_INTEGRATION") == "1", "requires explicit PostgreSQL integration opt-in")
class PostgresJobRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.job_ids = []
        self.now = datetime.now(timezone.utc)
        self.repository = JobRepository(clock=lambda: self.now)

    def tearDown(self):
        if not self.job_ids:
            return
        with SessionLocal.begin() as session:
            session.execute(delete(JobAttempt).where(JobAttempt.job_id.in_(self.job_ids)))
            session.execute(delete(Job).where(Job.id.in_(self.job_ids)))

    def create(self, key: str, maximum: int = 3):
        job, created = self.repository.create(
            DIAGNOSTIC_JOB_TYPE,
            {"mode": "success", "failures_before_success": 0},
            priority=0,
            max_attempts=maximum,
            idempotency_key=f"postgres-test-{key}-{uuid4()}",
        )
        self.job_ids.append(job.id)
        self.assertTrue(created)
        return job

    def test_idempotent_create_returns_existing_and_rejects_parameter_drift(self):
        key = f"postgres-idempotency-{uuid4()}"
        job, created = self.repository.create(
            DIAGNOSTIC_JOB_TYPE,
            {"mode": "success", "failures_before_success": 0},
            priority=0,
            max_attempts=3,
            idempotency_key=key,
        )
        self.job_ids.append(job.id)
        duplicate, duplicate_created = self.repository.create(
            DIAGNOSTIC_JOB_TYPE,
            {"mode": "success", "failures_before_success": 0},
            priority=0,
            max_attempts=3,
            idempotency_key=key,
        )
        self.assertTrue(created)
        self.assertFalse(duplicate_created)
        self.assertEqual(job.id, duplicate.id)
        with self.assertRaises(IdempotencyConflict):
            self.repository.create(
                DIAGNOSTIC_JOB_TYPE,
                {"mode": "permanent_failure", "failures_before_success": 0},
                priority=0,
                max_attempts=3,
                idempotency_key=key,
            )

    def test_two_concurrent_workers_only_claim_one_lease(self):
        job = self.create("concurrency")
        with ThreadPoolExecutor(max_workers=2) as executor:
            claims = list(executor.map(lambda worker: self.repository.claim(worker, 30), ("worker-a", "worker-b")))
        claimed = [item for item in claims if item is not None]
        self.assertEqual(1, len(claimed))
        self.assertEqual(job.id, claimed[0].id)
        self.assertTrue(self.repository.succeed(claimed[0], {"diagnostic": "ok"}))

    def test_expired_lease_is_recovered_and_stale_result_is_rejected(self):
        self.create("lease-recovery")
        first = self.repository.claim("worker-a", 5)
        self.now += timedelta(seconds=6)
        second = self.repository.claim("worker-b", 5)
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertEqual(first.id, second.id)
        self.assertEqual(2, second.attempt_number)
        self.assertFalse(self.repository.succeed(first, {"diagnostic": "stale"}))
        self.assertTrue(self.repository.succeed(second, {"diagnostic": "ok"}))
        self.assertEqual(["lease_expired", "succeeded"], [item.status for item in self.repository.attempts(first.id)])

    def test_retry_backoff_reaches_terminal_and_cannot_be_manually_retried(self):
        job = self.create("retry-terminal", maximum=2)
        first = self.repository.claim("worker-a", 5)
        self.assertEqual(
            "retry_wait",
            self.repository.fail(first, "temporary", "固定临时错误", True, backoff_seconds=5),
        )
        waiting = self.repository.get(job.id)
        self.assertEqual(self.now + timedelta(seconds=5), waiting.next_run_at)
        self.now += timedelta(seconds=5)
        second = self.repository.claim("worker-b", 5)
        self.assertEqual("failed", self.repository.fail(second, "temporary", "固定临时错误", True, 10))
        with self.assertRaises(InvalidManualRetry):
            self.repository.manual_retry(job.id)


if __name__ == "__main__":
    unittest.main()
