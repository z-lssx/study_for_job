import { useState } from 'react'
import { ArrowLeft, BriefcaseBusiness } from 'lucide-react'
import { createInternshipRequest } from '../api/internships'
import { useUnsavedGuard } from '../hooks/useUnsavedGuard'

export function InternshipCreatePage({ navigate }) {
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [dirty, setDirty] = useState(false)
  useUnsavedGuard(dirty, '新实习资产包还有未保存的修改，确定离开吗？')

  async function submit(event) {
    event.preventDefault()
    const values = new FormData(event.currentTarget)
    setSaving(true); setError('')
    try {
      const internship = await createInternshipRequest({
        organization: values.get('organization'), role_title: values.get('role_title'),
        started_on: values.get('started_on') || null, ended_on: values.get('ended_on') || null,
        summary: values.get('summary') || null,
      })
      setDirty(false)
      window.setTimeout(() => navigate(`/internships/${internship.id}`), 0)
    } catch (caught) { setError(caught.message) } finally { setSaving(false) }
  }

  return <section className="track-detail-page track-create-page">
    <button className="track-back" type="button" onClick={() => navigate('/internships')}><ArrowLeft size={17} />返回实习轨道</button>
    <nav className="track-breadcrumb" aria-label="面包屑"><button onClick={() => navigate('/internships')}>实习</button><span>/</span><b>新建资产包</b></nav>
    <header className="track-detail-heading"><div><span className="track-eyebrow">实习 · 新建</span><h1>先把经历边界说准确</h1><p>建立公司、角色和时间范围后，再分别维护职责事实、STAR、材料和情报回链。</p></div></header>
    <form className="track-editor track-create-form" onSubmit={submit} onChange={() => setDirty(true)}>
      <div className="track-form-columns"><label>公司或组织<input name="organization" required autoFocus maxLength={240} /></label><label>岗位或角色<input name="role_title" required maxLength={160} /></label></div>
      <div className="track-form-columns"><label>开始日期<input name="started_on" type="date" /></label><label>结束日期<input name="ended_on" type="date" /></label></div>
      <label>经历事实摘要<textarea name="summary" maxLength={2000} rows={7} placeholder="写清职责范围、协作边界与已核实结果。" /></label>
      {error && <p className="track-page-error">{error}</p>}
      <footer><button type="button" className="track-button-secondary" onClick={() => navigate('/internships')}>取消</button><button className="track-button-primary" disabled={saving}><BriefcaseBusiness size={16} />{saving ? '保存中…' : '保存并进入资产包'}</button></footer>
    </form>
  </section>
}
