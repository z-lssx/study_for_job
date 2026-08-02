CREATE TABLE IF NOT EXISTS knowledge_cards (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 240),
  prompt TEXT CHECK (prompt IS NULL OR length(prompt) <= 2000),
  notes TEXT CHECK (notes IS NULL OR length(notes) <= 10000),
  mastery_status TEXT NOT NULL DEFAULT 'not_started'
    CHECK (mastery_status IN ('not_started', 'learning', 'familiar', 'mastered')),
  origin TEXT NOT NULL DEFAULT 'user'
    CHECK (origin IN ('user', 'intelligence_suggestion')),
  last_reviewed_at TIMESTAMPTZ,
  next_review_at DATE,
  review_count INTEGER NOT NULL DEFAULT 0 CHECK (review_count >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS knowledge_cards_review_idx
  ON knowledge_cards(next_review_at, mastery_status);
CREATE INDEX IF NOT EXISTS knowledge_cards_updated_idx
  ON knowledge_cards(updated_at DESC);

CREATE TABLE IF NOT EXISTS knowledge_card_evidence (
  card_id UUID NOT NULL REFERENCES knowledge_cards(id) ON DELETE CASCADE,
  evidence_span_id UUID NOT NULL REFERENCES evidence_spans(id) ON DELETE RESTRICT,
  note_text TEXT CHECK (note_text IS NULL OR length(note_text) <= 1000),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (card_id, evidence_span_id)
);

CREATE INDEX IF NOT EXISTS knowledge_card_evidence_span_idx
  ON knowledge_card_evidence(evidence_span_id);
