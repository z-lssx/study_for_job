from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ...models import EvidenceSpan, ExtractionRun, InterviewDocument, InterviewRound, QuestionCandidate
from .models import CanonicalQuestion, QuestionMappingRevision, QuestionOccurrence, QuestionOccurrenceMapping
from .text import normalize_question_text, occurrence_key, question_normalization_key


@dataclass(frozen=True)
class RefreshResult:
    candidate_count: int
    occurrence_count: int
    canonical_count: int
    mapping_count: int
    skipped_without_evidence: int


class CanonicalQuestionRepository:
    @staticmethod
    def refresh(session: Session) -> RefreshResult:
        rows = session.execute(
            select(QuestionCandidate, ExtractionRun, InterviewDocument, InterviewRound, EvidenceSpan)
            .join(ExtractionRun, ExtractionRun.id == QuestionCandidate.run_id)
            .join(InterviewDocument, InterviewDocument.id == ExtractionRun.document_id)
            .outerjoin(InterviewRound, InterviewRound.id == QuestionCandidate.round_id)
            .outerjoin(EvidenceSpan, EvidenceSpan.candidate_id == QuestionCandidate.id)
            .where(ExtractionRun.status == "succeeded")
            .order_by(InterviewDocument.id, QuestionCandidate.start_char, QuestionCandidate.id)
        ).all()
        created_occurrences = created_canonical = created_mappings = skipped = 0
        for candidate, run, document, round_row, evidence in rows:
            if evidence is None:
                skipped += 1
                continue
            normalized = normalize_question_text(candidate.extracted_text)
            normalization_key = question_normalization_key(normalized)
            canonical_id, canonical_created = CanonicalQuestionRepository._canonical(
                session, normalized, normalization_key, "automatic"
            )
            created_canonical += int(canonical_created)
            identity = occurrence_key(document.id, round_row.ordinal if round_row else None, normalization_key)
            occurrence_id = session.execute(
                insert(QuestionOccurrence)
                .values(
                    candidate_id=candidate.id,
                    document_id=document.id,
                    run_id=run.id,
                    round_id=round_row.id if round_row else None,
                    chunk_id=candidate.chunk_id,
                    evidence_span_id=evidence.id,
                    occurrence_key=identity,
                    raw_text=candidate.extracted_text,
                    normalized_text=normalized,
                    normalization_key=normalization_key,
                    field_kind=candidate.field_kind,
                    round_ordinal=round_row.ordinal if round_row else None,
                )
                .on_conflict_do_nothing()
                .returning(QuestionOccurrence.id)
            ).scalar_one_or_none()
            if occurrence_id is None:
                continue
            created_occurrences += 1
            mapping_id = session.execute(
                insert(QuestionOccurrenceMapping)
                .values(
                    occurrence_id=occurrence_id,
                    canonical_question_id=canonical_id,
                    mapping_origin="automatic",
                    mapping_status="automatic",
                    revision=1,
                )
                .on_conflict_do_nothing(index_elements=[QuestionOccurrenceMapping.occurrence_id])
                .returning(QuestionOccurrenceMapping.occurrence_id)
            ).scalar_one_or_none()
            created_mappings += int(mapping_id is not None)
        return RefreshResult(len(rows), created_occurrences, created_canonical, created_mappings, skipped)

    @staticmethod
    def list_frequency(session: Session, search: str | None, round_ordinal: int | None, limit: int) -> list[dict]:
        return [dict(row) for row in session.execute(text("""
            SELECT cq.id, cq.canonical_text, cq.created_by,
                   COUNT(o.id)::int AS occurrence_count,
                   COUNT(DISTINCT o.document_id)::int AS document_count,
                   MIN(d.collected_at) AS first_seen_at,
                   MAX(d.collected_at) AS last_seen_at,
                   COUNT(*) FILTER (WHERE m.mapping_origin = 'manual')::int AS manually_mapped_count
            FROM canonical_questions cq
            JOIN question_occurrence_mappings m ON m.canonical_question_id = cq.id
            JOIN question_occurrences o ON o.id = m.occurrence_id
            JOIN interview_documents d ON d.id = o.document_id
            WHERE (CAST(:search AS text) IS NULL OR cq.canonical_text ILIKE '%' || CAST(:search AS text) || '%')
              AND (CAST(:round_ordinal AS integer) IS NULL OR o.round_ordinal = CAST(:round_ordinal AS integer))
            GROUP BY cq.id, cq.canonical_text, cq.created_by
            ORDER BY COUNT(o.id) DESC, MAX(d.collected_at) DESC, cq.canonical_text
            LIMIT :limit
        """), {"search": search, "round_ordinal": round_ordinal, "limit": limit}).mappings()]

    @staticmethod
    def detail(session: Session, canonical_id: UUID) -> dict | None:
        canonical = session.get(CanonicalQuestion, canonical_id)
        if canonical is None:
            return None
        rows = session.execute(text("""
            SELECT o.id, o.candidate_id, o.document_id, o.run_id, o.round_id, o.chunk_id,
                   o.evidence_span_id, o.raw_text, o.normalized_text, o.field_kind, o.round_ordinal,
                   o.created_at, m.mapping_origin, m.mapping_status, m.revision AS mapping_revision,
                   d.title AS document_title, d.collected_at, r.label AS round_label,
                   ch.ordinal AS chunk_ordinal, es.start_char, es.end_char,
                   substring(d.cleaned_content from es.start_char + 1 for es.end_char - es.start_char) AS evidence_text,
                   src.source_url, sub.id AS submission_id,
                   (SELECT COUNT(*) FROM question_mapping_revisions mr WHERE mr.occurrence_id = o.id)::int AS revision_count
            FROM question_occurrence_mappings m
            JOIN question_occurrences o ON o.id = m.occurrence_id
            JOIN interview_documents d ON d.id = o.document_id
            LEFT JOIN interview_rounds r ON r.id = o.round_id
            JOIN document_chunks ch ON ch.id = o.chunk_id
            JOIN evidence_spans es ON es.id = o.evidence_span_id
            LEFT JOIN interview_sources src ON src.id = d.first_source_id
            LEFT JOIN LATERAL (
              SELECT id FROM interview_submissions s WHERE s.document_id = d.id ORDER BY s.created_at LIMIT 1
            ) sub ON TRUE
            WHERE m.canonical_question_id = :canonical_id
            ORDER BY d.collected_at DESC, o.round_ordinal NULLS LAST, es.start_char
        """), {"canonical_id": canonical_id}).mappings()
        return {
            "id": canonical.id,
            "canonical_text": canonical.canonical_text,
            "normalization_key": canonical.normalization_key,
            "created_by": canonical.created_by,
            "occurrences": [dict(row) for row in rows],
        }

    @staticmethod
    def merge(session: Session, source_id: UUID, target_id: UUID, note: str | None) -> int:
        if source_id == target_id:
            raise ValueError("source_and_target_match")
        CanonicalQuestionRepository._require_canonical(session, source_id)
        CanonicalQuestionRepository._require_canonical(session, target_id)
        mappings = list(session.scalars(
            select(QuestionOccurrenceMapping)
            .where(QuestionOccurrenceMapping.canonical_question_id == source_id)
            .with_for_update()
        ))
        for mapping in mappings:
            CanonicalQuestionRepository._remap(session, mapping, target_id, "merge", note)
        return len(mappings)

    @staticmethod
    def split(session: Session, source_id: UUID, occurrence_ids: list[UUID], canonical_text: str, note: str | None) -> tuple[UUID, int]:
        CanonicalQuestionRepository._require_canonical(session, source_id)
        normalized = normalize_question_text(canonical_text)
        target_id, _created = CanonicalQuestionRepository._canonical(
            session, normalized, question_normalization_key(normalized), "manual"
        )
        if target_id == source_id:
            raise ValueError("split_target_matches_source")
        mappings = list(session.scalars(
            select(QuestionOccurrenceMapping)
            .where(
                QuestionOccurrenceMapping.occurrence_id.in_(occurrence_ids),
                QuestionOccurrenceMapping.canonical_question_id == source_id,
            )
            .with_for_update()
        ))
        if len(mappings) != len(set(occurrence_ids)):
            raise LookupError("occurrence_not_mapped_to_source")
        for mapping in mappings:
            CanonicalQuestionRepository._remap(session, mapping, target_id, "split", note)
        return target_id, len(mappings)

    @staticmethod
    def map_equivalent(session: Session, occurrence_id: UUID, target_id: UUID, note: str | None) -> None:
        CanonicalQuestionRepository._require_canonical(session, target_id)
        mapping = session.scalar(
            select(QuestionOccurrenceMapping)
            .where(QuestionOccurrenceMapping.occurrence_id == occurrence_id)
            .with_for_update()
        )
        if mapping is None:
            raise LookupError("occurrence_mapping_not_found")
        if mapping.canonical_question_id == target_id:
            return
        CanonicalQuestionRepository._remap(session, mapping, target_id, "equivalent", note)

    @staticmethod
    def _canonical(session: Session, canonical_text: str, normalization_key: str, created_by: str) -> tuple[UUID, bool]:
        canonical_id = session.execute(
            insert(CanonicalQuestion)
            .values(canonical_text=canonical_text, normalization_key=normalization_key, created_by=created_by)
            .on_conflict_do_nothing(index_elements=[CanonicalQuestion.normalization_key])
            .returning(CanonicalQuestion.id)
        ).scalar_one_or_none()
        if canonical_id is not None:
            return canonical_id, True
        existing = session.scalar(select(CanonicalQuestion.id).where(CanonicalQuestion.normalization_key == normalization_key))
        if existing is None:
            raise RuntimeError("canonical question conflict did not resolve")
        return existing, False

    @staticmethod
    def _require_canonical(session: Session, canonical_id: UUID) -> CanonicalQuestion:
        canonical = session.get(CanonicalQuestion, canonical_id)
        if canonical is None:
            raise LookupError("canonical_question_not_found")
        return canonical

    @staticmethod
    def _remap(session: Session, mapping: QuestionOccurrenceMapping, target_id: UUID, action: str, note: str | None) -> None:
        previous = mapping.canonical_question_id
        session.add(QuestionMappingRevision(
            occurrence_id=mapping.occurrence_id,
            from_canonical_question_id=previous,
            to_canonical_question_id=target_id,
            action=action,
            note_text=note,
        ))
        mapping.canonical_question_id = target_id
        mapping.mapping_origin = "manual"
        mapping.mapping_status = "confirmed"
        mapping.revision += 1
        mapping.updated_at = datetime.now(timezone.utc)
