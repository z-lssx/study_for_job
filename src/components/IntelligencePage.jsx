import { useEffect, useMemo, useState } from 'react'
import {
  ArrowUpRight,
  CheckCircle2,
  CircleAlert,
  Clock3,
  FileInput,
  Link2,
  LoaderCircle,
  RefreshCw,
  RotateCcw,
  ScanText,
  Search,
  ShieldCheck,
  Sigma,
  X,
} from 'lucide-react'
import { useIntelligenceData } from '../hooks/useIntelligenceData'
import { ExtractionPanel } from './intelligence/ExtractionPanel'
import { PageHeader } from './AppShell'

const STATUS = {
  queued: { label: '已排队', icon: Clock3 },
  processing: { label: '处理中', icon: LoaderCircle },
  retry_wait: { label: '等待重试', icon: RotateCcw },
  succeeded: { label: '已入库', icon: CheckCircle2 },
  failed: { label: '需处理', icon: CircleAlert },
}

function compactTime(value) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(value))
}

function SubmissionCard({ item, onSelect }) {
  const status = STATUS[item.status] || STATUS.failed
  const StatusIcon = status.icon
  const title = item.document?.title || item.source?.host || '手动正文'
  return <button className={`intel-ticket status-${item.status}`} onClick={() => onSelect(item.id)}>
    <span className="intel-status"><StatusIcon size={13} />{status.label}</span>
    <span className="intel-ticket-copy"><strong>{title}</strong><small>{item.source ? item.source.host : '手动正文'} · 修订 {item.revision}</small></span>
    <time>{compactTime(item.updated_at)}</time>
    <ArrowUpRight size={16} />
  </button>
}

function IntakeForm({ onSubmit, onClose }) {
  const [mode, setMode] = useState('url')
  const [url, setUrl] = useState('')
  const [content, setContent] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  function requestClose() {
    if ((url.trim() || content.trim()) && !window.confirm('尚未提交的内容会丢失，确认关闭吗？')) return
    onClose()
  }

  useEffect(() => {
    const closeOnEscape = (event) => event.key === 'Escape' && requestClose()
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  })

  async function submit(event) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setNotice('')
    try {
      const result = await onSubmit(mode === 'url' ? { url: url.trim() } : { content: content.trim() })
      if (result.created) {
        setNotice('已写入原始事实，Worker 将立即处理。')
        if (mode === 'url') setUrl('')
        else setContent('')
      } else {
        setNotice(result.duplicate_reason === 'normalized_url' ? '该规范化 URL 已存在，已打开原记录。' : '相同正文已存在，已打开原记录。')
      }
      return result
    } catch (caught) {
      setError(caught.message)
    } finally {
      setSaving(false)
    }
  }

  return <div className="intel-modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && requestClose()}>
    <section className="intake-console" role="dialog" aria-modal="true" aria-labelledby="intake-title">
    <header>
      <div><span>提交原始情报</span><h2 id="intake-title">保存链接或面经正文</h2><p>两种输入进入同一条可追溯链路。公开 URL 当前仅支持规则允许、无需登录的来源。</p></div>
      <button className="icon-button" type="button" onClick={requestClose} aria-label="关闭提交窗口"><X size={19} /></button>
    </header>
    <div className="intake-mode" role="tablist" aria-label="面经提交方式">
      <button type="button" className={mode === 'url' ? 'active' : ''} onClick={() => setMode('url')}><Link2 size={16} />公开 URL</button>
      <button type="button" className={mode === 'content' ? 'active' : ''} onClick={() => setMode('content')}><FileInput size={16} />直接正文</button>
    </div>
    <form onSubmit={submit}>
      {mode === 'url' ? <label>
        <span>公开文章 URL</span>
        <input autoFocus type="url" required value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://www.cnblogs.com/.../p/....html" />
        <small>当前首个适配路径：博客园公开文章。查询参数和 fragment 不参与身份判定。</small>
      </label> : <label>
        <span>面经纯文本正文</span>
        <textarea autoFocus required minLength={20} rows="9" value={content} onChange={(event) => setContent(event.target.value)} placeholder="粘贴面经正文。系统保存原始输入，并生成稳定的清洗文本与内容哈希。" />
        <small>{content.trim().length} 字符 · 只作为纯文本保存与展示</small>
      </label>}
      {error && <div className="intake-message error"><CircleAlert size={15} />{error}</div>}
      {notice && <div className="intake-message success"><CheckCircle2 size={15} />{notice}</div>}
      <button className="action-primary" disabled={saving}>{saving ? <><LoaderCircle className="spin" size={17} />写入中</> : <><ScanText size={17} />提交并处理</>}</button>
    </form>
    <footer><ShieldCheck size={16} /><span>服务端执行来源、robots、重定向、超时、体积和类型检查；原始 HTML 不会直接渲染。</span></footer>
    </section>
  </div>
}

