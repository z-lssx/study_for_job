import React, { useEffect, useState } from 'react'
import { BrainCircuit, Check, Dice5, Plus, RotateCcw } from 'lucide-react'
import {
  createAlgorithmProblemRequest,
  loadAlgorithmProblemsRequest,
  practiceAlgorithmProblemRequest,
  randomAlgorithmProblemRequest,
  updateAlgorithmProblemRequest,
} from '../api/algorithms'
import './algorithms.css'

const statuses = [
  ['not_started', '未开始'],
  ['in_progress', '进行中'],
  ['revisit', '待复盘'],
  ['solved', '已解决'],
]
const difficulties = [['unknown', '未标注'], ['easy', '简单'], ['medium', '中等'], ['hard', '困难']]

export function AlgorithmWorkspace() {
  const [problems, setProblems] = useState([])
  const [random, setRandom] = useState(null)
  const [title, setTitle] = useState('')
  const [sourceUrl, setSourceUrl] = useState('')
  const [sourcePlatform, setSourcePlatform] = useState('manual')
  const [difficulty, setDifficulty] = useState('unknown')
  const [tags, setTags] = useState('')
  const [error, setError] = useState('')

  async function refresh() {
    try { setProblems(await loadAlgorithmProblemsRequest()); setError('') } catch (caught) { setError(caught.message) }
  }
  useEffect(() => { refresh() }, [])

  async function createProblem(event) {
    event.preventDefault()
    if (!title.trim()) return
    try {
      await createAlgorithmProblemRequest({
        title, source_url: sourceUrl || null, source_platform: sourcePlatform || 'manual', difficulty,
        tags: tags.split(',').map((tag) => tag.trim()).filter(Boolean),
      })
      setTitle(''); setSourceUrl(''); setTags(''); setError(''); await refresh()
    } catch (caught) { setError(caught.message) }
  }

  async function pickRandom() {
    try { setRandom(await randomAlgorithmProblemRequest()); setError('') } catch (caught) { setError(caught.message) }
  }

  async function practice(problem) {
    const index = statuses.findIndex(([value]) => value === problem.status)
    const next = statuses[Math.min(index + 1, statuses.length - 1)][0]
    try {
      await practiceAlgorithmProblemRequest(problem.id, {
        status: next,
        mistake_reason: problem.mistake_reason || null,
        review_notes: problem.review_notes || null,
      })
      await refresh()
      if (random?.id === problem.id) setRandom((current) => ({ ...current, status: next, practice_count: (current.practice_count || 0) + 1 }))
    } catch (caught) { setError(caught.message) }
  }

  async function saveReview(event, problemId) {
    event.preventDefault()
    const values = new FormData(event.currentTarget)
    try {
      await updateAlgorithmProblemRequest(problemId, {
        status: values.get('status'),
        mistake_reason: values.get('mistake_reason') || null,
        review_notes: values.get('review_notes') || null,
        next_review_at: values.get('next_review_at') || null,
      })
      setError(''); await refresh()
    } catch (caught) { setError(caught.message) }
  }

  return <section className="algorithm-workspace">
    <header className="algorithm-heading">
      <div><p className="section-code">PREP TRACK / ALGORITHMS</p><h2>算法练习与错题复盘</h2><p>题目来源和状态由你维护；阶段二规范题只作为可解释参考，不等于评分。</p></div>
      <div className="algorithm-actions"><button className="refresh-action" onClick={refresh}><RotateCcw size={15} />刷新</button><button className="action-primary" onClick={pickRandom}><Dice5 size={16} />随机一题</button></div>
    </header>
    {error && <p className="algorithm-error">{error}</p>}
    {random && <article className="algorithm-random"><div><span className="algorithm-kicker">LIGHT PRACTICE / ONE QUESTION</span><h3>{random.title}</h3><p>{random.source_platform}{random.difficulty !== 'unknown' ? ` · ${difficulties.find(([value]) => value === random.difficulty)?.[1]}` : ''}</p>{random.source_url && <a href={random.source_url} target="_blank" rel="noreferrer">打开题目来源</a>}</div><button onClick={() => practice(random)} disabled={random.status === 'solved'}><Check size={15} />记录一次练习</button></article>}
    <div className="algorithm-grid">
      <aside className="algorithm-rail">
        <details className="algorithm-card algorithm-create">
          <summary><Plus size={16} /><strong>加入题单</strong><span>按需展开</span></summary>
          <form onSubmit={createProblem}>
            <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="题目标题" maxLength={240} />
            <input value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} placeholder="来源 URL（可选）" maxLength={2048} />
            <div className="algorithm-inline"><input value={sourcePlatform} onChange={(event) => setSourcePlatform(event.target.value)} placeholder="平台" maxLength={80} /><select value={difficulty} onChange={(event) => setDifficulty(event.target.value)}>{difficulties.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div>
            <input value={tags} onChange={(event) => setTags(event.target.value)} placeholder="标签，用逗号分隔" maxLength={500} />
            <button className="action-primary" type="submit"><BrainCircuit size={16} />保存题目</button>
          </form>
        </details>
        <p className="algorithm-guidance"><span>{String(problems.length).padStart(2, '0')}</span> 道题<br />随机练习始终只展开一题。</p>
      </aside>
      <div className="algorithm-list">
        {problems.length === 0 && <div className="algorithm-empty">题单还是空的，从一道近期要练的题开始。</div>}
        {problems.map((problem) => <article className="algorithm-card" key={problem.id}>
          <div className="algorithm-card-title"><strong>{problem.title}</strong><span className={`algorithm-status algorithm-status-${problem.status}`}>{statuses.find(([value]) => value === problem.status)?.[1]}</span></div>
          <p className="algorithm-meta">{problem.source_platform} · {difficulties.find(([value]) => value === problem.difficulty)?.[1]} · 练习 {problem.practice_count} 次</p>
          {problem.tags?.length > 0 && <p className="algorithm-tags">{problem.tags.join(' / ')}</p>}
          {problem.mistake_reason && <p className="algorithm-review"><b>卡点：</b>{problem.mistake_reason}</p>}
          {problem.canonical_question && <p className="algorithm-link"><b>情报关联：</b>{problem.canonical_question.text}（出现 {problem.canonical_question.occurrence_count} 次，仅作参考）</p>}
          <details className="algorithm-editor">
            <summary>修订状态与错题复盘</summary>
            <form onSubmit={(event) => saveReview(event, problem.id)}>
              <select name="status" defaultValue={problem.status}>{statuses.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
              <textarea name="mistake_reason" defaultValue={problem.mistake_reason || ''} placeholder="卡点或出错原因" maxLength={4000} rows={2} />
              <textarea name="review_notes" defaultValue={problem.review_notes || ''} placeholder="复盘：正确思路、复杂度、下次提醒" maxLength={10000} rows={3} />
              <label>下次复盘<input type="date" name="next_review_at" defaultValue={problem.next_review_at || ''} /></label>
              <button type="submit">保存修订</button>
            </form>
          </details>
          <div className="algorithm-card-footer"><span>{problem.next_review_at ? `下次复盘 ${problem.next_review_at}` : '尚未安排复盘'}</span><button onClick={() => practice(problem)} disabled={problem.status === 'solved'}><Check size={14} />记录练习</button></div>
        </article>)}
      </div>
    </div>
  </section>
}
