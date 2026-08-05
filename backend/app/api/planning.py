from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from ..db import get_db
from ..planning_service import generate_assessment


router = APIRouter(prefix="/api/planning", tags=["planning"])


class InterviewContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    application_id: UUID
    interview_date: date


class AssessmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["daily", "weekly", "pre_interview"]
    as_of_date: date
    target_profile_id: UUID | None = None
    interview_context: InterviewContext | None = None


@router.post("/assessments")
def create_assessment(payload: AssessmentRequest, db: Session = Depends(get_db)):
    return generate_assessment(
        db,
        mode=payload.mode,
        as_of_date=payload.as_of_date,
        target_profile_id=payload.target_profile_id,
        interview_context=payload.interview_context.model_dump() if payload.interview_context else None,
    )
