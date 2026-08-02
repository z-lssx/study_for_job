CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Read-only retrieval indexes. They never alter extraction or normalization facts.
CREATE INDEX IF NOT EXISTS canonical_questions_text_trgm_idx
  ON canonical_questions USING GIN (canonical_text gin_trgm_ops);
CREATE INDEX IF NOT EXISTS question_occurrences_raw_text_trgm_idx
  ON question_occurrences USING GIN (raw_text gin_trgm_ops);
CREATE INDEX IF NOT EXISTS question_occurrences_search_fts_idx
  ON question_occurrences USING GIN (
    to_tsvector('simple', coalesce(raw_text, '') || ' ' || coalesce(normalized_text, ''))
  );
