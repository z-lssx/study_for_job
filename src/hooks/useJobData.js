import { useCallback, useEffect, useState } from 'react'
import { patchApplicationRequest, saveApplicationRequest, saveProfileRequest } from '../api'

export function useJobData() {
  const [profiles, setProfiles] = useState([])
  const [profile, setProfile] = useState(null)
  const [applications, setApplications] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [environment, setEnvironment] = useState('development')

  const loadData = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [healthResponse, profileResponse, applicationsResponse] = await Promise.all([
        fetch('/api/health'),
        fetch('/api/target-profiles'),
        fetch('/api/applications'),
      ])
      if (!healthResponse.ok || !profileResponse.ok || !applicationsResponse.ok) {
        throw new Error('数据链路暂不可用，请检查 API 与 PostgreSQL。')
      }
      const [health, nextProfiles, nextApplications] = await Promise.all([
        healthResponse.json(),
        profileResponse.json(),
        applicationsResponse.json(),
      ])
      setEnvironment(health.environment || 'development')
      setProfiles(nextProfiles)
      setProfile(nextProfiles[0] || null)
      setApplications(nextApplications)
    } catch (caught) {
      setError(caught.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadData() }, [loadData])

  const saveApplication = useCallback(async (payload, applicationId = null) => {
    const saved = await saveApplicationRequest(payload, applicationId)
    await loadData()
    return saved
  }, [loadData])

  const saveProfile = useCallback(async (payload) => {
    const saved = await saveProfileRequest(payload, profile?.id)
    await loadData()
    return saved
  }, [loadData, profile?.id])

  const patchApplication = useCallback(async (applicationId, changes) => {
    const saved = await patchApplicationRequest(applicationId, changes)
    setApplications((current) => current.map((item) => item.id === applicationId ? { ...item, ...saved } : item))
    return saved
  }, [])

  return {
    profiles,
    profile,
    applications,
    loading,
    error,
    environment,
    loadData,
    saveApplication,
    patchApplication,
    saveProfile,
  }
}
