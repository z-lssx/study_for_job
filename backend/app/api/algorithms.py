from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AlgorithmProblem

router = APIRouter(prefix="/api/algorithms", tags=["algorithm-track"])

ALLOWED_STATUS = "^(not_started|in_progress|solved|revisit)$"
ALLOWED_DIFFICULTY = "^(unknown|easy|medium|hard)$"


class AlgorithmProblemIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=240)
    source_url: str | None = Field(default=None, max_length=2048)
    source_platform: str = Field(default="manual", min_length=1, max_length=80)
    difficulty: str = Field(default="unknown", pattern=ALLOWED_DIFFICULTY)
    tags: list[str] = Field(default_factory=list, max_length=20)
    status: str = Field(default="not_started", pattern=ALLOWED_STATUS)
    mistake_reason: str | None = Field(default=None, max_length=4000)
    review_notes: str | None = Field(default=None, max_length=10000)
    notes: str | None = Field(default=None, max_length=4000)
    origin: str = Field(default="user", pattern="^(user|intelligence_suggestion)$")
    canonical_question_id: UUID | None = None
    next_review_at: date | None = None


class AlgorithmProblemPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=240)
    source_url: str | None = Field(default=None, max_length=2048)
    source_platform: str | None = Field(default=None, min_length=1, max_length=80)
    difficulty: str | None = Field(default=None, pattern=ALLOWED_DIFFICULTY)
    tags: list[str] | None = Field(default=None, max_length=20)
    status: str | None = Field(default=None, pattern=ALLOWED_STATUS)
    mistake_reason: str | None = Field(default=None, max_length=4000)
    review_notes: str | None = Field(default=None, max_length=10000)
    notes: str | None = Field(default=None, max_length=4000)
    canonical_question_id: UUID | None = None
    next_review_at: date | None = None


class PracticeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: str = Field(pattern=ALLOWED_STATUS)
    mistake_reason: str | None = Field(default=None, max_length=4000)
    review_notes: str | None = Field(default=None, max_length=10000)
    next_review_at: date | None = None


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _canonical(db: Session, canonical_id: UUID | None) -> dict | None:
    if canonical_id is None:
        return None
    row = db.execute(
        text(
            """
            SELECT cq.id, cq.canonical_text, COUNT(qom.occurrence_id)::int AS occurrence_count
            FROM canonical_questions cq
            LEFT JOIN question_occurrence_mappings qom ON qom.canonical_question_id = cq.id
            WHERE cq.id = :id
            GROUP BY cq.id, cq.canonical_text
            """
        ),
        {"id": canonical_id},
    ).mappings().first()
    return (
        {
            "id": str(row["id"]),
            "text": row["canonical_text"],
            "occurrence_count": row["occurrence_count"],
            "frequency_is_reference_only": True,
        }
        if row
        else None
    )


def _serialize(db: Session, item: AlgorithmProblem) -> dict:
    return {
        "id": str(item.id),
        "title": item.title,
        "source_url": item.source_url,
        "source_platform": item.source_platform,
        "difficulty": item.difficulty,
        "tags": item.tags or [],
        "status": item.status,
        "mistake_reason": item.mistake_reason,
        "review_notes": item.review_notes,
        "notes": item.notes,
        "origin": item.origin,
        "canonical_question_id": str(item.canonical_question_id) if item.canonical_question_id else None,
        "canonical_question": _canonical(db, item.canonical_question_id),
        "last_practiced_at": _iso(item.last_practiced_at),
        "next_review_at": item.next_review_at.isoformat() if item.next_review_at else None,
        "practice_count": item.practice_count,
        "created_at": _iso(item.created_at),
        "updated_at": _iso(item.updated_at),
    }


def _get_problem(db: Session, problem_id: UUID) -> AlgorithmProblem:
    item = db.get(AlgorithmProblem, problem_id)
    if item is None:
        raise HTTPException(status_code=404, detail="算法题目不存在")
    return item


def _validate_canonical(db: Session, canonical_id: UUID | None) -> None:
    if canonical_id is not None and db.execute(
        text("SELECT 1 FROM canonical_questions WHERE id = :id"), {"id": canonical_id}
    ).first() is None:
        raise HTTPException(status_code=404, detail="关联的规范题不存在")


@router.get("")
def list_problems(
    status_filter: str | None = Query(default=None, alias="status", pattern=ALLOWED_STATUS),
    difficulty: str | None = Query(default=None, pattern=ALLOWED_DIFFICULTY),
    due_only: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    statement = select(AlgorithmProblem).order_by(AlgorithmProblem.updated_at.desc())
    if status_filter:
        statement = statement.where(AlgorithmProblem.status == status_filter)
    if difficulty:
        statement = statement.where(AlgorithmProblem.difficulty == difficulty)
    if due_only:
        statement = statement.where(
            AlgorithmProblem.status != "solved",
            (AlgorithmProblem.next_review_at.is_(None)) | (AlgorithmProblem.next_review_at <= date.today()),
        )
    return [_serialize(db, item) for item in db.scalars(statement)]


@router.get("/random")
def random_problem(db: Session = Depends(get_db)):
    due_statement = select(AlgorithmProblem).where(
        AlgorithmProblem.status != "solved",
        (AlgorithmProblem.next_review_at.is_(None)) | (AlgorithmProblem.next_review_at <= date.today()),
    ).order_by(func.random()).limit(1)
    item = db.scalars(due_statement).first()
    if item is None:
        item = db.scalars(select(AlgorithmProblem).order_by(func.random()).limit(1)).first()
    if item is None:
        raise HTTPException(status_code=404, detail="暂无可练习的算法题")
    return _serialize(db, item)


@router.get("/{problem_id}")
def get_problem(problem_id: UUID, db: Session = Depends(get_db)):
    return _serialize(db, _get_problem(db, problem_id))


@router.post("", status_code=status.HTTP_201_CREATED)
def create_problem(payload: AlgorithmProblemIn, db: Session = Depends(get_db)):
    _validate_canonical(db, payload.canonical_question_id)
    item = AlgorithmProblem(**payload.model_dump())
    db.add(item)
    db.flush()
    db.refresh(item)
    return _serialize(db, item)


@router.patch("/{problem_id}")
def update_problem(problem_id: UUID, payload: AlgorithmProblemPatch, db: Session = Depends(get_db)):
    item = _get_problem(db, problem_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="至少提供一个需要更新的字段")
    if "canonical_question_id" in changes:
        _validate_canonical(db, changes["canonical_question_id"])
    for key, value in changes.items():
        setattr(item, key, value)
    item.updated_at = datetime.now().astimezone()
    db.flush()
    db.refresh(item)
    return _serialize(db, item)


@router.post("/{problem_id}/practice")
def practice_problem(problem_id: UUID, payload: PracticeRequest, db: Session = Depends(get_db)):
    item = _get_problem(db, problem_id)
    item.status = payload.status
    item.mistake_reason = payload.mistake_reason
    item.review_notes = payload.review_notes
    item.next_review_at = payload.next_review_at
    item.last_practiced_at = datetime.now().astimezone()
    item.practice_count += 1
    item.updated_at = item.last_practiced_at
    db.flush()
    db.refresh(item)
    return _serialize(db, item)
