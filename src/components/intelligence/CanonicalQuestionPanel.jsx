import { useState } from 'react'
import { CircleAlert, GitMerge, Link2, LoaderCircle, RefreshCw, Sigma } from 'lucide-react'
import { useCanonicalQuestions } from '../../hooks/useCanonicalQuestions'
import { OccurrenceCorrection } from './OccurrenceCorrection'

function shortDate(value) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(value))
}

export function CanonicalQuestionPanel() {
  const { questions, selected, loading, error, refresh, select, merge, split, remap } = useCanonicalQuestions()
  const [mergeTarget, setMergeTarget] = useState('')
  const [busy, setBusy] = useState(false)
  const occurrenceTotal = questions.reduce((sum, item) => sum + item.occurrence_count, 0)

  async function refreshFacts() {
    setBusy(true)
    try { await refresh() } finally { setBusy(false) }
  }

  async function mergeQuestion() {
    setBusy(true)
    try { await merge(selected.id, mergeTarget); setMergeTarget('') } finally { setBusy(false) }
  }

  return <section className="canonical-panel">
    <header>
      <div><span>03 / CANONICAL FREQUENCY</span><h2>规范题与出现频率</h2><p>计数只来自不可覆盖的出现记录；人工合并、拆分与改映射保留独立修订边界。</p></div>
      <div className="canonical-metrics"><strong>{questions.length}</strong><span>规范题</span><strong>{occurrenceTotal}</strong><span>出现</span></div>
      <button className="action-primary" disabled={busy || loading} onClick={refreshFacts}><RefreshCw className={busy ? 'spin' : ''} size={16} />刷新归一化</button>
    </header>
    {error && <div className="intake-message error"><CircleAlert size={15} />{error}</div>}
    <div className="canonical-body">
      <aside className="canonical-list">
        {loading && questions.length === 0 && <p><LoaderCircle className="spin" size={18} />正在读取频率</p>}
        {!loading && questions.length === 0 && <p><Sigma size={18} />先完成原文标注，再刷新归一化。</p>}
        {questions.map((item, index) => <button key={item.id} className={selected?.id === item.id ? 'active' : ''} onClick={() => select(item.id)}>
          <span>{String(index + 1).padStart(2, '0')}</span><strong>{item.canonical_text}</strong>
          <b>{item.occurrence_count}</b><small>{item.document_count} 篇文档 · {item.manually_mapped_count ? `${item.manually_mapped_count} 条人工映射` : '自动映射'}</small>
        </button>)}
      </aside>
      <article className="canonical-detail">
        {!selected ? <div className="canonical-empty"><Sigma size={28} /><h3>选择规范题核对证据</h3><p>每个计数都可下钻至文档、轮次、内容块与 evidence span。</p></div> : <>
          <header><span>{selected.created_by === 'manual' ? 'MANUAL CANONICAL' : 'DETERMINISTIC CANONICAL'}</span><h3>{selected.canonical_text}</h3></header>
          <div className="canonical-merge">
            <select aria-label="合并目标规范题" value={mergeTarget} onChange={(event) => setMergeTarget(event.target.value)}>
              <option value="">将本题合并到…</option>
              {questions.filter((item) => item.id !== selected.id).map((item) => <option key={item.id} value={item.id}>{item.canonical_text}</option>)}
            </select>
            <button disabled={busy || !mergeTarget} onClick={mergeQuestion}><GitMerge size={14} />合并全部出现</button>
          </div>
          <div className="occurrence-stack">{selected.occurrences.map((item) => <section className="occurrence-card" key={item.id}>
            <div><span>{item.round_label || '轮次待确认'} · BLOCK {item.chunk_ordinal}</span><strong>{item.raw_text}</strong><small>{item.document_title || '未命名面经'} · {shortDate(item.collected_at)}</small></div>
            <blockquote>{item.evidence_text}</blockquote>
            <footer><code>document {item.document_id.slice(0, 8)} · run {item.run_id.slice(0, 8)} · evidence [{item.start_char}, {item.end_char})</code>
              {item.source_url && <a href={item.source_url} target="_blank" rel="noreferrer"><Link2 size={13} />原文</a>}
              <span>{item.mapping_origin === 'manual' ? `人工修订 R${item.mapping_revision}` : '自动映射'}{item.revision_count ? ` · ${item.revision_count} 条历史` : ''}</span>
            </footer>
            <OccurrenceCorrection question={selected} occurrence={item} questions={questions} onSplit={split} onRemap={remap} />
          </section>)}</div>
        </>}
      </article>
    </div>
  </section>
}
