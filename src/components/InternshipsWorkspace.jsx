import React, { useEffect, useMemo, useState } from 'react'
import { BriefcaseBusiness, Plus, RotateCcw } from 'lucide-react'
import { loadCanonicalQuestionsRequest } from '../api/canonicalQuestions'
import { createInternshipRequest, loadInternshipsRequest } from '../api/internships'
import { InternshipDetail } from './internships/InternshipDetail'
import './internships.css'

export function InternshipsWorkspace() {
  const [internships, setInternships] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [questions, setQuestions] = useState([])
  const [error, setError] = useState('')
  const selected = useMemo(
    () => internships.find((item) => item.id === selectedId) || null,
    [internships, selectedId],
  )

  function replaceInternship(item) {
    setInternships((current) => {
      const exists = current.some((candidate) => candidate.id === item.id)
      return exists ? current.map((candidate) => candidate.id === item.id ? item : candidate) : [item, ...current]
    })
    setSelectedId(item.id)
    setError('')
  }

  async function refresh() {
    try {
      const items = await loadInternshipsRequest()
      setInternships(items)
      setSelectedId((current) => items.some((item) => item.id === current) ? current : items[0]?.id || null)
      setError('')
    } catch (caught) { setError(caught.message) }
  }

  useEffect(() => {
    refresh()
    loadCanonicalQuestionsRequest({ limit: 100 }).then(setQuestions).catch(() => setQuestions([]))
  }, [])

  async function createInternship(event) {
    event.preventDefault()
    const values = new FormData(event.currentTarget)
    try {
      const item = await createInternshipRequest({
        organization: values.get('organization'),
        role_title: values.get('role_title'),
        started_on: values.get('started_on') || null,
        ended_on: values.get('ended_on') || null,
        summary: values.get('summary') || null,
      })
      event.currentTarget.reset()
      replaceInternship(item)
    } catch (caught) { setError(caught.message) }
  }

  return <section className="internships-workspace">
    <header className="internships-heading">
      <div><p className="section-code">PREP TRACK / INTERNSHIPS</p><h2>实习事实与材料资产</h2><p>事实、表达和面经信号分开维护；先核实，再组织 STAR 与量化表达。</p></div>
      <button className="refresh-action" onClick={refresh}><RotateCcw size={15} />刷新</button>
    </header>
    {error && <p className="internships-error">{error}</p>}
    <div className="internships-layout">
      <aside className="internships-rail">
        <details className="internship-panel internship-create-shell">
          <summary><Plus size={16} /><strong>新建实习资产包</strong><span>按需展开</span></summary>
          <form className="internship-create" onSubmit={createInternship}>
            <input name="organization" required placeholder="公司 / 组织" maxLength={240} />
            <input name="role_title" required placeholder="岗位 / 角色" maxLength={160} />
            <div className="internship-form-grid"><label>开始<input name="started_on" type="date" /></label><label>结束<input name="ended_on" type="date" /></label></div>
            <textarea name="summary" placeholder="经历事实摘要" maxLength={2000} rows={3} />
            <button className="action-primary" type="submit"><BriefcaseBusiness size={16} />保存经历</button>
          </form>
        </details>
        <div className="internship-list">
          {internships.map((item) => <button className={item.id === selectedId ? 'active' : ''} key={item.id} onClick={() => setSelectedId(item.id)}>
            <strong>{item.organization}</strong><span>{item.role_title} · 事实 {item.facts.length} · 材料 {item.materials.length}</span>
          </button>)}
          {internships.length === 0 && <p>还没有实习资产，从一段可核实的职责或结果开始。</p>}
        </div>
      </aside>
      {!selected ? <div className="internship-empty">选择或新建一段实习经历。</div> : <InternshipDetail
        key={selected.id}
        internship={selected}
        questions={questions}
        onChange={replaceInternship}
        onError={setError}
        onRefresh={refresh}
      />}
    </div>
  </section>
}
