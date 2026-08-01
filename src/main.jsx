import React, { useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { ArrowDownRight, CircleAlert, Database, Plus, RefreshCw, Search, Target, Zap } from 'lucide-react'
import { ApplicationBoard, DetailSheet } from './components/ApplicationBoard'
import { ApplicationForm, ProfileForm } from './components/Forms'
import { AiAdminPage } from './components/AiAdminPage'
import { useJobData } from './hooks/useJobData'
import './styles.css'

function dateStamp() {
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    weekday: 'short',
  }).format(new Date())
}

function App() {
  const {
    profile,
    applications,
    selected,
    loading,
    error,
    environment,
    loadData,
    saveApplication,
    saveProfile,
    selectApplication,
    closeSelection,
  } = useJobData()
  const [query, setQuery] = useState('')
  const [editing, setEditing] = useState(null)
  const [showApplicationForm, setShowApplicationForm] = useState(false)
  const [showProfileForm, setShowProfileForm] = useState(false)
  const [actionError, setActionError] = useState('')
  const [activeView, setActiveView] = useState('applications')

  const metrics = useMemo(() => {
    const active = applications.filter((item) => item.stage !== 'closed').length
    const interviews = applications.filter((item) => item.stage === 'interview').length
    const dated = applications.filter((item) => item.key_date && item.stage !== 'closed').sort((a, b) => a.key_date.localeCompare(b.key_date))
    return { active, interviews, nextDate: dated[0]?.key_date?.slice(5).replace('-', '.') || '—' }
  }, [applications])

  function openCreate() {
    setEditing(null)
    setShowApplicationForm(true)
  }

  async function submitApplication(payload) {
    await saveApplication(payload, editing?.id)
    setShowApplicationForm(false)
    setEditing(null)
  }

  async function moveApplication(item, stage) {
    setActionError('')
    try { await saveApplication({ ...item, stage }, item.id) } catch (caught) { setActionError(caught.message) }
  }

  async function submitProfile(payload) {
    await saveProfile(payload)
    setShowProfileForm(false)
  }

  const isDevelopment = environment !== 'usage'

  return <div className="app-canvas">
    <div className="grain" aria-hidden="true" />
    <header className="masthead">
      <a className="wordmark" href="#top" aria-label="study for job 首页">
        <span>S/J</span><strong>STUDY<br />FOR JOB</strong>
      </a>
      <nav aria-label="主导航">
        <button className={activeView === 'applications' ? 'active' : ''} onClick={() => setActiveView('applications')}>申请轨道</button>
        <button onClick={() => setShowProfileForm(true)}>目标画像</button>
        <button className={activeView === 'ai' ? 'active' : ''} onClick={() => setActiveView('ai')}>AI 管理</button>
      </nav>
      <div className={`environment-stamp ${isDevelopment ? 'development' : 'usage'}`}>
        <Database size={14} />
        <span>{isDevelopment ? '开发数据' : '使用数据'}</span>
        <i />
      </div>
    </header>

    <main id="top">
      {activeView === 'applications' ? <>
      <section className="hero-grid">
        <div className="hero-copy">
          <p className="section-code">CAREER OPERATIONS / {dateStamp()}</p>
          <h1>别管理焦虑，<br /><em>推进下一步。</em></h1>
          <p className="hero-lead">把分散的机会、日期与动作排成一条能前进的轨道。每次打开，只看此刻最值得做的事。</p>
          <div className="hero-actions">
            <button className="action-primary" onClick={openCreate}><Plus size={18} />新增投递</button>
            <button className="refresh-action" onClick={loadData}><RefreshCw size={16} />刷新事实</button>
          </div>
        </div>

        <div className="pulse-orbit" aria-hidden="true">
          <span className="orbit orbit-one" /><span className="orbit orbit-two" />
          <strong>{String(metrics.active).padStart(2, '0')}</strong>
          <small>ACTIVE<br />THREADS</small>
          <Zap size={24} />
        </div>

        <aside className="metric-stack" aria-label="求职进度摘要">
          <div><span>面试进行</span><strong>{String(metrics.interviews).padStart(2, '0')}</strong></div>
          <div><span>最近节点</span><strong>{metrics.nextDate}</strong></div>
          <div><span>全部记录</span><strong>{String(applications.length).padStart(2, '0')}</strong></div>
        </aside>
      </section>

      {(error || actionError) && <div className="error-ribbon">
        <CircleAlert size={17} /><span>{actionError || error}</span><button onClick={loadData}>重新连接</button>
      </div>}

      <section className="mission-brief">
        <div className="brief-label"><Target size={19} /><span>TARGET<br />BRIEF</span></div>
        <div className="brief-title">
          <p>当前主航向</p>
          <h2>{profile?.title || '还没有定义目标岗位'}</h2>
        </div>
        <div className="brief-meta">
          <span>{profile?.location || '地点待补充'}</span>
          <span>{profile?.focus || '重点方向待补充'}</span>
        </div>
        <p className="brief-summary">{profile?.summary || '先把目标写清楚，后续准备才有取舍依据。开发环境允许保留样例数据，使用环境只保存你的真实事实。'}</p>
        <button className="brief-edit" onClick={() => setShowProfileForm(true)}>{profile ? '校准画像' : '创建画像'}<ArrowDownRight size={18} /></button>
      </section>

      <section className="board-section" id="board">
        <header className="board-toolbar">
          <div><p className="section-code">APPLICATION FLOW / LIVE</p><h2>机会推进轨道</h2></div>
          <label className="search-field"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索公司、岗位、动作" /></label>
          <span className="source-note"><i />事实来自 PostgreSQL</span>
        </header>
        <ApplicationBoard
          applications={applications}
          loading={loading}
          query={query}
          onSelect={selectApplication}
          onCreate={openCreate}
        />
      </section>
      </> : <AiAdminPage />}
    </main>

    <footer className="page-footer"><span>STUDY_FOR_JOB / LOCAL FIRST</span><span>MOVE WITH INTENT — 2026</span></footer>

    <DetailSheet
      item={selected}
      onClose={closeSelection}
      onEdit={() => { setEditing(selected); setShowApplicationForm(true) }}
      onStageChange={moveApplication}
    />
    {showApplicationForm && <ApplicationForm
      initial={editing}
      onClose={() => { setShowApplicationForm(false); setEditing(null) }}
      onSubmit={submitApplication}
    />}
    {showProfileForm && <ProfileForm initial={profile} onClose={() => setShowProfileForm(false)} onSubmit={submitProfile} />}
  </div>
}

createRoot(document.getElementById('root')).render(<App />)
