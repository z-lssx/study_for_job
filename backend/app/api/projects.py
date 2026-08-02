from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..project_models import Project, ProjectEvidence, ProjectExpressionVersion, ProjectIntelligenceLink
from ..projects_service import get_owned, get_project, serialize_project, touch_project

router = APIRouter(prefix="/api/projects", tags=["project-track"])
EVIDENCE_CATEGORIES = "^(background_goal|responsibility|team_boundary|technical_choice|tradeoff|metric|other)$"
SOURCE_KINDS = "^(user_recollection|document|repository|external_link|metric_record)$"


class ProjectIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=240)
    target_role: str | None = Field(default=None, max_length=160)
    summary: str | None = Field(default=None, max_length=2000)
    status: str = Field(default="active", pattern="^(active|archived)$")


class ProjectPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str | None = Field(default=None, min_length=1, max_length=240)
    target_role: str | None = Field(default=None, max_length=160)
    summary: str | None = Field(default=None, max_length=2000)
    status: str | None = Field(default=None, pattern="^(active|archived)$")


class EvidenceIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    category: str = Field(pattern=EVIDENCE_CATEGORIES)
    statement: str = Field(min_length=1, max_length=10000)
    source_kind: str = Field(default="user_recollection", pattern=SOURCE_KINDS)
    source_reference: str | None = Field(default=None, max_length=2048)
    origin: str = Field(default="user", pattern="^(user|ai_draft)$")
    confirmation_status: str = Field(default="draft", pattern="^(draft|confirmed)$")


class EvidencePatch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    category: str | None = Field(default=None, pattern=EVIDENCE_CATEGORIES)
    statement: str | None = Field(default=None, min_length=1, max_length=10000)
    source_kind: str | None = Field(default=None, pattern=SOURCE_KINDS)
    source_reference: str | None = Field(default=None, max_length=2048)
    confirmation_status: str | None = Field(default=None, pattern="^(draft|confirmed)$")


class FollowUpItem(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=500)
    answer_note: str | None = Field(default=None, max_length=2000)


class VersionIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    label: str = Field(min_length=1, max_length=120)
    pitch_30s: str | None = Field(default=None, max_length=4000)
    pitch_2m: str | None = Field(default=None, max_length=12000)
    follow_up_tree: list[FollowUpItem] = Field(default_factory=list, max_length=30)
    origin: str = Field(default="user", pattern="^(user|ai_draft)$")
    based_on_version_id: UUID | None = None


class VersionPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    label: str | None = Field(default=None, min_length=1, max_length=120)
    pitch_30s: str | None = Field(default=None, max_length=4000)
    pitch_2m: str | None = Field(default=None, max_length=12000)
    follow_up_tree: list[FollowUpItem] | None = Field(default=None, max_length=30)


class IntelligenceLinkIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    canonical_question_id: UUID
    project_evidence_id: UUID | None = None
    relevance_note: str = Field(min_length=1, max_length=2000)


def _save_error(message: str, exc: IntegrityError) -> HTTPException:
    return HTTPException(status_code=409, detail=message)


@router.get("")
def list_projects(db: Session = Depends(get_db)):
    return [serialize_project(db, project) for project in db.scalars(select(Project).order_by(Project.updated_at.desc()))]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectIn, db: Session = Depends(get_db)):
    project = Project(**payload.model_dump())
    db.add(project)
    db.flush()
    db.refresh(project)
    return serialize_project(db, project)


@router.get("/{project_id}")
def get_project_detail(project_id: UUID, db: Session = Depends(get_db)):
    return serialize_project(db, get_project(db, project_id))


@router.patch("/{project_id}")
def update_project(project_id: UUID, payload: ProjectPatch, db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="至少提供一个需要更新的字段")
    for key, value in changes.items():
        setattr(project, key, value)
    touch_project(project)
    db.flush()
    db.refresh(project)
    return serialize_project(db, project)


