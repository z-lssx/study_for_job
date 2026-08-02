import { useMemo, useState } from 'react'
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
  ShieldCheck,
} from 'lucide-react'
import { useIntelligenceData } from '../hooks/useIntelligenceData'
import { ExtractionPanel } from './intelligence/ExtractionPanel'

const STATUS = {
  queued: { label: '已排队', code: 'QUEUE', icon: Clock3 },
  processing: { label: '处理中', code: 'RUN', icon: LoaderCircle },
  retry_wait: { label: '等待重试', code: 'RETRY', icon: RotateCcw },
  succeeded: { label: '已入库', code: 'READY', icon: CheckCircle2 },
  failed: { label: '需处理', code: 'FAILED', icon: CircleAlert },
}

function compactTime(value) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(value))
}

function SubmissionCard({ item, active, onSelect }) {
  const status = STATUS[item.status] || STATUS.failed
  const StatusIcon = status.icon
  const title = item.document?.title || item.source?.host || '手动正文'
  return <button className={`intel-ticket status-${item.status} ${active ? 'active' : ''}`} onClick={() => onSelect(item.id)}>
    <span className="intel-ticket-rail" />
    <span className="intel-status"><StatusIcon size={13} />{status.label}</span>
    <strong>{title}</strong>
    <small>{item.source ? item.source.host : 'MANUAL / TEXT'} · R{item.revision}</small>
    <time>{compactTime(item.updated_at)}</time>
  </button>
}

function IntakeForm({ onSubmit }) {
  const [mode, setMode] = useState('url')
  const [url, setUrl] = useState('')
  const [content, setContent] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

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
    } catch (caught) {
      setError(caught.message)
    } finally {
      setSaving(false)
    }
  }

  return <section className="intake-console">
    <header>
      <span>01 / INTAKE</span>
      <h2>投递一条原始情报</h2>
      <p>链接与正文进入同一条可追溯链路。只处理公开、无需登录且规则允许的页面。</p>
    </header>
    <div className="intake-mode" role="tablist" aria-label="面经提交方式">
      <button type="button" className={mode === 'url' ? 'active' : ''} onClick={() => setMode('url')}><Link2 size={16} />公开 URL</button>
      <button type="button" className={mode === 'content' ? 'active' : ''} onClick={() => setMode('content')}><FileInput size={16} />直接正文</button>
    </div>
    <form onSubmit={submit}>
      {mode === 'url' ? <label>
        <span>PUBLIC ARTICLE URL</span>
        <input autoFocus type="url" required value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://www.cnblogs.com/.../p/....html" />
        <small>当前首个适配路径：博客园公开文章。查询参数和 fragment 不参与身份判定。</small>
      </label> : <label>
        <span>INTERVIEW NOTES / PLAIN TEXT</span>
        <textarea autoFocus required minLength={20} rows="9" value={content} onChange={(event) => setContent(event.target.value)} placeholder="粘贴面经正文。系统保存原始输入，并生成稳定的清洗文本与内容哈希。" />
        <small>{content.trim().length} 字符 · 只作为纯文本保存与展示</small>
      </label>}
      {error && <div className="intake-message error"><CircleAlert size={15} />{error}</div>}
      {notice && <div className="intake-message success"><CheckCircle2 size={15} />{notice}</div>}
      <button className="action-primary" disabled={saving}>{saving ? <><LoaderCircle className="spin" size={17} />写入中</> : <><ScanText size={17} />提交并处理</>}</button>
    </form>
    <footer><ShieldCheck size={16} /><span>服务端执行来源、robots、重定向、超时、体积和类型检查；已登记的外网安全边界风险仍待后续治理。</span></footer>
  </section>
}

function DetailPanel({ item, onSupplement, onRetry, onTriggerExtraction, onSaveAnnotation }) {
  const [showSupplement, setShowSupplement] = useState(false)
  const [content, setContent] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  if (!item) return <section className="intel-detail intel-empty-detail"><ScanText size={34} /><h3>选择一条情报</h3><p>查看来源、状态、失败原因和安全纯文本预览。</p></section>
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

  return <section className="intel-detail">
    <header className={`detail-status status-${item.status}`}>
      <span>{status.code} / REVISION {String(item.revision).padStart(2, '0')}</span>
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
      <span>SAFE PLAIN-TEXT PREVIEW</span>
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

export function IntelligencePage() {
  const { submissions, selected, loading, error, loadData, selectSubmission, submit, supplement, retry, triggerExtraction, saveChunkAnnotation } = useIntelligenceData()
  const metrics = useMemo(() => ({
    ready: submissions.filter((item) => item.status === 'succeeded').length,
    active: submissions.filter((item) => ['queued', 'processing', 'retry_wait'].includes(item.status)).length,
    failed: submissions.filter((item) => item.status === 'failed').length,
  }), [submissions])

  return <div className="intelligence-page">
    <section className="intel-hero">
      <div><p className="section-code">INTERVIEW INTELLIGENCE / RAW FACTS</p><h1>先保存证据，<br /><em>再提炼情报。</em></h1><p>每条公开链接或手动正文，都保留来源、原始输入、清洗文本、处理状态与失败恢复路径。</p></div>
      <aside>
        <div><span>READY</span><strong>{String(metrics.ready).padStart(2, '0')}</strong></div>
        <div><span>IN FLIGHT</span><strong>{String(metrics.active).padStart(2, '0')}</strong></div>
        <div className={metrics.failed ? 'has-failure' : ''}><span>NEEDS INPUT</span><strong>{String(metrics.failed).padStart(2, '0')}</strong></div>
      </aside>
    </section>
    {error && <div className="error-ribbon"><CircleAlert size={17} /><span>{error}</span><button onClick={() => loadData()}>重新连接</button></div>}
    <div className="intel-workspace">
      <IntakeForm onSubmit={submit} />
      <section className="intel-ledger">
        <header><div><span>02 / LEDGER</span><h2>原始事实台账</h2></div><button onClick={() => loadData()} disabled={loading}><RefreshCw className={loading ? 'spin' : ''} size={16} />刷新</button></header>
        <div className="intel-ledger-body">
          <div className="intel-list">
            {loading && submissions.length === 0 && <div className="intel-list-empty"><LoaderCircle className="spin" size={22} />正在同步</div>}
            {!loading && submissions.length === 0 && <div className="intel-list-empty">还没有原始面经事实</div>}
            {submissions.map((item) => <SubmissionCard key={item.id} item={item} active={selected?.id === item.id} onSelect={selectSubmission} />)}
          </div>
          <DetailPanel item={selected} onSupplement={supplement} onRetry={retry} onTriggerExtraction={triggerExtraction} onSaveAnnotation={saveChunkAnnotation} />
        </div>
      </section>
    </div>
  </div>
}
