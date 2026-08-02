import React, { useEffect, useMemo, useState } from 'react'
import { Archive, Check, FolderKanban, Link2, Plus, RotateCcw, ShieldCheck } from 'lucide-react'
import { loadCanonicalQuestionsRequest } from '../api/canonicalQuestions'
import {
  confirmProjectVersionRequest,
  createProjectEvidenceRequest,
  createProjectRequest,
  createProjectVersionRequest,
  linkProjectIntelligenceRequest,
  loadProjectsRequest,
  unlinkProjectIntelligenceRequest,
  updateProjectEvidenceRequest,
  updateProjectRequest,
  updateProjectVersionRequest,
} from '../api/projects'
import './projects.css'

const evidenceCategories = [
  ['background_goal', '背景与目标'],
  ['responsibility', '个人职责'],
  ['team_boundary', '团队边界'],
  ['technical_choice', '技术选择'],
  ['tradeoff', '困难与取舍'],
  ['metric', '可核实指标'],
  ['other', '其他事实'],
]
const sourceKinds = [
  ['user_recollection', '本人回忆'],
  ['document', '项目文档'],
  ['repository', '代码仓库'],
  ['external_link', '外部链接'],
  ['metric_record', '指标记录'],
]

function followUps(value) {
  return value.split('\n').map((line) => line.trim()).filter(Boolean).map((question) => ({ question }))
}

function followUpText(items) {
  return (items || []).map((item) => item.question).filter(Boolean).join('\n')
}

