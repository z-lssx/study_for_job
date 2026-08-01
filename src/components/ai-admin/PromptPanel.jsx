import { useState } from 'react'
import { Braces, Check, Save } from 'lucide-react'

function PromptEditor({ prompt, onSave }) {
  const [form, setForm] = useState({ ...prompt })
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }))

  async function submit(event) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setMessage('')
    try {
      await onSave(prompt.scenario_key, form)
      setMessage('配置已写入 PostgreSQL')
    } catch (caught) {
      setError(caught.message)
    } finally {
      setSaving(false)
    }
  }

  return <form className="prompt-editor" onSubmit={submit}>
    <header>
      <div><span>{prompt.module} / {prompt.scenario_key}</span><h3>{prompt.name}</h3></div>
      <label className="toggle-field"><input type="checkbox" checked={form.enabled} onChange={(event) => update('enabled', event.target.checked)} /><i />{form.enabled ? '启用' : '停用'}</label>
    </header>
    <p className="prompt-description">{prompt.description}</p>
    <div className="variable-strip"><Braces size={15} /><span>开放变量</span>{prompt.editable_variables.map((variable) => <code key={variable}>{`{${variable}}`}</code>)}</div>
    {error && <div className="admin-inline-error">{error}</div>}
    {message && <div className="admin-inline-success"><Check size={15} />{message}</div>}
    <label>System 指令<textarea rows="5" required value={form.system_template} onChange={(event) => update('system_template', event.target.value)} /></label>
    <label>Task 模板<textarea rows="7" required value={form.task_template} onChange={(event) => update('task_template', event.target.value)} /></label>
    <div className="prompt-parameters">
      <label>Temperature<input type="number" min="0" max="2" step="0.1" value={form.temperature} onChange={(event) => update('temperature', event.target.value)} /></label>
      <label>Max tokens<input type="number" min="1" max="8192" step="1" value={form.max_tokens} onChange={(event) => update('max_tokens', event.target.value)} /></label>
      <button className="action-primary" disabled={saving}><Save size={16} />{saving ? '保存中…' : '保存配置'}</button>
    </div>
  </form>
}

export function PromptPanel({ prompts, onSave }) {
  const [selectedKey, setSelectedKey] = useState('')
  const resolvedKey = prompts.some((item) => item.scenario_key === selectedKey) ? selectedKey : prompts[0]?.scenario_key
  const selected = prompts.find((item) => item.scenario_key === resolvedKey)

  return <section className="prompt-workbench">
    <aside className="prompt-index">
      <div className="admin-section-label">PROMPT / REGISTRY</div>
      {prompts.map((prompt, index) => <button
        key={prompt.scenario_key}
        className={prompt.scenario_key === resolvedKey ? 'active' : ''}
        onClick={() => setSelectedKey(prompt.scenario_key)}
      >
        <span>{String(index + 1).padStart(2, '0')}</span>
        <strong>{prompt.name}</strong>
        <small>{prompt.module}</small>
        <i className={prompt.enabled ? 'enabled' : ''} />
      </button>)}
    </aside>
    {selected ? <PromptEditor key={selected.scenario_key} prompt={selected} onSave={onSave} /> : <div className="admin-empty">没有可配置的关键场景</div>}
  </section>
}
