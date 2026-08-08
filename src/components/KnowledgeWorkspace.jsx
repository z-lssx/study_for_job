import React, { useEffect, useMemo, useRef, useState } from 'react'
import { ArrowLeft, BookOpen, Check, ExternalLink, Link2, Plus, RotateCcw, Search, X } from 'lucide-react'
import {
  addKnowledgeEvidenceRequest,
  createKnowledgeCardRequest,
  loadKnowledgeCardRequest,
  loadKnowledgeCardsRequest,
  removeKnowledgeEvidenceRequest,
  reviewKnowledgeCardRequest,
  updateKnowledgeCardRequest,
} from '../api/knowledge'
import { searchIntelligenceRequest } from '../api/intelligenceSearch'
import { useUnsavedGuard } from '../hooks/useUnsavedGuard'
import './knowledge.css'

const statuses = [
  ['not_started', '未开始'], ['learning', '学习中'], ['familiar', '已熟悉'], ['mastered', '已掌握'],
]
const statusLabel = (value) => statuses.find(([key]) => key === value)?.[1] || value
const localDateValue = () => {
  const now = new Date()
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10)
}

function CreateCardDialog({ onClose, onSaved }) {
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { const close = (event) => event.key === 'Escape' && onClose(); window.addEventListener('keydown', close); return () => window.removeEventListener('keydown', close) }, [onClose])
  async function submit(event) {
    event.preventDefault()
    const values = new FormData(event.currentTarget)
    setSaving(true)
    try {
      const card = await createKnowledgeCardRequest({
        title: values.get('title'), prompt: values.get('prompt') || null, notes: values.get('notes') || null,
      })
      onSaved(card)
    } catch (caught) { setError(caught.message) } finally { setSaving(false) }
  }
  return <div className="track-dialog-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
    <section className="track-dialog" role="dialog" aria-modal="true" aria-labelledby="knowledge-create-title">
      <header><div><span>快速新建</span><h2 id="knowledge-create-title">加入一张知识题卡</h2></div><button type="button" onClick={onClose} aria-label="关闭"><X size={19} /></button></header>
      <form onSubmit={submit}>
        <label>题目或知识点<input name="title" required autoFocus maxLength={240} placeholder="例如：PostgreSQL 索引失效场景" /></label>
        <label>口述版本<textarea name="prompt" maxLength={2000} rows={3} placeholder="先写一版能够当场讲清楚的回答" /></label>
        <label>个人笔记<textarea name="notes" maxLength={10000} rows={4} placeholder="追问、资料位置或待补证据" /></label>
        {error && <p className="track-inline-error">{error}</p>}
        <footer><button type="button" className="track-button-secondary" onClick={onClose}>取消</button><button className="track-button-primary" disabled={saving}>{saving ? '保存中…' : '保存题卡'}</button></footer>
      </form>
    </section>
  </div>
}

