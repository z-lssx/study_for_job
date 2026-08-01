CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS target_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL CHECK (length(trim(title)) > 0),
  location TEXT,
  focus TEXT,
  summary TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS applications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company TEXT NOT NULL CHECK (length(trim(company)) > 0),
  role TEXT NOT NULL CHECK (length(trim(role)) > 0),
  stage TEXT NOT NULL CHECK (stage IN ('saved', 'applied', 'interview', 'offer', 'closed')),
  key_date DATE,
  next_action TEXT,
  channel TEXT,
  notes TEXT,
  url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT applications_company_role_unique UNIQUE (company, role)
);

CREATE INDEX IF NOT EXISTS applications_stage_idx ON applications(stage);
CREATE INDEX IF NOT EXISTS applications_key_date_idx ON applications(key_date);
