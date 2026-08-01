from __future__ import annotations

import httpx

from .contracts import ProviderRequest, ProviderResponse, TokenUsage
from .errors import ProviderError


class FakeProvider:
    name = "fake"

    def __init__(self, model: str):
        self.model = model

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        if request.simulate_failure:
            raise ProviderError("fake_provider_failure", "本地 fake provider 按诊断要求返回失败", 502)
        input_size = len((request.system_prompt + request.task_prompt).encode("utf-8"))
        input_tokens = max(1, (input_size + 3) // 4)
        output_tokens = 8
        return ProviderResponse(
            content="LOCAL_FAKE_DIAGNOSTIC_OK",
            model=self.model,
            usage=TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
            ),
        )


class DeepSeekCompatibleProvider:
    name = "deepseek"

    def __init__(self, base_url: str, model: str, api_key: str, timeout_seconds: float):
        self.base_url = base_url.rstrip("/")
        self.model = model or "unconfigured-deepseek-model"
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        if not self.base_url or self.model == "unconfigured-deepseek-model" or not self.api_key.strip():
            raise ProviderError("provider_not_configured", "DeepSeek provider 缺少 base URL、model 或 API key", 503)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.task_prompt},
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=self.timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise ProviderError("provider_timeout", "DeepSeek compatible 调用超时", 504) from exc
        except httpx.RequestError as exc:
            raise ProviderError("provider_unavailable", "DeepSeek compatible 服务不可达", 503) from exc

        if response.status_code in (401, 403):
            raise ProviderError("provider_authentication", "DeepSeek compatible 鉴权失败", 502)
        if response.status_code == 429:
            raise ProviderError("provider_rate_limited", "DeepSeek compatible 请求受到限流", 503)
        if response.status_code >= 500:
            raise ProviderError("provider_upstream_error", "DeepSeek compatible 服务返回上游错误", 502)
        if response.status_code >= 400:
            raise ProviderError("provider_request_rejected", "DeepSeek compatible 拒绝了请求", 502)

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage") or {}
            if not isinstance(content, str):
                raise TypeError("content must be a string")
            token_usage = TokenUsage(
                input_tokens=_optional_nonnegative_int(usage.get("prompt_tokens")),
                output_tokens=_optional_nonnegative_int(usage.get("completion_tokens")),
                total_tokens=_optional_nonnegative_int(usage.get("total_tokens")),
            )
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError("provider_invalid_response", "DeepSeek compatible 返回格式不符合约定", 502) from exc
        return ProviderResponse(content=content, model=str(data.get("model") or self.model), usage=token_usage)


def _optional_nonnegative_int(value) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("token count must be a nonnegative integer")
    return value
