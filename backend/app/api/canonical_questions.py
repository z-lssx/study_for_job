from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..intelligence.normalization.repository import CanonicalQuestionRepository

router = APIRouter(prefix="/api/intelligence/canonical-questions", tags=["interview-intelligence"])


class MergeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    target_canonical_question_id: UUID
    note_text: str | None = Field(default=None, max_length=1000)


class SplitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    occurrence_ids: list[UUID] = Field(min_length=1, max_length=200)
    canonical_text: str = Field(min_length=1, max_length=4000)
    note_text: str | None = Field(default=None, max_length=1000)


class EquivalentMappingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    target_canonical_question_id: UUID
    note_text: str | None = Field(default=None, max_length=1000)


@router.post("/refresh")
def refresh_canonical_questions(db: Session = Depends(get_db)):
    result = CanonicalQuestionRepository.refresh(db)
    return {
        "candidate_count": result.candidate_count,
        "created_occurrence_count": result.occurrence_count,
        "created_canonical_count": result.canonical_count,
        "created_mapping_count": result.mapping_count,
        "skipped_without_evidence": result.skipped_without_evidence,
    }


@router.get("")
def list_canonical_questions(
    search: str | None = Query(default=None, max_length=200),
    round_ordinal: int | None = Query(default=None, ge=1),
    limit: int = Query(default=100, ge=1, le=300),
    db: Session = Depends(get_db),
):
    rows = CanonicalQuestionRepository.list_frequency(db, search.strip() if search else None, round_ordinal, limit)
    return [_serialize(row) for row in rows]


@router.patch("/occurrences/{occurrence_id}/mapping")
def map_occurrence_as_equivalent(
    occurrence_id: UUID,
    payload: EquivalentMappingRequest,
    db: Session = Depends(get_db),
):
    try:
        CanonicalQuestionRepository.map_equivalent(
            db, occurrence_id, payload.target_canonical_question_id, payload.note_text
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="出现记录或目标规范题不存在") from exc
    return {"occurrence_id": str(occurrence_id), "target_canonical_question_id": str(payload.target_canonical_question_id)}


@router.post("/{canonical_id}/merge")
def merge_canonical_question(canonical_id: UUID, payload: MergeRequest, db: Session = Depends(get_db)):
    try:
        moved = CanonicalQuestionRepository.merge(
            db, canonical_id, payload.target_canonical_question_id, payload.note_text
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="来源或目标规范题不存在") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="不能把规范题合并到自身") from exc
    return {"source_canonical_question_id": str(canonical_id), "target_canonical_question_id": str(payload.target_canonical_question_id), "moved_occurrence_count": moved}


@router.post("/{canonical_id}/split")
def split_canonical_question(canonical_id: UUID, payload: SplitRequest, db: Session = Depends(get_db)):
    try:
        target_id, moved = CanonicalQuestionRepository.split(
            db, canonical_id, payload.occurrence_ids, payload.canonical_text, payload.note_text
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="规范题或所选出现记录不存在") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="拆分后的规范题必须与当前规范题不同") from exc
    return {"source_canonical_question_id": str(canonical_id), "target_canonical_question_id": str(target_id), "moved_occurrence_count": moved}


@router.get("/{canonical_id}")
def get_canonical_question(canonical_id: UUID, db: Session = Depends(get_db)):
    result = CanonicalQuestionRepository.detail(db, canonical_id)
    if result is None:
        raise HTTPException(status_code=404, detail="规范题不存在")
    return _serialize(result)


def _serialize(value):
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    return value
