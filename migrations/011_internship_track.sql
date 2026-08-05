CREATE TABLE IF NOT EXISTS internships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization TEXT NOT NULL CHECK (length(trim(organization)) BETWEEN 1 AND 240),
  role_title TEXT NOT NULL CHECK (length(trim(role_title)) BETWEEN 1 AND 160),
  started_on DATE,
  ended_on DATE,
  summary TEXT CHECK (summary IS NULL OR length(summary) <= 2000),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT internships_period_valid CHECK (ended_on IS NULL OR started_on IS NULL OR ended_on >= started_on)
);

CREATE TABLE IF NOT EXISTS internship_facts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  internship_id UUID NOT NULL REFERENCES internships(id) ON DELETE CASCADE,
  category TEXT NOT NULL CHECK (category IN (
    'responsibility', 'team_boundary', 'technical_context', 'collaboration_context',
    'challenge', 'result', 'metric', 'other'
  )),
  statement TEXT NOT NULL CHECK (length(trim(statement)) BETWEEN 1 AND 10000),
  source_kind TEXT NOT NULL DEFAULT 'user_recollection' CHECK (source_kind IN (
    'user_recollection', 'document', 'work_item', 'external_link', 'metric_record'
  )),
  source_reference TEXT CHECK (source_reference IS NULL OR length(source_reference) <= 2048),
  origin TEXT NOT NULL DEFAULT 'user' CHECK (origin IN ('user', 'ai_draft')),
  confirmation_status TEXT NOT NULL DEFAULT 'draft' CHECK (confirmation_status IN ('draft', 'confirmed')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT internship_facts_internship_identity_unique UNIQUE (id, internship_id)
);

CREATE TABLE IF NOT EXISTS internship_expression_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  internship_id UUID NOT NULL REFERENCES internships(id) ON DELETE CASCADE,
  version_number INTEGER NOT NULL CHECK (version_number >= 1),
  label TEXT NOT NULL CHECK (length(trim(label)) BETWEEN 1 AND 120),
  situation TEXT CHECK (situation IS NULL OR length(situation) <= 4000),
  task TEXT CHECK (task IS NULL OR length(task) <= 4000),
  action TEXT CHECK (action IS NULL OR length(action) <= 8000),
  result TEXT CHECK (result IS NULL OR length(result) <= 4000),
  quantified_pitch TEXT CHECK (quantified_pitch IS NULL OR length(quantified_pitch) <= 4000),
  follow_up_tree JSONB NOT NULL DEFAULT '[]'::jsonb,
  origin TEXT NOT NULL DEFAULT 'user' CHECK (origin IN ('user', 'ai_draft')),
  confirmation_status TEXT NOT NULL DEFAULT 'draft' CHECK (confirmation_status IN ('draft', 'confirmed')),
  based_on_version_id UUID REFERENCES internship_expression_versions(id) ON DELETE RESTRICT,
  confirmed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT internship_versions_number_unique UNIQUE (internship_id, version_number),
  CONSTRAINT internship_versions_internship_identity_unique UNIQUE (id, internship_id),
  CONSTRAINT internship_versions_base_same_internship_fk
    FOREIGN KEY (based_on_version_id, internship_id)
    REFERENCES internship_expression_versions(id, internship_id) ON DELETE RESTRICT,
  CONSTRAINT internship_versions_confirmation_consistent CHECK (
    (confirmation_status = 'confirmed' AND confirmed_at IS NOT NULL)
    OR (confirmation_status = 'draft' AND confirmed_at IS NULL)
  )
);

CREATE TABLE IF NOT EXISTS internship_materials (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  internship_id UUID NOT NULL REFERENCES internships(id) ON DELETE CASCADE,
  material_type TEXT NOT NULL CHECK (material_type IN (
    'resume_bullet', 'work_sample', 'evidence_document', 'reference_link', 'other'
  )),
  label TEXT NOT NULL CHECK (length(trim(label)) BETWEEN 1 AND 240),
  locator TEXT CHECK (locator IS NULL OR length(locator) <= 2048),
  notes TEXT CHECK (notes IS NULL OR length(notes) <= 4000),
  preparation_status TEXT NOT NULL DEFAULT 'missing' CHECK (preparation_status IN ('missing', 'draft', 'ready', 'verified')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT internship_materials_internship_identity_unique UNIQUE (id, internship_id)
);

CREATE TABLE IF NOT EXISTS internship_intelligence_links (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  internship_id UUID NOT NULL REFERENCES internships(id) ON DELETE CASCADE,
  canonical_question_id UUID NOT NULL REFERENCES canonical_questions(id) ON DELETE RESTRICT,
  internship_fact_id UUID,
  relevance_note TEXT NOT NULL CHECK (length(trim(relevance_note)) BETWEEN 1 AND 2000),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT internship_intelligence_links_unique UNIQUE (internship_id, canonical_question_id),
  CONSTRAINT internship_links_fact_same_internship_fk
    FOREIGN KEY (internship_fact_id, internship_id)
    REFERENCES internship_facts(id, internship_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS internships_updated_idx ON internships(updated_at DESC);
CREATE INDEX IF NOT EXISTS internship_facts_internship_idx ON internship_facts(internship_id, category, updated_at DESC);
CREATE INDEX IF NOT EXISTS internship_versions_internship_idx ON internship_expression_versions(internship_id, version_number DESC);
CREATE INDEX IF NOT EXISTS internship_materials_internship_idx ON internship_materials(internship_id, preparation_status, updated_at DESC);
CREATE INDEX IF NOT EXISTS internship_intelligence_links_internship_idx ON internship_intelligence_links(internship_id, created_at DESC);
