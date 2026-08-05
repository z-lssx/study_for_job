import React from 'react'
import {
  confirmInternshipVersionRequest,
  createInternshipVersionRequest,
  updateInternshipVersionRequest,
} from '../../api/internships'
import { followUps, followUpText } from './options'

function StarFields({ version }) {
  return <>
    <div className="internship-form-grid"><label>Situation<textarea name="situation" defaultValue={version?.situation || ''} maxLength={4000} rows={2} /></label><label>Task<textarea name="task" defaultValue={version?.task || ''} maxLength={4000} rows={2} /></label></div>
    <div className="internship-form-grid"><label>Action<textarea name="action" defaultValue={version?.action || ''} maxLength={8000} rows={3} /></label><label>Result<textarea name="result" defaultValue={version?.result || ''} maxLength={4000} rows={3} /></label></div>
    <label>量化表达<textarea name="quantified_pitch" defaultValue={version?.quantified_pitch || ''} maxLength={4000} rows={2} placeholder="仅使用已经核实的指标，不确定时保留缺口" /></label>
    <label>追问树<textarea name="follow_up_tree" defaultValue={followUpText(version?.follow_up_tree)} rows={3} placeholder="每行一个追问" /></label>
  </>
}

function versionPayload(values) {
  return {
    label: values.get('label'),
    situation: values.get('situation') || null,
    task: values.get('task') || null,
    action: values.get('action') || null,
    result: values.get('result') || null,
    quantified_pitch: values.get('quantified_pitch') || null,
    follow_up_tree: followUps(values.get('follow_up_tree') || ''),
  }
}

export function InternshipExpressionPanel({ internship, onChange, onError }) {
  async function createVersion(event) {
    event.preventDefault()
    const form = event.currentTarget
    const payload = versionPayload(new FormData(form))
    payload.based_on_version_id = internship.versions[0]?.id || null
    try {
      onChange(await createInternshipVersionRequest(internship.id, payload))
      form.reset()
    } catch (caught) { onError(caught.message) }
  }

  async function saveVersion(event, versionId) {
    event.preventDefault()
    try {
      onChange(await updateInternshipVersionRequest(internship.id, versionId, versionPayload(new FormData(event.currentTarget))))
    } catch (caught) { onError(caught.message) }
  }

  async function confirmVersion(versionId) {
    try { onChange(await confirmInternshipVersionRequest(internship.id, versionId)) } catch (caught) { onError(caught.message) }
  }

  return <section className="internship-panel">
    <div className="internship-section-title"><div><span>03 / STAR</span><h3>STAR 与量化表达版本</h3></div><small>确认后保留历史</small></div>
    <details className="internship-create-details">
      <summary>创建新表达版本</summary>
      <form className="internship-inline-form" onSubmit={createVersion}>
        <label>版本名称<input name="label" required maxLength={120} placeholder="例如：后端岗位简历版" /></label>
        <StarFields />
        <button type="submit">保存表达草稿</button>
      </form>
    </details>
    <div className="internship-card-list version-list">
      {internship.versions.map((version) => <article key={version.id}>
        <div className="internship-card-head"><div><span>V{version.version_number}</span><strong>{version.label}</strong></div><div><b className={version.confirmation_status}>{version.confirmation_status === 'confirmed' ? '已确认' : '草稿'}</b>{version.origin === 'ai_draft' && <b>AI 草稿</b>}</div></div>
        <dl className="star-grid"><div><dt>S</dt><dd>{version.situation || '—'}</dd></div><div><dt>T</dt><dd>{version.task || '—'}</dd></div><div><dt>A</dt><dd>{version.action || '—'}</dd></div><div><dt>R</dt><dd>{version.result || '—'}</dd></div></dl>
        {version.quantified_pitch && <blockquote>{version.quantified_pitch}</blockquote>}
        {version.follow_up_tree.length > 0 && <ul>{version.follow_up_tree.map((item, index) => <li key={`${version.id}-${index}`}>{item.question}</li>)}</ul>}
        <div className="internship-version-actions">
          {version.confirmation_status === 'draft' && <button type="button" onClick={() => confirmVersion(version.id)}>确认并锁定</button>}
          {version.confirmation_status === 'draft' && <details><summary>修订草稿</summary><form className="internship-inline-form" onSubmit={(event) => saveVersion(event, version.id)}><label>版本名称<input name="label" defaultValue={version.label} required maxLength={120} /></label><StarFields version={version} /><button type="submit">保存草稿</button></form></details>}
          {version.confirmation_status === 'confirmed' && <small>已确认内容不可覆盖；请创建下一版本。</small>}
        </div>
      </article>)}
      {internship.versions.length === 0 && <p className="internship-muted">尚无表达版本。先补事实，再把已核实内容组织为 STAR。</p>}
    </div>
  </section>
}
