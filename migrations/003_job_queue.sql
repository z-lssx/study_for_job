CREATE TABLE IF NOT EXISTS jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_type TEXT NOT NULL CHECK (length(trim(job_type)) > 0),
  status TEXT NOT NULL DEFAULT 'queued'
    CHECK (status IN ('queued', 'running', 'retry_wait', 'succeeded', 'failed')),
  payload JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(payload) = 'object'),
  result_summary JSONB CHECK (result_summary IS NULL OR jsonb_typeof(result_summary) = 'object'),
  priority SMALLINT NOT NULL DEFAULT 0 CHECK (priority BETWEEN -100 AND 100),
  attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
  max_attempts INTEGER NOT NULL DEFAULT 3 CHECK (max_attempts BETWEEN 1 AND 20),
  next_run_at TIMESTAMPTZ,
  claimed_by TEXT CHECK (claimed_by IS NULL OR length(claimed_by) BETWEEN 1 AND 200),
  lease_token UUID,
  lease_expires_at TIMESTAMPTZ,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  last_error_code TEXT CHECK (last_error_code IS NULL OR length(last_error_code) <= 120),
  last_error_message TEXT CHECK (last_error_message IS NULL OR length(last_error_message) <= 1000),
  idempotency_key TEXT CHECK (idempotency_key IS NULL OR length(idempotency_key) BETWEEN 1 AND 200),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT jobs_attempt_count_bounded CHECK (attempt_count <= max_attempts),
  CONSTRAINT jobs_runtime_fields_consistent CHECK (
    (
      status = 'running'
      AND claimed_by IS NOT NULL
      AND lease_token IS NOT NULL
      AND lease_expires_at IS NOT NULL
      AND next_run_at IS NULL
      AND completed_at IS NULL
    )
    OR
    (
      status IN ('queued', 'retry_wait')
      AND claimed_by IS NULL
      AND lease_token IS NULL
      AND lease_expires_at IS NULL
      AND next_run_at IS NOT NULL
      AND completed_at IS NULL
    )
    OR
    (
      status IN ('succeeded', 'failed')
      AND claimed_by IS NULL
      AND lease_token IS NULL
      AND lease_expires_at IS NULL
      AND next_run_at IS NULL
      AND completed_at IS NOT NULL
    )
  )
);

CREATE TABLE IF NOT EXISTS job_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE RESTRICT,
  attempt_number INTEGER NOT NULL CHECK (attempt_number >= 1),
  worker_id TEXT NOT NULL CHECK (length(worker_id) BETWEEN 1 AND 200),
  lease_token UUID NOT NULL,
  status TEXT NOT NULL DEFAULT 'running'
    CHECK (status IN ('running', 'succeeded', 'retry_scheduled', 'failed', 'lease_expired')),
  result_summary JSONB CHECK (result_summary IS NULL OR jsonb_typeof(result_summary) = 'object'),
  error_code TEXT CHECK (error_code IS NULL OR length(error_code) <= 120),
  error_message TEXT CHECK (error_message IS NULL OR length(error_message) <= 1000),
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  finished_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT job_attempts_job_number_unique UNIQUE (job_id, attempt_number),
  CONSTRAINT job_attempts_lease_token_unique UNIQUE (lease_token),
  CONSTRAINT job_attempts_finished_consistent CHECK (
    (status = 'running' AND finished_at IS NULL)
    OR (status <> 'running' AND finished_at IS NOT NULL)
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS jobs_idempotency_unique_idx
  ON jobs(job_type, idempotency_key)
  WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS jobs_claimable_idx
  ON jobs(
    priority DESC,
    (CASE WHEN status = 'running' THEN lease_expires_at ELSE next_run_at END),
    created_at,
    id
  )
  WHERE status IN ('queued', 'retry_wait', 'running');

CREATE INDEX IF NOT EXISTS jobs_created_idx
  ON jobs(created_at DESC, id DESC)
  INCLUDE (job_type, status, priority, attempt_count, max_attempts, next_run_at);

CREATE INDEX IF NOT EXISTS job_attempts_job_started_idx
  ON job_attempts(job_id, started_at DESC, id DESC)
  INCLUDE (attempt_number, status, worker_id, finished_at, error_code);
