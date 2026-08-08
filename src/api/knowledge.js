import { requestJson } from '../api'

export function loadKnowledgeCardsRequest(params = '') {
  return requestJson(`/api/knowledge/cards${params ? `?${params}` : ''}`, undefined, '读取知识卡片失败')
}

export function loadKnowledgeCardRequest(cardId) {
  return requestJson(`/api/knowledge/cards/${cardId}`, undefined, '读取知识卡片详情失败')
}

export function createKnowledgeCardRequest(payload) {
  return requestJson('/api/knowledge/cards', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }, '创建知识卡片失败')
}

export function updateKnowledgeCardRequest(cardId, payload) {
  return requestJson(`/api/knowledge/cards/${cardId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }, '更新知识卡片失败')
}

export function reviewKnowledgeCardRequest(cardId, payload) {
  return requestJson(`/api/knowledge/cards/${cardId}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }, '记录复习失败')
}

export function addKnowledgeEvidenceRequest(cardId, payload) {
  return requestJson(`/api/knowledge/cards/${cardId}/evidence`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }, '关联知识证据失败')
}

export function removeKnowledgeEvidenceRequest(cardId, evidenceSpanId) {
  return requestJson(`/api/knowledge/cards/${cardId}/evidence/${evidenceSpanId}`, {
    method: 'DELETE',
  }, '移除知识证据失败')
}
