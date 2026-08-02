CREATE TABLE IF NOT EXISTS projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 240),
  target_role TEXT CHECK (target_role IS NULL OR length(target_role) <= 160),
  summary TEXT CHECK (summary IS NULL OR length(summary) <= 2000),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS project_evidence (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  category TEXT NOT NULL CHECK (category IN (
    'background_goal', 'responsibility', 'team_boundary', 'technical_choice',
    'tradeoff', 'metric', 'other'
  )),
  statement TEXT NOT NULL CHECK (length(trim(statement)) BETWEEN 1 AND 10000),
  source_kind TEXT NOT NULL DEFAULT 'user_recollection' CHECK (source_kind IN (
    'user_recollection', 'document', 'repository', 'external_link', 'metric_record'
  )),
  source_reference TEXT CHECK (source_reference IS NULL OR length(source_reference) <= 2048),
  origin TEXT NOT NULL DEFAULT 'user' CHECK (origin IN ('user', 'ai_draft')),
  confirmation_status TEXT NOT NULL DEFAULT 'draft' CHECK (confirmation_status IN ('draft', 'confirmed')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT project_evidence_project_identity_unique UNIQUE (id, project_id)
);

CREATE TABLE IF NOT EXISTS project_expression_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  version_number INTEGER NOT NULL CHECK (version_number >= 1),
  label TEXT NOT NULL CHECK (length(trim(label)) BETWEEN 1 AND 120),
  pitch_30s TEXT CHECK (pitch_30s IS NULL OR length(pitch_30s) <= 4000),
  pitch_2m TEXT CHECK (pitch_2m IS NULL OR length(pitch_2m) <= 12000),
  follow_up_tree JSONB NOT NULL DEFAULT '[]'::jsonb,
  origin TEXT NOT NULL DEFAULT 'user' CHECK (origin IN ('user', 'ai_draft')),
  confirmation_status TEXT NOT NULL DEFAULT 'draft' CHECK (confirmation_status IN ('draft', 'confirmed')),
  based_on_version_id UUID REFERENCES project_expression_versions(id) ON DELETE RESTRICT,
  confirmed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT project_expression_versions_number_unique UNIQUE (project_id, version_number),
  CONSTRAINT project_expression_versions_project_identity_unique UNIQUE (id, project_id),
  CONSTRAINT project_expression_versions_base_same_project_fk
    FOREIGN KEY (based_on_version_id, project_id)
    REFERENCES project_expression_versions(id, project_id) ON DELETE RESTRICT,
  CONSTRAINT project_expression_versions_confirmation_consistent CHECK (
    (confirmation_status = 'confirmed' AND confirmed_at IS NOT NULL)
    OR (confirmation_status = 'draft' AND confirmed_at IS NULL)
  )
);

CREATE TABLE IF NOT EXISTS project_intelligence_links (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  canonical_question_id UUID NOT NULL REFERENCES canonical_questions(id) ON DELETE RESTRICT,
  project_evidence_id UUID,
  relevance_note TEXT NOT NULL CHECK (length(trim(relevance_note)) BETWEEN 1 AND 2000),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT project_intelligence_links_unique UNIQUE (project_id, canonical_question_id),
  CONSTRAINT project_intelligence_links_evidence_same_project_fk
    FOREIGN KEY (project_evidence_id, project_id)
    REFERENCES project_evidence(id, project_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS projects_updated_idx ON projects(updated_at DESC);
CREATE INDEX IF NOT EXISTS project_evidence_project_idx ON project_evidence(project_id, category, updated_at DESC);
CREATE INDEX IF NOT EXISTS project_versions_project_idx ON project_expression_versions(project_id, version_number DESC);
CREATE INDEX IF NOT EXISTS project_intelligence_links_project_idx ON project_intelligence_links(project_id, created_at DESC);
