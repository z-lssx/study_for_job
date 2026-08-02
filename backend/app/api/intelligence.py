from __future__ import annotations

from datetime import datetime
from typing import Self
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from ..db import get_db
from ..intelligence.errors import IntelligenceError, InvalidIntelligenceInput
from ..intelligence.repository import IntelligenceRepository, SubmissionBundle
from ..intelligence.sources import SourceAdapterRegistry
from ..intelligence.extraction.repository import ExtractionRepository
from .extraction import serialize_extraction

router = APIRouter(prefix="/api/intelligence/submissions", tags=["interview-intelligence"])


class SubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    url: str | None = Field(default=None, min_length=1, max_length=2048)
    content: str | None = Field(default=None, min_length=1, max_length=200_000)

    @model_validator(mode="after")
    def exactly_one_input(self) -> Self:
        if (self.url is None) == (self.content is None):
            raise ValueError("必须且只能提交 URL 或正文中的一种")
        return self


class SupplementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    content: str = Field(min_length=1, max_length=200_000)


class ChunkAnnotationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    note_text: str | None = Field(default=None, max_length=2000)
    review_status: str = Field(pattern="^(confirmed|needs_review|rejected)$")


@router.post("")
def create_submission(
    payload: SubmissionRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    repository = IntelligenceRepository()
    try:
        if payload.url is not None:
            address = SourceAdapterRegistry().normalize(payload.url)
            result = repository.submit_url(db, address)
        else:
            result = repository.submit_content(db, payload.content or "")
    except IntelligenceError as exc:
        raise _http_error(exc, status.HTTP_422_UNPROCESSABLE_ENTITY) from exc
    db.flush()
    bundle = repository.get_bundle(db, result.submission_id)
    if bundle is None:
        raise HTTPException(status_code=500, detail="面经提交写入后无法读取")
    response.status_code = status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
    return {
        "created": result.created,
        "duplicate_reason": result.duplicate_reason,
        "submission": _serialize_bundle(bundle, include_content=True),
    }


@router.get("")
def list_submissions(limit: int = Query(default=100, ge=1, le=200), db: Session = Depends(get_db)):
    return [_serialize_bundle(item, include_content=False) for item in IntelligenceRepository.list_bundles(db, limit)]


@router.get("/{submission_id}")
def get_submission(submission_id: UUID, db: Session = Depends(get_db)):
    bundle = IntelligenceRepository.get_bundle(db, submission_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="面经提交不存在")
    return _serialize_bundle(bundle, include_content=True)


@router.post("/{submission_id}/supplement")
def supplement_submission(
    submission_id: UUID,
    payload: SupplementRequest,
    db: Session = Depends(get_db),
):
    repository = IntelligenceRepository()
    try:
        result = repository.supplement(db, submission_id, payload.content)
    except IntelligenceError as exc:
        raise _http_error(exc, 404 if exc.code == "submission_not_found" else 409) from exc
    db.flush()
    bundle = repository.get_bundle(db, result.submission_id)
    return _serialize_bundle(bundle, include_content=True)


@router.post("/{submission_id}/retry")
def retry_submission(submission_id: UUID, db: Session = Depends(get_db)):
    repository = IntelligenceRepository()
    try:
        result = repository.retry(db, submission_id)
    except IntelligenceError as exc:
        raise _http_error(exc, 404 if exc.code == "submission_not_found" else 409) from exc
    db.flush()
    bundle = repository.get_bundle(db, result.submission_id)
    return _serialize_bundle(bundle, include_content=True)


@router.post("/{submission_id}/extractions")
def trigger_extraction(submission_id: UUID, response: Response, db: Session = Depends(get_db)):
    bundle = IntelligenceRepository.get_bundle(db, submission_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="面经提交不存在")
    if bundle.document is None:
        raise HTTPException(status_code=409, detail="面经正文尚未成功入库")
    run, created = ExtractionRepository.trigger(db, bundle.document.id)
    db.flush()
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return {"created": created, "extraction": serialize_extraction(db, bundle.document, run)}


@router.get("/{submission_id}/extractions")
def get_extraction(submission_id: UUID, db: Session = Depends(get_db)):
    bundle = IntelligenceRepository.get_bundle(db, submission_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="面经提交不存在")
    if bundle.document is None:
        return {"extraction": None}
    run = ExtractionRepository.latest(db, bundle.document.id)
    return {"extraction": serialize_extraction(db, bundle.document, run) if run else None}


@router.patch("/{submission_id}/extractions/chunks/{chunk_id}/annotation")
def save_chunk_annotation(
    submission_id: UUID,
    chunk_id: UUID,
    payload: ChunkAnnotationRequest,
    db: Session = Depends(get_db),
):
    bundle = IntelligenceRepository.get_bundle(db, submission_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="面经提交不存在")
    chunk = ExtractionRepository.chunk_for_document(db, chunk_id, bundle.submission.document_id)
    if chunk is None:
        raise HTTPException(status_code=404, detail="内容块不存在")
    annotation = ExtractionRepository.save_annotation(db, chunk_id, payload.note_text, payload.review_status)
    return {
        "chunk_id": str(annotation.chunk_id),
        "note_text": annotation.note_text,
        "review_status": annotation.review_status,
        "updated_at": _iso(annotation.updated_at),
    }


def _http_error(exc: IntelligenceError, status_code: int) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": exc.message, "retryable": exc.retryable},
    )


def _serialize_bundle(bundle: SubmissionBundle, include_content: bool) -> dict:
    submission = bundle.submission
    document = bundle.document
    job = bundle.job
    state = {
        "queued": "queued",
        "running": "processing",
        "retry_wait": "retry_wait",
        "succeeded": "succeeded",
        "failed": "failed",
    }.get(job.status if job else "", "failed")
    preview_limit = 6000 if include_content else 280
    preview = document.cleaned_content[:preview_limit] if document else None
    return {
        "id": str(submission.id),
        "status": state,
        "initial_method": submission.initial_method,
        "collection_method": submission.current_method,
        "revision": submission.revision,
        "source": (
            {
                "url": bundle.source.source_url,
                "normalized_url": bundle.source.normalized_url,
                "host": bundle.source.host,
            }
            if bundle.source
            else None
        ),
        "document": (
            {
                "id": str(document.id),
                "title": document.title,
                "content_hash": document.content_hash,
                "cleaning_version": document.cleaning_version,
                "acquisition_method": document.acquisition_method,
                "collected_at": _iso(document.collected_at),
                "content_preview": preview,
                "preview_truncated": len(document.cleaned_content) > preview_limit,
            }
            if document
            else None
        ),
        "error": (
            {
                "code": submission.last_error_code,
                "message": submission.last_error_message,
                "retryable": submission.last_error_retryable,
            }
            if submission.last_error_code
            else None
        ),
        "can_retry": state == "failed" and submission.last_error_retryable is not False,
        "can_supplement": state == "failed" and submission.document_id is None,
        "submitted_at": _iso(submission.submitted_at),
        "processing_started_at": _iso(submission.processing_started_at),
        "completed_at": _iso(submission.completed_at),
        "updated_at": _iso(submission.updated_at),
    }


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
