import { useCallback, useEffect, useRef, useState } from 'react'
import {
  loadCanonicalQuestionDetailRequest,
  loadCanonicalQuestionsRequest,
  mapQuestionOccurrenceRequest,
  mergeCanonicalQuestionRequest,
  refreshCanonicalQuestionsRequest,
  splitCanonicalQuestionRequest,
} from '../api/canonicalQuestions'

export function useCanonicalQuestions() {
  const [questions, setQuestions] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const selectedId = useRef(null)

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const rows = await loadCanonicalQuestionsRequest()
      setQuestions(rows)
      if (selected?.id) {
        const requestedId = selected.id
        const detail = await loadCanonicalQuestionDetailRequest(requestedId)
        if (selectedId.current === requestedId) setSelected(detail)
      }
      return rows
    } catch (caught) { setError(caught.message); return [] } finally { setLoading(false) }
  }, [selected?.id])

  useEffect(() => { load() }, [load])

  const refresh = useCallback(async () => {
    setError('')
    try { const result = await refreshCanonicalQuestionsRequest(); await load(); return result }
    catch (caught) { setError(caught.message); throw caught }
  }, [load])

  const select = useCallback(async (id) => {
    setError('')
    selectedId.current = id
    setSelected(null)
    try {
      const detail = await loadCanonicalQuestionDetailRequest(id)
      if (selectedId.current === id) setSelected(detail)
      return detail
    }
    catch (caught) { if (selectedId.current === id) setError(caught.message); throw caught }
  }, [])

  const clearSelected = useCallback(() => {
    selectedId.current = null
    setSelected(null)
  }, [])

  const afterMutation = useCallback(async (id) => {
    await load()
    if (id) {
      selectedId.current = id
      const detail = await loadCanonicalQuestionDetailRequest(id).catch(() => null)
      if (selectedId.current === id) setSelected(detail)
    }
  }, [load])

  const merge = useCallback(async (sourceId, targetId) => {
    const result = await mergeCanonicalQuestionRequest(sourceId, { target_canonical_question_id: targetId, note_text: '页面人工合并' })
    await afterMutation(targetId); return result
  }, [afterMutation])

  const split = useCallback(async (sourceId, occurrenceId, canonicalText) => {
    const result = await splitCanonicalQuestionRequest(sourceId, { occurrence_ids: [occurrenceId], canonical_text: canonicalText, note_text: '页面人工拆分' })
    await afterMutation(sourceId); return result
  }, [afterMutation])

  const remap = useCallback(async (occurrenceId, targetId) => {
    const result = await mapQuestionOccurrenceRequest(occurrenceId, { target_canonical_question_id: targetId, note_text: '页面人工等价修正' })
    await afterMutation(targetId); return result
  }, [afterMutation])

  return { questions, selected, loading, error, load, refresh, select, clearSelected, merge, split, remap }
}
