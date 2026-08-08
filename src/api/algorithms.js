import { requestJson } from '../api'

export function loadAlgorithmProblemsRequest(params = '') {
  return requestJson(`/api/algorithms${params ? `?${params}` : ''}`, undefined, '读取算法题单失败')
}

export function loadAlgorithmProblemRequest(problemId) {
  return requestJson(`/api/algorithms/${problemId}`, undefined, '读取算法题详情失败')
}

export function randomAlgorithmProblemRequest() {
  return requestJson('/api/algorithms/random', undefined, '获取随机练习题失败')
}

export function createAlgorithmProblemRequest(payload) {
  return requestJson('/api/algorithms', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }, '创建算法题失败')
}

export function practiceAlgorithmProblemRequest(problemId, payload) {
  return requestJson(`/api/algorithms/${problemId}/practice`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }, '记录算法练习失败')
}

export function updateAlgorithmProblemRequest(problemId, payload) {
  return requestJson(`/api/algorithms/${problemId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }, '更新算法题失败')
}
