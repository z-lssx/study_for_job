import React, { useEffect, useMemo, useRef, useState } from 'react'
import { ArrowLeft, BrainCircuit, Check, Dice5, ExternalLink, Plus, RotateCcw, X } from 'lucide-react'
import {
  createAlgorithmProblemRequest,
  loadAlgorithmProblemRequest,
  loadAlgorithmProblemsRequest,
  practiceAlgorithmProblemRequest,
  randomAlgorithmProblemRequest,
  updateAlgorithmProblemRequest,
} from '../api/algorithms'
import { loadCanonicalQuestionsRequest } from '../api/canonicalQuestions'
import { useUnsavedGuard } from '../hooks/useUnsavedGuard'
import './knowledge.css'
import './algorithms.css'

const statuses = [['not_started', '未开始'], ['in_progress', '进行中'], ['revisit', '待复盘'], ['solved', '已解决']]
const difficulties = [['unknown', '未标注'], ['easy', '简单'], ['medium', '中等'], ['hard', '困难']]
const labelOf = (options, value) => options.find(([key]) => key === value)?.[1] || value

function CreateProblemDialog({ onClose, onSaved }) {
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { const close = (event) => event.key === 'Escape' && onClose(); window.addEventListener('keydown', close); return () => window.removeEventListener('keydown', close) }, [onClose])
  async function submit(event) {
    event.preventDefault()
    const values = new FormData(event.currentTarget)
    setSaving(true)
    try {
      const problem = await createAlgorithmProblemRequest({
        title: values.get('title'), source_url: values.get('source_url') || null,
        source_platform: values.get('source_platform') || 'manual', difficulty: values.get('difficulty'),
        tags: String(values.get('tags') || '').split(',').map((tag) => tag.trim()).filter(Boolean),
      })
      onSaved(problem)
    } catch (caught) { setError(caught.message) } finally { setSaving(false) }
  }
  return <div className="track-dialog-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><section className="track-dialog" role="dialog" aria-modal="true" aria-labelledby="algorithm-create-title"><header><div><span>加入优先题单</span><h2 id="algorithm-create-title">记录一道外部算法题</h2></div><button type="button" onClick={onClose} aria-label="关闭"><X size={19} /></button></header><form onSubmit={submit}>
    <label>题目标题<input name="title" required autoFocus maxLength={240} /></label>
    <div className="track-form-columns"><label>来源平台<input name="source_platform" defaultValue="manual" maxLength={80} /></label><label>难度<select name="difficulty" defaultValue="unknown">{difficulties.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label></div>
    <label>外部题目链接<input name="source_url" type="url" maxLength={2048} placeholder="https://…" /></label><label>标签<input name="tags" maxLength={500} placeholder="数组, 双指针, 滑动窗口" /></label>
    {error && <p className="track-inline-error">{error}</p>}<footer><button type="button" className="track-button-secondary" onClick={onClose}>取消</button><button className="track-button-primary" disabled={saving}>{saving ? '保存中…' : '保存题目'}</button></footer>
  </form></section></div>
}

