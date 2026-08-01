import { useCallback, useEffect, useState } from 'react'
import {
  loadAiCallsRequest,
  loadAiRuntimeRequest,
  loadAiStatisticsRequest,
  loadPromptsRequest,
  runAiDiagnosticRequest,
  savePromptRequest,
} from '../api'

export function useAiAdminData() {
  const [runtime, setRuntime] = useState(null)
  const [prompts, setPrompts] = useState([])
  const [statistics, setStatistics] = useState([])
  const [calls, setCalls] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadData = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [nextRuntime, nextPrompts, nextStatistics, nextCalls] = await Promise.all([
        loadAiRuntimeRequest(),
        loadPromptsRequest(),
        loadAiStatisticsRequest(),
        loadAiCallsRequest(),
      ])
      setRuntime(nextRuntime)
      setPrompts(nextPrompts)
      setStatistics(nextStatistics.items)
      setCalls(nextCalls)
    } catch (caught) {
      setError(caught.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadData() }, [loadData])

  const savePrompt = useCallback(async (scenarioKey, payload) => {
    const saved = await savePromptRequest(scenarioKey, payload)
    setPrompts((current) => current.map((item) => item.scenario_key === scenarioKey ? saved : item))
    return saved
  }, [])

  const runDiagnostic = useCallback(async (simulateFailure) => {
    try {
      return await runAiDiagnosticRequest(simulateFailure)
    } finally {
      await loadData()
    }
  }, [loadData])

  return { runtime, prompts, statistics, calls, loading, error, loadData, savePrompt, runDiagnostic }
}
