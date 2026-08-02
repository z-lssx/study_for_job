from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (
    DocumentChunk,
    EvidenceSpan,
    ExtractionRun,
    InterviewDocument,
    InterviewSource,
    InterviewSubmission,
    KnowledgeCard,
    KnowledgeCardEvidence,
)

router = APIRouter(prefix="/api/knowledge", tags=["knowledge-track"])


class KnowledgeCardIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=240)
    prompt: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=10000)
    mastery_status: str = Field(default="not_started", pattern="^(not_started|learning|familiar|mastered)$")
    origin: str = Field(default="user", pattern="^(user|intelligence_suggestion)$")
    next_review_at: date | None = None
    evidence_span_ids: list[UUID] = Field(default_factory=list, max_length=20)


class KnowledgeCardPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=240)
    prompt: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=10000)
    mastery_status: str | None = Field(default=None, pattern="^(not_started|learning|familiar|mastered)$")
    next_review_at: date | None = None


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    mastery_status: str = Field(pattern="^(not_started|learning|familiar|mastered)$")
    next_review_at: date | None = None


class EvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    evidence_span_id: UUID
    note_text: str | None = Field(default=None, max_length=1000)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _evidence(db: Session, card_id: UUID) -> list[dict]:
    statement = (
        select(KnowledgeCardEvidence, EvidenceSpan, DocumentChunk, ExtractionRun, InterviewDocument)
        .join(EvidenceSpan, EvidenceSpan.id == KnowledgeCardEvidence.evidence_span_id)
        .join(DocumentChunk, DocumentChunk.id == EvidenceSpan.chunk_id)
        .join(ExtractionRun, ExtractionRun.id == EvidenceSpan.run_id)
        .join(InterviewDocument, InterviewDocument.id == ExtractionRun.document_id)
        .where(KnowledgeCardEvidence.card_id == card_id)
        .order_by(KnowledgeCardEvidence.created_at.asc())
    )
    result = []
    for link, span, chunk, run, document in db.execute(statement).all():
        submission = db.scalars(
            select(InterviewSubmission)
            .where(InterviewSubmission.document_id == document.id)
            .order_by(InterviewSubmission.submitted_at.desc())
            .limit(1)
        ).first()
        source = db.get(InterviewSource, submission.source_id) if submission and submission.source_id else None
        quote = document.cleaned_content[span.start_char : span.end_char]
        result.append(
            {
                "evidence_span_id": str(span.id),
                "field_name": span.field_name,
                "start_char": span.start_char,
                "end_char": span.end_char,
                "quote": quote,
                "note_text": link.note_text,
                "document_id": str(document.id),
                "submission_id": str(submission.id) if submission else None,
                "source": {"url": source.source_url, "host": source.host} if source else None,
                "chunk_id": str(chunk.id),
                "run_id": str(run.id),
            }
        )
    return result


def _serialize(db: Session, card: KnowledgeCard) -> dict:
    return {
        "id": str(card.id),
        "title": card.title,
        "prompt": card.prompt,
        "notes": card.notes,
        "mastery_status": card.mastery_status,
        "origin": card.origin,
        "last_reviewed_at": _iso(card.last_reviewed_at),
        "next_review_at": card.next_review_at.isoformat() if card.next_review_at else None,
        "review_count": card.review_count,
        "created_at": _iso(card.created_at),
        "updated_at": _iso(card.updated_at),
        "evidence": _evidence(db, card.id),
    }


def _get_card(db: Session, card_id: UUID) -> KnowledgeCard:
    card = db.get(KnowledgeCard, card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="知识卡片不存在")
    return card


@router.get("/cards")
def list_cards(
    status_filter: str | None = Query(default=None, alias="status", pattern="^(not_started|learning|familiar|mastered)$"),
    due_only: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    statement = select(KnowledgeCard).order_by(KnowledgeCard.updated_at.desc())
    if status_filter:
        statement = statement.where(KnowledgeCard.mastery_status == status_filter)
    if due_only:
        statement = statement.where(
            KnowledgeCard.mastery_status != "mastered",
            (KnowledgeCard.next_review_at.is_(None)) | (KnowledgeCard.next_review_at <= date.today()),
        )
    return [_serialize(db, card) for card in db.scalars(statement)]


@router.get("/cards/{card_id}")
def get_card(card_id: UUID, db: Session = Depends(get_db)):
    return _serialize(db, _get_card(db, card_id))


@router.post("/cards", status_code=status.HTTP_201_CREATED)
def create_card(payload: KnowledgeCardIn, response: Response, db: Session = Depends(get_db)):
    card = KnowledgeCard(**payload.model_dump(exclude={"evidence_span_ids"}))
    db.add(card)
    db.flush()
    _attach_evidence(db, card.id, payload.evidence_span_ids)
    db.refresh(card)
    response.status_code = status.HTTP_201_CREATED
    return _serialize(db, card)


@router.patch("/cards/{card_id}")
def update_card(card_id: UUID, payload: KnowledgeCardPatch, db: Session = Depends(get_db)):
    card = _get_card(db, card_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="至少提供一个需要更新的字段")
    for key, value in changes.items():
        setattr(card, key, value)
    card.updated_at = datetime.now().astimezone()
    db.flush()
    db.refresh(card)
    return _serialize(db, card)


@router.post("/cards/{card_id}/review")
def review_card(card_id: UUID, payload: ReviewRequest, db: Session = Depends(get_db)):
    card = _get_card(db, card_id)
    card.mastery_status = payload.mastery_status
    card.next_review_at = payload.next_review_at
    card.last_reviewed_at = datetime.now().astimezone()
    card.review_count += 1
    card.updated_at = card.last_reviewed_at
    db.flush()
    db.refresh(card)
    return _serialize(db, card)


@router.post("/cards/{card_id}/evidence")
def add_evidence(card_id: UUID, payload: EvidenceRequest, db: Session = Depends(get_db)):
    _get_card(db, card_id)
    if db.get(EvidenceSpan, payload.evidence_span_id) is None:
        raise HTTPException(status_code=404, detail="证据片段不存在")
    link = KnowledgeCardEvidence(card_id=card_id, evidence_span_id=payload.evidence_span_id, note_text=payload.note_text)
    db.add(link)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="该证据已关联到知识卡片") from exc
    return _serialize(db, _get_card(db, card_id))


@router.delete("/cards/{card_id}/evidence/{evidence_span_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_evidence(card_id: UUID, evidence_span_id: UUID, db: Session = Depends(get_db)):
    _get_card(db, card_id)
    link = db.get(KnowledgeCardEvidence, {"card_id": card_id, "evidence_span_id": evidence_span_id})
    if link is None:
        raise HTTPException(status_code=404, detail="证据关联不存在")
    db.delete(link)


def _attach_evidence(db: Session, card_id: UUID, evidence_ids: list[UUID]) -> None:
    unique_ids = list(dict.fromkeys(evidence_ids))
    for evidence_id in unique_ids:
        if db.get(EvidenceSpan, evidence_id) is None:
            raise HTTPException(status_code=404, detail="证据片段不存在")
        db.add(KnowledgeCardEvidence(card_id=card_id, evidence_span_id=evidence_id))
    db.flush()
