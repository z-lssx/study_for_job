import { useCallback, useEffect, useState } from 'react'
import { loadIntelligenceQualityRequest, searchIntelligenceRequest } from '../api/intelligenceSearch'

export function useIntelligenceSearch() {
  const [result, setResult] = useState({ results: [], search_paths: [] })
  const [quality, setQuality] = useState(null)
  const [loading, setLoading] = useState(false)
  const [qualityLoading, setQualityLoading] = useState(true)
  const [error, setError] = useState('')

  const loadQuality = useCallback(async () => {
    setQualityLoading(true)
    try { const value = await loadIntelligenceQualityRequest(); setQuality(value); return value }
    catch (caught) { setError(caught.message); return null }
    finally { setQualityLoading(false) }
  }, [])

  useEffect(() => { loadQuality() }, [loadQuality])

  const search = useCallback(async (params) => {
    setLoading(true); setError('')
    try { const value = await searchIntelligenceRequest(params); setResult(value); return value }
    catch (caught) { setError(caught.message); throw caught }
    finally { setLoading(false) }
  }, [])

  return { result, quality, loading, qualityLoading, error, search, loadQuality }
}
