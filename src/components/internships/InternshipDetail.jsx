import React from 'react'
import { updateInternshipRequest } from '../../api/internships'
import { InternshipFactsPanel, InternshipMaterialsPanel } from './InternshipAssets'
import { InternshipExpressionPanel } from './InternshipExpression'
import { InternshipIntelligencePanel } from './InternshipIntelligence'

export function InternshipDetail({ internship, questions, onChange, onError, onRefresh }) {
  async function saveBasics(event) {
    event.preventDefault()
    const values = new FormData(event.currentTarget)
    try {
      onChange(await updateInternshipRequest(internship.id, {
        organization: values.get('organization'), role_title: values.get('role_title'),
        started_on: values.get('started_on') || null, ended_on: values.get('ended_on') || null,
        summary: values.get('summary') || null, status: values.get('status'),
      }))
    } catch (caught) { onError(caught.message) }
  }

  return <div className="internship-detail">
    <section className="internship-panel internship-overview">
      <div className="internship-section-title"><div><span>01 / FACTS</span><h3>经历基本事实</h3></div><small>{internship.status === 'active' ? '持续维护' : '已归档'}</small></div>
      <div className="internship-overview-copy"><strong>{internship.organization}</strong><span>{internship.role_title}</span><p>{internship.summary || '尚未补充经历事实摘要。'}</p></div>
      <details className="internship-create-details"><summary>修订基本事实</summary><form className="internship-inline-form internship-basics" onSubmit={saveBasics}>
        <div className="internship-form-grid"><label>公司 / 组织<input name="organization" defaultValue={internship.organization} required maxLength={240} /></label><label>岗位 / 角色<input name="role_title" defaultValue={internship.role_title} required maxLength={160} /></label></div>
        <div className="internship-form-grid"><label>开始日期<input name="started_on" type="date" defaultValue={internship.started_on || ''} /></label><label>结束日期<input name="ended_on" type="date" defaultValue={internship.ended_on || ''} /></label></div>
        <label>事实摘要<textarea name="summary" defaultValue={internship.summary || ''} maxLength={2000} rows={3} /></label>
        <label>状态<select name="status" defaultValue={internship.status}><option value="active">持续维护</option><option value="archived">已归档</option></select></label>
        <button type="submit">保存修订</button>
      </form></details>
    </section>
    <InternshipFactsPanel internship={internship} onChange={onChange} onError={onError} />
    <InternshipExpressionPanel internship={internship} onChange={onChange} onError={onError} />
    <InternshipMaterialsPanel internship={internship} onChange={onChange} onError={onError} />
    <InternshipIntelligencePanel internship={internship} questions={questions} onChange={onChange} onError={onError} onRefresh={onRefresh} />
  </div>
}
