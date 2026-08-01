CREATE TABLE IF NOT EXISTS prompt_scenarios (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  module TEXT NOT NULL CHECK (length(trim(module)) > 0),
  scenario_key TEXT NOT NULL CHECK (length(trim(scenario_key)) > 0),
  name TEXT NOT NULL CHECK (length(trim(name)) > 0),
  description TEXT NOT NULL DEFAULT '',
  editable_variables JSONB NOT NULL DEFAULT '[]'::jsonb
    CHECK (jsonb_typeof(editable_variables) = 'array'),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT prompt_scenarios_key_unique UNIQUE (scenario_key),
  CONSTRAINT prompt_scenarios_module_key_unique UNIQUE (module, scenario_key)
);

CREATE TABLE IF NOT EXISTS prompt_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_id UUID NOT NULL REFERENCES prompt_scenarios(id) ON DELETE RESTRICT,
  system_template TEXT NOT NULL CHECK (length(trim(system_template)) > 0),
  task_template TEXT NOT NULL CHECK (length(trim(task_template)) > 0),
  parameters JSONB NOT NULL DEFAULT '{"temperature": 0.2, "max_tokens": 1024}'::jsonb,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT prompt_templates_scenario_unique UNIQUE (scenario_id),
  CONSTRAINT prompt_templates_parameters_object CHECK (jsonb_typeof(parameters) = 'object'),
  CONSTRAINT prompt_templates_parameters_allowed CHECK (
    parameters ?& ARRAY['temperature', 'max_tokens']
    AND parameters - 'temperature' - 'max_tokens' = '{}'::jsonb
    AND jsonb_typeof(parameters -> 'temperature') = 'number'
    AND (parameters ->> 'temperature')::numeric BETWEEN 0 AND 2
    AND jsonb_typeof(parameters -> 'max_tokens') = 'number'
    AND (parameters ->> 'max_tokens')::numeric BETWEEN 1 AND 8192
    AND (parameters ->> 'max_tokens')::numeric = trunc((parameters ->> 'max_tokens')::numeric)
  )
);

CREATE TABLE IF NOT EXISTS ai_call_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_id UUID NOT NULL REFERENCES prompt_scenarios(id) ON DELETE RESTRICT,
  module TEXT NOT NULL CHECK (length(trim(module)) > 0),
  scenario_key TEXT NOT NULL CHECK (length(trim(scenario_key)) > 0),
  provider TEXT NOT NULL CHECK (length(trim(provider)) > 0),
  model TEXT NOT NULL CHECK (length(trim(model)) > 0),
  status TEXT NOT NULL CHECK (status IN ('success', 'error')),
  input_tokens INTEGER CHECK (input_tokens IS NULL OR input_tokens >= 0),
  output_tokens INTEGER CHECK (output_tokens IS NULL OR output_tokens >= 0),
  total_tokens INTEGER CHECK (total_tokens IS NULL OR total_tokens >= 0),
  duration_ms INTEGER NOT NULL CHECK (duration_ms >= 0),
  prompt_hash CHAR(64) NOT NULL CHECK (prompt_hash ~ '^[0-9a-f]{64}$'),
  trace_id UUID NOT NULL,
  error_code TEXT,
  error_message TEXT CHECK (error_message IS NULL OR length(error_message) <= 1000),
  request_parameters JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(request_parameters) = 'object'),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ai_call_logs_module_scenario_created_idx
  ON ai_call_logs(module, scenario_key, created_at DESC, id DESC)
  INCLUDE (status, input_tokens, output_tokens, total_tokens, duration_ms, model);
CREATE INDEX IF NOT EXISTS ai_call_logs_created_idx
  ON ai_call_logs(created_at DESC, id DESC)
  INCLUDE (module, scenario_key, status, total_tokens);
CREATE INDEX IF NOT EXISTS ai_call_logs_trace_idx ON ai_call_logs(trace_id);

INSERT INTO prompt_scenarios (module, scenario_key, name, description, editable_variables)
VALUES
  ('diagnostics', 'gateway_diagnostic', 'Gateway 受限诊断', '仅用于验证 provider、日志与 token 链路，不接收自由对话输入。', '["purpose"]'::jsonb),
  ('intelligence', 'interview_extract', '面经结构化抽取', '后续面经情报链路使用；输入输出 Schema 与安全规则由代码控制。', '["document_text"]'::jsonb),
  ('planning', 'readiness_plan', '备战计划生成', '后续准备评估链路使用；只消费代码筛选后的摘要与证据。', '["profile_summary", "evidence_summary"]'::jsonb)
ON CONFLICT (scenario_key) DO NOTHING;

INSERT INTO prompt_templates (scenario_id, system_template, task_template, parameters)
SELECT id,
  '你是本地求职准备工具的 AI Gateway 诊断器。只返回简短、确定的诊断结果，不扩展为对话。',
  '执行固定诊断：{purpose}',
  '{"temperature": 0, "max_tokens": 64}'::jsonb
FROM prompt_scenarios WHERE scenario_key = 'gateway_diagnostic'
ON CONFLICT (scenario_id) DO NOTHING;

INSERT INTO prompt_templates (scenario_id, system_template, task_template, parameters)
SELECT id,
  '从面经原文中抽取结构化事实。不得编造；输出必须符合代码提供的 Schema，并保留证据位置。',
  '分析以下面经正文：\n{document_text}',
  '{"temperature": 0.1, "max_tokens": 2048}'::jsonb
FROM prompt_scenarios WHERE scenario_key = 'interview_extract'
ON CONFLICT (scenario_id) DO NOTHING;

INSERT INTO prompt_templates (scenario_id, system_template, task_template, parameters)
SELECT id,
  '根据目标画像与证据摘要生成可执行的备战建议。只使用给定事实，并明确证据不足之处。',
  '目标画像：\n{profile_summary}\n\n证据摘要：\n{evidence_summary}',
  '{"temperature": 0.3, "max_tokens": 1536}'::jsonb
FROM prompt_scenarios WHERE scenario_key = 'readiness_plan'
ON CONFLICT (scenario_id) DO NOTHING;
