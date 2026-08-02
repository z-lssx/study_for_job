CREATE TABLE IF NOT EXISTS interview_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_url TEXT NOT NULL CHECK (length(source_url) BETWEEN 1 AND 2048),
  normalized_url TEXT NOT NULL CHECK (length(normalized_url) BETWEEN 1 AND 2048),
  host TEXT NOT NULL CHECK (length(host) BETWEEN 1 AND 253),
  first_submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT interview_sources_normalized_url_unique UNIQUE (normalized_url)
);

CREATE TABLE IF NOT EXISTS interview_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content_hash CHAR(64) NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
  title TEXT CHECK (title IS NULL OR length(title) <= 300),
  raw_content TEXT NOT NULL CHECK (length(raw_content) BETWEEN 1 AND 2097152),
  raw_content_type TEXT NOT NULL
    CHECK (raw_content_type IN ('text/html', 'text/plain')),
  cleaned_content TEXT NOT NULL CHECK (length(cleaned_content) BETWEEN 1 AND 500000),
  cleaning_version TEXT NOT NULL CHECK (length(cleaning_version) BETWEEN 1 AND 80),
  acquisition_method TEXT NOT NULL
    CHECK (acquisition_method IN ('url_fetch', 'manual_text', 'manual_fallback')),
  first_source_id UUID REFERENCES interview_sources(id) ON DELETE RESTRICT,
  collected_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT interview_documents_content_hash_unique UNIQUE (content_hash)
);

CREATE TABLE IF NOT EXISTS interview_submissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  initial_method TEXT NOT NULL
    CHECK (initial_method IN ('url', 'manual_text')),
  current_method TEXT NOT NULL
    CHECK (current_method IN ('url_fetch', 'manual_text', 'manual_fallback')),
  source_id UUID REFERENCES interview_sources(id) ON DELETE RESTRICT,
  document_id UUID REFERENCES interview_documents(id) ON DELETE RESTRICT,
  raw_content TEXT CHECK (raw_content IS NULL OR length(raw_content) BETWEEN 1 AND 2097152),
  raw_content_type TEXT CHECK (
    raw_content_type IS NULL OR raw_content_type IN ('text/html', 'text/plain')
  ),
  input_fingerprint CHAR(64) NOT NULL CHECK (input_fingerprint ~ '^[0-9a-f]{64}$'),
  revision INTEGER NOT NULL DEFAULT 1 CHECK (revision >= 1),
  current_job_id UUID REFERENCES jobs(id) ON DELETE RESTRICT,
  last_error_code TEXT CHECK (last_error_code IS NULL OR length(last_error_code) <= 120),
  last_error_message TEXT CHECK (last_error_message IS NULL OR length(last_error_message) <= 1000),
  last_error_retryable BOOLEAN,
  submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  processing_started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT interview_submissions_method_fields_consistent CHECK (
    (initial_method = 'url' AND source_id IS NOT NULL)
    OR (initial_method = 'manual_text' AND source_id IS NULL)
  ),
  CONSTRAINT interview_submissions_current_input_consistent CHECK (
    (current_method = 'url_fetch' AND source_id IS NOT NULL)
    OR (
      current_method = 'manual_text'
      AND source_id IS NULL
      AND raw_content IS NOT NULL
      AND raw_content_type = 'text/plain'
    )
    OR (
      current_method = 'manual_fallback'
      AND source_id IS NOT NULL
      AND raw_content IS NOT NULL
      AND raw_content_type = 'text/plain'
    )
  ),
  CONSTRAINT interview_submissions_error_fields_consistent CHECK (
    (last_error_code IS NULL AND last_error_message IS NULL AND last_error_retryable IS NULL)
    OR (last_error_code IS NOT NULL AND last_error_message IS NOT NULL AND last_error_retryable IS NOT NULL)
  ),
  CONSTRAINT interview_submissions_completion_consistent CHECK (
    (document_id IS NULL AND completed_at IS NULL)
    OR (document_id IS NOT NULL AND completed_at IS NOT NULL)
  )
);

CREATE TABLE IF NOT EXISTS interview_document_sources (
  document_id UUID NOT NULL REFERENCES interview_documents(id) ON DELETE RESTRICT,
  source_id UUID NOT NULL REFERENCES interview_sources(id) ON DELETE RESTRICT,
  first_submission_id UUID NOT NULL REFERENCES interview_submissions(id) ON DELETE RESTRICT,
  linked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (document_id, source_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS interview_submissions_source_unique_idx
  ON interview_submissions(source_id)
  WHERE source_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS interview_submissions_manual_fingerprint_unique_idx
  ON interview_submissions(input_fingerprint)
  WHERE initial_method = 'manual_text';

CREATE UNIQUE INDEX IF NOT EXISTS interview_submissions_current_job_unique_idx
  ON interview_submissions(current_job_id)
  WHERE current_job_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS interview_documents_first_source_idx
  ON interview_documents(first_source_id)
  WHERE first_source_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS interview_submissions_document_idx
  ON interview_submissions(document_id)
  WHERE document_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS interview_submissions_status_list_idx
  ON interview_submissions(updated_at DESC, id DESC)
  INCLUDE (current_method, source_id, document_id, current_job_id, last_error_code);

CREATE INDEX IF NOT EXISTS interview_document_sources_source_idx
  ON interview_document_sources(source_id, linked_at DESC, document_id);

CREATE INDEX IF NOT EXISTS interview_document_sources_submission_idx
  ON interview_document_sources(first_submission_id);
