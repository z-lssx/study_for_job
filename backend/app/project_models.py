import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    target_role: Mapped[str | None] = mapped_column(String(160))
    summary: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), nullable=False, server_default=text("'active'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))


class ProjectEvidence(Base):
    __tablename__ = "project_evidence"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'user_recollection'"))
    source_reference: Mapped[str | None] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(String(24), nullable=False, server_default=text("'user'"))
    confirmation_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default=text("'draft'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    __table_args__ = (UniqueConstraint("id", "project_id", name="project_evidence_project_identity_unique"),)


class ProjectExpressionVersion(Base):
    __tablename__ = "project_expression_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    pitch_30s: Mapped[str | None] = mapped_column(Text)
    pitch_2m: Mapped[str | None] = mapped_column(Text)
    follow_up_tree: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    origin: Mapped[str] = mapped_column(String(24), nullable=False, server_default=text("'user'"))
    confirmation_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default=text("'draft'"))
    based_on_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    __table_args__ = (
        UniqueConstraint("project_id", "version_number", name="project_expression_versions_number_unique"),
        UniqueConstraint("id", "project_id", name="project_expression_versions_project_identity_unique"),
        ForeignKeyConstraint(
            ["based_on_version_id", "project_id"],
            ["project_expression_versions.id", "project_expression_versions.project_id"],
            name="project_expression_versions_base_same_project_fk",
            ondelete="RESTRICT",
        ),
    )


class ProjectIntelligenceLink(Base):
    __tablename__ = "project_intelligence_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    canonical_question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("canonical_questions.id", ondelete="RESTRICT"), nullable=False
    )
    project_evidence_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    relevance_note: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    __table_args__ = (
        UniqueConstraint("project_id", "canonical_question_id", name="project_intelligence_links_unique"),
        ForeignKeyConstraint(
            ["project_evidence_id", "project_id"],
            ["project_evidence.id", "project_evidence.project_id"],
            name="project_intelligence_links_evidence_same_project_fk",
            ondelete="RESTRICT",
        ),
    )
