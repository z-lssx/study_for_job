import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base


class Internship(Base):
    __tablename__ = "internships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    organization: Mapped[str] = mapped_column(Text, nullable=False)
    role_title: Mapped[str] = mapped_column(String(160), nullable=False)
    started_on: Mapped[date | None] = mapped_column(Date)
    ended_on: Mapped[date | None] = mapped_column(Date)
    summary: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), nullable=False, server_default=text("'active'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))


class InternshipFact(Base):
    __tablename__ = "internship_facts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    internship_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("internships.id", ondelete="CASCADE"), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'user_recollection'"))
    source_reference: Mapped[str | None] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(String(24), nullable=False, server_default=text("'user'"))
    confirmation_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default=text("'draft'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    __table_args__ = (UniqueConstraint("id", "internship_id", name="internship_facts_internship_identity_unique"),)


class InternshipExpressionVersion(Base):
    __tablename__ = "internship_expression_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    internship_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("internships.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    situation: Mapped[str | None] = mapped_column(Text)
    task: Mapped[str | None] = mapped_column(Text)
    action: Mapped[str | None] = mapped_column(Text)
    result: Mapped[str | None] = mapped_column(Text)
    quantified_pitch: Mapped[str | None] = mapped_column(Text)
    follow_up_tree: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    origin: Mapped[str] = mapped_column(String(24), nullable=False, server_default=text("'user'"))
    confirmation_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default=text("'draft'"))
    based_on_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    __table_args__ = (
        UniqueConstraint("internship_id", "version_number", name="internship_versions_number_unique"),
        UniqueConstraint("id", "internship_id", name="internship_versions_internship_identity_unique"),
        ForeignKeyConstraint(
            ["based_on_version_id", "internship_id"],
            ["internship_expression_versions.id", "internship_expression_versions.internship_id"],
            name="internship_versions_base_same_internship_fk",
            ondelete="RESTRICT",
        ),
    )


class InternshipMaterial(Base):
    __tablename__ = "internship_materials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    internship_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("internships.id", ondelete="CASCADE"), nullable=False)
    material_type: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(240), nullable=False)
    locator: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    preparation_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default=text("'missing'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    __table_args__ = (UniqueConstraint("id", "internship_id", name="internship_materials_internship_identity_unique"),)


class InternshipIntelligenceLink(Base):
    __tablename__ = "internship_intelligence_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    internship_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("internships.id", ondelete="CASCADE"), nullable=False)
    canonical_question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("canonical_questions.id", ondelete="RESTRICT"), nullable=False)
    internship_fact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    relevance_note: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    __table_args__ = (
        UniqueConstraint("internship_id", "canonical_question_id", name="internship_intelligence_links_unique"),
        ForeignKeyConstraint(
            ["internship_fact_id", "internship_id"],
            ["internship_facts.id", "internship_facts.internship_id"],
            name="internship_links_fact_same_internship_fk",
            ondelete="RESTRICT",
        ),
    )
