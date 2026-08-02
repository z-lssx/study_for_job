import { requestJson } from '../api'

const jsonOptions = (method, payload) => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload),
})

export function loadProjectsRequest() {
  return requestJson('/api/projects', undefined, '读取项目证据包失败')
}

export function createProjectRequest(payload) {
  return requestJson('/api/projects', jsonOptions('POST', payload), '创建项目失败')
}

export function updateProjectRequest(projectId, payload) {
  return requestJson(`/api/projects/${projectId}`, jsonOptions('PATCH', payload), '更新项目事实失败')
}

export function createProjectEvidenceRequest(projectId, payload) {
  return requestJson(`/api/projects/${projectId}/evidence`, jsonOptions('POST', payload), '保存项目证据失败')
}

export function updateProjectEvidenceRequest(projectId, evidenceId, payload) {
  return requestJson(
    `/api/projects/${projectId}/evidence/${evidenceId}`,
    jsonOptions('PATCH', payload),
    '修订项目证据失败',
  )
}

export function createProjectVersionRequest(projectId, payload) {
  return requestJson(`/api/projects/${projectId}/versions`, jsonOptions('POST', payload), '创建表达版本失败')
}

export function updateProjectVersionRequest(projectId, versionId, payload) {
  return requestJson(
    `/api/projects/${projectId}/versions/${versionId}`,
    jsonOptions('PATCH', payload),
    '修订表达版本失败',
  )
}

export function confirmProjectVersionRequest(projectId, versionId) {
  return requestJson(
    `/api/projects/${projectId}/versions/${versionId}/confirm`,
    { method: 'POST' },
    '确认表达版本失败',
  )
}

export function linkProjectIntelligenceRequest(projectId, payload) {
  return requestJson(`/api/projects/${projectId}/intelligence`, jsonOptions('POST', payload), '关联面试情报失败')
}

export function unlinkProjectIntelligenceRequest(projectId, linkId) {
  return requestJson(
    `/api/projects/${projectId}/intelligence/${linkId}`,
    { method: 'DELETE' },
    '移除面试情报关联失败',
  )
}
