from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


FACT_CATEGORIES = "^(responsibility|team_boundary|technical_context|collaboration_context|challenge|result|metric|other)$"
SOURCE_KINDS = "^(user_recollection|document|work_item|external_link|metric_record)$"
MATERIAL_TYPES = "^(resume_bullet|work_sample|evidence_document|reference_link|other)$"
MATERIAL_STATUSES = "^(missing|draft|ready|verified)$"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class InternshipIn(StrictModel):
    organization: str = Field(min_length=1, max_length=240)
    role_title: str = Field(min_length=1, max_length=160)
    started_on: date | None = None
    ended_on: date | None = None
    summary: str | None = Field(default=None, max_length=2000)
    status: str = Field(default="active", pattern="^(active|archived)$")


class InternshipPatch(StrictModel):
    organization: str | None = Field(default=None, min_length=1, max_length=240)
    role_title: str | None = Field(default=None, min_length=1, max_length=160)
    started_on: date | None = None
    ended_on: date | None = None
    summary: str | None = Field(default=None, max_length=2000)
    status: str | None = Field(default=None, pattern="^(active|archived)$")


class FactIn(StrictModel):
    category: str = Field(pattern=FACT_CATEGORIES)
    statement: str = Field(min_length=1, max_length=10000)
    source_kind: str = Field(default="user_recollection", pattern=SOURCE_KINDS)
    source_reference: str | None = Field(default=None, max_length=2048)
    origin: str = Field(default="user", pattern="^(user|ai_draft)$")
    confirmation_status: str = Field(default="draft", pattern="^(draft|confirmed)$")


class FactPatch(StrictModel):
    category: str | None = Field(default=None, pattern=FACT_CATEGORIES)
    statement: str | None = Field(default=None, min_length=1, max_length=10000)
    source_kind: str | None = Field(default=None, pattern=SOURCE_KINDS)
    source_reference: str | None = Field(default=None, max_length=2048)
    confirmation_status: str | None = Field(default=None, pattern="^(draft|confirmed)$")


class FollowUpItem(StrictModel):
    question: str = Field(min_length=1, max_length=500)
    answer_note: str | None = Field(default=None, max_length=2000)


class VersionIn(StrictModel):
    label: str = Field(min_length=1, max_length=120)
    situation: str | None = Field(default=None, max_length=4000)
    task: str | None = Field(default=None, max_length=4000)
    action: str | None = Field(default=None, max_length=8000)
    result: str | None = Field(default=None, max_length=4000)
    quantified_pitch: str | None = Field(default=None, max_length=4000)
    follow_up_tree: list[FollowUpItem] = Field(default_factory=list, max_length=30)
    origin: str = Field(default="user", pattern="^(user|ai_draft)$")
    based_on_version_id: UUID | None = None


class VersionPatch(StrictModel):
    label: str | None = Field(default=None, min_length=1, max_length=120)
    situation: str | None = Field(default=None, max_length=4000)
    task: str | None = Field(default=None, max_length=4000)
    action: str | None = Field(default=None, max_length=8000)
    result: str | None = Field(default=None, max_length=4000)
    quantified_pitch: str | None = Field(default=None, max_length=4000)
    follow_up_tree: list[FollowUpItem] | None = Field(default=None, max_length=30)


class MaterialIn(StrictModel):
    material_type: str = Field(pattern=MATERIAL_TYPES)
    label: str = Field(min_length=1, max_length=240)
    locator: str | None = Field(default=None, max_length=2048)
    notes: str | None = Field(default=None, max_length=4000)
    preparation_status: str = Field(default="missing", pattern=MATERIAL_STATUSES)


class MaterialPatch(StrictModel):
    material_type: str | None = Field(default=None, pattern=MATERIAL_TYPES)
    label: str | None = Field(default=None, min_length=1, max_length=240)
    locator: str | None = Field(default=None, max_length=2048)
    notes: str | None = Field(default=None, max_length=4000)
    preparation_status: str | None = Field(default=None, pattern=MATERIAL_STATUSES)


class IntelligenceLinkIn(StrictModel):
    canonical_question_id: UUID
    internship_fact_id: UUID | None = None
    relevance_note: str = Field(min_length=1, max_length=2000)
