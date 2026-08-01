from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import case, func, select

from ..db import SessionLocal
from ..models import AiCallLog, PromptScenario, PromptTemplate
from .contracts import CallLogEntry, PromptDefinition


class SqlPromptStore:
    def list(self) -> list[PromptDefinition]:
        with SessionLocal() as session:
            rows = session.execute(
                select(PromptScenario, PromptTemplate)
                .join(PromptTemplate, PromptTemplate.scenario_id == PromptScenario.id)
                .order_by(PromptScenario.module, PromptScenario.scenario_key)
            ).all()
            return [_definition(scenario, template) for scenario, template in rows]

    def get(self, scenario_key: str) -> PromptDefinition | None:
        with SessionLocal() as session:
            row = session.execute(
                select(PromptScenario, PromptTemplate)
                .join(PromptTemplate, PromptTemplate.scenario_id == PromptScenario.id)
                .where(PromptScenario.scenario_key == scenario_key)
            ).one_or_none()
            return _definition(*row) if row else None

    def update(self, scenario_key: str, system_template: str, task_template: str, parameters: dict, enabled: bool) -> PromptDefinition | None:
        with SessionLocal.begin() as session:
            row = session.execute(
                select(PromptScenario, PromptTemplate)
                .join(PromptTemplate, PromptTemplate.scenario_id == PromptScenario.id)
                .where(PromptScenario.scenario_key == scenario_key)
                .with_for_update(of=PromptTemplate)
            ).one_or_none()
            if row is None:
                return None
            scenario, template = row
            template.system_template = system_template
            template.task_template = task_template
            template.parameters = parameters
            template.enabled = enabled
            template.updated_at = datetime.now(timezone.utc)
            session.flush()
            session.refresh(template)
            return _definition(scenario, template)


class SqlCallLogStore:
    def write(self, entry: CallLogEntry) -> None:
        with SessionLocal.begin() as session:
            session.add(AiCallLog(
                scenario_id=entry.scenario_id,
                module=entry.module,
                scenario_key=entry.scenario_key,
                provider=entry.provider,
                model=entry.model,
                status=entry.status,
                input_tokens=entry.usage.input_tokens,
                output_tokens=entry.usage.output_tokens,
                total_tokens=entry.usage.total_tokens,
                duration_ms=entry.duration_ms,
                prompt_hash=entry.prompt_hash,
                trace_id=entry.trace_id,
                error_code=entry.error_code,
                error_message=entry.error_message,
                request_parameters=entry.parameters,
            ))

    def recent(self, limit: int, module: str | None = None, scenario_key: str | None = None) -> list[AiCallLog]:
        statement = select(AiCallLog)
        if module:
            statement = statement.where(AiCallLog.module == module)
        if scenario_key:
            statement = statement.where(AiCallLog.scenario_key == scenario_key)
        statement = statement.order_by(AiCallLog.created_at.desc(), AiCallLog.id.desc()).limit(limit)
        with SessionLocal() as session:
            return list(session.scalars(statement))

    def statistics(self, days: int, module: str | None = None, scenario_key: str | None = None) -> list[dict]:
        statement = select(
            AiCallLog.module,
            AiCallLog.scenario_key,
            func.count().label("call_count"),
            func.sum(case((AiCallLog.status == "success", 1), else_=0)).label("success_count"),
            func.sum(case((AiCallLog.status == "error", 1), else_=0)).label("error_count"),
            func.coalesce(func.sum(AiCallLog.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(AiCallLog.output_tokens), 0).label("output_tokens"),
            func.coalesce(func.sum(AiCallLog.total_tokens), 0).label("total_tokens"),
            func.round(func.avg(AiCallLog.duration_ms), 1).label("average_duration_ms"),
        ).where(AiCallLog.created_at >= datetime.now(timezone.utc) - timedelta(days=days))
        if module:
            statement = statement.where(AiCallLog.module == module)
        if scenario_key:
            statement = statement.where(AiCallLog.scenario_key == scenario_key)
        statement = statement.group_by(AiCallLog.module, AiCallLog.scenario_key).order_by(
            func.coalesce(func.sum(AiCallLog.total_tokens), 0).desc(), AiCallLog.module, AiCallLog.scenario_key
        )
        with SessionLocal() as session:
            return [dict(row._mapping) for row in session.execute(statement)]


def _definition(scenario: PromptScenario, template: PromptTemplate) -> PromptDefinition:
    return PromptDefinition(
        scenario_id=scenario.id,
        module=scenario.module,
        scenario_key=scenario.scenario_key,
        name=scenario.name,
        description=scenario.description,
        editable_variables=tuple(scenario.editable_variables),
        system_template=template.system_template,
        task_template=template.task_template,
        parameters=dict(template.parameters),
        enabled=template.enabled,
        updated_at=template.updated_at,
    )
