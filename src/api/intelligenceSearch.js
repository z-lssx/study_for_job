import { requestJson } from '../api'

export function searchIntelligenceRequest(params = {}) {
  const query = new URLSearchParams()
  if (params.q?.trim()) query.set('q', params.q.trim())
  if (params.roundOrdinal) query.set('round_ordinal', params.roundOrdinal)
  if (params.fieldKind) query.set('field_kind', params.fieldKind)
  if (params.sourceHost?.trim()) query.set('source_host', params.sourceHost.trim())
  if (params.limit) query.set('limit', params.limit)
  return requestJson(`/api/intelligence/search?${query.toString()}`, undefined, '妫€绱㈤潰璇曟儏鎶ュけ璐?)
}

export function loadIntelligenceQualityRequest() {
  return requestJson('/api/intelligence/quality', undefined, '璇诲彇鎯呮姤璐ㄩ噺鐘舵€佸け璐?)
}
