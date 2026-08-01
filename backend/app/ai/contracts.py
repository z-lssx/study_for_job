from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True)
class ProviderRequest:
    system_prompt: str
    task_prompt: str
    temperature: float
    max_tokens: int
    trace_id: UUID
    simulate_failure: bool = False


@dataclass(frozen=True)
class ProviderResponse:
    content: str
    model: str
    usage: TokenUsage


class AiProvider(Protocol):
    name: str
    model: str

    def complete(self, request: ProviderRequest) -> ProviderResponse: ...


@dataclass(frozen=True)
class PromptDefinition:
    scenario_id: UUID
    module: str
    scenario_key: str
    name: str
    description: str
    editable_variables: tuple[str, ...]
    system_template: str
    task_template: str
    parameters: dict
    enabled: bool
    updated_at: datetime


@dataclass(frozen=True)
class AiCallResult:
    content: str
    provider: str
    model: str
    usage: TokenUsage
    duration_ms: int
    prompt_hash: str
    trace_id: UUID


@dataclass(frozen=True)
class CallLogEntry:
    scenario_id: UUID
    module: str
    scenario_key: str
    provider: str
    model: str
    status: str
    duration_ms: int
    prompt_hash: str
    trace_id: UUID
    parameters: dict = field(default_factory=dict)
    usage: TokenUsage = field(default_factory=TokenUsage)
    error_code: str | None = None
    error_message: str | None = None


class PromptStore(Protocol):
    def get(self, scenario_key: str) -> PromptDefinition | None: ...


class CallLogStore(Protocol):
    def write(self, entry: CallLogEntry) -> None: ...
