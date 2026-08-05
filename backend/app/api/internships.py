from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..internship_models import (
    Internship,
    InternshipExpressionVersion,
    InternshipFact,
    InternshipIntelligenceLink,
    InternshipMaterial,
)
from ..internship_schemas import (
    FactIn,
    FactPatch,
    IntelligenceLinkIn,
    InternshipIn,
    InternshipPatch,
    MaterialIn,
    MaterialPatch,
    VersionIn,
    VersionPatch,
)
from ..internships_service import get_internship, get_owned, serialize_internship, touch

router = APIRouter(prefix="/api/internships", tags=["internship-track"])


def require_changes(payload) -> dict:
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="至少提供一个需要更新的字段")
    return changes


def validate_period(started_on, ended_on) -> None:
    if started_on and ended_on and ended_on < started_on:
        raise HTTPException(status_code=422, detail="实习结束日期不能早于开始日期")


@router.get("")
def list_internships(db: Session = Depends(get_db)):
    rows = db.scalars(select(Internship).order_by(Internship.updated_at.desc()))
    return [serialize_internship(db, item) for item in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_internship(payload: InternshipIn, db: Session = Depends(get_db)):
    validate_period(payload.started_on, payload.ended_on)
    internship = Internship(**payload.model_dump())
    db.add(internship)
    db.flush()
    db.refresh(internship)
    return serialize_internship(db, internship)


@router.get("/{internship_id}")
def get_internship_detail(internship_id: UUID, db: Session = Depends(get_db)):
    return serialize_internship(db, get_internship(db, internship_id))


@router.patch("/{internship_id}")
def update_internship(internship_id: UUID, payload: InternshipPatch, db: Session = Depends(get_db)):
    internship = get_internship(db, internship_id)
    changes = require_changes(payload)
    validate_period(changes.get("started_on", internship.started_on), changes.get("ended_on", internship.ended_on))
    for key, value in changes.items():
        setattr(internship, key, value)
    touch(internship)
    db.flush()
    return serialize_internship(db, internship)


@router.post("/{internship_id}/facts", status_code=status.HTTP_201_CREATED)
def create_fact(internship_id: UUID, payload: FactIn, db: Session = Depends(get_db)):
    internship = get_internship(db, internship_id)
    if payload.origin == "ai_draft" and payload.confirmation_status == "confirmed":
        raise HTTPException(status_code=422, detail="AI 草稿必须先以待核实状态保存，再由用户确认")
    db.add(InternshipFact(internship_id=internship_id, **payload.model_dump()))
    touch(internship)
    db.flush()
    return serialize_internship(db, internship)


@router.patch("/{internship_id}/facts/{fact_id}")
def update_fact(internship_id: UUID, fact_id: UUID, payload: FactPatch, db: Session = Depends(get_db)):
    fact = get_owned(db, InternshipFact, fact_id, internship_id, "实习事实不存在")
    for key, value in require_changes(payload).items():
        setattr(fact, key, value)
    fact.updated_at = datetime.now().astimezone()
    internship = get_internship(db, internship_id)
    touch(internship)
    db.flush()
    return serialize_internship(db, internship)


@router.post("/{internship_id}/versions", status_code=status.HTTP_201_CREATED)
def create_version(internship_id: UUID, payload: VersionIn, db: Session = Depends(get_db)):
    internship = get_internship(db, internship_id, lock=True)
    if payload.based_on_version_id:
        get_owned(db, InternshipExpressionVersion, payload.based_on_version_id, internship_id, "基准表达版本不存在")
    last = db.scalar(select(InternshipExpressionVersion.version_number).where(
        InternshipExpressionVersion.internship_id == internship_id
    ).order_by(InternshipExpressionVersion.version_number.desc()).limit(1)) or 0
    db.add(InternshipExpressionVersion(internship_id=internship_id, version_number=last + 1, **payload.model_dump()))
    touch(internship)
    try:
        db.flush()
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="表达版本号冲突，请重试") from exc
    return serialize_internship(db, internship)


@router.patch("/{internship_id}/versions/{version_id}")
def update_version(internship_id: UUID, version_id: UUID, payload: VersionPatch, db: Session = Depends(get_db)):
    version = get_owned(db, InternshipExpressionVersion, version_id, internship_id, "表达版本不存在")
    if version.confirmation_status == "confirmed":
        raise HTTPException(status_code=409, detail="已确认版本不可覆盖，请基于历史创建新版本")
    for key, value in require_changes(payload).items():
        setattr(version, key, value)
    version.updated_at = datetime.now().astimezone()
    internship = get_internship(db, internship_id)
    touch(internship)
    db.flush()
    return serialize_internship(db, internship)


@router.post("/{internship_id}/versions/{version_id}/confirm")
def confirm_version(internship_id: UUID, version_id: UUID, db: Session = Depends(get_db)):
    version = get_owned(db, InternshipExpressionVersion, version_id, internship_id, "表达版本不存在")
    if version.confirmation_status == "draft":
        version.confirmation_status = "confirmed"
        version.confirmed_at = datetime.now().astimezone()
        version.updated_at = version.confirmed_at
    internship = get_internship(db, internship_id)
    touch(internship)
    db.flush()
    return serialize_internship(db, internship)


@router.post("/{internship_id}/materials", status_code=status.HTTP_201_CREATED)
def create_material(internship_id: UUID, payload: MaterialIn, db: Session = Depends(get_db)):
    internship = get_internship(db, internship_id)
    db.add(InternshipMaterial(internship_id=internship_id, **payload.model_dump()))
    touch(internship)
    db.flush()
    return serialize_internship(db, internship)


@router.patch("/{internship_id}/materials/{material_id}")
def update_material(internship_id: UUID, material_id: UUID, payload: MaterialPatch, db: Session = Depends(get_db)):
    material = get_owned(db, InternshipMaterial, material_id, internship_id, "实习材料不存在")
    for key, value in require_changes(payload).items():
        setattr(material, key, value)
    material.updated_at = datetime.now().astimezone()
    internship = get_internship(db, internship_id)
    touch(internship)
    db.flush()
    return serialize_internship(db, internship)


@router.post("/{internship_id}/intelligence", status_code=status.HTTP_201_CREATED)
def link_intelligence(internship_id: UUID, payload: IntelligenceLinkIn, db: Session = Depends(get_db)):
    internship = get_internship(db, internship_id)
    if db.execute(text("SELECT 1 FROM canonical_questions WHERE id = :id"), {"id": payload.canonical_question_id}).first() is None:
        raise HTTPException(status_code=404, detail="关联的规范题不存在")
    if payload.internship_fact_id:
        get_owned(db, InternshipFact, payload.internship_fact_id, internship_id, "关联的实习事实不存在")
    db.add(InternshipIntelligenceLink(internship_id=internship_id, **payload.model_dump()))
    touch(internship)
    try:
        db.flush()
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="该规范题已关联到实习") from exc
    return serialize_internship(db, internship)


@router.delete("/{internship_id}/intelligence/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_intelligence(internship_id: UUID, link_id: UUID, db: Session = Depends(get_db)):
    link = get_owned(db, InternshipIntelligenceLink, link_id, internship_id, "实习情报关联不存在")
    db.delete(link)
    touch(get_internship(db, internship_id))