@router.post("/{project_id}/evidence", status_code=status.HTTP_201_CREATED)
def create_evidence(project_id: UUID, payload: EvidenceIn, db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    if payload.origin == "ai_draft" and payload.confirmation_status == "confirmed":
        raise HTTPException(status_code=422, detail="AI 草稿必须先以待核实状态保存，再由用户确认")
    evidence = ProjectEvidence(project_id=project_id, **payload.model_dump())
    db.add(evidence)
    touch_project(project)
    db.flush()
    db.refresh(evidence)
    return serialize_project(db, get_project(db, project_id))


@router.patch("/{project_id}/evidence/{evidence_id}")
def update_evidence(project_id: UUID, evidence_id: UUID, payload: EvidencePatch, db: Session = Depends(get_db)):
    evidence = get_owned(db, ProjectEvidence, evidence_id, project_id, "项目证据不存在")
    changes = payload.model_dump(exclude_unset=True)
    if not changes: raise HTTPException(status_code=422, detail="至少提供一个需要更新的字段")
    for key, value in changes.items():
        setattr(evidence, key, value)
    evidence.updated_at = datetime.now().astimezone()
    project = get_project(db, project_id)
    touch_project(project)
    db.flush()
    return serialize_project(db, project)


@router.post("/{project_id}/versions", status_code=status.HTTP_201_CREATED)
def create_version(project_id: UUID, payload: VersionIn, db: Session = Depends(get_db)):
    project = get_project(db, project_id, lock=True)
    if payload.based_on_version_id:
        get_owned(
            db,
            ProjectExpressionVersion,
            payload.based_on_version_id,
            project_id,
            "基准表达版本不存在",
        )
    last = db.scalar(
        select(ProjectExpressionVersion.version_number)
        .where(ProjectExpressionVersion.project_id == project_id)
        .order_by(ProjectExpressionVersion.version_number.desc())
        .limit(1)
    ) or 0
    version = ProjectExpressionVersion(project_id=project_id, version_number=last + 1, **payload.model_dump())
    db.add(version)
    touch_project(project)
    try:
        db.flush()
    except IntegrityError as exc:
        raise _save_error("表达版本号冲突，请重试", exc) from exc
    return serialize_project(db, project)


@router.patch("/{project_id}/versions/{version_id}")
def update_version(project_id: UUID, version_id: UUID, payload: VersionPatch, db: Session = Depends(get_db)):
    version = get_owned(db, ProjectExpressionVersion, version_id, project_id, "表达版本不存在")
    if version.confirmation_status == "confirmed":
        raise HTTPException(status_code=409, detail="已确认版本不可覆盖，请创建新版本保留历史")
    changes = payload.model_dump(exclude_unset=True)
    if not changes: raise HTTPException(status_code=422, detail="至少提供一个需要更新的字段")
    for key, value in changes.items():
        setattr(version, key, value)
    version.updated_at = datetime.now().astimezone()
    project = get_project(db, project_id)
    touch_project(project)
    db.flush()
    return serialize_project(db, project)


@router.post("/{project_id}/versions/{version_id}/confirm")
def confirm_version(project_id: UUID, version_id: UUID, db: Session = Depends(get_db)):
    version = get_owned(db, ProjectExpressionVersion, version_id, project_id, "表达版本不存在")
    if version.confirmation_status == "confirmed":
        return serialize_project(db, get_project(db, project_id))
    version.confirmation_status = "confirmed"
    version.confirmed_at = datetime.now().astimezone()
    version.updated_at = version.confirmed_at
    project = get_project(db, project_id)
    touch_project(project)
    db.flush()
    return serialize_project(db, project)


@router.post("/{project_id}/intelligence", status_code=status.HTTP_201_CREATED)
def link_intelligence(project_id: UUID, payload: IntelligenceLinkIn, db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    if db.execute(text("SELECT 1 FROM canonical_questions WHERE id = :id"), {"id": payload.canonical_question_id}).first() is None:
        raise HTTPException(status_code=404, detail="关联的规范题不存在")
    if payload.project_evidence_id:
        get_owned(db, ProjectEvidence, payload.project_evidence_id, project_id, "关联的项目证据不存在")
    link = ProjectIntelligenceLink(project_id=project_id, **payload.model_dump())
    db.add(link)
    touch_project(project)
    try:
        db.flush()
    except IntegrityError as exc:
        raise _save_error("该规范题已关联到项目", exc) from exc
    return serialize_project(db, project)


@router.delete("/{project_id}/intelligence/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_intelligence(project_id: UUID, link_id: UUID, db: Session = Depends(get_db)):
    link = get_owned(db, ProjectIntelligenceLink, link_id, project_id, "项目情报关联不存在")
    db.delete(link)
    project = get_project(db, project_id)
    touch_project(project)