export function ProjectsWorkspace() {
  const [projects, setProjects] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [canonicalQuestions, setCanonicalQuestions] = useState([])
  const [error, setError] = useState('')
  const selected = useMemo(() => projects.find((project) => project.id === selectedId) || null, [projects, selectedId])

  function replaceProject(project) {
    setProjects((current) => {
      const exists = current.some((item) => item.id === project.id)
      return exists ? current.map((item) => item.id === project.id ? project : item) : [project, ...current]
    })
    setSelectedId(project.id)
    setError('')
  }

  async function refresh() {
    try {
      const items = await loadProjectsRequest()
      setProjects(items)
      setSelectedId((current) => items.some((item) => item.id === current) ? current : items[0]?.id || null)
      setError('')
    } catch (caught) { setError(caught.message) }
  }

  useEffect(() => {
    refresh()
    loadCanonicalQuestionsRequest({ limit: 100 }).then(setCanonicalQuestions).catch(() => setCanonicalQuestions([]))
  }, [])

  async function createProject(event) {
    event.preventDefault()
    const values = new FormData(event.currentTarget)
    try {
      const project = await createProjectRequest({
        title: values.get('title'),
        target_role: values.get('target_role') || null,
        summary: values.get('summary') || null,
      })
      event.currentTarget.reset()
      replaceProject(project)
    } catch (caught) { setError(caught.message) }
  }

  async function saveProject(event) {
    event.preventDefault()
    const values = new FormData(event.currentTarget)
    try {
      replaceProject(await updateProjectRequest(selected.id, {
        title: values.get('title'),
        target_role: values.get('target_role') || null,
        summary: values.get('summary') || null,
        status: values.get('status'),
      }))
    } catch (caught) { setError(caught.message) }
  }

  async function createEvidence(event) {
    event.preventDefault()
    const values = new FormData(event.currentTarget)
    try {
      replaceProject(await createProjectEvidenceRequest(selected.id, {
        category: values.get('category'),
        statement: values.get('statement'),
        source_kind: values.get('source_kind'),
        source_reference: values.get('source_reference') || null,
        confirmation_status: values.get('confirmation_status'),
      }))
      event.currentTarget.reset()
    } catch (caught) { setError(caught.message) }
  }

  async function saveEvidence(event, evidenceId) {
    event.preventDefault()
    const values = new FormData(event.currentTarget)
    try {
      replaceProject(await updateProjectEvidenceRequest(selected.id, evidenceId, {
        category: values.get('category'),
        statement: values.get('statement'),
        source_kind: values.get('source_kind'),
        source_reference: values.get('source_reference') || null,
        confirmation_status: values.get('confirmation_status'),
      }))
    } catch (caught) { setError(caught.message) }
  }

  async function createVersion(event) {
    event.preventDefault()
    const values = new FormData(event.currentTarget)
    try {
      replaceProject(await createProjectVersionRequest(selected.id, {
        label: values.get('label'),
        pitch_30s: values.get('pitch_30s') || null,
        pitch_2m: values.get('pitch_2m') || null,
        follow_up_tree: followUps(values.get('follow_up_tree') || ''),
        based_on_version_id: selected.versions[0]?.id || null,
      }))
      event.currentTarget.reset()
    } catch (caught) { setError(caught.message) }
  }

  async function saveVersion(event, versionId) {
    event.preventDefault()
    const values = new FormData(event.currentTarget)
    try {
      replaceProject(await updateProjectVersionRequest(selected.id, versionId, {
        label: values.get('label'),
        pitch_30s: values.get('pitch_30s') || null,
        pitch_2m: values.get('pitch_2m') || null,
        follow_up_tree: followUps(values.get('follow_up_tree') || ''),
      }))
    } catch (caught) { setError(caught.message) }
  }

  async function confirmVersion(versionId) {
    try { replaceProject(await confirmProjectVersionRequest(selected.id, versionId)) } catch (caught) { setError(caught.message) }
  }

  async function linkIntelligence(event) {
    event.preventDefault()
    const values = new FormData(event.currentTarget)
    try {
      replaceProject(await linkProjectIntelligenceRequest(selected.id, {
        canonical_question_id: values.get('canonical_question_id'),
        project_evidence_id: values.get('project_evidence_id') || null,
        relevance_note: values.get('relevance_note'),
      }))
      event.currentTarget.reset()
    } catch (caught) { setError(caught.message) }
  }

  async function unlinkIntelligence(linkId) {
    try {
      await unlinkProjectIntelligenceRequest(selected.id, linkId)
      await refresh()
    } catch (caught) { setError(caught.message) }
  }

  return <section className="projects-workspace">
    <header className="projects-heading">
      <div><p className="section-code">PREP TRACK / PROJECTS</p><h2>项目事实与表达版本</h2><p>先保存可核实事实，再组织表达；情报频率只解释关联，不替你编造经历。</p></div>
      <button className="refresh-action" onClick={refresh}><RotateCcw size={15} />刷新</button>
    </header>
    {error && <p className="projects-error">{error}</p>}
    <div className="projects-layout">
      <aside className="projects-rail">
        <form className="project-panel project-create" onSubmit={createProject}>
          <div className="project-panel-title"><Plus size={16} /><strong>新建项目证据包</strong></div>
          <input name="title" required placeholder="项目名称" maxLength={240} />
          <input name="target_role" placeholder="目标岗位（可选）" maxLength={160} />
          <textarea name="summary" placeholder="项目事实摘要" maxLength={2000} rows={3} />
          <button className="action-primary" type="submit"><FolderKanban size={16} />保存项目</button>
        </form>
        <div className="project-list">
          {projects.map((project) => <button className={project.id === selectedId ? 'active' : ''} key={project.id} onClick={() => setSelectedId(project.id)}>
            <strong>{project.title}</strong><span>{project.target_role || '未指定目标岗位'} · 证据 {project.evidence.length} · 版本 {project.versions.length}</span>
          </button>)}
          {projects.length === 0 && <p>还没有项目，从一个最熟悉、最能核实的项目开始。</p>}
        </div>
      </aside>

      {!selected ? <div className="project-empty">选择或新建一个项目，开始整理事实证据。</div> : <div className="project-detail">
        <form className="project-panel project-facts" onSubmit={saveProject}>
          <div className="project-section-title"><div><span>01 / FACTS</span><h3>项目基本事实</h3></div><button type="submit">保存修订</button></div>
          <div className="project-form-grid"><label>项目名称<input name="title" defaultValue={selected.title} required maxLength={240} /></label><label>目标岗位<input name="target_role" defaultValue={selected.target_role || ''} maxLength={160} /></label></div>
          <label>事实摘要<textarea name="summary" defaultValue={selected.summary || ''} maxLength={2000} rows={3} /></label>
          <label>状态<select name="status" defaultValue={selected.status}><option value="active">持续维护</option><option value="archived">已归档</option></select></label>
        </form>

        <section className="project-panel">
          <div className="project-section-title"><div><span>02 / EVIDENCE</span><h3>证据包</h3></div><small>用户事实与来源分开保存</small></div>
          <details className="project-create-details"><summary><Plus size={14} />新增事实证据</summary><form className="project-inline-form" onSubmit={createEvidence}>
            <div className="project-form-grid"><label>类别<select name="category">{evidenceCategories.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label><label>来源类型<select name="source_kind">{sourceKinds.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label></div>
            <label>事实陈述<textarea name="statement" required maxLength={10000} rows={3} /></label>
            <div className="project-form-grid"><label>来源定位<input name="source_reference" placeholder="文档、仓库、URL 或记录位置" maxLength={2048} /></label><label>核实状态<select name="confirmation_status"><option value="draft">待核实</option><option value="confirmed">已由我确认</option></select></label></div>
            <button type="submit">保存证据</button>
          </form></details>
          <div className="project-evidence-list">
            {selected.evidence.map((evidence) => <article key={evidence.id}>
              <div><span>{evidenceCategories.find(([value]) => value === evidence.category)?.[1]}</span><b className={evidence.confirmation_status}>{evidence.confirmation_status === 'confirmed' ? '已确认' : '待核实'}</b>{evidence.origin === 'ai_draft' && <b>AI 草稿</b>}</div>
              <p>{evidence.statement}</p><small>{evidence.source_reference || sourceKinds.find(([value]) => value === evidence.source_kind)?.[1]}</small>
              <details><summary>修订此证据</summary><form className="project-inline-form" onSubmit={(event) => saveEvidence(event, evidence.id)}>
                <div className="project-form-grid"><select name="category" defaultValue={evidence.category}>{evidenceCategories.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select><select name="source_kind" defaultValue={evidence.source_kind}>{sourceKinds.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></div>
                <textarea name="statement" defaultValue={evidence.statement} required maxLength={10000} rows={3} />
                <div className="project-form-grid"><input name="source_reference" defaultValue={evidence.source_reference || ''} maxLength={2048} /><select name="confirmation_status" defaultValue={evidence.confirmation_status}><option value="draft">待核实</option><option value="confirmed">已由我确认</option></select></div>
                <button type="submit">保存修订</button>
              </form></details>
            </article>)}
            {selected.evidence.length === 0 && <p className="project-muted">暂无证据。优先补充职责边界、技术取舍和可核实结果。</p>}
          </div>
        </section>

        <section className="project-panel">
          <div className="project-section-title"><div><span>03 / EXPRESSIONS</span><h3>表达版本与历史</h3></div><small>已确认版本不可覆盖</small></div>
          <details className="project-create-details"><summary><Plus size={14} />创建新表达版本</summary><form className="project-inline-form" onSubmit={createVersion}>
            <label>版本标签<input name="label" required placeholder="如：后端岗位首版" maxLength={120} /></label><label>30 秒版本<textarea name="pitch_30s" maxLength={4000} rows={3} /></label><label>2 分钟版本<textarea name="pitch_2m" maxLength={12000} rows={5} /></label><label>追问树（每行一个问题）<textarea name="follow_up_tree" rows={4} /></label><button type="submit">保存为新版本</button>
          </form></details>
          <div className="project-version-list">
            {selected.versions.map((version) => <article key={version.id}>
              <div className="project-version-head"><strong>V{version.version_number} · {version.label}</strong><span>{version.confirmation_status === 'confirmed' ? <><ShieldCheck size={14} />已确认</> : '草稿'}</span></div>
              {version.pitch_30s && <p><b>30 秒：</b>{version.pitch_30s}</p>}{version.pitch_2m && <details><summary>展开 2 分钟版本</summary><p>{version.pitch_2m}</p></details>}
              {version.follow_up_tree.length > 0 && <details><summary>追问树 {version.follow_up_tree.length} 项</summary><ul>{version.follow_up_tree.map((item, index) => <li key={`${version.id}-${index}`}>{item.question}</li>)}</ul></details>}
              {version.confirmation_status === 'draft' && <div className="project-version-actions"><details><summary>修订草稿</summary><form className="project-inline-form" onSubmit={(event) => saveVersion(event, version.id)}><input name="label" defaultValue={version.label} required maxLength={120} /><textarea name="pitch_30s" defaultValue={version.pitch_30s || ''} maxLength={4000} rows={3} /><textarea name="pitch_2m" defaultValue={version.pitch_2m || ''} maxLength={12000} rows={5} /><textarea name="follow_up_tree" defaultValue={followUpText(version.follow_up_tree)} rows={4} /><button type="submit">保存草稿</button></form></details><button onClick={() => confirmVersion(version.id)}><Check size={14} />确认此版本</button></div>}
            </article>)}
            {selected.versions.length === 0 && <p className="project-muted">暂无表达版本。表达应从上方事实证据派生。</p>}
          </div>
        </section>

        <section className="project-panel">
          <div className="project-section-title"><div><span>04 / INTELLIGENCE</span><h3>岗位考点关联</h3></div><small>出现次数仅供解释</small></div>
          <details className="project-create-details"><summary><Link2 size={14} />关联阶段二规范题</summary><form className="project-inline-form" onSubmit={linkIntelligence}>
            <label>规范题<select name="canonical_question_id" required defaultValue=""><option value="" disabled>选择规范题</option>{canonicalQuestions.map((question) => <option key={question.id} value={question.id}>{question.canonical_text}（{question.occurrence_count} 次）</option>)}</select></label>
            <label>可支撑的项目证据<select name="project_evidence_id" defaultValue=""><option value="">暂不绑定具体证据</option>{selected.evidence.map((evidence) => <option key={evidence.id} value={evidence.id}>{evidence.statement.slice(0, 70)}</option>)}</select></label>
            <label>关联说明<textarea name="relevance_note" required maxLength={2000} rows={3} placeholder="说明该考点如何由项目事实支撑，或还缺什么事实" /></label><button type="submit">保存关联</button>
          </form></details>
          <div className="project-intelligence-list">
            {selected.intelligence_links.map((link) => <article key={link.id}>
              <div><strong>{link.canonical_text}</strong><span>出现 {link.occurrence_count} 次 · 仅供参考</span></div><p>{link.relevance_note}</p>
              {link.project_evidence && <blockquote>{link.project_evidence.statement}</blockquote>}
              {link.occurrence_evidence.length > 0 && <details><summary>查看原始面经证据</summary>{link.occurrence_evidence.map((evidence) => <p className="project-source" key={evidence.occurrence_id}>“{evidence.quote}” {evidence.source_url && <a href={evidence.source_url} target="_blank" rel="noreferrer">打开来源</a>}</p>)}</details>}
              <button className="project-unlink" onClick={() => unlinkIntelligence(link.id)}><Archive size={13} />移除关联</button>
            </article>)}
            {selected.intelligence_links.length === 0 && <p className="project-muted">尚未关联岗位考点；项目事实不会因情报变化而被改写。</p>}
          </div>
        </section>
      </div>}
    </div>
  </section>
}
