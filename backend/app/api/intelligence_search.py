from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..intelligence.search import IntelligenceSearchRepository

router = APIRouter(prefix="/api/intelligence", tags=["interview-intelligence"])


@router.get("/search")
def search_intelligence(
    q: str = Query(min_length=1, max_length=200),
    round_ordinal: int | None = Query(default=None, ge=1),
    field_kind: str | None = Query(default=None, pattern="^(question|follow_up)$"),
    source_host: str | None = Query(default=None, max_length=253),
    limit: int = Query(default=40, ge=1, le=100),
    db: Session = Depends(get_db),
):
    if not q.strip():
        raise HTTPException(status_code=422, detail="搜索词不能为空")
    result = IntelligenceSearchRepository.search(
        db,
        q,
        round_ordinal,
        field_kind,
        source_host.strip() if source_host and source_host.strip() else None,
        limit,
    )
    return _serialize(result)


@router.get("/quality")
def intelligence_quality(db: Session = Depends(get_db)):
    return _serialize(IntelligenceSearchRepository.quality(db))


def _serialize(value):
    if isinstance(value, (UUID, datetime)):
        return str(value) if isinstance(value, UUID) else value.isoformat()
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    return value
