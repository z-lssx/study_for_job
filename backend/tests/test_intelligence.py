from __future__ import annotations

import socket
import unittest
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.intelligence import SubmissionRequest
from app.intelligence.content import clean_html, content_hash, normalize_plain_text, validate_manual_content
from app.intelligence.errors import IntelligenceError, InvalidIntelligenceInput
from app.intelligence.fetcher import MAX_PAGE_BYTES, SafePublicFetcher
from app.intelligence.handler import InterviewIngestionHandler
from app.intelligence.repository import INGEST_JOB_TYPE, SubmissionSnapshot
from app.intelligence.sources import SourceAdapterRegistry
from app.jobs.contracts import ClaimedJob
from app.jobs.errors import PermanentJobError
from app.jobs.handlers import build_handler_registry


def public_resolver(_host, port, **_kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]


class SourceNormalizationTests(unittest.TestCase):
    def test_equivalent_cnblogs_urls_share_one_normalized_fact(self):
        registry = SourceAdapterRegistry()
        variants = [
            "http://cnblogs.com/demo/p/12345.html/",
            "https://www.cnblogs.com/demo/p/12345.html?utm_source=test#comments",
            "https://cnblogs.com/demo/p/12345.html?token=must-not-persist",
        ]
        normalized = {registry.normalize(item).normalized_url for item in variants}
        self.assertEqual({"https://www.cnblogs.com/demo/p/12345.html"}, normalized)
        self.assertNotIn("token", registry.normalize(variants[-1]).source_url)

    def test_unsupported_protocol_credentials_port_host_and_path_are_rejected(self):
        registry = SourceAdapterRegistry()
        invalid = [
            "file:///etc/passwd",
            "https://user:secret@www.cnblogs.com/demo/p/123.html",
            "https://www.cnblogs.com:8443/demo/p/123.html",
            "https://127.0.0.1/demo/p/123.html",
            "https://www.cnblogs.com/search?q=interview",
        ]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(InvalidIntelligenceInput):
                registry.normalize(value)


class ContentCleaningTests(unittest.TestCase):
    def test_manual_normalization_is_stable_for_hash_deduplication(self):
        first, first_hash = validate_manual_content("第一轮： Java 基础\r\n\r\n  TCP   三次握手怎么做？")
        second, second_hash = validate_manual_content("第一轮: Java 基础\n\nTCP 三次握手怎么做?")
        self.assertEqual(first, second)
        self.assertEqual(first_hash, second_hash)
        self.assertEqual(first_hash, content_hash(normalize_plain_text(second)))

    def test_html_cleaning_prefers_article_and_never_returns_scripts(self):
        html = """
        <html><head><title>无关站点标题</title><script>secretToken()</script></head>
        <body><nav>导航噪音</nav><article><h1>后端面经</h1><p>一面主要问了 Java、Redis 和网络协议，还讨论了项目中的事务边界。</p>
        <p>随后追问线程池参数、缓存一致性，以及 TCP 三次握手。二面继续询问数据库索引、消息队列与故障恢复的实际取舍。</p></article><footer>页脚噪音</footer></body></html>
        """
        title, cleaned = clean_html(html)
        self.assertEqual("后端面经", title)
        self.assertIn("线程池参数", cleaned)
        self.assertNotIn("secretToken", cleaned)
        self.assertNotIn("导航噪音", cleaned)


