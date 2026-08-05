from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from ..db import get_db
from ..export_service import generate_export


router = APIRouter(prefix="/api/exports", tags=["exports"])


class ExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: Literal["json", "markdown"]
    as_of_date: date


@router.post("/snapshots")
def create_export_snapshot(payload: ExportRequest, db: Session = Depends(get_db)):
    return generate_export(db, export_format=payload.format, as_of_date=payload.as_of_date)
