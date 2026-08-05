import { requestJson } from '../api'

const jsonOptions = (method, payload) => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload),
})

export const loadInternshipsRequest = () => requestJson('/api/internships', undefined, '读取实习资产失败')
export const createInternshipRequest = (payload) => requestJson('/api/internships', jsonOptions('POST', payload), '创建实习经历失败')
export const updateInternshipRequest = (id, payload) => requestJson(`/api/internships/${id}`, jsonOptions('PATCH', payload), '更新实习事实失败')
export const createInternshipFactRequest = (id, payload) => requestJson(`/api/internships/${id}/facts`, jsonOptions('POST', payload), '保存实习事实失败')
export const updateInternshipFactRequest = (id, factId, payload) => requestJson(`/api/internships/${id}/facts/${factId}`, jsonOptions('PATCH', payload), '修订实习事实失败')
export const createInternshipVersionRequest = (id, payload) => requestJson(`/api/internships/${id}/versions`, jsonOptions('POST', payload), '创建 STAR 版本失败')
export const updateInternshipVersionRequest = (id, versionId, payload) => requestJson(`/api/internships/${id}/versions/${versionId}`, jsonOptions('PATCH', payload), '修订 STAR 版本失败')
export const confirmInternshipVersionRequest = (id, versionId) => requestJson(`/api/internships/${id}/versions/${versionId}/confirm`, { method: 'POST' }, '确认 STAR 版本失败')
export const createInternshipMaterialRequest = (id, payload) => requestJson(`/api/internships/${id}/materials`, jsonOptions('POST', payload), '保存实习材料失败')
export const updateInternshipMaterialRequest = (id, materialId, payload) => requestJson(`/api/internships/${id}/materials/${materialId}`, jsonOptions('PATCH', payload), '更新实习材料失败')
export const linkInternshipIntelligenceRequest = (id, payload) => requestJson(`/api/internships/${id}/intelligence`, jsonOptions('POST', payload), '关联面试情报失败')
export const unlinkInternshipIntelligenceRequest = (id, linkId) => requestJson(`/api/internships/${id}/intelligence/${linkId}`, { method: 'DELETE' }, '移除面试情报关联失败')
