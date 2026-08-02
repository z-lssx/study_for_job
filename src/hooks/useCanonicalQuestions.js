import { useCallback, useEffect, useState } from 'react'
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

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const rows = await loadCanonicalQuestionsRequest()
      setQuestions(rows)
      if (selected?.id) setSelected(await loadCanonicalQuestionDetailRequest(selected.id))
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
    try { const detail = await loadCanonicalQuestionDetailRequest(id); setSelected(detail); return detail }
    catch (caught) { setError(caught.message); throw caught }
  }, [])

  const afterMutation = useCallback(async (id) => {
    await load()
    if (id) setSelected(await loadCanonicalQuestionDetailRequest(id).catch(() => null))
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

  return { questions, selected, loading, error, load, refresh, select, merge, split, remap }
}
