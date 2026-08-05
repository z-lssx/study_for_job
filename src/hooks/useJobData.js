import { useCallback, useEffect, useMemo, useState } from 'react'
import { saveApplicationRequest, saveProfileRequest } from '../api'

export function useJobData() {
  const [profiles, setProfiles] = useState([])
  const [profile, setProfile] = useState(null)
  const [applications, setApplications] = useState([])
  const [selectedId, setSelectedId] = useState(null)
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
      setSelectedId((current) => current && nextApplications.some((item) => item.id === current) ? current : null)
    } catch (caught) {
      setError(caught.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadData() }, [loadData])

  const selected = useMemo(
    () => applications.find((item) => item.id === selectedId) || null,
    [applications, selectedId],
  )

  const saveApplication = useCallback(async (payload, applicationId = null) => {
    const saved = await saveApplicationRequest(payload, applicationId)
    await loadData()
    setSelectedId(saved.id)
    return saved
  }, [loadData])

  const saveProfile = useCallback(async (payload) => {
    const saved = await saveProfileRequest(payload, profile?.id)
    await loadData()
    return saved
  }, [loadData, profile?.id])

  return {
    profiles,
    profile,
    applications,
    selected,
    selectedId,
    loading,
    error,
    environment,
    loadData,
    saveApplication,
    saveProfile,
    selectApplication: setSelectedId,
    closeSelection: () => setSelectedId(null),
  }
}
