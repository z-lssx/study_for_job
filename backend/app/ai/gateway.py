from __future__ import annotations

import time
from uuid import UUID, uuid4

from .contracts import AiCallResult, AiProvider, CallLogEntry, CallLogStore, PromptStore, ProviderRequest, TokenUsage
from .errors import GatewayError
from .prompting import prompt_hash, render_templates, validate_parameters, validate_templates


class AiGateway:
    def __init__(self, provider: AiProvider, prompts: PromptStore, logs: CallLogStore):
        self.provider = provider
        self.prompts = prompts
        self.logs = logs

    def call(
        self,
        module: str,
        scenario_key: str,
        variables: dict[str, str],
        trace_id: UUID | None = None,
        simulate_provider_failure: bool = False,
    ) -> AiCallResult:
        trace = trace_id or uuid4()
        started = time.perf_counter()
        definition = self.prompts.get(scenario_key)
        if definition is None:
            raise GatewayError("unknown_prompt_scenario", "未知的 prompt 场景", 404)
        raw_hash = prompt_hash(definition.system_template, definition.task_template, definition.parameters, self.provider.model)
        resolved_hash = raw_hash
        parameters = dict(definition.parameters)

        try:
            if definition.module != module:
                raise GatewayError("prompt_module_mismatch", "prompt 场景不属于指定模块", 422)
            if not definition.enabled:
                raise GatewayError("prompt_scenario_disabled", "prompt 场景已停用", 409)
            validate_templates(scenario_key, definition.system_template, definition.task_template)
            parameters = validate_parameters(parameters)
            system_prompt, task_prompt = render_templates(definition.system_template, definition.task_template, variables)
            resolved_hash = prompt_hash(system_prompt, task_prompt, parameters, self.provider.model)
            response = self.provider.complete(ProviderRequest(
                system_prompt=system_prompt,
                task_prompt=task_prompt,
                temperature=parameters["temperature"],
                max_tokens=parameters["max_tokens"],
                trace_id=trace,
                simulate_failure=simulate_provider_failure,
            ))
        except GatewayError as exc:
            duration_ms = _elapsed_ms(started)
            self._write_error(definition, duration_ms, resolved_hash, trace, parameters, exc)
            exc.trace_id = trace
            raise
        except Exception as exc:
            wrapped = GatewayError("provider_internal_error", "AI provider 发生未映射错误", 502)
            duration_ms = _elapsed_ms(started)
            self._write_error(definition, duration_ms, resolved_hash, trace, parameters, wrapped)
            wrapped.trace_id = trace
            raise wrapped from exc

        duration_ms = _elapsed_ms(started)
        self.logs.write(CallLogEntry(
            scenario_id=definition.scenario_id,
            module=definition.module,
            scenario_key=definition.scenario_key,
            provider=self.provider.name,
            model=response.model,
            status="success",
            duration_ms=duration_ms,
            prompt_hash=resolved_hash,
            trace_id=trace,
            parameters=parameters,
            usage=response.usage,
        ))
        return AiCallResult(
            content=response.content,
            provider=self.provider.name,
            model=response.model,
            usage=response.usage,
            duration_ms=duration_ms,
            prompt_hash=resolved_hash,
            trace_id=trace,
        )

    def _write_error(self, definition, duration_ms, resolved_hash, trace, parameters, error) -> None:
        self.logs.write(CallLogEntry(
            scenario_id=definition.scenario_id,
            module=definition.module,
            scenario_key=definition.scenario_key,
            provider=self.provider.name,
            model=self.provider.model,
            status="error",
            duration_ms=duration_ms,
            prompt_hash=resolved_hash,
            trace_id=trace,
            parameters=parameters,
            error_code=error.code,
            error_message=error.message[:1000],
        ))


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.perf_counter() - started) * 1000))
