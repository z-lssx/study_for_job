import React from 'react'
import {
  createInternshipFactRequest,
  createInternshipMaterialRequest,
  updateInternshipFactRequest,
  updateInternshipMaterialRequest,
} from '../../api/internships'
import {
  factCategories,
  materialStatuses,
  materialTypes,
  optionLabel,
  sourceKinds,
} from './options'

function Options({ items }) {
  return items.map(([value, label]) => <option value={value} key={value}>{label}</option>)
}

export function InternshipFactsPanel({ internship, onChange, onError }) {
  async function createFact(event) {
    event.preventDefault()
    const form = event.currentTarget
    const values = new FormData(form)
    try {
      onChange(await createInternshipFactRequest(internship.id, {
        category: values.get('category'),
        statement: values.get('statement'),
        source_kind: values.get('source_kind'),
        source_reference: values.get('source_reference') || null,
        confirmation_status: values.get('confirmation_status'),
      }))
      form.reset()
    } catch (caught) { onError(caught.message) }
  }

  async function saveFact(event, factId) {
    event.preventDefault()
    const values = new FormData(event.currentTarget)
    try {
      onChange(await updateInternshipFactRequest(internship.id, factId, {
        category: values.get('category'),
        statement: values.get('statement'),
        source_kind: values.get('source_kind'),
        source_reference: values.get('source_reference') || null,
        confirmation_status: values.get('confirmation_status'),
      }))
    } catch (caught) { onError(caught.message) }
  }

  return <section className="internship-panel">
    <div className="internship-section-title"><div><span>02 / EVIDENCE</span><h3>职责、协作与结果事实</h3></div><small>表达不能覆盖事实</small></div>
    <details className="internship-create-details">
      <summary>新增可核实事实</summary>
      <form className="internship-inline-form" onSubmit={createFact}>
        <div className="internship-form-grid">
          <label>事实类别<select name="category"><Options items={factCategories} /></select></label>
          <label>来源类型<select name="source_kind"><Options items={sourceKinds} /></select></label>
        </div>
        <label>事实陈述<textarea name="statement" required maxLength={10000} rows={3} placeholder="只写本人确认的职责、协作背景、技术上下文或结果" /></label>
        <div className="internship-form-grid">
          <label>来源定位<input name="source_reference" maxLength={2048} placeholder="文档、任务、URL 或指标位置" /></label>
          <label>核实状态<select name="confirmation_status"><option value="draft">待核实</option><option value="confirmed">已由我确认</option></select></label>
        </div>
        <button type="submit">保存事实</button>
      </form>
    </details>
    <div className="internship-card-list">
      {internship.facts.map((fact) => <article key={fact.id}>
        <div className="internship-card-head">
          <span>{optionLabel(factCategories, fact.category)}</span>
          <div><b className={fact.confirmation_status}>{fact.confirmation_status === 'confirmed' ? '已确认' : '待核实'}</b>{fact.origin === 'ai_draft' && <b>AI 草稿</b>}</div>
        </div>
        <p>{fact.statement}</p>
        <small>{fact.source_reference || optionLabel(sourceKinds, fact.source_kind)}</small>
        <details>
          <summary>修订此事实</summary>
          <form className="internship-inline-form" onSubmit={(event) => saveFact(event, fact.id)}>
            <div className="internship-form-grid">
              <select name="category" defaultValue={fact.category}><Options items={factCategories} /></select>
              <select name="source_kind" defaultValue={fact.source_kind}><Options items={sourceKinds} /></select>
            </div>
            <textarea name="statement" defaultValue={fact.statement} required maxLength={10000} rows={3} />
            <div className="internship-form-grid">
              <input name="source_reference" defaultValue={fact.source_reference || ''} maxLength={2048} />
              <select name="confirmation_status" defaultValue={fact.confirmation_status}><option value="draft">待核实</option><option value="confirmed">已由我确认</option></select>
            </div>
            <button type="submit">保存修订</button>
          </form>
        </details>
      </article>)}
      {internship.facts.length === 0 && <p className="internship-muted">尚无事实。先记录一条能够说明本人边界的职责或结果。</p>}
    </div>
  </section>
}

export function InternshipMaterialsPanel({ internship, onChange, onError }) {
  async function createMaterial(event) {
    event.preventDefault()
    const form = event.currentTarget
    const values = new FormData(form)
    try {
      onChange(await createInternshipMaterialRequest(internship.id, {
        material_type: values.get('material_type'),
        label: values.get('label'),
        locator: values.get('locator') || null,
        notes: values.get('notes') || null,
        preparation_status: values.get('preparation_status'),
      }))
      form.reset()
    } catch (caught) { onError(caught.message) }
  }

  async function saveMaterial(event, materialId) {
    event.preventDefault()
    const values = new FormData(event.currentTarget)
    try {
      onChange(await updateInternshipMaterialRequest(internship.id, materialId, {
        material_type: values.get('material_type'),
        label: values.get('label'),
        locator: values.get('locator') || null,
        notes: values.get('notes') || null,
        preparation_status: values.get('preparation_status'),
      }))
    } catch (caught) { onError(caught.message) }
  }

  return <section className="internship-panel">
    <div className="internship-section-title"><div><span>04 / MATERIALS</span><h3>材料准备清单</h3></div><small>状态由用户维护</small></div>
    <details className="internship-create-details">
      <summary>新增材料资产</summary>
      <form className="internship-inline-form" onSubmit={createMaterial}>
        <div className="internship-form-grid">
          <label>材料类型<select name="material_type"><Options items={materialTypes} /></select></label>
          <label>准备状态<select name="preparation_status"><Options items={materialStatuses} /></select></label>
        </div>
        <label>材料名称<input name="label" required maxLength={240} placeholder="例如：简历中的实习条目" /></label>
        <label>文件或链接定位<input name="locator" maxLength={2048} placeholder="本地位置或参考链接，可留空" /></label>
        <label>准备备注<textarea name="notes" maxLength={4000} rows={2} /></label>
        <button type="submit">保存材料</button>
      </form>
    </details>
    <div className="internship-card-list compact">
      {internship.materials.map((material) => <article key={material.id}>
        <div className="internship-card-head"><strong>{material.label}</strong><b className={material.preparation_status}>{optionLabel(materialStatuses, material.preparation_status)}</b></div>
        <p>{material.notes || '暂无备注'}</p>
        <small>{optionLabel(materialTypes, material.material_type)}{material.locator ? ` · ${material.locator}` : ''}</small>
        <details><summary>更新材料状态</summary><form className="internship-inline-form" onSubmit={(event) => saveMaterial(event, material.id)}>
          <div className="internship-form-grid"><select name="material_type" defaultValue={material.material_type}><Options items={materialTypes} /></select><select name="preparation_status" defaultValue={material.preparation_status}><Options items={materialStatuses} /></select></div>
          <input name="label" defaultValue={material.label} required maxLength={240} />
          <input name="locator" defaultValue={material.locator || ''} maxLength={2048} />
          <textarea name="notes" defaultValue={material.notes || ''} maxLength={4000} rows={2} />
          <button type="submit">保存材料</button>
        </form></details>
      </article>)}
      {internship.materials.length === 0 && <p className="internship-muted">尚无材料。可从简历条目或可核实的工作样例开始。</p>}
    </div>
  </section>
}
