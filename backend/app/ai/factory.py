from functools import lru_cache

from ..config import get_settings
from .errors import GatewayError
from .gateway import AiGateway
from .providers import DeepSeekCompatibleProvider, FakeProvider
from .repository import SqlCallLogStore, SqlPromptStore


def create_provider():
    settings = get_settings()
    provider_name = settings.ai_provider.strip().lower()
    if provider_name == "fake":
        return FakeProvider(settings.ai_fake_model)
    if provider_name == "deepseek":
        return DeepSeekCompatibleProvider(
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model,
            api_key=settings.resolved_deepseek_api_key,
            timeout_seconds=settings.ai_request_timeout_seconds,
        )
    raise GatewayError("provider_not_supported", "AI_PROVIDER 只支持 fake 或 deepseek", 503)


@lru_cache
def get_gateway() -> AiGateway:
    return AiGateway(create_provider(), SqlPromptStore(), SqlCallLogStore())
