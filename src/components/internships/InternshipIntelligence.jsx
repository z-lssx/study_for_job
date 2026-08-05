import React from 'react'
import { Link2, Unlink } from 'lucide-react'
import { linkInternshipIntelligenceRequest, unlinkInternshipIntelligenceRequest } from '../../api/internships'

export function InternshipIntelligencePanel({ internship, questions, onChange, onError, onRefresh }) {
  async function linkIntelligence(event) {
    event.preventDefault()
    const form = event.currentTarget
    const values = new FormData(form)
    try {
      onChange(await linkInternshipIntelligenceRequest(internship.id, {
        canonical_question_id: values.get('canonical_question_id'),
        internship_fact_id: values.get('internship_fact_id') || null,
        relevance_note: values.get('relevance_note'),
      }))
      form.reset()
    } catch (caught) { onError(caught.message) }
  }

  async function unlink(linkId) {
    try {
      await unlinkInternshipIntelligenceRequest(internship.id, linkId)
      await onRefresh()
    } catch (caught) { onError(caught.message) }
  }

  return <section className="internship-panel">
    <div className="internship-section-title"><div><span>05 / INTELLIGENCE</span><h3>规范题与面经证据回链</h3></div><small>频率仅供解释</small></div>
    <details className="internship-create-details">
      <summary><Link2 size={14} />建立显式关联</summary>
      <form className="internship-inline-form" onSubmit={linkIntelligence}>
        <label>规范题<select name="canonical_question_id" required defaultValue=""><option value="" disabled>选择阶段二规范题</option>{questions.map((question) => <option value={question.id} key={question.id}>{question.canonical_text} · {question.occurrence_count} 次</option>)}</select></label>
        <label>对应实习事实<select name="internship_fact_id" defaultValue=""><option value="">不绑定具体事实</option>{internship.facts.map((fact) => <option value={fact.id} key={fact.id}>{fact.statement.slice(0, 60)}</option>)}</select></label>
        <label>关联说明<textarea name="relevance_note" required maxLength={2000} rows={2} placeholder="说明这个考点为什么与真实经历相关；不等于岗位匹配评分" /></label>
        <button type="submit">保存关联</button>
      </form>
    </details>
    <div className="internship-card-list intelligence-list">
      {internship.intelligence_links.map((link) => <article key={link.id}>
        <div className="internship-card-head"><strong>{link.canonical_text || '规范题'}</strong><span>{link.occurrence_count} 次原始出现</span></div>
        <p>{link.relevance_note}</p>
        {link.internship_fact && <small>关联事实：{link.internship_fact.statement}</small>}
        {link.occurrence_evidence.map((evidence) => <div className="internship-source" key={evidence.occurrence_id}>
          <blockquote>{evidence.quote}</blockquote>
          <small>轮次 {evidence.round_ordinal || '未标注'} · 字符 {evidence.start_char}–{evidence.end_char}</small>
          {evidence.source_url && <a href={evidence.source_url} target="_blank" rel="noreferrer">查看原始来源</a>}
        </div>)}
        <button className="internship-unlink" type="button" onClick={() => unlink(link.id)}><Unlink size={13} />移除关联</button>
      </article>)}
      {internship.intelligence_links.length === 0 && <p className="internship-muted">尚未关联规范题。关联只提供可解释需求信号，不会改写经历事实。</p>}
    </div>
  </section>
}
