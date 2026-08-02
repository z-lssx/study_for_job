import { useState } from 'react'
import { CircleAlert, Search, ShieldCheck } from 'lucide-react'
import { useIntelligenceSearch } from '../../hooks/useIntelligenceSearch'

function shortDate(value) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit' }).format(new Date(value))
}

function SearchResult({ item }) {
  return <article className="search-result-card">
    <header><span>{item.match_path.replace('_', ' ').toUpperCase()}</span><b>{item.canonical_occurrence_count} 次出现</b></header>
    <h3>{item.canonical_text}</h3>
    <p className="search-result-raw">{item.raw_text}</p>
    <blockquote>{item.evidence_text || '暂无 evidence span 文本'}</blockquote>
    <footer>
      <span>{item.document_title || '未命名面经'} · {item.round_label || `Round ${item.round_ordinal || '—'}`} · BLOCK {item.chunk_ordinal}</span>
      <span>{item.host || 'MANUAL / TEXT'} · {shortDate(item.collected_at)}</span>
      <code>submission {String(item.submission_id || '—').slice(0, 8)} · document {String(item.document_id).slice(0, 8)} · evidence [{item.start_char}, {item.end_char})</code>
      {item.source_url && <a href={item.source_url} target="_blank" rel="noreferrer">查看原文 ↗</a>}
    </footer>
  </article>
}

export function IntelligenceSearchPanel() {
  const { result, quality, loading, qualityLoading, error, search } = useIntelligenceSearch()
  const [q, setQ] = useState('')
  const [roundOrdinal, setRoundOrdinal] = useState('')
  const [fieldKind, setFieldKind] = useState('')
  const [sourceHost, setSourceHost] = useState('')

  async function submit(event) {
    event.preventDefault()
    if (!q.trim()) return
    await search({ q, roundOrdinal, fieldKind, sourceHost })
  }

  return <section className="intelligence-search-panel">
    <header className="search-panel-heading">
      <div><span>04 / RETRIEVAL DESK</span><h2>从证据里找问题</h2><p>精确术语优先，FTS 与 trigram 只提供可解释候选；每条结果都能回到来源与原文位置。</p></div>
      <div className={`quality-stamp ${quality?.status === 'insufficient_data' ? 'limited' : ''}`}>
        <ShieldCheck size={16} /><span>{qualityLoading ? 'QUALITY / LOADING' : `QUALITY / ${quality?.status || 'UNKNOWN'}`}</span>
        <small>{quality?.conclusion || '尚未读取质量状态'}</small>
      </div>
    </header>
    <form className="search-controls" onSubmit={submit}>
      <label className="search-query"><Search size={17} /><input value={q} onChange={(event) => setQ(event.target.value)} placeholder="例如：如何排查线上慢查询？" /></label>
      <label><span>ROUND</span><input inputMode="numeric" value={roundOrdinal} onChange={(event) => setRoundOrdinal(event.target.value)} placeholder="全部" /></label>
      <label><span>FIELD</span><select value={fieldKind} onChange={(event) => setFieldKind(event.target.value)}><option value="">全部问题</option><option value="question">主问题</option><option value="follow_up">追问</option></select></label>
      <label><span>SOURCE HOST</span><input value={sourceHost} onChange={(event) => setSourceHost(event.target.value)} placeholder="cnblogs.com" /></label>
      <button className="action-primary" disabled={loading || !q.trim()}>{loading ? '检索中…' : '开始检索'}</button>
    </form>
    {error && <div className="intake-message error"><CircleAlert size={15} />{error}</div>}
    {result.query && <div className="search-meta"><span>{result.results.length} 条结果 · 精确/FTS {result.exact_result_count} · 候选 {result.candidate_result_count}</span><small>{result.explanation}</small></div>}
    <div className="search-result-stack">
      {result.query && result.results.length === 0 && <p className="search-empty">没有命中当前事实链路。可换一个明确术语；系统未启用未经证据验证的 embedding 召回。</p>}
      {result.results.map((item) => <SearchResult item={item} key={item.occurrence_id} />)}
    </div>
  </section>
}
