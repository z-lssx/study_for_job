import { requestJson } from '../api'

export function loadKnowledgeCardsRequest(params = '') {
  return requestJson(`/api/knowledge/cards${params ? `?${params}` : ''}`, undefined, '读取知识卡片失败')
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
