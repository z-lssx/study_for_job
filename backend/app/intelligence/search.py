from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


class IntelligenceSearchRepository:
    """Read-only retrieval over the T005-T007 fact chain.

    A request is idempotent because it only reads immutable source/extraction facts
    and the current mapping layer. Trigram rows are candidates, never new facts.
    """

    @staticmethod
    def search(
        session: Session,
        query: str,
        round_ordinal: int | None,
        field_kind: str | None,
        source_host: str | None,
        limit: int,
    ) -> dict:
        q = query.strip()
        rows = session.execute(
            text("""
                WITH facts AS (
                  SELECT
                    cq.id AS canonical_question_id,
                    cq.canonical_text,
                    o.id AS occurrence_id,
                    o.raw_text,
                    o.normalized_text,
                    o.field_kind,
                    o.round_ordinal,
                    o.document_id,
                    o.run_id,
                    o.round_id,
                    o.chunk_id,
                    o.evidence_span_id,
                    d.title AS document_title,
                    d.collected_at,
                    d.cleaned_content,
                    src.id AS source_id,
                    src.source_url,
                    src.normalized_url,
                    src.host,
                    sub.id AS submission_id,
                    sub.ids AS submission_ids,
                    source_links.sources,
                    r.label AS round_label,
                    ch.ordinal AS chunk_ordinal,
                    ch.block_type,
                    es.start_char,
                    es.end_char,
                    to_tsvector('simple', coalesce(o.raw_text, '') || ' ' || coalesce(o.normalized_text, ''))
                      @@ plainto_tsquery('simple', CAST(:q AS text)) AS fts_match,
                    greatest(
                      similarity(cq.canonical_text, CAST(:q AS text)),
                      similarity(o.raw_text, CAST(:q AS text)),
                      similarity(o.normalized_text, CAST(:q AS text))
                    ) AS trigram_score,
                    (
                      SELECT COUNT(*)::int
                      FROM question_occurrence_mappings fm
                      WHERE fm.canonical_question_id = cq.id
                    ) AS canonical_occurrence_count
                  FROM question_occurrence_mappings m
                  JOIN canonical_questions cq ON cq.id = m.canonical_question_id
                  JOIN question_occurrences o ON o.id = m.occurrence_id
                  JOIN interview_documents d ON d.id = o.document_id
                  LEFT JOIN interview_sources src ON src.id = d.first_source_id
                  LEFT JOIN LATERAL (
                    SELECT jsonb_agg(
                      jsonb_build_object(
                        'id', linked_source.id,
                        'url', linked_source.source_url,
                        'normalized_url', linked_source.normalized_url,
                        'host', linked_source.host
                      ) ORDER BY links.linked_at, linked_source.id
                    ) AS sources
                    FROM interview_document_sources links
                    JOIN interview_sources linked_source ON linked_source.id = links.source_id
                    WHERE links.document_id = d.id
                  ) source_links ON TRUE
                  LEFT JOIN interview_rounds r ON r.id = o.round_id
                  JOIN document_chunks ch ON ch.id = o.chunk_id
                  JOIN evidence_spans es ON es.id = o.evidence_span_id
                  LEFT JOIN LATERAL (
                    SELECT
                      (array_agg(s.id ORDER BY s.created_at, s.id))[1] AS id,
                      array_agg(s.id ORDER BY s.created_at, s.id) AS ids
                    FROM interview_submissions s
                    WHERE s.document_id = d.id
                  ) sub ON TRUE
                  WHERE (CAST(:round_ordinal AS integer) IS NULL OR o.round_ordinal = CAST(:round_ordinal AS integer))
                    AND (CAST(:field_kind AS text) IS NULL OR o.field_kind = CAST(:field_kind AS text))
                    AND (CAST(:source_host AS text) IS NULL OR src.host = CAST(:source_host AS text))
                ), ranked AS (
                  SELECT facts.*,
                    CASE
                      WHEN canonical_text ILIKE '%' || CAST(:q AS text) || '%'
                        OR raw_text ILIKE '%' || CAST(:q AS text) || '%'
                        OR normalized_text ILIKE '%' || CAST(:q AS text) || '%'
                        THEN 'exact_term'
                      WHEN fts_match THEN 'full_text'
                      ELSE 'trigram_candidate'
                    END AS match_path,
                    CASE
                      WHEN canonical_text ILIKE '%' || CAST(:q AS text) || '%'
                        OR raw_text ILIKE '%' || CAST(:q AS text) || '%'
                        OR normalized_text ILIKE '%' || CAST(:q AS text) || '%'
                        THEN 0
                      WHEN fts_match THEN 1
                      ELSE 2
                    END AS path_rank
                  FROM facts
                  WHERE canonical_text ILIKE '%' || CAST(:q AS text) || '%'
                    OR raw_text ILIKE '%' || CAST(:q AS text) || '%'
                    OR normalized_text ILIKE '%' || CAST(:q AS text) || '%'
                    OR fts_match
                    OR trigram_score >= CAST(:trigram_threshold AS real)
                )
                SELECT *,
                  substring(cleaned_content from start_char + 1 for end_char - start_char) AS evidence_text
                FROM ranked
                ORDER BY path_rank, trigram_score DESC, collected_at DESC NULLS LAST, occurrence_id
                LIMIT CAST(:limit AS integer)
            """),
            {
                "q": q,
                "round_ordinal": round_ordinal,
                "field_kind": field_kind,
                "source_host": source_host,
                "trigram_threshold": 0.18,
                "limit": limit,
            },
        ).mappings()
        result_rows = [dict(row) for row in rows]
        exact_count = sum(row["match_path"] in {"exact_term", "full_text"} for row in result_rows)
        candidate_count = sum(row["match_path"] == "trigram_candidate" for row in result_rows)
        return {
            "query": q,
            "results": result_rows,
            "search_paths": ["exact_term", "full_text", "trigram_candidate"],
            "exact_result_count": exact_count,
            "candidate_result_count": candidate_count,
            "semantic_recall": "unproven",
            "explanation": (
                "精确术语与 FTS 结果优先；trigram 仅作为措辞相近候选，未证明同义语义覆盖。"
                if candidate_count
                else "当前结果来自精确术语或 PostgreSQL FTS；未启用 embedding 语义召回。"
            ),
        }

    @staticmethod
    def quality(session: Session) -> dict:
        counts = session.execute(text("""
            SELECT
              (SELECT COUNT(*)::int FROM interview_documents) AS document_count,
              (SELECT COUNT(*)::int FROM extraction_runs WHERE status = 'succeeded') AS succeeded_run_count,
              (SELECT COUNT(*)::int FROM question_occurrences) AS occurrence_count,
              (SELECT COUNT(*)::int FROM canonical_questions) AS canonical_count,
              (SELECT COUNT(*)::int FROM evidence_spans) AS evidence_span_count,
              (SELECT COUNT(*)::int FROM question_occurrence_mappings) AS mapping_count
        """)).mappings().one()
        volume_limited = counts["document_count"] < 3 or counts["occurrence_count"] < 10
        return {
            "status": "insufficient_data" if volume_limited else "limited_but_traceable",
            "facts": dict(counts),
            "retrieval": {
                "exact_term": "available",
                "full_text": "available",
                "trigram_candidate": "available",
                "embedding": "not_configured",
                "pgvector": "not_selected",
            },
            "semantic_recall": {
                "status": "unproven",
                "reason": "尚无真实同义问题样本与评估证据，不能宣称语义覆盖。",
            },
            "conclusion": (
                "数据量不足，当前仅适合精确检索和可解释候选检索。"
                if volume_limited
                else "事实链路可追溯；精确检索可用，同义召回仍需真实样本验收。"
            ),
        }
