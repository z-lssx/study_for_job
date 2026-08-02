from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .contracts import ClaimedJob, HandlerRegistry
from .errors import PermanentJobError, RetryableJobError

DIAGNOSTIC_JOB_TYPE = "diagnostic.lifecycle"


class DiagnosticPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["success", "retry_then_success", "permanent_failure"]
    failures_before_success: int = Field(default=0, ge=0, le=10)


def diagnostic_handler(job: ClaimedJob) -> dict:
    try:
        payload = DiagnosticPayload.model_validate(job.payload)
    except ValidationError as exc:
        raise PermanentJobError("invalid_job_payload", "诊断任务 payload 不符合固定契约") from exc

    if payload.mode == "permanent_failure":
        raise PermanentJobError("diagnostic_permanent_failure", "固定诊断按要求终止")
    if payload.mode == "retry_then_success" and job.attempt_number <= payload.failures_before_success:
        raise RetryableJobError("diagnostic_retryable_failure", "固定诊断按要求进入重试")
    return {"diagnostic": "ok", "attempt_number": job.attempt_number}


def build_handler_registry() -> HandlerRegistry:
    from ..intelligence.extraction.handler import InterviewExtractionHandler
    from ..intelligence.extraction.repository import EXTRACTION_JOB_TYPE
    from ..intelligence.handler import InterviewIngestionHandler
    from ..intelligence.repository import INGEST_JOB_TYPE

    registry = HandlerRegistry()
    registry.register(DIAGNOSTIC_JOB_TYPE, diagnostic_handler)
    registry.register(INGEST_JOB_TYPE, InterviewIngestionHandler())
    registry.register(EXTRACTION_JOB_TYPE, InterviewExtractionHandler())
    return registry
