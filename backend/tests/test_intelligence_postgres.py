from __future__ import annotations

import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update

from app.db import SessionLocal
from app.intelligence.content import content_hash
from app.intelligence.errors import IntelligenceError
from app.intelligence.fetcher import FetchedContent
from app.intelligence.handler import InterviewIngestionHandler
from app.intelligence.repository import INGEST_JOB_TYPE, IntelligenceRepository
from app.intelligence.sources import SourceAdapterRegistry
from app.jobs.contracts import ClaimedJob, HandlerRegistry
from app.jobs.repository import JobRepository
from app.jobs.worker import JobWorker
from app.main import app
from app.models import (
    InterviewDocument,
    InterviewDocumentSource,
    InterviewSource,
    InterviewSubmission,
    Job,
    JobAttempt,
)


class SameHtmlFetcher:
    def fetch(self, _url):
        body = "<article><h1>并发面经</h1><p>" + ("Java、Redis、MySQL、线程池与网络协议问题。" * 15) + "</p></article>"
        return FetchedContent(body, "text/html", _url)


class RetryableFetcher:
    def fetch(self, _url):
        raise IntelligenceError("network_timeout", "来源响应超时，系统将按退避策略重试", True)


@unittest.skipUnless(os.getenv("RUN_POSTGRES_INTEGRATION") == "1", "requires explicit PostgreSQL integration opt-in")
class PostgresIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.submission_ids: set[UUID] = set()

    def tearDown(self):
        if not self.submission_ids:
            return
        with SessionLocal.begin() as session:
            submissions = list(session.scalars(
                select(InterviewSubmission).where(InterviewSubmission.id.in_(self.submission_ids))
            ))
            submission_keys = [str(item.id) for item in submissions]
            job_ids = list(session.scalars(
                select(Job.id).where(
                    Job.job_type == INGEST_JOB_TYPE,
                    Job.payload["submission_id"].astext.in_(submission_keys),
                )
            ))
            document_ids = [item.document_id for item in submissions if item.document_id]
            source_ids = [item.source_id for item in submissions if item.source_id]
            session.execute(delete(InterviewDocumentSource).where(
                (InterviewDocumentSource.first_submission_id.in_(self.submission_ids))
                | (InterviewDocumentSource.document_id.in_(document_ids or [uuid4()]))
            ))
            session.execute(delete(InterviewSubmission).where(InterviewSubmission.id.in_(self.submission_ids)))
            if document_ids:
                session.execute(delete(InterviewDocument).where(InterviewDocument.id.in_(document_ids)))
            if source_ids:
                session.execute(delete(InterviewSource).where(InterviewSource.id.in_(source_ids)))
            if job_ids:
                session.execute(delete(JobAttempt).where(JobAttempt.job_id.in_(job_ids)))
                session.execute(delete(Job).where(Job.id.in_(job_ids)))

    def submit_manual(self, content: str):
        with SessionLocal.begin() as session:
            result = IntelligenceRepository().submit_content(session, content)
            self.submission_ids.add(result.submission_id)
            return result

    def submit_url(self, url: str):
        address = SourceAdapterRegistry().normalize(url)
        with SessionLocal.begin() as session:
            result = IntelligenceRepository().submit_url(session, address)
            self.submission_ids.add(result.submission_id)
            return result

    @staticmethod
    def claimed_for(submission_id: UUID) -> ClaimedJob:
        with SessionLocal() as session:
            submission = session.get(InterviewSubmission, submission_id)
            job = session.get(Job, submission.current_job_id)
            return ClaimedJob(
                id=job.id,
                job_type=job.job_type,
                payload=dict(job.payload),
                attempt_number=1,
                max_attempts=job.max_attempts,
                lease_token=uuid4(),
            )

    def test_concurrent_identical_manual_submissions_return_one_fact(self):
        unique = uuid4()
        content = f"并发面经 {unique}：一面询问 Java 线程池、Redis 缓存和数据库索引；二面追问消息队列幂等、事务边界、故障恢复和网络协议。"

        def submit(_index):
            with SessionLocal.begin() as session:
                return IntelligenceRepository().submit_content(session, content)

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(submit, (1, 2)))
        self.submission_ids.update(item.submission_id for item in results)
        self.assertEqual(1, len({item.submission_id for item in results}))
        self.assertEqual([False, True], sorted(item.created for item in results))

    def test_worker_replay_and_two_sources_merge_on_content_hash(self):
        suffix = uuid4().hex[:12]
        first = self.submit_url(f"https://www.cnblogs.com/t005-a/p/{suffix}.html")
        second = self.submit_url(f"https://www.cnblogs.com/t005-b/p/{suffix}.html")
        handler = InterviewIngestionHandler(fetcher=SameHtmlFetcher())
        first_result = handler(self.claimed_for(first.submission_id))
        replay_result = handler(self.claimed_for(first.submission_id))
        second_result = handler(self.claimed_for(second.submission_id))
        self.assertEqual(first_result["document_id"], replay_result["document_id"])
        self.assertEqual(first_result["document_id"], second_result["document_id"])
        with SessionLocal() as session:
            document_id = UUID(first_result["document_id"])
            self.assertEqual(1, len(list(session.scalars(
                select(InterviewDocument).where(InterviewDocument.id == document_id)
            ))))
            self.assertEqual(2, len(list(session.scalars(
                select(InterviewDocumentSource).where(InterviewDocumentSource.document_id == document_id)
            ))))

    def test_late_replay_cannot_create_an_orphan_document_fact(self):
        created = self.submit_manual(
            f"迟到写回验证 {uuid4()}：Java 并发、数据库索引、缓存一致性、消息幂等与故障恢复。"
        )
        repository = IntelligenceRepository()
        snapshot = repository.load_snapshot(created.submission_id)
        accepted_text = "已接受的正文事实：线程池、事务边界、Redis 一致性、消息重复消费和线上排障。"
        stale_text = "迟到且不应落库的旧结果：完全不同的页面响应与解析内容，只用于验证事务边界。"
        document_id, _deduplicated = repository.complete(
            snapshot,
            accepted_text,
            "text/plain",
            accepted_text,
            "已接受的正文事实",
        )

        replay_document_id, replay_deduplicated = repository.complete(
            snapshot,
            stale_text,
            "text/plain",
            stale_text,
            "迟到结果",
        )

        self.assertEqual(document_id, replay_document_id)
        self.assertTrue(replay_deduplicated)
        with SessionLocal() as session:
            self.assertIsNone(session.scalar(
                select(InterviewDocument.id).where(InterviewDocument.content_hash == content_hash(stale_text))
            ))

    def test_retryable_terminal_failure_can_create_new_revision_without_drift(self):
        suffix = uuid4().hex[:12]
        created = self.submit_url(f"https://www.cnblogs.com/t005-retry/p/{suffix}.html")
        with SessionLocal.begin() as session:
            submission = session.get(InterviewSubmission, created.submission_id)
            session.execute(update(Job).where(Job.id == submission.current_job_id).values(max_attempts=1))

        registry = HandlerRegistry()
        registry.register(INGEST_JOB_TYPE, InterviewIngestionHandler(fetcher=RetryableFetcher()))
        worker = JobWorker(
            repository=JobRepository(),
            registry=registry,
            worker_id="intelligence-postgres-test",
            lease_seconds=60,
            poll_interval_seconds=1,
            backoff_base_seconds=1,
            backoff_max_seconds=1,
        )
        self.assertTrue(worker.run_once())
        with SessionLocal() as session:
            failed = IntelligenceRepository.get_bundle(session, created.submission_id)
            self.assertEqual("failed", failed.job.status)
            self.assertEqual("network_timeout", failed.submission.last_error_code)

        response = TestClient(app).post(f"/api/intelligence/submissions/{created.submission_id}/retry")
        self.assertEqual(200, response.status_code, response.text)
        self.assertEqual(str(created.submission_id), response.json()["id"])
        self.assertEqual("queued", response.json()["status"])
        with SessionLocal() as session:
            current = IntelligenceRepository.get_bundle(session, created.submission_id)
            self.submission_ids.add(created.submission_id)
            self.assertEqual(2, current.submission.revision)
            self.assertEqual("queued", current.job.status)
            self.assertEqual(
                {
                    "submission_id": str(created.submission_id),
                    "revision": 2,
                    "input_fingerprint": current.submission.input_fingerprint,
                },
                dict(current.job.payload),
            )


if __name__ == "__main__":
    unittest.main()
