from datetime import date, datetime
from typing import Optional
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import get_settings
from .api.admin_ai import router as admin_ai_router
from .api.admin_jobs import router as admin_jobs_router
from .api.algorithms import router as algorithms_router
from .api.canonical_questions import router as canonical_questions_router
from .api.intelligence import router as intelligence_router
from .api.intelligence_search import router as intelligence_search_router
from .api.internships import router as internships_router
from .api.knowledge import router as knowledge_router
from .api.projects import router as projects_router
from .db import engine, get_db
from .models import Application, TargetProfile

settings = get_settings()
app = FastAPI(title="study_for_job API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[item.strip() for item in settings.cors_origins.split(",") if item.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(admin_ai_router)
app.include_router(admin_jobs_router)
app.include_router(algorithms_router)
app.include_router(intelligence_router)
app.include_router(intelligence_search_router)
app.include_router(canonical_questions_router)
app.include_router(internships_router)
app.include_router(knowledge_router)
app.include_router(projects_router)


@app.exception_handler(RequestValidationError)
async def validation_error_without_input(_request, exc: RequestValidationError):
    safe_errors = [
        {key: value for key, value in error.items() if key not in {"input", "ctx"}}
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": safe_errors})


class ProfileIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=120)
    location: Optional[str] = Field(default=None, max_length=120)
    focus: Optional[str] = Field(default=None, max_length=200)
    summary: Optional[str] = Field(default=None, max_length=1000)


class ProfilePatch(ProfileIn):
    title: Optional[str] = Field(default=None, min_length=1, max_length=120)


class ApplicationIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    company: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=160)
    stage: str = Field(pattern="^(saved|applied|interview|offer|closed)$")
    key_date: Optional[date] = None
    next_action: Optional[str] = Field(default=None, max_length=300)
    channel: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = Field(default=None, max_length=2000)
    url: Optional[HttpUrl] = None


class ApplicationPatch(ApplicationIn):
    company: Optional[str] = Field(default=None, min_length=1, max_length=120)
    role: Optional[str] = Field(default=None, min_length=1, max_length=160)
    stage: Optional[str] = Field(default=None, pattern="^(saved|applied|interview|offer|closed)$")


def serialize(entity):
    result = {}
    for column in entity.__table__.columns:
        value = getattr(entity, column.name)
        if isinstance(value, UUID):
            value = str(value)
        elif isinstance(value, (date, datetime)):
            value = value.isoformat()
        result[column.name] = value
    return result


def integrity_conflict() -> HTTPException:
    return HTTPException(status_code=409, detail="同一公司与岗位的投递记录已存在")


@app.get("/api/health")
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": "ok",
            "database_name": settings.postgres_db,
            "environment": settings.app_environment,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"status": "degraded", "database": "unavailable", "reason": str(exc)},
        ) from exc


@app.get("/api/target-profiles")
def list_profiles(db: Session = Depends(get_db)):
    return [serialize(profile) for profile in db.scalars(select(TargetProfile).order_by(TargetProfile.updated_at.desc()))]


@app.post("/api/target-profiles", status_code=status.HTTP_201_CREATED)
def create_profile(payload: ProfileIn, db: Session = Depends(get_db)):
    profile = TargetProfile(**payload.model_dump())
    db.add(profile)
    db.flush()
    db.refresh(profile)
    return serialize(profile)


@app.get("/api/target-profiles/{profile_id}")
def get_profile(profile_id: UUID, db: Session = Depends(get_db)):
    profile = db.get(TargetProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="目标岗位画像不存在")
    return serialize(profile)


@app.patch("/api/target-profiles/{profile_id}")
def update_profile(profile_id: UUID, payload: ProfilePatch, db: Session = Depends(get_db)):
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="至少提供一个需要更新的字段")
    profile = db.get(TargetProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="目标岗位画像不存在")
    for key, value in changes.items():
        setattr(profile, key, value)
    profile.updated_at = datetime.now().astimezone()
    db.flush()
    db.refresh(profile)
    return serialize(profile)


@app.get("/api/applications")
def list_applications(db: Session = Depends(get_db)):
    statement = select(Application).order_by(Application.key_date.asc().nulls_last(), Application.updated_at.desc())
    return [serialize(application) for application in db.scalars(statement)]


@app.get("/api/applications/{application_id}")
def get_application(application_id: UUID, db: Session = Depends(get_db)):
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="投递记录不存在")
    return serialize(application)


@app.post("/api/applications", status_code=status.HTTP_201_CREATED)
def create_application(payload: ApplicationIn, db: Session = Depends(get_db)):
    application = Application(**payload.model_dump())
    application.url = str(payload.url) if payload.url else None
    db.add(application)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise integrity_conflict() from exc
    db.refresh(application)
    return serialize(application)


@app.patch("/api/applications/{application_id}")
def update_application(application_id: UUID, payload: ApplicationPatch, db: Session = Depends(get_db)):
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="至少提供一个需要更新的字段")
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="投递记录不存在")
    if "url" in changes and changes["url"] is not None:
        changes["url"] = str(changes["url"])
    for key, value in changes.items():
        setattr(application, key, value)
    application.updated_at = datetime.now().astimezone()
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise integrity_conflict() from exc
    db.refresh(application)
    return serialize(application)
