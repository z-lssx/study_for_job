CREATE TABLE IF NOT EXISTS extraction_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL REFERENCES interview_documents(id) ON DELETE RESTRICT,
  job_id UUID REFERENCES jobs(id) ON DELETE RESTRICT,
  input_fingerprint CHAR(64) NOT NULL CHECK (input_fingerprint ~ '^[0-9a-f]{64}$'),
  extraction_method TEXT NOT NULL CHECK (extraction_method IN ('deterministic')),
  schema_version TEXT NOT NULL CHECK (length(schema_version) BETWEEN 1 AND 80),
  processor_version TEXT NOT NULL CHECK (length(processor_version) BETWEEN 1 AND 80),
  status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'succeeded', 'failed')),
  trigger_revision INTEGER NOT NULL DEFAULT 1 CHECK (trigger_revision >= 1),
  error_code TEXT CHECK (error_code IS NULL OR length(error_code) <= 120),
  error_message TEXT CHECK (error_message IS NULL OR length(error_message) <= 1000),
  started_at TIMESTAMPTZ,
  generated_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT extraction_runs_document_input_unique UNIQUE (document_id, input_fingerprint),
  CONSTRAINT extraction_runs_error_consistent CHECK (
    (status = 'failed' AND error_code IS NOT NULL AND error_message IS NOT NULL)
    OR (status <> 'failed' AND error_code IS NULL AND error_message IS NULL)
  ),
  CONSTRAINT extraction_runs_generation_consistent CHECK (
    (status = 'succeeded' AND generated_at IS NOT NULL)
    OR (status <> 'succeeded' AND generated_at IS NULL)
  )
);

CREATE TABLE IF NOT EXISTS interview_rounds (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES extraction_runs(id) ON DELETE CASCADE,
  ordinal INTEGER NOT NULL CHECK (ordinal >= 1),
  label TEXT CHECK (label IS NULL OR length(label) <= 200),
  start_char INTEGER NOT NULL CHECK (start_char >= 0),
  end_char INTEGER NOT NULL CHECK (end_char > start_char),
  validation_status TEXT NOT NULL DEFAULT 'pending_review'
    CHECK (validation_status IN ('pending_review', 'confirmed', 'needs_review')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT interview_rounds_run_ordinal_unique UNIQUE (run_id, ordinal),
  CONSTRAINT interview_rounds_run_range_unique UNIQUE (run_id, start_char, end_char)
);

CREATE TABLE IF NOT EXISTS document_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES extraction_runs(id) ON DELETE CASCADE,
  round_id UUID REFERENCES interview_rounds(id) ON DELETE RESTRICT,
  ordinal INTEGER NOT NULL CHECK (ordinal >= 1),
  block_type TEXT NOT NULL CHECK (
    block_type IN ('question', 'author_answer', 'interviewer_feedback', 'follow_up', 'process_description', 'unknown')
  ),
  start_char INTEGER NOT NULL CHECK (start_char >= 0),
  end_char INTEGER NOT NULL CHECK (end_char > start_char),
  validation_status TEXT NOT NULL DEFAULT 'pending_review'
    CHECK (validation_status IN ('pending_review', 'confirmed', 'needs_review')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT document_chunks_run_ordinal_unique UNIQUE (run_id, ordinal),
  CONSTRAINT document_chunks_run_range_unique UNIQUE (run_id, start_char, end_char)
);

CREATE TABLE IF NOT EXISTS question_candidates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES extraction_runs(id) ON DELETE CASCADE,
  chunk_id UUID NOT NULL REFERENCES document_chunks(id) ON DELETE RESTRICT,
  round_id UUID REFERENCES interview_rounds(id) ON DELETE RESTRICT,
  candidate_key CHAR(64) NOT NULL CHECK (candidate_key ~ '^[0-9a-f]{64}$'),
  field_kind TEXT NOT NULL CHECK (field_kind IN ('question', 'follow_up')),
  extracted_text TEXT NOT NULL CHECK (length(trim(extracted_text)) BETWEEN 1 AND 4000),
  topic_candidate TEXT CHECK (topic_candidate IS NULL OR length(topic_candidate) <= 200),
  start_char INTEGER NOT NULL CHECK (start_char >= 0),
  end_char INTEGER NOT NULL CHECK (end_char > start_char),
  validation_status TEXT NOT NULL DEFAULT 'pending_review'
    CHECK (validation_status IN ('pending_review', 'confirmed', 'needs_review')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT question_candidates_run_key_unique UNIQUE (run_id, candidate_key)
);

CREATE TABLE IF NOT EXISTS evidence_spans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES extraction_runs(id) ON DELETE CASCADE,
  chunk_id UUID NOT NULL REFERENCES document_chunks(id) ON DELETE RESTRICT,
  candidate_id UUID REFERENCES question_candidates(id) ON DELETE RESTRICT,
  field_name TEXT NOT NULL CHECK (field_name IN ('content_block', 'question_text', 'follow_up_text')),
  start_char INTEGER NOT NULL CHECK (start_char >= 0),
  end_char INTEGER NOT NULL CHECK (end_char > start_char),
  quote_hash CHAR(64) NOT NULL CHECK (quote_hash ~ '^[0-9a-f]{64}$'),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT evidence_spans_target_unique UNIQUE (run_id, chunk_id, candidate_id, field_name)
);

CREATE TABLE IF NOT EXISTS extraction_chunk_annotations (
  chunk_id UUID PRIMARY KEY REFERENCES document_chunks(id) ON DELETE CASCADE,
  note_text TEXT CHECK (note_text IS NULL OR length(note_text) <= 2000),
  review_status TEXT NOT NULL DEFAULT 'needs_review'
    CHECK (review_status IN ('confirmed', 'needs_review', 'rejected')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS extraction_runs_job_unique_idx
  ON extraction_runs(job_id) WHERE job_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS extraction_runs_document_status_idx
  ON extraction_runs(document_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS interview_rounds_run_range_idx
  ON interview_rounds(run_id, start_char, end_char);
CREATE INDEX IF NOT EXISTS document_chunks_run_type_ordinal_idx
  ON document_chunks(run_id, block_type, ordinal);
CREATE INDEX IF NOT EXISTS document_chunks_round_idx
  ON document_chunks(round_id, ordinal) WHERE round_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS question_candidates_run_kind_idx
  ON question_candidates(run_id, field_kind, start_char);
CREATE INDEX IF NOT EXISTS question_candidates_chunk_idx
  ON question_candidates(chunk_id);
CREATE INDEX IF NOT EXISTS question_candidates_round_idx
  ON question_candidates(round_id, start_char) WHERE round_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS evidence_spans_run_range_idx
  ON evidence_spans(run_id, start_char, end_char);
CREATE UNIQUE INDEX IF NOT EXISTS evidence_spans_chunk_fact_unique_idx
  ON evidence_spans(run_id, chunk_id, field_name)
  WHERE candidate_id IS NULL;
CREATE INDEX IF NOT EXISTS evidence_spans_chunk_idx
  ON evidence_spans(chunk_id);
CREATE INDEX IF NOT EXISTS evidence_spans_candidate_idx
  ON evidence_spans(candidate_id) WHERE candidate_id IS NOT NULL;
