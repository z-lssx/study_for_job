import { useCallback, useEffect, useRef, useState } from 'react'
import {
  createIntelligenceSubmissionRequest,
  loadIntelligenceSubmissionRequest,
  loadIntelligenceExtractionRequest,
  loadIntelligenceSubmissionsRequest,
  retryIntelligenceSubmissionRequest,
  saveIntelligenceChunkAnnotationRequest,
  supplementIntelligenceSubmissionRequest,
  triggerIntelligenceExtractionRequest,
} from '../api'

export function useIntelligenceData() {
  const [submissions, setSubmissions] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const selectedId = useRef(null)

  const loadData = useCallback(async (quiet = false) => {
    if (!quiet) setLoading(true)
    setError('')
    try {
      const items = await loadIntelligenceSubmissionsRequest()
      setSubmissions(items)
      if (selectedId.current) {
        const detail = await loadIntelligenceSubmissionRequest(selectedId.current)
        const extraction = await loadIntelligenceExtractionRequest(selectedId.current)
        setSelected({ ...detail, extraction: extraction.extraction })
      }
      return items
    } catch (caught) {
      setError(caught.message)
      return []
    } finally {
      if (!quiet) setLoading(false)
    }
  }, [])

  useEffect(() => { loadData() }, [loadData])
  useEffect(() => {
    const hasActive = submissions.some((item) => ['queued', 'processing', 'retry_wait'].includes(item.status))
      || ['queued', 'processing', 'retry_wait'].includes(selected?.extraction?.status)
    if (!hasActive) return undefined
    const timer = window.setInterval(() => loadData(true), 2500)
    return () => window.clearInterval(timer)
  }, [submissions, selected?.extraction?.status, loadData])

  const selectSubmission = useCallback(async (submissionId) => {
    setError('')
    try {
      const detail = await loadIntelligenceSubmissionRequest(submissionId)
      const extraction = await loadIntelligenceExtractionRequest(submissionId)
      selectedId.current = submissionId
      const merged = { ...detail, extraction: extraction.extraction }
      setSelected(merged)
      return merged
    } catch (caught) {
      setError(caught.message)
      throw caught
    }
  }, [])

  const refreshSelectedExtraction = useCallback(async (submissionId) => {
    const extraction = await loadIntelligenceExtractionRequest(submissionId)
    setSelected((current) => current?.id === submissionId ? { ...current, extraction: extraction.extraction } : current)
    return extraction.extraction
  }, [])

  const submit = useCallback(async (payload) => {
    const result = await createIntelligenceSubmissionRequest(payload)
    selectedId.current = result.submission.id
    await loadData(true)
    setSelected(result.submission)
    return result
  }, [loadData])

  const supplement = useCallback(async (submissionId, content) => {
    const result = await supplementIntelligenceSubmissionRequest(submissionId, content)
    selectedId.current = submissionId
    await loadData(true)
    setSelected(result)
    return result
  }, [loadData])

  const retry = useCallback(async (submissionId) => {
    const result = await retryIntelligenceSubmissionRequest(submissionId)
    selectedId.current = submissionId
    await loadData(true)
    setSelected(result)
    return result
  }, [loadData])

  const triggerExtraction = useCallback(async (submissionId) => {
    const result = await triggerIntelligenceExtractionRequest(submissionId)
    await refreshSelectedExtraction(submissionId)
    return result
  }, [refreshSelectedExtraction])

  const saveChunkAnnotation = useCallback(async (submissionId, chunkId, payload) => {
    const result = await saveIntelligenceChunkAnnotationRequest(submissionId, chunkId, payload)
    await refreshSelectedExtraction(submissionId)
    return result
  }, [refreshSelectedExtraction])

  return { submissions, selected, loading, error, loadData, selectSubmission, submit, supplement, retry, triggerExtraction, saveChunkAnnotation, refreshSelectedExtraction }
}
