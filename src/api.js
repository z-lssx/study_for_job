function responseError(data, fallback) {
  if (typeof data?.detail === 'string') return data.detail
  if (typeof data?.detail?.message === 'string') {
    const trace = data.detail.trace_id ? `（trace: ${data.detail.trace_id}）` : ''
    return `${data.detail.message}${trace}`
  }
  if (Array.isArray(data?.detail)) return data.detail.map((issue) => issue.msg).join('；')
  return fallback
}

function nullable(value) {
  const normalized = typeof value === 'string' ? value.trim() : value
  return normalized || null
}

async function requestJson(url, options, fallback) {
  const response = await fetch(url, options)
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(responseError(data, fallback))
  return data
}

export function applicationPayload(payload) {
  return {
    company: payload.company.trim(),
    role: payload.role.trim(),
    stage: payload.stage,
    key_date: nullable(payload.key_date),
    next_action: nullable(payload.next_action),
    channel: nullable(payload.channel),
    notes: nullable(payload.notes),
    url: nullable(payload.url),
  }
}

export function profilePayload(payload) {
  return {
    title: payload.title.trim(),
    location: nullable(payload.location),
    focus: nullable(payload.focus),
    summary: nullable(payload.summary),
  }
}

export function saveApplicationRequest(payload, applicationId) {
  return requestJson(
    applicationId ? `/api/applications/${applicationId}` : '/api/applications',
    {
      method: applicationId ? 'PATCH' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(applicationPayload(payload)),
    },
    '保存投递记录失败',
  )
}

export function saveProfileRequest(payload, profileId) {
  return requestJson(
    profileId ? `/api/target-profiles/${profileId}` : '/api/target-profiles',
    {
      method: profileId ? 'PATCH' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profilePayload(payload)),
    },
    '保存目标岗位失败',
  )
}

export function loadAiRuntimeRequest() {
  return requestJson('/api/admin/ai/runtime', undefined, '读取 AI 运行状态失败')
}

export function loadPromptsRequest() {
  return requestJson('/api/admin/ai/prompts', undefined, '读取 prompt 配置失败')
}

export function loadAiStatisticsRequest(days = 30) {
  return requestJson(`/api/admin/ai/statistics?days=${days}`, undefined, '读取 token 统计失败')
}

export function loadAiCallsRequest(limit = 30) {
  return requestJson(`/api/admin/ai/calls?limit=${limit}`, undefined, '读取 AI 调用日志失败')
}

export function savePromptRequest(scenarioKey, payload) {
  return requestJson(
    `/api/admin/ai/prompts/${encodeURIComponent(scenarioKey)}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        system_template: payload.system_template.trim(),
        task_template: payload.task_template.trim(),
        temperature: Number(payload.temperature),
        max_tokens: Number(payload.max_tokens),
        enabled: payload.enabled,
      }),
    },
    '保存 prompt 配置失败',
  )
}

export function runAiDiagnosticRequest(simulateFailure = false) {
  return requestJson(
    '/api/admin/ai/diagnostics',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ simulate_failure: simulateFailure }),
    },
    'AI Gateway 诊断失败',
  )
}
