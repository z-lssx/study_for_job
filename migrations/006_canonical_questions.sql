CREATE TABLE IF NOT EXISTS canonical_questions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical_text TEXT NOT NULL CHECK (length(trim(canonical_text)) BETWEEN 1 AND 4000),
  normalization_key CHAR(64) NOT NULL CHECK (normalization_key ~ '^[0-9a-f]{64}$'),
  created_by TEXT NOT NULL CHECK (created_by IN ('automatic', 'manual')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT canonical_questions_normalization_key_unique UNIQUE (normalization_key)
);

CREATE TABLE IF NOT EXISTS question_occurrences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id UUID NOT NULL REFERENCES question_candidates(id) ON DELETE RESTRICT,
  document_id UUID NOT NULL REFERENCES interview_documents(id) ON DELETE RESTRICT,
  run_id UUID NOT NULL REFERENCES extraction_runs(id) ON DELETE RESTRICT,
  round_id UUID REFERENCES interview_rounds(id) ON DELETE RESTRICT,
  chunk_id UUID NOT NULL REFERENCES document_chunks(id) ON DELETE RESTRICT,
  evidence_span_id UUID NOT NULL REFERENCES evidence_spans(id) ON DELETE RESTRICT,
  occurrence_key CHAR(64) NOT NULL CHECK (occurrence_key ~ '^[0-9a-f]{64}$'),
  raw_text TEXT NOT NULL CHECK (length(trim(raw_text)) BETWEEN 1 AND 4000),
  normalized_text TEXT NOT NULL CHECK (length(trim(normalized_text)) BETWEEN 1 AND 4000),
  normalization_key CHAR(64) NOT NULL CHECK (normalization_key ~ '^[0-9a-f]{64}$'),
  field_kind TEXT NOT NULL CHECK (field_kind IN ('question', 'follow_up')),
  round_ordinal INTEGER CHECK (round_ordinal IS NULL OR round_ordinal >= 1),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT question_occurrences_candidate_unique UNIQUE (candidate_id),
  CONSTRAINT question_occurrences_occurrence_key_unique UNIQUE (occurrence_key),
  CONSTRAINT question_occurrences_evidence_unique UNIQUE (evidence_span_id)
);

CREATE TABLE IF NOT EXISTS question_occurrence_mappings (
  occurrence_id UUID PRIMARY KEY REFERENCES question_occurrences(id) ON DELETE RESTRICT,
  canonical_question_id UUID NOT NULL REFERENCES canonical_questions(id) ON DELETE RESTRICT,
  mapping_origin TEXT NOT NULL CHECK (mapping_origin IN ('automatic', 'manual')),
  mapping_status TEXT NOT NULL CHECK (mapping_status IN ('automatic', 'confirmed', 'needs_review')),
  revision INTEGER NOT NULL DEFAULT 1 CHECK (revision >= 1),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS question_mapping_revisions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  occurrence_id UUID NOT NULL REFERENCES question_occurrences(id) ON DELETE RESTRICT,
  from_canonical_question_id UUID REFERENCES canonical_questions(id) ON DELETE RESTRICT,
  to_canonical_question_id UUID NOT NULL REFERENCES canonical_questions(id) ON DELETE RESTRICT,
  action TEXT NOT NULL CHECK (action IN ('merge', 'split', 'equivalent')),
  note_text TEXT CHECK (note_text IS NULL OR length(note_text) <= 1000),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT question_mapping_revisions_changed CHECK (
    from_canonical_question_id IS NULL OR from_canonical_question_id <> to_canonical_question_id
  )
);

CREATE INDEX IF NOT EXISTS question_occurrences_document_round_idx
  ON question_occurrences(document_id, round_ordinal, normalization_key);
CREATE INDEX IF NOT EXISTS question_occurrences_run_idx ON question_occurrences(run_id);
CREATE INDEX IF NOT EXISTS question_occurrences_round_idx
  ON question_occurrences(round_id) WHERE round_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS question_occurrences_chunk_idx ON question_occurrences(chunk_id);
CREATE INDEX IF NOT EXISTS question_occurrence_mappings_canonical_idx
  ON question_occurrence_mappings(canonical_question_id, occurrence_id);
CREATE INDEX IF NOT EXISTS question_mapping_revisions_occurrence_created_idx
  ON question_mapping_revisions(occurrence_id, created_at DESC);
CREATE INDEX IF NOT EXISTS question_mapping_revisions_from_idx
  ON question_mapping_revisions(from_canonical_question_id)
  WHERE from_canonical_question_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS question_mapping_revisions_to_idx
  ON question_mapping_revisions(to_canonical_question_id);
