import { useState } from 'react'
import { CircleAlert, Save, Tags } from 'lucide-react'

const BLOCK_LABELS = {
  question: '问题', author_answer: '原作者回答', interviewer_feedback: '面试官反馈',
  follow_up: '追问', process_description: '过程描述', unknown: '待确认',
}

function ChunkAnnotationEditor({ submissionId, chunk, onSave }) {
  const [note, setNote] = useState(chunk.annotation?.note_text || '')
  const [reviewStatus, setReviewStatus] = useState(chunk.annotation?.review_status || 'needs_review')
  const [saving, setSaving] = useState(false)
  async function save() {
    setSaving(true)
    try { await onSave(submissionId, chunk.id, { note_text: note.trim() || null, review_status: reviewStatus }) } finally { setSaving(false) }
  }
  return <div className="chunk-review">
    <select aria-label="人工校验状态" value={reviewStatus} onChange={(event) => setReviewStatus(event.target.value)}>
      <option value="needs_review">待确认</option><option value="confirmed">已确认</option><option value="rejected">不采用</option>
    </select>
    <input aria-label="个人备注" value={note} onChange={(event) => setNote(event.target.value)} placeholder="个人备注（不改写机器事实）" />
    <button type="button" onClick={save} disabled={saving}><Save size={13} />{saving ? '保存中' : '保存'}</button>
  </div>
}

export function ExtractionPanel({ item, onTrigger, onSaveAnnotation }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  if (!item.document) return null
  const extraction = item.extraction
  const active = extraction && ['queued', 'processing', 'retry_wait'].includes(extraction.status)

  async function trigger() {
    setBusy(true); setError('')
    try { await onTrigger(item.id) } catch (caught) { setError(caught.message) } finally { setBusy(false) }
  }

  return <section className="extraction-panel">
    <header>
      <div><span>STRUCTURED EVIDENCE / T006</span><h3>原文标注与证据链</h3></div>
      {(!extraction || extraction.status === 'failed') && <button className="action-primary" onClick={trigger} disabled={busy}><Tags size={15} />{extraction ? '重新抽取' : '开始标注'}</button>}
    </header>
    {!extraction && <p className="extraction-empty">使用版本化确定性规则标注轮次、块类型、问题与追问；不会把原作者回答当作标准答案。</p>}
    {extraction && <>
      <div className={`extraction-run status-${extraction.status}`}>
        <strong>{active ? '标注处理中' : extraction.status === 'succeeded' ? '标注已生成' : '标注失败'}</strong>
        <span>{extraction.schema_version} · {extraction.processor_version} · R{extraction.trigger_revision}</span>
      </div>
      {extraction.error && <div className="intel-failure"><span>{extraction.error.code}</span><strong>{extraction.error.message}</strong></div>}
      {extraction.status === 'succeeded' && <div className="chunk-stack">
        {extraction.chunks.map((chunk) => <details className={`evidence-chunk type-${chunk.block_type}`} key={chunk.id} open={['question', 'follow_up'].includes(chunk.block_type)}>
          <summary><span>{String(chunk.ordinal).padStart(2, '0')}</span><strong>{BLOCK_LABELS[chunk.block_type]}</strong><small>{chunk.round_label || '轮次待确认'} · [{chunk.start_char}, {chunk.end_char})</small></summary>
          <blockquote>{chunk.evidence_text}</blockquote>
          {chunk.candidates.map((candidate) => <div className="candidate-line" key={candidate.id}>
            <span>{candidate.field_kind === 'follow_up' ? '追问字段' : '问题字段'}</span><strong>{candidate.text}</strong>
            <small>{candidate.topic_candidate || '主题待确认'} · evidence [{candidate.start_char}, {candidate.end_char}) · ID {candidate.candidate_key.slice(0, 10)}</small>
          </div>)}
          {chunk.block_type === 'author_answer' && <p className="author-answer-note">仅表示原作者经验内容，不代表标准答案。</p>}
          <ChunkAnnotationEditor submissionId={item.id} chunk={chunk} onSave={onSaveAnnotation} />
        </details>)}
      </div>}
    </>}
    {error && <div className="intake-message error"><CircleAlert size={15} />{error}</div>}
  </section>
}
