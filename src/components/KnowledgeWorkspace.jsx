import React, { useEffect, useState } from 'react'
import { BookOpen, Check, Plus, RotateCcw } from 'lucide-react'
import { createKnowledgeCardRequest, loadKnowledgeCardsRequest, reviewKnowledgeCardRequest } from '../api/knowledge'
import './knowledge.css'

const statuses = [
  ['not_started', '未开始'],
  ['learning', '学习中'],
  ['familiar', '已熟悉'],
  ['mastered', '已掌握'],
]

export function KnowledgeWorkspace() {
  const [cards, setCards] = useState([])
  const [title, setTitle] = useState('')
  const [prompt, setPrompt] = useState('')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState('')

  async function refresh() {
    try { setCards(await loadKnowledgeCardsRequest()) } catch (caught) { setError(caught.message) }
  }

  useEffect(() => { refresh() }, [])

  async function createCard(event) {
    event.preventDefault()
    if (!title.trim()) return
    try {
      await createKnowledgeCardRequest({ title, prompt: prompt || null, notes: notes || null })
      setTitle(''); setPrompt(''); setNotes(''); setError(''); await refresh()
    } catch (caught) { setError(caught.message) }
  }

  async function review(card) {
    const index = statuses.findIndex(([value]) => value === card.mastery_status)
    const next = statuses[Math.min(index + 1, statuses.length - 1)][0]
    try { await reviewKnowledgeCardRequest(card.id, { mastery_status: next }); await refresh() } catch (caught) { setError(caught.message) }
  }

  return <section className="knowledge-workspace">
    <header className="knowledge-heading">
      <div><p className="section-code">PREP TRACK / KNOWLEDGE</p><h2>知识复习台</h2><p>掌握状态由你维护；情报只作为可回链的参考。</p></div>
      <button className="refresh-action" onClick={refresh}><RotateCcw size={15} />刷新</button>
    </header>
    {error && <p className="knowledge-error">{error}</p>}
    <div className="knowledge-grid">
      <aside className="knowledge-rail">
        <details className="knowledge-card knowledge-create">
          <summary><Plus size={16} /><strong>新增知识卡片</strong><span>按需展开</span></summary>
          <form onSubmit={createCard}>
            <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="主题，如：PostgreSQL 索引" maxLength={240} />
            <input value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="面试可述版本（可选）" maxLength={2000} />
            <textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="自己的笔记或待补证据" maxLength={10000} rows={4} />
            <button className="action-primary" type="submit"><BookOpen size={16} />保存卡片</button>
          </form>
        </details>
        <p className="knowledge-guidance"><span>{String(cards.length).padStart(2, '0')}</span> 张卡片<br />状态与复习记录以你的修订为准。</p>
      </aside>
      <div className="knowledge-list">
        {cards.length === 0 && <div className="knowledge-empty">还没有知识卡片，从一个近期高频主题开始。</div>}
        {cards.map((card) => <article className="knowledge-card" key={card.id}>
          <div className="knowledge-card-title"><strong>{card.title}</strong><span className={`mastery mastery-${card.mastery_status}`}>{statuses.find(([value]) => value === card.mastery_status)?.[1]}</span></div>
          {card.prompt && <p className="knowledge-prompt">{card.prompt}</p>}
          {card.notes && <details className="knowledge-notes"><summary>展开个人笔记</summary><p>{card.notes}</p></details>}
          <div className="knowledge-meta"><span>复习 {card.review_count} 次</span><span>{card.evidence.length ? `证据 ${card.evidence.length} 条` : '暂无证据回链'}</span><button onClick={() => review(card)} disabled={card.mastery_status === 'mastered'}><Check size={14} />记录复习</button></div>
        </article>)}
      </div>
    </div>
  </section>
}
