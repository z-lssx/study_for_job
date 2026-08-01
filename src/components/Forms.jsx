import { useEffect, useState } from 'react'
import { Check, X } from 'lucide-react'
import { EMPTY_APPLICATION, EMPTY_PROFILE, STAGES } from '../constants'

function ModalFrame({ eyebrow, title, children, saving, error, submitLabel, onClose, onSubmit }) {
  useEffect(() => {
    const closeOnEscape = (event) => event.key === 'Escape' && onClose()
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [onClose])

  return <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
    <form className="editor-modal" onSubmit={onSubmit}>
      <header className="editor-header">
        <div><p>{eyebrow}</p><h2>{title}</h2></div>
        <button type="button" className="bare-icon" onClick={onClose} aria-label="关闭表单"><X size={20} /></button>
      </header>
      {error && <div className="form-error">{error}</div>}
      {children}
      <footer className="editor-actions">
        <button type="button" className="action-secondary" onClick={onClose}>取消</button>
        <button className="action-primary" disabled={saving}>{saving ? '写入中…' : <><Check size={16} />{submitLabel}</>}</button>
      </footer>
    </form>
  </div>
}

export function ApplicationForm({ initial, onClose, onSubmit }) {
  const [form, setForm] = useState(initial ? { ...initial } : EMPTY_APPLICATION)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }))

  async function submit(event) {
    event.preventDefault()
    setSaving(true)
    setError('')
    try { await onSubmit(form) } catch (caught) { setError(caught.message) } finally { setSaving(false) }
  }

  return <ModalFrame
    eyebrow={initial ? 'UPDATE / FACT' : 'NEW / APPLICATION'}
    title={initial ? '编辑投递记录' : '把新机会放上轨道'}
    saving={saving}
    error={error}
    submitLabel="保存记录"
    onClose={onClose}
    onSubmit={submit}
  >
    <div className="editor-grid">
      <label>公司名称<input autoFocus required value={form.company} onChange={(event) => update('company', event.target.value)} /></label>
      <label>岗位名称<input required value={form.role} onChange={(event) => update('role', event.target.value)} /></label>
      <fieldset className="stage-field">
        <legend>当前阶段</legend>
        <div>{STAGES.map((stage) => <label key={stage.key} className={form.stage === stage.key ? 'checked' : ''}>
          <input type="radio" name="stage" value={stage.key} checked={form.stage === stage.key} onChange={(event) => update('stage', event.target.value)} />
          <span>{stage.index}</span>{stage.short}
        </label>)}</div>
      </fieldset>
      <label>关键日期<input type="date" value={form.key_date || ''} onChange={(event) => update('key_date', event.target.value)} /></label>
      <label>投递渠道<input value={form.channel || ''} onChange={(event) => update('channel', event.target.value)} placeholder="官网 / 内推 / 招聘平台" /></label>
      <label className="wide">下一步动作<input value={form.next_action || ''} onChange={(event) => update('next_action', event.target.value)} placeholder="把动作写具体，下一次打开就能开始" /></label>
      <label className="wide">岗位链接<input type="url" value={form.url || ''} onChange={(event) => update('url', event.target.value)} placeholder="https://" /></label>
      <label className="wide">备注<textarea rows="4" value={form.notes || ''} onChange={(event) => update('notes', event.target.value)} placeholder="面试线索、联系人、需要验证的问题…" /></label>
    </div>
  </ModalFrame>
}

export function ProfileForm({ initial, onClose, onSubmit }) {
  const [form, setForm] = useState(initial ? { ...initial } : EMPTY_PROFILE)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }))

  async function submit(event) {
    event.preventDefault()
    setSaving(true)
    setError('')
    try { await onSubmit(form) } catch (caught) { setError(caught.message) } finally { setSaving(false) }
  }

  return <ModalFrame
    eyebrow="TARGET / PROFILE"
    title={initial ? '校准目标画像' : '定义你的主航向'}
    saving={saving}
    error={error}
    submitLabel="保存画像"
    onClose={onClose}
    onSubmit={submit}
  >
    <div className="editor-grid">
      <label className="wide">岗位名称<input autoFocus required value={form.title} onChange={(event) => update('title', event.target.value)} placeholder="例如：Agent 工程师 / Java 后端" /></label>
      <label>目标地点<input value={form.location || ''} onChange={(event) => update('location', event.target.value)} /></label>
      <label>重点方向<input value={form.focus || ''} onChange={(event) => update('focus', event.target.value)} /></label>
      <label className="wide">画像摘要<textarea rows="5" value={form.summary || ''} onChange={(event) => update('summary', event.target.value)} placeholder="你的能力组合、偏好与边界" /></label>
    </div>
  </ModalFrame>
}