function KnowledgeDetail({ cardId, navigate, onDirty, onSaved }) {
  const [card, setCard] = useState(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [query, setQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const requestVersion = useRef(0)

  async function refresh() {
    const version = ++requestVersion.current
    setLoading(true)
    setCard(null)
    try {
      const value = await loadKnowledgeCardRequest(cardId)
      if (version !== requestVersion.current) return
      setCard(value); setError('')
    } catch (caught) { if (version === requestVersion.current) setError(caught.message) } finally { if (version === requestVersion.current) setLoading(false) }
  }
  useEffect(() => {
    let active = true
    const version = ++requestVersion.current
    setCard(null); setEditing(false); setLoading(true); setQuery(''); setSearchResults([]); setMessage(''); setError('')
    loadKnowledgeCardRequest(cardId)
      .then((value) => { if (active && version === requestVersion.current) setCard(value) })
      .catch((caught) => { if (active && version === requestVersion.current) setError(caught.message) })
      .finally(() => { if (active && version === requestVersion.current) setLoading(false) })
    return () => { active = false }
  }, [cardId])

  async function save(event) {
    event.preventDefault()
    const values = new FormData(event.currentTarget)
    const version = requestVersion.current
    try {
      const value = await updateKnowledgeCardRequest(cardId, {
        title: values.get('title'), prompt: values.get('prompt') || null, notes: values.get('notes') || null,
        mastery_status: values.get('mastery_status'), next_review_at: values.get('next_review_at') || null,
      })
      if (version !== requestVersion.current) return
      setCard(value)
      setEditing(false); setMessage('题卡修订已保存'); setError(''); onSaved()
    } catch (caught) { if (version === requestVersion.current) setError(caught.message) }
  }

  async function recordReview() {
    const index = statuses.findIndex(([value]) => value === card.mastery_status)
    const next = statuses[Math.min(index + 1, statuses.length - 1)][0]
    const version = requestVersion.current
    try {
      const value = await reviewKnowledgeCardRequest(cardId, { mastery_status: next, next_review_at: card.next_review_at })
      if (version !== requestVersion.current) return
      setCard(value); setMessage('已记录本次复习')
    } catch (caught) { if (version === requestVersion.current) setError(caught.message) }
  }

  async function searchEvidence(event) {
    event.preventDefault()
    const version = requestVersion.current
    try {
      const result = await searchIntelligenceRequest({ q: query, limit: 12 })
      if (version !== requestVersion.current) return
      setSearchResults(result.results || []); setError('')
    } catch (caught) { if (version === requestVersion.current) setError(caught.message) }
  }
  async function addEvidence(result) {
    const version = requestVersion.current
    try {
      const value = await addKnowledgeEvidenceRequest(cardId, { evidence_span_id: result.evidence_span_id })
      if (version !== requestVersion.current) return
      setCard(value); setMessage('证据已关联'); setSearchResults([])
    } catch (caught) { if (version === requestVersion.current) setError(caught.message) }
  }
  async function removeEvidence(evidenceSpanId) {
    const version = requestVersion.current
    try {
      await removeKnowledgeEvidenceRequest(cardId, evidenceSpanId)
      if (version !== requestVersion.current) return
      await refresh(); setMessage('证据关联已移除')
    } catch (caught) { if (version === requestVersion.current) setError(caught.message) }
  }
  function cancelEditing() { setEditing(false); onSaved() }

  if (loading) return <section className="track-detail-page"><div className="track-skeleton tall" /></section>
  if (!card) return <section className="track-detail-page"><button className="track-back" onClick={() => navigate('/knowledge')}><ArrowLeft size={17} />返回知识轨道</button><p className="track-page-error">{error || '知识题卡不存在'}</p></section>

  return <section className="track-detail-page knowledge-detail-page">
    <button className="track-back" type="button" onClick={() => navigate('/knowledge')}><ArrowLeft size={17} />返回知识轨道</button>
    <nav className="track-breadcrumb" aria-label="面包屑"><button onClick={() => navigate('/knowledge')}>知识</button><span>/</span><b>{card.title}</b></nav>
    <header className="track-detail-heading"><div><span className="track-eyebrow">知识题详情</span><h1>{card.title}</h1><p>复习 {card.review_count} 次{card.last_reviewed_at ? ` · 最近复习 ${new Date(card.last_reviewed_at).toLocaleDateString('zh-CN')}` : ''}</p></div><div><span className={`track-status status-${card.mastery_status}`}>{statusLabel(card.mastery_status)}</span><button className="track-button-secondary" onClick={() => editing ? cancelEditing() : setEditing(true)}>{editing ? '取消编辑' : '编辑题卡'}</button><button className="track-button-primary" onClick={recordReview} disabled={card.mastery_status === 'mastered'}><Check size={16} />记录复习</button></div></header>
    {message && <p className="track-success" role="status">{message}</p>}{error && <p className="track-page-error">{error}</p>}
    {editing ? <form className="track-editor knowledge-editor" onSubmit={save} onChange={onDirty}>
      <label>题目<input name="title" defaultValue={card.title} required maxLength={240} /></label>
      <label>口述版本<textarea name="prompt" defaultValue={card.prompt || ''} maxLength={2000} rows={7} /></label>
      <label>个人笔记与追问<textarea name="notes" defaultValue={card.notes || ''} maxLength={10000} rows={9} /></label>
      <div className="track-form-columns"><label>掌握状态<select name="mastery_status" defaultValue={card.mastery_status}>{statuses.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>下次复习<input name="next_review_at" type="date" defaultValue={card.next_review_at || ''} /></label></div>
      <footer><button type="button" className="track-button-secondary" onClick={cancelEditing}>取消</button><button className="track-button-primary">保存修订</button></footer>
    </form> : <div className="knowledge-reading-grid">
      <article className="track-reading-surface"><span className="track-section-label">口述练习</span><h2>一版能够讲清楚的回答</h2><p>{card.prompt || '还没有口述版本。进入编辑，先写下你能自然讲出的第一版。'}</p></article>
      <aside className="track-note-surface"><span className="track-section-label">复习安排</span><dl><div><dt>掌握状态</dt><dd>{statusLabel(card.mastery_status)}</dd></div><div><dt>下次复习</dt><dd>{card.next_review_at || '尚未安排'}</dd></div><div><dt>事实来源</dt><dd>{card.origin === 'user' ? '用户创建' : '情报建议后创建'}</dd></div></dl></aside>
      <article className="track-reading-surface"><span className="track-section-label">个人笔记与追问</span><h2>容易遗漏的边界</h2><p>{card.notes || '暂无笔记。可以记录追问、反例和仍需查证的部分。'}</p></article>
    </div>}
    <section className="knowledge-evidence-section">
      <header><div><span className="track-section-label">证据回链</span><h2>让回答回到原始面经</h2></div><span>{card.evidence.length} 条</span></header>
      <div className="knowledge-evidence-list">{card.evidence.map((item) => <article key={item.evidence_span_id}><blockquote>{item.quote}</blockquote><div><span>{item.source?.host || '本地面经事实'}</span>{item.source?.url && <a href={item.source.url} target="_blank" rel="noreferrer">打开来源<ExternalLink size={13} /></a>}<button onClick={() => removeEvidence(item.evidence_span_id)}>移除关联</button></div></article>)}{card.evidence.length === 0 && <p className="track-empty-compact">暂未关联证据。题卡仍是用户事实，不会因缺少证据被自动改写。</p>}</div>
      <details className="track-disclosure"><summary><Link2 size={15} />检索并关联证据</summary><form className="knowledge-evidence-search" onSubmit={searchEvidence}><label><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} required placeholder="输入知识点或追问关键词" /></label><button className="track-button-secondary">检索</button></form><div className="knowledge-search-results">{searchResults.map((item) => <article key={item.evidence_span_id}><p>{item.evidence_text}</p><span>{item.source_host || '面经证据'} · {item.match_path}</span><button onClick={() => addEvidence(item)}>关联此证据</button></article>)}</div></details>
    </section>
  </section>
}

export function KnowledgeWorkspace({ selectedId, navigate = () => {} }) {
  const [cards, setCards] = useState([])
  const [filter, setFilter] = useState('due')
  const [showCreate, setShowCreate] = useState(false)
  const [dirty, setDirty] = useState(false)
  useUnsavedGuard(dirty, '知识题卡还有未保存的修改，确定离开吗？')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  async function refresh() {
    setLoading(true)
    try { setCards(await loadKnowledgeCardsRequest()); setError('') } catch (caught) { setError(caught.message) } finally { setLoading(false) }
  }
  useEffect(() => { if (!selectedId) refresh() }, [selectedId])
  useEffect(() => { setDirty(false) }, [selectedId])
  const visible = useMemo(() => cards.filter((card) => {
    if (filter === 'all') return true
    if (filter === 'due') return card.mastery_status !== 'mastered' && (!card.next_review_at || card.next_review_at <= new Date().toISOString().slice(0, 10))
    return card.mastery_status === filter
  }), [cards, filter])
  if (selectedId) return <KnowledgeDetail cardId={selectedId} navigate={navigate} onDirty={() => setDirty(true)} onSaved={() => setDirty(false)} />
  return <section className="track-index-page knowledge-workspace">
    <header className="track-index-heading"><div><span className="track-eyebrow">准备轨道 · 知识</span><h1>把知识练成能说出口的答案</h1><p>优先处理到期题目，掌握状态与复习节奏始终由你维护。</p></div><button className="track-button-primary" onClick={() => setShowCreate(true)}><Plus size={17} />新建题卡</button></header>
    {error && <p className="track-page-error">{error}</p>}
    <section className="knowledge-focus-strip"><div><span>今日复习入口</span><strong>{cards.filter((card) => card.mastery_status !== 'mastered' && (!card.next_review_at || card.next_review_at <= localDateValue())).length}</strong><p>张题卡已到复习时间或尚未安排节奏。</p></div><button disabled={visible.length === 0} onClick={() => navigate(`/knowledge/${visible[Math.floor(Math.random() * visible.length)]?.id}`)}><BookOpen size={18} />随机练一题</button></section>
    <div className="track-filter-row" aria-label="掌握状态筛选"><button className={filter === 'due' ? 'active' : ''} onClick={() => setFilter('due')}>待复习</button>{statuses.map(([value, label]) => <button key={value} className={filter === value ? 'active' : ''} onClick={() => setFilter(value)}>{label}</button>)}<button className={filter === 'all' ? 'active' : ''} onClick={() => setFilter('all')}>全部</button><button className="track-refresh" onClick={refresh}><RotateCcw size={15} />刷新</button></div>
    {loading ? <div className="track-list"><div className="track-skeleton" /><div className="track-skeleton" /></div> : <div className="track-list knowledge-list">{visible.map((card) => <button className="knowledge-list-row" key={card.id} onClick={() => navigate(`/knowledge/${card.id}`)}><div><span className={`track-status status-${card.mastery_status}`}>{statusLabel(card.mastery_status)}</span><strong>{card.title}</strong><p>{card.prompt || card.notes || '还没有口述版本，进入题卡补充。'}</p></div><dl><div><dt>复习</dt><dd>{card.review_count} 次</dd></div><div><dt>证据</dt><dd>{card.evidence.length} 条</dd></div><div><dt>下次</dt><dd>{card.next_review_at || '待安排'}</dd></div></dl></button>)}{visible.length === 0 && <div className="track-empty"><BookOpen size={24} /><h2>{cards.length ? '当前筛选下没有题卡' : '从一个近期高频主题开始'}</h2><p>{cards.length ? '切换掌握状态查看其他题卡。' : '创建题卡后，可以持续记录口述版本、复习和证据回链。'}</p>{cards.length === 0 && <button className="track-button-primary" onClick={() => setShowCreate(true)}>新建第一张题卡</button>}</div>}</div>}
    {showCreate && <CreateCardDialog onClose={() => setShowCreate(false)} onSaved={(card) => { setShowCreate(false); navigate(`/knowledge/${card.id}`) }} />}
  </section>
}
