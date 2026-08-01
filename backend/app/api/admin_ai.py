from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from ..ai.errors import GatewayError
from ..ai.factory import create_provider, get_gateway
from ..ai.prompting import SCENARIO_VARIABLES, validate_parameters, validate_templates
from ..ai.repository import SqlCallLogStore, SqlPromptStore
from ..config import get_settings

router = APIRouter(prefix="/api/admin/ai", tags=["ai-admin"])


class PromptUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    system_template: str = Field(min_length=1, max_length=12000)
    task_template: str = Field(min_length=1, max_length=24000)
    temperature: float = Field(ge=0, le=2)
    max_tokens: int = Field(ge=1, le=8192)
    enabled: bool


class DiagnosticRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    simulate_failure: bool = False


@router.get("/runtime")
def runtime_status():
    settings = get_settings()
    provider_name = settings.ai_provider.strip().lower()
    model = settings.ai_fake_model if provider_name == "fake" else settings.deepseek_model
    return {
        "provider": provider_name,
        "model": model or "未配置",
        "remote_configured": settings.deepseek_configured if provider_name == "deepseek" else False,
        "supports_failure_simulation": provider_name == "fake",
    }


@router.get("/prompts")
def list_prompts():
    return [_serialize_prompt(item) for item in SqlPromptStore().list()]


@router.patch("/prompts/{scenario_key}")
def update_prompt(scenario_key: str, payload: PromptUpdate):
    try:
        variables = validate_templates(scenario_key, payload.system_template, payload.task_template)
        parameters = validate_parameters({"temperature": payload.temperature, "max_tokens": payload.max_tokens})
    except GatewayError as exc:
        raise HTTPException(status_code=exc.http_status, detail=exc.message) from exc
    store = SqlPromptStore()
    existing = store.get(scenario_key)
    if existing is None:
        raise HTTPException(status_code=404, detail="prompt 场景不存在")
    if set(existing.editable_variables) != set(variables) or set(variables) != set(SCENARIO_VARIABLES[scenario_key]):
        raise HTTPException(status_code=409, detail="数据库场景变量与代码白名单不一致")
    updated = store.update(
        scenario_key,
        payload.system_template,
        payload.task_template,
        parameters,
        payload.enabled,
    )
    return _serialize_prompt(updated)


@router.get("/statistics")
def token_statistics(
    days: int = Query(default=30, ge=1, le=365),
    module: str | None = Query(default=None, max_length=120),
    scenario_key: str | None = Query(default=None, max_length=160),
):
    return {"days": days, "items": SqlCallLogStore().statistics(days, module, scenario_key)}


@router.get("/calls")
def recent_calls(
    limit: int = Query(default=30, ge=1, le=100),
    module: str | None = Query(default=None, max_length=120),
    scenario_key: str | None = Query(default=None, max_length=160),
):
    return [_serialize_log(item) for item in SqlCallLogStore().recent(limit, module, scenario_key)]


@router.post("/diagnostics")
def run_diagnostic(payload: DiagnosticRequest, x_trace_id: UUID | None = Header(default=None)):
    try:
        provider = create_provider()
        if payload.simulate_failure and provider.name != "fake":
            raise HTTPException(status_code=422, detail="失败模拟只允许用于本地 fake provider")
        result = get_gateway().call(
            module="diagnostics",
            scenario_key="gateway_diagnostic",
            variables={"purpose": "验证固定 Gateway、token 与 trace 日志链路"},
            trace_id=x_trace_id,
            simulate_provider_failure=payload.simulate_failure,
        )
    except GatewayError as exc:
        trace_id = getattr(exc, "trace_id", x_trace_id)
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message, "trace_id": str(trace_id) if trace_id else None},
        ) from exc
    return {
        "status": "success",
        "provider": result.provider,
        "model": result.model,
        "input_tokens": result.usage.input_tokens,
        "output_tokens": result.usage.output_tokens,
        "total_tokens": result.usage.total_tokens,
        "duration_ms": result.duration_ms,
        "prompt_hash": result.prompt_hash,
        "trace_id": str(result.trace_id),
    }


def _serialize_prompt(item):
    return {
        "module": item.module,
        "scenario_key": item.scenario_key,
        "name": item.name,
        "description": item.description,
        "editable_variables": list(SCENARIO_VARIABLES.get(item.scenario_key, ())),
        "system_template": item.system_template,
        "task_template": item.task_template,
        "temperature": item.parameters.get("temperature"),
        "max_tokens": item.parameters.get("max_tokens"),
        "enabled": item.enabled,
        "updated_at": item.updated_at.isoformat(),
    }


def _serialize_log(item):
    result = {}
    for column in item.__table__.columns:
        if column.name in {"scenario_id", "request_parameters"}:
            continue
        value = getattr(item, column.name)
        if isinstance(value, UUID):
            value = str(value)
        elif isinstance(value, (date, datetime)):
            value = value.isoformat()
        result[column.name] = value
    return result
