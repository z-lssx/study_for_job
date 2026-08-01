from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from uuid import uuid4

import httpx

from app.ai.contracts import PromptDefinition, ProviderRequest
from app.ai.errors import GatewayError, ProviderError
from app.ai.gateway import AiGateway
from app.ai.providers import DeepSeekCompatibleProvider, FakeProvider


class MemoryPromptStore:
    def __init__(self, definition):
        self.definition = definition

    def get(self, scenario_key):
        return self.definition if scenario_key == self.definition.scenario_key else None


class MemoryLogStore:
    def __init__(self):
        self.entries = []

    def write(self, entry):
        self.entries.append(entry)


def diagnostic_prompt(task_template="执行固定诊断：{purpose}"):
    return PromptDefinition(
        scenario_id=uuid4(),
        module="diagnostics",
        scenario_key="gateway_diagnostic",
        name="diagnostic",
        description="",
        editable_variables=("purpose",),
        system_template="只执行诊断。",
        task_template=task_template,
        parameters={"temperature": 0, "max_tokens": 64},
        enabled=True,
        updated_at=datetime.now(timezone.utc),
    )


class AiGatewayTests(unittest.TestCase):
    def test_fake_success_returns_usage_and_writes_trace_log(self):
        logs = MemoryLogStore()
        gateway = AiGateway(FakeProvider("fake-v1"), MemoryPromptStore(diagnostic_prompt()), logs)

        result = gateway.call("diagnostics", "gateway_diagnostic", {"purpose": "unit test"})

        self.assertEqual("LOCAL_FAKE_DIAGNOSTIC_OK", result.content)
        self.assertGreater(result.usage.total_tokens, 0)
        self.assertEqual(64, len(result.prompt_hash))
        self.assertEqual("success", logs.entries[0].status)
        self.assertEqual(result.trace_id, logs.entries[0].trace_id)

    def test_fake_failure_is_logged_without_prompt_content(self):
        logs = MemoryLogStore()
        gateway = AiGateway(FakeProvider("fake-v1"), MemoryPromptStore(diagnostic_prompt()), logs)
        variables = {"purpose": "sensitive input that must not be logged"}
        gateway.call("diagnostics", "gateway_diagnostic", variables)

        with self.assertRaisesRegex(GatewayError, "fake provider"):
            gateway.call(
                "diagnostics",
                "gateway_diagnostic",
                variables,
                simulate_provider_failure=True,
            )

        entry = logs.entries[1]
        self.assertEqual("error", entry.status)
        self.assertEqual("fake_provider_failure", entry.error_code)
        self.assertEqual(logs.entries[0].prompt_hash, entry.prompt_hash)
        self.assertNotIn("sensitive input", repr(entry))

    def test_invalid_template_is_logged_before_provider_call(self):
        logs = MemoryLogStore()
        gateway = AiGateway(
            FakeProvider("fake-v1"),
            MemoryPromptStore(diagnostic_prompt("非法变量：{unknown}")),
            logs,
        )

        with self.assertRaises(GatewayError) as caught:
            gateway.call("diagnostics", "gateway_diagnostic", {"purpose": "unit test"})

        self.assertEqual("invalid_prompt_template", caught.exception.code)
        self.assertEqual("error", logs.entries[0].status)

    def test_unexpected_provider_exception_is_mapped_and_logged(self):
        provider = FakeProvider("fake-v1")
        provider.complete = Mock(side_effect=RuntimeError("do not leak me"))
        logs = MemoryLogStore()
        gateway = AiGateway(provider, MemoryPromptStore(diagnostic_prompt()), logs)

        with self.assertRaises(GatewayError) as caught:
            gateway.call("diagnostics", "gateway_diagnostic", {"purpose": "unit test"})

        self.assertEqual("provider_internal_error", caught.exception.code)
        self.assertNotIn("do not leak me", logs.entries[0].error_message)


class DeepSeekProviderTests(unittest.TestCase):
    def setUp(self):
        self.provider = DeepSeekCompatibleProvider("https://provider.invalid/v1", "configured-model", "secret-key", 5)
        self.request = ProviderRequest("system", "task", 0.2, 100, uuid4())

    @patch("app.ai.providers.httpx.post")
    def test_openai_compatible_response_is_structured(self, post):
        post.return_value = Mock(
            status_code=200,
            json=Mock(return_value={
                "model": "returned-model",
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
            }),
        )

        result = self.provider.complete(self.request)

        self.assertEqual("ok", result.content)
        self.assertEqual(7, result.usage.total_tokens)
        sent_headers = post.call_args.kwargs["headers"]
        self.assertEqual("Bearer secret-key", sent_headers["Authorization"])

    @patch("app.ai.providers.httpx.post", side_effect=httpx.TimeoutException("timeout"))
    def test_timeout_is_mapped(self, _post):
        with self.assertRaises(ProviderError) as caught:
            self.provider.complete(self.request)
        self.assertEqual("provider_timeout", caught.exception.code)
        self.assertEqual(504, caught.exception.http_status)

    def test_missing_real_configuration_is_deferred_to_logged_call(self):
        provider = DeepSeekCompatibleProvider("", "", "", 5)
        with self.assertRaises(ProviderError) as caught:
            provider.complete(self.request)
        self.assertEqual("provider_not_configured", caught.exception.code)


if __name__ == "__main__":
    unittest.main()
