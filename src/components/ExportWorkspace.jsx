import React, { useState } from 'react'
import { AlertTriangle, CalendarDays, Database, Download, FileJson, FileText, RefreshCw, ShieldCheck } from 'lucide-react'
import { createExportSnapshotRequest } from '../api/exports'
import { PageHeader } from './AppShell'
import './export.css'

const formats = [
  ['json', 'JSON', '规范关系快照', '保留完整集合、字段、稳定 ID 与关系，适合迁移和后续机器处理。'],
  ['markdown', 'Markdown', '可读事实档案', '按事实边界、集合和关系分章，适合个人阅读、复习和分享。'],
]

const collectionGroups = [
  ['目标 / 投递', ['target_profiles', 'applications']],
  ['结构化情报', ['canonical_questions', 'question_occurrences', 'question_occurrence_mappings', 'evidence_refs']],
  ['知识 / 算法', ['knowledge_cards', 'algorithm_problems']],
  ['项目资产', ['projects', 'project_facts', 'project_expression_versions', 'project_intelligence_links']],
  ['实习资产', ['internships', 'internship_facts', 'internship_expression_versions', 'internship_materials', 'internship_intelligence_links']],
]

function localDateValue() {
  const now = new Date()
  const offset = now.getTimezoneOffset() * 60_000
  return new Date(now.getTime() - offset).toISOString().slice(0, 10)
}

function groupCount(collections, names) {
  return names.reduce((sum, name) => sum + (collections[name] || 0), 0)
}

function downloadResult(result) {
  const body = result.format === 'json' ? JSON.stringify(result.content, null, 2) : result.content
  const blob = new Blob([body], { type: `${result.media_type};charset=utf-8` })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = result.file_name
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

export function ExportWorkspace({ navigate }) {
  const [format, setFormat] = useState('json')
  const [asOfDate, setAsOfDate] = useState(localDateValue)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function submitExport(event) {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      setResult(await createExportSnapshotRequest({ format, as_of_date: asOfDate }))
    } catch (caught) {
      setError(caught.message)
    } finally {
      setLoading(false)
    }
  }

  const manifest = result?.manifest
  const isEmpty = manifest?.counts.total_records === 0

  return <section className="export-workspace page-stack">
    <PageHeader
      eyebrow="导出"
      title="生成一次可携带的事实快照"
      description="Markdown 与 JSON 使用同一关系模型，直接读取 PostgreSQL 当前事实；不会创建定时备份或后台任务。"
      action={<span className="export-rule-badge"><ShieldCheck size={16} />同源 · 可复现</span>}
      navigate={navigate}
    />

    <div className="export-layout">
      <aside className="export-control">
        <form onSubmit={submitExport}>
          <fieldset className="export-format-field">
            <legend>导出格式</legend>
            {formats.map(([value, label, eyebrow, description]) => <label className={format === value ? 'selected' : ''} key={value}>
              <input type="radio" name="export-format" value={value} checked={format === value} onChange={() => setFormat(value)} />
              {value === 'json' ? <FileJson size={19} /> : <FileText size={19} />}
              <span><small>{eyebrow}</small><strong>{label}</strong><p>{description}</p></span>
            </label>)}
          </fieldset>

          <label className="export-date-field">
            <span>快照基准日期</span>
            <input type="date" value={asOfDate} onChange={(event) => setAsOfDate(event.target.value)} required />
            <small>日期会显式进入请求与指纹。当前表不保存完整时态历史，因此它不是过去状态恢复点。</small>
          </label>

          <div className="export-boundary-card">
            <strong>导出边界</strong>
            <ul>
              <li>投递 key_date 保持未标注日期，不解释为面试日期。</li>
              <li>confirmed、draft、AI 起草来源、表达和材料状态分别保留。</li>
              <li>occurrence 与 association 只是情报需求信号，不证明能力。</li>
              <li>证据只含既有有界片段与回链，不包含全量面经正文。</li>
            </ul>
          </div>

          <button className="action-primary export-submit" type="submit" disabled={loading}>
            {loading ? <><RefreshCw size={16} className="export-spinner" />生成中</> : <><Database size={16} />{result ? '重新生成快照' : '生成导出快照'}</>}
          </button>
          <p className="export-submit-note">只有点击此按钮才会调用导出 API；切换格式、修改日期或打开页面都不会自动生成。</p>
        </form>
      </aside>

      <div className="export-results" aria-live="polite">
        {error && <div className="export-error"><AlertTriangle size={18} /><div><strong>本次快照未生成</strong><p>{error}</p><small>已有成功快照不会被失败请求改写；可调整输入后再次主动生成。</small></div></div>}
        {!result && !loading && !error && <div className="export-pristine">
          <CalendarDays size={26} />
          <p className="section-code">等待主动生成</p>
          <h3>尚未生成事实快照</h3>
          <p>选择格式并确认可见日期，再主动生成。系统不会从当前页面状态拼接数据。</p>
        </div>}
        {loading && <div className="export-loading"><RefreshCw size={20} className="export-spinner" /><span>正在固定只读快照并整理稳定关系…</span></div>}

        {result && !loading && <>
          <section className="export-snapshot-head">
            <div>
              <p className="section-code">导出快照 · {manifest.export_version}</p>
              <h3>{result.format === 'json' ? 'JSON 规范关系快照' : 'Markdown 可读事实档案'}</h3>
              <p>{manifest.as_of_date} · {manifest.counts.total_records} 条记录 · {manifest.counts.total_relationships} 条关系</p>
            </div>
            <span><ShieldCheck size={15} />用户主动触发</span>
          </section>

          {isEmpty ? <div className="export-empty"><h3>当前没有可导出的业务记录</h3><p>快照仍保留 schema、边界、warnings 和稳定指纹；系统不会为了填满文件补写事实。</p></div> : <div className="export-count-grid">
            {collectionGroups.map(([label, names]) => <div key={label}><span>{label}</span><strong>{String(groupCount(manifest.counts.collections, names)).padStart(2, '0')}</strong></div>)}
          </div>}

          <section className="export-download-card">
            <div>
              <span>文件已准备好</span>
              <strong>{result.file_name}</strong>
              <p>文件内容与下方 fingerprint 对应。下载不会创建服务端备份或后台任务。</p>
            </div>
            <button type="button" onClick={() => downloadResult(result)}><Download size={17} />下载 {result.format === 'json' ? '.json' : '.md'}</button>
          </section>

          {manifest.warnings.length > 0 && <section className="export-warnings">
            <h4>缺失关系与降级说明</h4>
            <ul>{manifest.warnings.map((warning) => <li key={warning.code}><AlertTriangle size={14} /><div><p>{warning.message}</p><code>{warning.code}</code></div></li>)}</ul>
          </section>}

          <details className="export-details">
            <summary>查看分类计数、限制与稳定指纹</summary>
            <div className="export-detail-grid">
              <section><h4>分类计数</h4><pre>{JSON.stringify(manifest.counts.classifications, null, 2)}</pre></section>
              <section><h4>限制</h4><ul>{manifest.limitations.map((item) => <li key={item}>{item}</li>)}</ul></section>
            </div>
            <p className="export-fingerprint"><span>snapshot fingerprint</span><code>{manifest.snapshot_fingerprint}</code></p>
          </details>
        </>}
      </div>
    </div>
  </section>
}
