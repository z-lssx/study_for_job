import { requestJson } from '../api'

export function loadCanonicalQuestionsRequest(params = {}) {
  const search = new URLSearchParams()
  if (params.search?.trim()) search.set('search', params.search.trim())
  if (params.roundOrdinal) search.set('round_ordinal', params.roundOrdinal)
  if (params.limit) search.set('limit', params.limit)
  const query = search.toString()
  return requestJson(`/api/intelligence/canonical-questions${query ? `?${query}` : ''}`, undefined, '读取规范题频率失败')
}

export function loadCanonicalQuestionDetailRequest(canonicalId) {
  return requestJson(`/api/intelligence/canonical-questions/${canonicalId}`, undefined, '读取规范题证据失败')
}

export function refreshCanonicalQuestionsRequest() {
  return requestJson('/api/intelligence/canonical-questions/refresh', { method: 'POST' }, '刷新规范题频率失败')
}

export function mergeCanonicalQuestionRequest(sourceId, payload) {
  return requestJson(`/api/intelligence/canonical-questions/${sourceId}/merge`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  }, '合并规范题失败')
}

export function splitCanonicalQuestionRequest(sourceId, payload) {
  return requestJson(`/api/intelligence/canonical-questions/${sourceId}/split`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  }, '拆分规范题失败')
}

export function mapQuestionOccurrenceRequest(occurrenceId, payload) {
  return requestJson(`/api/intelligence/canonical-questions/occurrences/${occurrenceId}/mapping`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  }, '修正出现记录映射失败')
}
