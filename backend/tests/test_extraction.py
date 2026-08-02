from __future__ import annotations

import unittest
from uuid import uuid4

from app.intelligence.extraction.extractor import (
    PROCESSOR_VERSION,
    SCHEMA_VERSION,
    extract_document,
    input_fingerprint,
)
from app.intelligence.extraction.handler import InterviewExtractionHandler
from app.intelligence.extraction.repository import EXTRACTION_JOB_TYPE, ExtractionSnapshot
from app.jobs.contracts import ClaimedJob
from app.jobs.errors import PermanentJobError
from app.jobs.handlers import build_handler_registry


class DeterministicExtractionTests(unittest.TestCase):
    content = (
        "一面：基础\n"
        "Q: Redis 缓存一致性怎么保证？\n"
        "A: 这是我的项目经验，不是标准答案。\n"
        "追问：如果发生故障如何恢复？\n"
        "面试官反馈：回答需要补充监控指标。\n"
        "二面\n"
        "面试流程：先做自我介绍，然后讨论项目。\n"
        "未能判断的记录"
    )

    def test_types_rounds_and_offsets_are_stable(self):
        first = extract_document(self.content, "a" * 64)
        second = extract_document(self.content, "a" * 64)
        self.assertEqual(first, second)
        self.assertEqual([item.label for item in first.rounds], ["一面：基础", "二面"])
        self.assertEqual(
            [item.block_type for item in first.chunks],
            ["process_description", "question", "author_answer", "follow_up", "interviewer_feedback", "process_description", "process_description", "unknown"],
        )
        self.assertEqual([item.field_kind for item in first.candidates], ["question", "follow_up"])
        for chunk in first.chunks:
            self.assertEqual(self.content[chunk.start_char:chunk.end_char].strip(), self.content[chunk.start_char:chunk.end_char])
        for candidate in first.candidates:
            self.assertEqual(self.content[candidate.start_char:candidate.end_char], candidate.extracted_text)

    def test_fingerprint_includes_schema_and_processor_versions(self):
        digest = input_fingerprint("b" * 64, "clean.v1")
        self.assertEqual(len(digest), 64)
        self.assertIn(SCHEMA_VERSION, "interview-extraction.v1")
        self.assertTrue(PROCESSOR_VERSION.startswith("deterministic-"))

    def test_no_evidence_means_no_candidate(self):
        result = extract_document("作者分享了一个项目过程。\n未知内容", "c" * 64)
        self.assertEqual([], list(result.candidates))
        self.assertTrue(all(item.block_type in {"unknown", "process_description"} for item in result.chunks))


class ExtractionHandlerContractTests(unittest.TestCase):
    def test_registry_contains_only_the_fixed_extraction_type(self):
        self.assertIsNotNone(build_handler_registry().get(EXTRACTION_JOB_TYPE))

    def test_snapshot_drift_is_rejected_before_extraction(self):
        run_id, document_id, job_id = uuid4(), uuid4(), uuid4()
        snapshot = ExtractionSnapshot(
            run_id=run_id, document_id=document_id, job_id=job_id,
            input_fingerprint=input_fingerprint("a" * 64, "clean.v1"), trigger_revision=2,
            content_hash="a" * 64, cleaning_version="clean.v1", cleaned_content=self._content(),
        )

        class Repository:
            def load_snapshot(self, _run_id): return snapshot

        claimed = self._job(run_id, document_id, job_id, snapshot.input_fingerprint, trigger_revision=1)
        with self.assertRaises(PermanentJobError) as caught:
            InterviewExtractionHandler(repository=Repository())(claimed)
        self.assertEqual("extraction_snapshot_drift", caught.exception.code)

    def test_processing_failure_is_stable_and_does_not_write_facts(self):
        run_id, document_id, job_id = uuid4(), uuid4(), uuid4()
        fingerprint = input_fingerprint("b" * 64, "clean.v1")
        snapshot = ExtractionSnapshot(
            run_id=run_id, document_id=document_id, job_id=job_id,
            input_fingerprint=fingerprint, trigger_revision=1, content_hash="b" * 64,
            cleaning_version="clean.v1", cleaned_content="   ",
        )

        class Repository:
            failed = None
            def load_snapshot(self, _run_id): return snapshot
            def mark_running(self, _snapshot): return "running"
            def complete(self, *_args): raise AssertionError("empty content must not write facts")
            def fail(self, _snapshot, code, message): self.failed = (code, message)

        repository = Repository()
        with self.assertRaises(PermanentJobError) as caught:
            InterviewExtractionHandler(repository=repository)(self._job(run_id, document_id, job_id, fingerprint, 1))
        self.assertEqual("extraction_processing_error", caught.exception.code)
        self.assertEqual("extraction_processing_error", repository.failed[0])
        self.assertNotIn("cleaned_content", repository.failed[1])

    @staticmethod
    def _content():
        return "一面\nQ: Redis 为什么快？\nA: 作者的个人回答。"

    @staticmethod
    def _job(run_id, document_id, job_id, fingerprint, trigger_revision):
        return ClaimedJob(
            id=job_id, job_type=EXTRACTION_JOB_TYPE,
            payload={"run_id": str(run_id), "document_id": str(document_id), "input_fingerprint": fingerprint, "trigger_revision": trigger_revision},
            attempt_number=1, max_attempts=3, lease_token=uuid4(),
        )


if __name__ == "__main__":
    unittest.main()
