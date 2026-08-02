from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationError

from ...jobs.contracts import ClaimedJob
from ...jobs.errors import PermanentJobError
from .extractor import extract_document, input_fingerprint
from .repository import ExtractionRepository


class ExtractionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    document_id: UUID
    input_fingerprint: str
    trigger_revision: int


class InterviewExtractionHandler:
    def __init__(self, repository: ExtractionRepository | None = None) -> None:
        self.repository = repository or ExtractionRepository()

    def __call__(self, job: ClaimedJob) -> dict:
        try:
            payload = ExtractionPayload.model_validate(job.payload)
        except ValidationError as exc:
            raise PermanentJobError("invalid_job_payload", "面经抽取任务 payload 不符合固定契约") from exc

        snapshot = self.repository.load_snapshot(payload.run_id)
        if snapshot is None:
            raise PermanentJobError("extraction_run_not_found", "面经抽取运行不存在")
        if (
            snapshot.job_id != job.id
            or snapshot.document_id != payload.document_id
            or snapshot.input_fingerprint != payload.input_fingerprint
            or snapshot.trigger_revision != payload.trigger_revision
            or input_fingerprint(snapshot.content_hash, snapshot.cleaning_version) != snapshot.input_fingerprint
        ):
            raise PermanentJobError("extraction_snapshot_drift", "抽取输入快照已经变化，已拒绝旧任务")

        state = self.repository.mark_running(snapshot)
        if state == "succeeded":
            return {"run_id": str(snapshot.run_id), "replayed": True}
        if state != "running":
            raise PermanentJobError("extraction_snapshot_drift", "抽取输入快照已经变化，已拒绝旧任务")

        try:
            result = extract_document(snapshot.cleaned_content, snapshot.content_hash)
            summary = self.repository.complete(snapshot, result)
            return {"run_id": str(snapshot.run_id), "document_id": str(snapshot.document_id), **summary}
        except Exception as exc:
            code = "extraction_processing_error"
            message = "面经标注与结构化抽取失败，可重新触发"
            self.repository.fail(snapshot, code, message)
            raise PermanentJobError(code, message) from exc
