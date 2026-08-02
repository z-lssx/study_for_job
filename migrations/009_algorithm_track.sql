CREATE TABLE IF NOT EXISTS algorithm_problems (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 240),
  source_url TEXT CHECK (source_url IS NULL OR length(source_url) <= 2048),
  source_platform TEXT NOT NULL DEFAULT 'manual' CHECK (length(trim(source_platform)) BETWEEN 1 AND 80),
  difficulty TEXT NOT NULL DEFAULT 'unknown' CHECK (difficulty IN ('unknown', 'easy', 'medium', 'hard')),
  tags JSONB NOT NULL DEFAULT '[]'::jsonb,
  status TEXT NOT NULL DEFAULT 'not_started' CHECK (status IN ('not_started', 'in_progress', 'solved', 'revisit')),
  mistake_reason TEXT CHECK (mistake_reason IS NULL OR length(mistake_reason) <= 4000),
  review_notes TEXT CHECK (review_notes IS NULL OR length(review_notes) <= 10000),
  notes TEXT CHECK (notes IS NULL OR length(notes) <= 4000),
  origin TEXT NOT NULL DEFAULT 'user' CHECK (origin IN ('user', 'intelligence_suggestion')),
  canonical_question_id UUID REFERENCES canonical_questions(id) ON DELETE RESTRICT,
  last_practiced_at TIMESTAMPTZ,
  next_review_at DATE,
  practice_count INTEGER NOT NULL DEFAULT 0 CHECK (practice_count >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS algorithm_problems_status_idx ON algorithm_problems(status, next_review_at);
CREATE INDEX IF NOT EXISTS algorithm_problems_updated_idx ON algorithm_problems(updated_at DESC);
CREATE INDEX IF NOT EXISTS algorithm_problems_canonical_idx
  ON algorithm_problems(canonical_question_id) WHERE canonical_question_id IS NOT NULL;
