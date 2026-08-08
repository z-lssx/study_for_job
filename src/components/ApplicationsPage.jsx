import { useEffect, useMemo, useState } from 'react'
import { CircleAlert, Plus, Search } from 'lucide-react'
import { loadApplicationRequest } from '../api'
import { STAGES } from '../constants'
import { ApplicationBoard, DetailSheet } from './ApplicationBoard'
import { ApplicationForm } from './Forms'
import { PageHeader } from './AppShell'

export function ApplicationsPage({ applications, loading, error, selectedId, navigate, onSave, onPatch, onReload }) {
  const [query, setQuery] = useState('')
  const [stage, setStage] = useState('all')
  const [editing, setEditing] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [actionError, setActionError] = useState('')
  const [selected, setSelected] = useState(null)
  const [detailVersion, setDetailVersion] = useState(0)
  const counts = useMemo(() => Object.fromEntries(STAGES.map((item) => [item.key, applications.filter((application) => application.stage === item.key).length])), [applications])

  useEffect(() => {
    if (!selectedId) { setSelected(null); return undefined }
    let active = true
    setSelected(null)
    setActionError('')
    loadApplicationRequest(selectedId)
      .then((item) => { if (active) setSelected(item) })
      .catch((caught) => { if (active) setActionError(caught.message) })
    return () => { active = false }
  }, [selectedId, detailVersion])

  async function submit(payload) {
    const saved = await onSave(payload, editing?.id)
    setSelected(saved)
    setShowForm(false); setEditing(null)
    window.setTimeout(() => navigate(`/applications/${saved.id}`, { preserveScroll: true }), 0)
  }

  async function changeStage(item, nextStage) {
    setActionError('')
    try {
      const saved = await onPatch(item.id, { stage: nextStage })
      setSelected(saved)
    } catch (caught) { setActionError(caught.message) }
  }

  return <div className="applications-page page-stack">
    <PageHeader eyebrow="工作流" title="投递记录" description="用阶段概要看分布，用舒适列表推进下一步；投递仍只是手动维护的求职流程事实。" navigate={navigate} action={<button className="button-primary" onClick={() => { setEditing(null); setShowForm(true) }}><Plus size={17} />新增投递</button>} />
    {(error || actionError) && <div className="page-error"><CircleAlert size={17} /><span>{actionError || error}</span><button onClick={() => { onReload(); if (selectedId) setDetailVersion((value) => value + 1) }}>重新读取</button></div>}
    <section className="stage-summary" aria-label="投递阶段概要">
      <button className={stage === 'all' ? 'active' : ''} onClick={() => setStage('all')}><span>全部</span><strong>{applications.length}</strong><i style={{ '--stage-progress': '100%' }} /></button>
      {STAGES.map((item) => <button key={item.key} className={stage === item.key ? 'active' : ''} onClick={() => setStage(item.key)}><span>{item.label}</span><strong>{counts[item.key]}</strong><i style={{ '--stage-progress': `${applications.length ? Math.max(5, counts[item.key] / applications.length * 100) : 0}%` }} /></button>)}
    </section>
    <section className="application-ledger calm-panel">
      <header className="list-toolbar"><div><p>投递台账</p><h2>{stage === 'all' ? '全部机会' : STAGES.find((item) => item.key === stage)?.label}</h2></div><label className="search-control"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索公司、岗位或下一步" /></label></header>
      <ApplicationBoard applications={applications} loading={loading} query={query} stage={stage} onSelect={(id) => navigate(`/applications/${id}`, { preserveScroll: true })} onCreate={() => setShowForm(true)} />
    </section>
    <DetailSheet item={selected} onClose={() => navigate('/applications', { preserveScroll: true })} onEdit={() => { setEditing(selected); setShowForm(true) }} onStageChange={changeStage} />
    {showForm && <ApplicationForm initial={editing} onClose={() => { setShowForm(false); setEditing(null) }} onSubmit={submit} />}
  </div>
}
