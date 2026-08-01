from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..jobs.errors import IdempotencyConflict, InvalidManualRetry, JobNotFound
from ..jobs.handlers import DIAGNOSTIC_JOB_TYPE
from ..jobs.repository import JobRepository

router = APIRouter(prefix="/api/admin/jobs", tags=["job-admin"])


class DiagnosticJobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    mode: Literal["success", "retry_then_success", "permanent_failure"]
    failures_before_success: int = Field(default=0, ge=0, le=10)
    max_attempts: int = Field(default=3, ge=1, le=10)
    priority: int = Field(default=0, ge=-10, le=10)
    idempotency_key: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9._:-]+$")

    @model_validator(mode="after")
    def validate_mode(self):
        if self.mode == "retry_then_success" and self.failures_before_success < 1:
            raise ValueError("retry_then_success 至少失败一次")
        if self.mode != "retry_then_success" and self.failures_before_success != 0:
            raise ValueError("只有 retry_then_success 允许设置 failures_before_success")
        return self


@router.post("/diagnostics")
def create_diagnostic(payload: DiagnosticJobRequest, response: Response):
    repository = JobRepository()
    try:
        job, created = repository.create(
            job_type=DIAGNOSTIC_JOB_TYPE,
            payload={
                "mode": payload.mode,
                "failures_before_success": payload.failures_before_success,
            },
            priority=payload.priority,
            max_attempts=payload.max_attempts,
            idempotency_key=payload.idempotency_key,
        )
    except IdempotencyConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return {"created": created, "job": _serialize_job(job)}


@router.get("")
def list_jobs(
    limit: int = Query(default=50, ge=1, le=100),
    job_status: Literal["queued", "running", "retry_wait", "succeeded", "failed"] | None = Query(
        default=None, alias="status"
    ),
):
    return [_serialize_job(item) for item in JobRepository().list(limit, job_status)]


@router.get("/{job_id}")
def get_job(job_id: UUID):
    repository = JobRepository()
    job = repository.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {
        "job": _serialize_job(job),
        "attempts": [_serialize_attempt(item) for item in repository.attempts(job_id)],
    }


@router.post("/{job_id}/retry")
def retry_job(job_id: UUID):
    try:
        job = JobRepository().manual_retry(job_id)
    except JobNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidManualRetry as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _serialize_job(job)


def _serialize_job(item):
    result = {}
    for column in item.__table__.columns:
        if column.name in {"lease_token", "payload"}:
            continue
        value = getattr(item, column.name)
        if isinstance(value, UUID):
            value = str(value)
        elif isinstance(value, (date, datetime)):
            value = value.isoformat()
        result[column.name] = value
    return result


def _serialize_attempt(item):
    result = {}
    for column in item.__table__.columns:
        if column.name == "lease_token":
            continue
        value = getattr(item, column.name)
        if isinstance(value, UUID):
            value = str(value)
        elif isinstance(value, (date, datetime)):
            value = value.isoformat()
        result[column.name] = value
    return result