class SafeFetcherTests(unittest.TestCase):
    target = "https://www.cnblogs.com/demo/p/12345.html"

    def fetcher(self, handler, resolver=public_resolver):
        return SafePublicFetcher(resolver=resolver, transport=httpx.MockTransport(handler))

    def test_public_html_is_fetched_only_after_explicit_robots_allow(self):
        def handler(request: httpx.Request):
            if request.url.path == "/robots.txt":
                return httpx.Response(200, headers={"content-type": "text/plain"}, text="User-agent: *\nAllow: /\n")
            return httpx.Response(
                200,
                headers={"content-type": "text/html; charset=utf-8"},
                text="<article>" + ("公开后端面经问题与回答。" * 20) + "</article>",
            )

        result = self.fetcher(handler).fetch(self.target)
        self.assertEqual("text/html", result.media_type)
        self.assertIn("公开后端面经", result.raw_content)

    def test_robots_denial_is_permanent_and_safe(self):
        def handler(_request):
            return httpx.Response(200, headers={"content-type": "text/plain"}, text="User-agent: *\nDisallow: /\n")

        with self.assertRaises(IntelligenceError) as caught:
            self.fetcher(handler).fetch(self.target)
        self.assertEqual("source_disallowed", caught.exception.code)
        self.assertFalse(caught.exception.retryable)

    def test_private_dns_is_rejected_before_http_request(self):
        called = []

        def handler(_request):
            called.append(True)
            return httpx.Response(200, headers={"content-type": "text/plain"}, text="User-agent: *\nAllow: /\n")

        def private_resolver(_host, port, **_kwargs):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port))]

        with self.assertRaises(IntelligenceError) as caught:
            self.fetcher(handler, private_resolver).fetch(self.target)
        self.assertEqual("unsafe_network_target", caught.exception.code)
        self.assertEqual([], called)

    def test_redirect_to_unsupported_host_is_rejected(self):
        def handler(request):
            if request.url.path == "/robots.txt":
                return httpx.Response(200, headers={"content-type": "text/plain"}, text="User-agent: *\nAllow: /\n")
            return httpx.Response(302, headers={"location": "http://127.0.0.1/private"})

        with self.assertRaises(IntelligenceError) as caught:
            self.fetcher(handler).fetch(self.target)
        self.assertEqual("redirect_not_allowed", caught.exception.code)

    def test_timeout_size_and_content_type_have_stable_classification(self):
        def robots_or_timeout(request):
            if request.url.path == "/robots.txt":
                return httpx.Response(200, headers={"content-type": "text/plain"}, text="User-agent: *\nAllow: /\n")
            raise httpx.ReadTimeout("sensitive-url-must-not-leak", request=request)

        with self.assertRaises(IntelligenceError) as timeout:
            self.fetcher(robots_or_timeout).fetch(self.target)
        self.assertEqual("network_timeout", timeout.exception.code)
        self.assertNotIn("sensitive-url", timeout.exception.message)

        def too_large(request):
            if request.url.path == "/robots.txt":
                return httpx.Response(200, headers={"content-type": "text/plain"}, text="User-agent: *\nAllow: /\n")
            return httpx.Response(200, headers={"content-type": "text/html", "content-length": str(MAX_PAGE_BYTES + 1)})

        with self.assertRaises(IntelligenceError) as size:
            self.fetcher(too_large).fetch(self.target)
        self.assertEqual("content_too_large", size.exception.code)

        def json_response(request):
            if request.url.path == "/robots.txt":
                return httpx.Response(200, headers={"content-type": "text/plain"}, text="User-agent: *\nAllow: /\n")
            return httpx.Response(200, headers={"content-type": "application/json"}, json={"content": "no"})

        with self.assertRaises(IntelligenceError) as media:
            self.fetcher(json_response).fetch(self.target)
        self.assertEqual("unsupported_content_type", media.exception.code)


class HandlerContractTests(unittest.TestCase):
    def test_registry_contains_fixed_intelligence_job_type(self):
        self.assertIsNotNone(build_handler_registry().get(INGEST_JOB_TYPE))

    def test_parameter_drift_is_rejected_without_fetching(self):
        job_id = uuid4()
        submission_id = uuid4()
        snapshot = SubmissionSnapshot(
            id=submission_id,
            current_job_id=job_id,
            current_method="manual_text",
            source_id=None,
            normalized_url=None,
            raw_content="足够长的面经正文内容，包含多个技术问题与回答，用于固定契约测试。",
            raw_content_type="text/plain",
            input_fingerprint="a" * 64,
            revision=2,
            document_id=None,
        )

        class Repository:
            def load_snapshot(self, _submission_id):
                return snapshot

        claimed = ClaimedJob(
            id=job_id,
            job_type=INGEST_JOB_TYPE,
            payload={"submission_id": str(submission_id), "revision": 1, "input_fingerprint": "a" * 64},
            attempt_number=1,
            max_attempts=3,
            lease_token=uuid4(),
        )
        with self.assertRaises(PermanentJobError) as caught:
            InterviewIngestionHandler(repository=Repository())(claimed)
        self.assertEqual("input_snapshot_drift", caught.exception.code)

    def test_api_xor_validation_and_422_do_not_echo_rejected_content(self):
        with self.assertRaises(ValidationError):
            SubmissionRequest.model_validate({"url": self.target if hasattr(self, "target") else "https://example.com", "content": "both"})
        from app.main import app

        secret = "private-interview-body-must-not-echo"
        response = TestClient(app).post("/api/intelligence/submissions", json={"content": secret, "unexpected": True})
        self.assertEqual(422, response.status_code)
        self.assertNotIn(secret, response.text)


if __name__ == "__main__":
    unittest.main()
