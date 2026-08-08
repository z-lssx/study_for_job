import { useState } from 'react'
import { ArrowLeft, FolderKanban } from 'lucide-react'
import { createProjectRequest } from '../api/projects'
import { useUnsavedGuard } from '../hooks/useUnsavedGuard'

export function ProjectCreatePage({ navigate }) {
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [dirty, setDirty] = useState(false)
  useUnsavedGuard(dirty, '新项目还有未保存的修改，确定离开吗？')

  async function submit(event) {
    event.preventDefault()
    const values = new FormData(event.currentTarget)
    setSaving(true); setError('')
    try {
      const project = await createProjectRequest({
        title: values.get('title'),
        target_role: values.get('target_role') || null,
        summary: values.get('summary') || null,
      })
      setDirty(false)
      window.setTimeout(() => navigate(`/projects/${project.id}`), 0)
    } catch (caught) { setError(caught.message) } finally { setSaving(false) }
  }

  return <section className="track-detail-page track-create-page">
    <button className="track-back" type="button" onClick={() => navigate('/projects')}><ArrowLeft size={17} />返回项目轨道</button>
    <nav className="track-breadcrumb" aria-label="面包屑"><button onClick={() => navigate('/projects')}>项目</button><span>/</span><b>新建证据包</b></nav>
    <header className="track-detail-heading"><div><span className="track-eyebrow">项目 · 新建</span><h1>从可核实的基本事实开始</h1><p>这里只建立项目身份与摘要；证据、表达版本和情报关联在保存后分开维护。</p></div></header>
    <form className="track-editor track-create-form" onSubmit={submit} onChange={() => setDirty(true)}>
      <label>项目名称<input name="title" required autoFocus maxLength={240} /></label>
      <label>目标岗位<input name="target_role" maxLength={160} placeholder="可选" /></label>
      <label>项目事实摘要<textarea name="summary" maxLength={2000} rows={7} placeholder="写清项目背景、你的职责边界与可核实结果。" /></label>
      {error && <p className="track-page-error">{error}</p>}
      <footer><button type="button" className="track-button-secondary" onClick={() => navigate('/projects')}>取消</button><button className="track-button-primary" disabled={saving}><FolderKanban size={16} />{saving ? '保存中…' : '保存并进入证据包'}</button></footer>
    </form>
  </section>
}