function DetailPanel({ item, onSupplement, onRetry, onTriggerExtraction, onSaveAnnotation }) {
  const [showSupplement, setShowSupplement] = useState(false)
  const [content, setContent] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  if (!item) return null
  const status = STATUS[item.status] || STATUS.failed

  async function supplement(event) {
    event.preventDefault()
    setSaving(true)
    setError('')
    try {
      await onSupplement(item.id, content)
      setContent('')
      setShowSupplement(false)
    } catch (caught) {
      setError(caught.message)
    } finally {
      setSaving(false)
    }
  }

  async function retry() {
    setSaving(true)
    setError('')
    try { await onRetry(item.id) } catch (caught) { setError(caught.message) } finally { setSaving(false) }
  }

  return <section className="intel-detail calm-panel">
    <header className={`detail-status status-${item.status}`}>
      <span>修订 {String(item.revision).padStart(2, '0')}</span>
      <strong>{status.label}</strong>
    </header>
    <div className="intel-detail-title">
      <p>{item.collection_method.replaceAll('_', ' / ')}</p>
      <h2>{item.document?.title || (item.source ? '等待公开来源处理' : '等待正文处理')}</h2>
    </div>
    <dl className="intel-facts">
      <div><dt>提交时间</dt><dd>{compactTime(item.submitted_at)}</dd></div>
      <div><dt>采集方式</dt><dd>{item.collection_method}</dd></div>
      <div><dt>内容哈希</dt><dd>{item.document?.content_hash?.slice(0, 12) || '等待生成'}</dd></div>
      <div><dt>清洗版本</dt><dd>{item.document?.cleaning_version || '—'}</dd></div>
    </dl>
    {item.source && <a className="intel-source-link" href={item.source.url} target="_blank" rel="noreferrer">
      <span><Link2 size={15} />{item.source.host}</span><code>{item.source.normalized_url}</code><ArrowUpRight size={17} />
    </a>}
    {item.error && <div className="intel-failure">
      <span>{item.error.code}</span><strong>{item.error.message}</strong><small>{item.error.retryable ? '可重新触发；队列失败时会先按退避策略重试。' : '永久分类；建议补充正文。'}</small>
    </div>}
    {item.document ? <article className="intel-preview">
      <span>安全纯文本预览</span>
      <p>{item.document.content_preview}</p>
      {item.document.preview_truncated && <small>预览已截断，原始事实完整保存在 PostgreSQL。</small>}
    </article> : <div className="intel-processing"><span /><p>{item.status === 'failed' ? '原始输入仍然保留，可在下方恢复处理。' : 'Worker 正在建立原始事实与内容哈希。'}</p></div>}
    <ExtractionPanel item={item} onTrigger={onTriggerExtraction} onSaveAnnotation={onSaveAnnotation} />
    {error && <div className="intake-message error"><CircleAlert size={15} />{error}</div>}
    {item.status === 'failed' && <div className="recovery-actions">
      {item.can_retry && <button className="action-secondary" disabled={saving} onClick={retry}><RotateCcw size={16} />重新触发</button>}
      {item.can_supplement && <button className="action-primary" disabled={saving} onClick={() => setShowSupplement((value) => !value)}><FileInput size={16} />补充正文</button>}
    </div>}
    {showSupplement && <form className="supplement-form" onSubmit={supplement}>
      <label>补充纯文本正文<textarea autoFocus required minLength={20} rows="8" value={content} onChange={(event) => setContent(event.target.value)} /></label>
      <div><button type="button" className="action-secondary" onClick={() => setShowSupplement(false)}>取消</button><button className="action-primary" disabled={saving}>保存并重新处理</button></div>
    </form>}
  </section>
}

