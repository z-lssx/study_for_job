from __future__ import annotations

from pydantic import BaseModel, ConfigDict, ValidationError

from ..jobs.contracts import ClaimedJob
from ..jobs.errors import PermanentJobError, RetryableJobError
from .content import MIN_FETCHED_TEXT_LENGTH, clean_html, normalize_plain_text
from .errors import IntelligenceError, InvalidSubmissionAction
from .fetcher import SafePublicFetcher
from .repository import IntelligenceRepository, manual_title


class IngestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    submission_id: str
    revision: int
    input_fingerprint: str


class InterviewIngestionHandler:
    def __init__(
        self,
        repository: IntelligenceRepository | None = None,
        fetcher: SafePublicFetcher | None = None,
    ) -> None:
        self.repository = repository or IntelligenceRepository()
        self.fetcher = fetcher or SafePublicFetcher()

    def __call__(self, job: ClaimedJob) -> dict:
        try:
            payload = IngestPayload.model_validate(job.payload)
        except ValidationError as exc:
            raise PermanentJobError("invalid_job_payload", "面经入库任务 payload 不符合固定契约") from exc

        try:
            from uuid import UUID

            submission_id = UUID(payload.submission_id)
        except (ValueError, TypeError) as exc:
            raise PermanentJobError("invalid_job_payload", "面经入库任务 payload 不符合固定契约") from exc

        snapshot = self.repository.load_snapshot(submission_id)
        if snapshot is None:
            raise PermanentJobError("submission_not_found", "面经提交不存在")
        if (
            snapshot.current_job_id != job.id
            or snapshot.revision != payload.revision
            or snapshot.input_fingerprint != payload.input_fingerprint
        ):
            raise PermanentJobError("input_snapshot_drift", "任务输入快照已经变化，已拒绝旧任务")
        if snapshot.document_id is not None:
            return {"submission_id": str(snapshot.id), "document_id": str(snapshot.document_id), "replayed": True}
        if not self.repository.mark_processing(snapshot):
            raise PermanentJobError("input_snapshot_drift", "任务输入快照已经变化，已拒绝旧任务")

        try:
            if snapshot.current_method == "url_fetch":
                if not snapshot.normalized_url:
                    raise InvalidSubmissionAction("source_missing", "面经来源事实缺失", False)
                fetched = self.fetcher.fetch(snapshot.normalized_url)
                if fetched.media_type == "text/html":
                    title, cleaned = clean_html(fetched.raw_content)
                else:
                    cleaned = normalize_plain_text(fetched.raw_content)
                    if len(cleaned) < MIN_FETCHED_TEXT_LENGTH:
                        raise IntelligenceError("content_too_short", "页面没有足够的有效面经正文，可补充正文后重新处理", False)
                    title = manual_title(cleaned)
                raw_content = fetched.raw_content
                raw_content_type = fetched.media_type
            else:
                if not snapshot.raw_content:
                    raise InvalidSubmissionAction("manual_content_missing", "手动正文事实缺失", False)
                raw_content = snapshot.raw_content
                raw_content_type = "text/plain"
                cleaned = normalize_plain_text(raw_content)
                title = manual_title(cleaned)
            document_id, deduplicated = self.repository.complete(
                snapshot,
                raw_content=raw_content,
                raw_content_type=raw_content_type,
                cleaned_content=cleaned,
                title=title,
            )
            return {
                "submission_id": str(snapshot.id),
                "document_id": str(document_id),
                "content_deduplicated": deduplicated,
            }
        except IntelligenceError as exc:
            self.repository.record_failure(snapshot, exc.code, exc.message, exc.retryable)
            error_type = RetryableJobError if exc.retryable else PermanentJobError
            raise error_type(exc.code, exc.message) from exc
        except Exception as exc:
            code = "processing_unknown_error"
            message = "面经处理发生未知错误，可稍后重新触发或补充正文"
            self.repository.record_failure(snapshot, code, message, False)
            raise PermanentJobError(code, message) from exc
