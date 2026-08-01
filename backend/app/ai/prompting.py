from __future__ import annotations

import hashlib
import json
from string import Formatter

from .errors import GatewayError

SCENARIO_VARIABLES: dict[str, frozenset[str]] = {
    "gateway_diagnostic": frozenset({"purpose"}),
    "interview_extract": frozenset({"document_text"}),
    "readiness_plan": frozenset({"profile_summary", "evidence_summary"}),
}
PARAMETER_KEYS = frozenset({"temperature", "max_tokens"})


def validate_parameters(parameters: dict) -> dict:
    if set(parameters) != PARAMETER_KEYS:
        raise GatewayError("invalid_prompt_parameters", "参数只允许 temperature 与 max_tokens", 422)
    temperature = parameters.get("temperature")
    max_tokens = parameters.get("max_tokens")
    if isinstance(temperature, bool) or not isinstance(temperature, (int, float)) or not 0 <= temperature <= 2:
        raise GatewayError("invalid_prompt_parameters", "temperature 必须在 0 到 2 之间", 422)
    if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or not 1 <= max_tokens <= 8192:
        raise GatewayError("invalid_prompt_parameters", "max_tokens 必须是 1 到 8192 的整数", 422)
    return {"temperature": float(temperature), "max_tokens": max_tokens}


def template_variables(template: str) -> set[str]:
    fields: set[str] = set()
    try:
        for _, field_name, format_spec, conversion in Formatter().parse(template):
            if field_name is None:
                continue
            if not field_name or format_spec or conversion or "." in field_name or "[" in field_name:
                raise GatewayError("invalid_prompt_template", "模板只允许简单的命名变量", 422)
            fields.add(field_name)
    except ValueError as exc:
        raise GatewayError("invalid_prompt_template", "模板花括号格式不合法", 422) from exc
    return fields


def validate_templates(scenario_key: str, system_template: str, task_template: str) -> tuple[str, ...]:
    allowed = SCENARIO_VARIABLES.get(scenario_key)
    if allowed is None:
        raise GatewayError("unknown_prompt_scenario", "未知的 prompt 场景", 404)
    used = template_variables(system_template) | template_variables(task_template)
    unknown = used - allowed
    if unknown:
        raise GatewayError("invalid_prompt_template", f"模板包含未开放变量：{', '.join(sorted(unknown))}", 422)
    missing = allowed - used
    if missing:
        raise GatewayError("invalid_prompt_template", f"模板缺少必需变量：{', '.join(sorted(missing))}", 422)
    return tuple(sorted(allowed))


def render_templates(system_template: str, task_template: str, variables: dict[str, str]) -> tuple[str, str]:
    expected = template_variables(system_template) | template_variables(task_template)
    provided = set(variables)
    if provided != expected:
        missing = expected - provided
        extra = provided - expected
        details = []
        if missing:
            details.append(f"缺少 {', '.join(sorted(missing))}")
        if extra:
            details.append(f"多余 {', '.join(sorted(extra))}")
        raise GatewayError("invalid_prompt_input", "；".join(details), 422)
    return system_template.format_map(variables), task_template.format_map(variables)


def prompt_hash(system_prompt: str, task_prompt: str, parameters: dict, model: str) -> str:
    payload = json.dumps(
        {"system": system_prompt, "task": task_prompt, "parameters": parameters, "model": model},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
