import { useEffect, useState } from 'react'
import { Check, CircleAlert, MapPin, PencilLine, Target, X } from 'lucide-react'
import { EMPTY_PROFILE } from '../constants'
import { PageHeader } from './AppShell'

export function ProfilePage({ profile, loading, onSave, navigate }) {
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState(profile ? { ...profile } : EMPTY_PROFILE)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => { if (!editing) setForm(profile ? { ...profile } : EMPTY_PROFILE) }, [profile, editing])
  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }))
  const baseline = profile ? { ...profile } : EMPTY_PROFILE
  const dirty = JSON.stringify(form) !== JSON.stringify(baseline)
  const cancelEditing = () => (!dirty || window.confirm('还有未保存的修改，确定离开编辑模式吗？')) && setEditing(false)

  useEffect(() => {
    if (!editing || !dirty) return undefined
    const warnBeforeLeave = (event) => { event.preventDefault(); event.returnValue = '' }
    const confirmNavigation = (event) => {
      if (!window.confirm('还有未保存的修改，确定离开目标画像吗？')) event.preventDefault()
    }
    window.addEventListener('beforeunload', warnBeforeLeave)
    window.addEventListener('app:navigate', confirmNavigation)
    return () => {
      window.removeEventListener('beforeunload', warnBeforeLeave)
      window.removeEventListener('app:navigate', confirmNavigation)
    }
  }, [dirty, editing])

  async function submit(event) {
    event.preventDefault()
    setSaving(true); setError(''); setSaved(false)
    try { await onSave(form); setSaved(true); setEditing(false) } catch (caught) { setError(caught.message) } finally { setSaving(false) }
  }

  return <div className="profile-page page-stack reading-width">
    <PageHeader eyebrow="全局上下文" title="目标画像" description="目标决定准备取舍，但不被包装成虚假的能力评分。" navigate={navigate} action={!editing && <button className="button-primary" onClick={() => setEditing(true)}><PencilLine size={16} />{profile ? '编辑画像' : '创建画像'}</button>} />
    {saved && <div className="toast-inline"><Check size={16} />目标画像已保存</div>}
    {loading && !profile ? <div className="profile-skeleton"><i /><i /><i /></div> : editing ? <form className="profile-editor calm-panel" onSubmit={submit}>
      <div className="form-heading"><div><p>编辑模式</p><h2>校准主航向</h2></div><button type="button" className="icon-button" onClick={cancelEditing} aria-label="取消编辑"><X size={18} /></button></div>
      {error && <div className="inline-error"><CircleAlert size={16} />{error}</div>}
      <div className="form-grid">
        <label className="wide"><span>目标岗位</span><input autoFocus required value={form.title} onChange={(event) => update('title', event.target.value)} /></label>
        <label><span>目标地点</span><input value={form.location || ''} onChange={(event) => update('location', event.target.value)} /></label>
        <label><span>重点方向</span><input value={form.focus || ''} onChange={(event) => update('focus', event.target.value)} /></label>
        <label className="wide"><span>画像摘要</span><textarea rows="7" value={form.summary || ''} onChange={(event) => update('summary', event.target.value)} /></label>
      </div>
      <div className="form-actions"><button type="button" className="button-secondary" onClick={cancelEditing}>取消</button><button className="button-primary" disabled={saving}><Check size={16} />{saving ? '保存中…' : '保存画像'}</button></div>
    </form> : profile ? <section className="profile-card calm-panel">
      <div className="profile-emblem"><Target size={28} /></div>
      <p>当前目标岗位</p><h2>{profile.title}</h2>
      <div className="profile-facts"><span><MapPin size={16} />{profile.location || '地点待补充'}</span><span><Target size={16} />{profile.focus || '重点方向待补充'}</span></div>
      <blockquote>{profile.summary || '暂未填写画像摘要。补充真实偏好、能力组合与边界，后续策略才有取舍依据。'}</blockquote>
      <footer><span>最近更新</span><time>{profile.updated_at ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'long', timeStyle: 'short' }).format(new Date(profile.updated_at)) : '—'}</time></footer>
    </section> : <section className="quiet-empty calm-panel"><Target size={24} /><h2>还没有目标画像</h2><p>先定义岗位、地点与重点方向，让情报和准备轨道拥有共同上下文。</p><button className="button-primary" onClick={() => setEditing(true)}>创建画像</button></section>}
  </div>
}