function AlgorithmDetail({ problemId, navigate, onDirty, onSaved }) {
  const [problem, setProblem] = useState(null)
  const [questions, setQuestions] = useState([])
  const [editing, setEditing] = useState(false)
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const requestVersion = useRef(0)
  async function refresh() {
    const version = ++requestVersion.current
    setLoading(true)
    setProblem(null)
    try {
      const value = await loadAlgorithmProblemRequest(problemId)
      if (version !== requestVersion.current) return
      setProblem(value); setError('')
    } catch (caught) { if (version === requestVersion.current) setError(caught.message) } finally { if (version === requestVersion.current) setLoading(false) }
  }
  useEffect(() => {
    let active = true
    const version = ++requestVersion.current
    setProblem(null); setEditing(false); setLoading(true); setMessage(''); setError('')
    loadAlgorithmProblemRequest(problemId)
      .then((value) => { if (active && version === requestVersion.current) setProblem(value) })
      .catch((caught) => { if (active && version === requestVersion.current) setError(caught.message) })
      .finally(() => { if (active && version === requestVersion.current) setLoading(false) })
    loadCanonicalQuestionsRequest({ limit: 100 }).then((items) => { if (active) setQuestions(items) }).catch(() => { if (active) setQuestions([]) })
    return () => { active = false }
  }, [problemId])
  async function save(event) {
    event.preventDefault()
    const values = new FormData(event.currentTarget)
    const version = requestVersion.current
    try {
      const value = await updateAlgorithmProblemRequest(problemId, {
        title: values.get('title'), source_url: values.get('source_url') || null,
        source_platform: values.get('source_platform'), difficulty: values.get('difficulty'),
        tags: String(values.get('tags') || '').split(',').map((tag) => tag.trim()).filter(Boolean),
        status: values.get('status'), mistake_reason: values.get('mistake_reason') || null,
        review_notes: values.get('review_notes') || null, notes: values.get('notes') || null,
        canonical_question_id: values.get('canonical_question_id') || null,
        next_review_at: values.get('next_review_at') || null,
      })
      if (version !== requestVersion.current) return
      setProblem(value)
      setEditing(false); setMessage('题目修订已保存'); setError(''); onSaved()
    } catch (caught) { if (version === requestVersion.current) setError(caught.message) }
  }
  async function recordPractice() {
    const index = statuses.findIndex(([value]) => value === problem.status)
    const next = statuses[Math.min(index + 1, statuses.length - 1)][0]
    const version = requestVersion.current
    try {
      const value = await practiceAlgorithmProblemRequest(problemId, {
        status: next, mistake_reason: problem.mistake_reason || null,
        review_notes: problem.review_notes || null, next_review_at: problem.next_review_at || null,
      })
      if (version !== requestVersion.current) return
      setProblem(value)
      setMessage('已记录本次外部练习'); setError('')
    } catch (caught) { if (version === requestVersion.current) setError(caught.message) }
  }
  function cancelEditing() { setEditing(false); onSaved() }
  if (loading) return <section className="track-detail-page"><div className="track-skeleton tall" /></section>
  if (!problem) return <section className="track-detail-page"><button className="track-back" onClick={() => navigate('/algorithms')}><ArrowLeft size={17} />返回算法轨道</button><p className="track-page-error">{error || '算法题不存在'}</p></section>
  return <section className="track-detail-page algorithm-detail-page">
    <button className="track-back" onClick={() => navigate('/algorithms')}><ArrowLeft size={17} />返回算法轨道</button>
    <nav className="track-breadcrumb" aria-label="面包屑"><button onClick={() => navigate('/algorithms')}>算法</button><span>/</span><b>{problem.title}</b></nav>
    <header className="track-detail-heading"><div><span className="track-eyebrow">算法题详情</span><h1>{problem.title}</h1><p>{problem.source_platform} · {labelOf(difficulties, problem.difficulty)} · 练习 {problem.practice_count} 次</p></div><div><span className={`track-status status-${problem.status}`}>{labelOf(statuses, problem.status)}</span><button className="track-button-secondary" onClick={() => editing ? cancelEditing() : setEditing(true)}>{editing ? '取消编辑' : '编辑复盘'}</button><button className="track-button-primary" onClick={recordPractice} disabled={problem.status === 'solved'}><Check size={16} />记录练习</button></div></header>
    {message && <p className="track-success" role="status">{message}</p>}{error && <p className="track-page-error">{error}</p>}
    {editing ? <form className="track-editor algorithm-detail-editor" onSubmit={save} onChange={onDirty}>
      <div className="track-form-columns"><label>题目标题<input name="title" defaultValue={problem.title} required maxLength={240} /></label><label>来源平台<input name="source_platform" defaultValue={problem.source_platform} required maxLength={80} /></label></div>
      <div className="track-form-columns"><label>难度<select name="difficulty" defaultValue={problem.difficulty}>{difficulties.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>状态<select name="status" defaultValue={problem.status}>{statuses.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label></div>
      <label>外部题目链接<input name="source_url" defaultValue={problem.source_url || ''} type="url" maxLength={2048} /></label><label>标签<input name="tags" defaultValue={(problem.tags || []).join(', ')} maxLength={500} /></label>
      <label>卡点与出错原因<textarea name="mistake_reason" defaultValue={problem.mistake_reason || ''} maxLength={4000} rows={4} /></label><label>复盘<textarea name="review_notes" defaultValue={problem.review_notes || ''} maxLength={10000} rows={7} /></label><label>补充笔记<textarea name="notes" defaultValue={problem.notes || ''} maxLength={4000} rows={4} /></label>
      <div className="track-form-columns"><label>关联规范题<select name="canonical_question_id" defaultValue={problem.canonical_question_id || ''}><option value="">不关联</option>{questions.map((question) => <option key={question.id} value={question.id}>{question.canonical_text}（{question.occurrence_count} 次）</option>)}</select></label><label>下次复盘<input name="next_review_at" type="date" defaultValue={problem.next_review_at || ''} /></label></div>
      <footer><button type="button" className="track-button-secondary" onClick={cancelEditing}>取消</button><button className="track-button-primary">保存修订</button></footer>
    </form> : <div className="algorithm-detail-grid">
      <article className="algorithm-practice-card"><span className="track-section-label">外部练习</span><h2>回到题目完成练习</h2><p>本工作台只记录状态、卡点与复盘，不提供在线编辑或判题。</p>{problem.source_url ? <a className="track-button-primary" href={problem.source_url} target="_blank" rel="noreferrer">打开原题<ExternalLink size={16} /></a> : <button className="track-button-secondary" onClick={() => setEditing(true)}>补充题目链接</button>}</article>
      <aside className="algorithm-practice-meta"><dl><div><dt>最近练习</dt><dd>{problem.last_practiced_at ? new Date(problem.last_practiced_at).toLocaleString('zh-CN') : '尚未练习'}</dd></div><div><dt>下次复盘</dt><dd>{problem.next_review_at || '尚未安排'}</dd></div><div><dt>累计次数</dt><dd>{problem.practice_count} 次</dd></div></dl><p>当前数据只保存累计次数与最近练习时间，不虚构逐次练习历史。</p></aside>
      <article className="track-reading-surface"><span className="track-section-label">卡点</span><h2>这道题为什么会卡住</h2><p>{problem.mistake_reason || '尚未记录卡点。练习后写下判断失误或思路中断的位置。'}</p></article>
      <article className="track-reading-surface"><span className="track-section-label">复盘</span><h2>下次如何更快识别</h2><p>{problem.review_notes || '尚未记录复盘。可以补充正确思路、复杂度和下次提醒。'}</p>{problem.notes && <p className="algorithm-secondary-note">{problem.notes}</p>}</article>
      {problem.canonical_question && <article className="algorithm-intelligence-note"><span className="track-section-label">情报关联 · 仅供解释</span><strong>{problem.canonical_question.text}</strong><p>原始情报出现 {problem.canonical_question.occurrence_count} 次；这不是题目难度或个人能力评分。</p></article>}
    </div>}
  </section>
}

export function AlgorithmWorkspace({ selectedId, navigate = () => {} }) {
  const [problems, setProblems] = useState([])
  const [filter, setFilter] = useState('priority')
  const [random, setRandom] = useState(null)
  const [showCreate, setShowCreate] = useState(false)
  const [dirty, setDirty] = useState(false)
  useUnsavedGuard(dirty, '算法复盘还有未保存的修改，确定离开吗？')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  async function refresh() { setLoading(true); try { setProblems(await loadAlgorithmProblemsRequest()); setError('') } catch (caught) { setError(caught.message) } finally { setLoading(false) } }
  useEffect(() => { if (!selectedId) refresh() }, [selectedId])
  useEffect(() => { setDirty(false) }, [selectedId])
  async function pickRandom() { try { setRandom(await randomAlgorithmProblemRequest()); setError('') } catch (caught) { setError(caught.message) } }
  const visible = useMemo(() => problems.filter((problem) => filter === 'all' || (filter === 'priority' ? problem.status !== 'solved' && (!problem.next_review_at || problem.next_review_at <= new Date().toISOString().slice(0, 10)) : problem.status === filter)), [problems, filter])
  if (selectedId) return <AlgorithmDetail problemId={selectedId} navigate={navigate} onDirty={() => setDirty(true)} onSaved={() => setDirty(false)} />
  return <section className="track-index-page algorithm-workspace">
    <header className="track-index-heading"><div><span className="track-eyebrow">准备轨道 · 算法</span><h1>带着卡点回到外部题目</h1><p>先看待复盘与到期题目，再记录真实练习；这里不提供在线判题。</p></div><div><button className="track-button-secondary" onClick={pickRandom}><Dice5 size={17} />随机一题</button><button className="track-button-primary" onClick={() => setShowCreate(true)}><Plus size={17} />加入题单</button></div></header>
    {error && <p className="track-page-error">{error}</p>}
    {random && <article className="algorithm-random-focus"><div><span>随机练习 · 单题</span><h2>{random.title}</h2><p>{random.source_platform} · {labelOf(difficulties, random.difficulty)}</p></div><button className="track-button-primary" onClick={() => navigate(`/algorithms/${random.id}`)}>进入题目</button></article>}
    <div className="track-filter-row"><button className={filter === 'priority' ? 'active' : ''} onClick={() => setFilter('priority')}>优先题单</button>{statuses.map(([value, label]) => <button key={value} className={filter === value ? 'active' : ''} onClick={() => setFilter(value)}>{label}</button>)}<button className={filter === 'all' ? 'active' : ''} onClick={() => setFilter('all')}>全部</button><button className="track-refresh" onClick={refresh}><RotateCcw size={15} />刷新</button></div>
    {loading ? <div className="track-list"><div className="track-skeleton" /><div className="track-skeleton" /></div> : <div className="track-list algorithm-list">{visible.map((problem) => <button className="algorithm-list-row" key={problem.id} onClick={() => navigate(`/algorithms/${problem.id}`)}><div className="algorithm-title-cell"><span className={`track-status status-${problem.status}`}>{labelOf(statuses, problem.status)}</span><strong>{problem.title}</strong><p>{problem.mistake_reason || (problem.tags || []).join(' · ') || '尚未记录卡点'}</p></div><div className="algorithm-source-cell"><span>{problem.source_platform}</span><b>{labelOf(difficulties, problem.difficulty)}</b></div><div className="algorithm-review-cell"><span>下次复盘</span><b>{problem.next_review_at || '待安排'}</b><small>练习 {problem.practice_count} 次</small></div></button>)}{visible.length === 0 && <div className="track-empty"><BrainCircuit size={25} /><h2>{problems.length ? '当前筛选下没有题目' : '优先题单还是空的'}</h2><p>{problems.length ? '切换状态查看其他题目。' : '先加入一道近期要练的外部题目。'}</p>{problems.length === 0 && <button className="track-button-primary" onClick={() => setShowCreate(true)}>加入第一题</button>}</div>}</div>}
    {showCreate && <CreateProblemDialog onClose={() => setShowCreate(false)} onSaved={(problem) => { setShowCreate(false); navigate(`/algorithms/${problem.id}`) }} />}
  </section>
}