export function IntelligencePage({ navigate }) {
  const { submissions, loading, error, loadData, submit } = useIntelligenceData()
  const [showIntake, setShowIntake] = useState(false)
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const metrics = useMemo(() => ({
    ready: submissions.filter((item) => item.status === 'succeeded').length,
    active: submissions.filter((item) => ['queued', 'processing', 'retry_wait'].includes(item.status)).length,
    failed: submissions.filter((item) => item.status === 'failed').length,
  }), [submissions])
  const visible = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    return submissions.filter((item) => {
      if (statusFilter === 'active' && !['queued', 'processing', 'retry_wait'].includes(item.status)) return false
      if (statusFilter !== 'all' && statusFilter !== 'active' && item.status !== statusFilter) return false
      if (!normalized) return true
      const text = `${item.document?.title || ''} ${item.source?.host || ''} ${item.collection_method || ''}`.toLowerCase()
      return text.includes(normalized)
    })
  }, [submissions, query, statusFilter])

  async function submitAndOpen(payload) {
    const result = await submit(payload)
    setShowIntake(false)
    navigate(`/intelligence/${result.submission.id}`)
    return result
  }

  return <div className="intelligence-page page-stack">
    <PageHeader
      eyebrow="面试情报"
      title="原始事实台账"
      description="保存来源、处理状态和证据链，再进入单条情报完成阅读、恢复与人工标注。"
      action={<button className="button-primary" onClick={() => setShowIntake(true)}><FileInput size={17} />提交情报</button>}
      navigate={navigate}
    />
    {error && <div className="error-ribbon"><CircleAlert size={17} /><span>{error}</span><button onClick={() => loadData()}>重新连接</button></div>}
    <section className="intel-summary" aria-label="情报状态摘要">
      <button className={statusFilter === 'all' ? 'active' : ''} onClick={() => setStatusFilter('all')}><span>全部记录</span><strong>{submissions.length}</strong></button>
      <button className={statusFilter === 'succeeded' ? 'active' : ''} onClick={() => setStatusFilter('succeeded')}><span>已入库</span><strong>{metrics.ready}</strong></button>
      <button className={statusFilter === 'active' ? 'active' : ''} onClick={() => setStatusFilter('active')}><span>处理中</span><strong>{metrics.active}</strong></button>
      <button className={`${statusFilter === 'failed' ? 'active' : ''} ${metrics.failed ? 'has-failure' : ''}`} onClick={() => setStatusFilter('failed')}><span>需处理</span><strong>{metrics.failed}</strong></button>
    </section>

    <section className="intel-ledger calm-panel">
      <header className="intel-ledger-toolbar">
        <div><p>台账</p><h2>最近提交</h2></div>
        <label className="intel-search"><Search size={17} /><span className="sr-only">筛选情报</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索标题、来源或采集方式" /></label>
        <button className="icon-button" onClick={() => loadData()} disabled={loading} aria-label="刷新情报台账"><RefreshCw className={loading ? 'spin' : ''} size={17} /></button>
      </header>
      <div className="intel-list">
        {loading && submissions.length === 0 && <div className="ledger-skeleton" aria-label="正在加载情报"><i /><i /><i /></div>}
        {!loading && submissions.length === 0 && <div className="quiet-empty"><ScanText size={25} /><strong>还没有原始面经事实</strong><p>从一篇公开文章或一段面经正文开始。</p><button className="button-primary" onClick={() => setShowIntake(true)}>提交第一条情报</button></div>}
        {!loading && submissions.length > 0 && visible.length === 0 && <div className="quiet-empty"><Search size={24} /><strong>没有符合条件的记录</strong><p>清除搜索词或切换状态筛选后再看。</p><button className="button-secondary" onClick={() => { setQuery(''); setStatusFilter('all') }}>清除筛选</button></div>}
        {visible.map((item) => <SubmissionCard key={item.id} item={item} onSelect={(id) => navigate(`/intelligence/${id}`)} />)}
      </div>
    </section>

    <section className="intel-tools-grid">
      <button className="calm-panel" onClick={() => navigate('/intelligence/search')}><Search size={20} /><span><strong>证据检索</strong><small>用精确术语、轮次和来源过滤原始证据。</small></span><ArrowUpRight size={17} /></button>
      <button className="calm-panel" onClick={() => navigate('/intelligence/questions')}><Sigma size={20} /><span><strong>规范题与频率</strong><small>核对出现记录，并进行人工合并、拆分或改映射。</small></span><ArrowUpRight size={17} /></button>
    </section>
    {showIntake && <IntakeForm onSubmit={submitAndOpen} onClose={() => setShowIntake(false)} />}
  </div>
}

export function IntelligenceDetailPage({ submissionId, navigate }) {
  const { selected, error, selectSubmission, supplement, retry, triggerExtraction, saveChunkAnnotation } = useIntelligenceData()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    setLoading(true)
    selectSubmission(submissionId).catch(() => null).finally(() => active && setLoading(false))
    return () => { active = false }
  }, [submissionId, selectSubmission])

  const title = selected?.document?.title || selected?.source?.host || '情报详情'
  return <div className="intelligence-detail-page page-stack">
    <PageHeader
      eyebrow="面试情报 / 单条详情"
      title={title}
      description={selected ? `提交于 ${compactTime(selected.submitted_at)} · 修订 ${selected.revision}` : '正在读取来源、处理状态与证据链。'}
      backTo="/intelligence"
      breadcrumbs={[{ label: '面试情报', to: '/intelligence' }, { label: '详情' }]}
      action={<button className="button-secondary" onClick={() => selectSubmission(submissionId)} disabled={loading}><RefreshCw className={loading ? 'spin' : ''} size={16} />刷新详情</button>}
      navigate={navigate}
    />
    {error && <div className="page-error"><CircleAlert size={17} /><span>{error}</span><button onClick={() => selectSubmission(submissionId)}>重试</button></div>}
    {loading && !selected ? <div className="ledger-skeleton"><i /><i /><i /></div> : <DetailPanel item={selected} onSupplement={supplement} onRetry={retry} onTriggerExtraction={triggerExtraction} onSaveAnnotation={saveChunkAnnotation} />}
  </div>
}
