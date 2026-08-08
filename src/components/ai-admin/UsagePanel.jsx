import { useMemo, useState } from 'react'
import { Activity, Clock3, Hash, TriangleAlert } from 'lucide-react'

function compactTime(value) {
  return new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(value))
}

export function UsagePanel({ prompts, statistics, calls }) {
  const [moduleFilter, setModuleFilter] = useState('all')
  const [scenarioFilter, setScenarioFilter] = useState('all')
  const modules = useMemo(() => [...new Set(prompts.map((item) => item.module))], [prompts])
  const visibleStats = useMemo(() => statistics.filter((item) => (
    (moduleFilter === 'all' || item.module === moduleFilter)
    && (scenarioFilter === 'all' || item.scenario_key === scenarioFilter)
  )), [statistics, moduleFilter, scenarioFilter])
  const visibleCalls = useMemo(() => calls.filter((item) => (
    (moduleFilter === 'all' || item.module === moduleFilter)
    && (scenarioFilter === 'all' || item.scenario_key === scenarioFilter)
  )), [calls, moduleFilter, scenarioFilter])
  const totals = useMemo(() => {
    const next = { calls: 0, errors: 0, tokens: 0, duration: 0 }
    for (const item of visibleStats) {
      next.calls += Number(item.call_count)
      next.errors += Number(item.error_count)
      next.tokens += Number(item.total_tokens)
      next.duration += Number(item.average_duration_ms || 0) * Number(item.call_count)
    }
    return { ...next, average: next.calls ? Math.round(next.duration / next.calls) : 0 }
  }, [visibleStats])

  return <section className="usage-console">
    <header className="usage-heading">
      <div><p className="admin-section-label">近 30 天调用观察</p><h2>调用与 token 账本</h2></div>
      <div className="usage-filters">
        <label>模块<select value={moduleFilter} onChange={(event) => { setModuleFilter(event.target.value); setScenarioFilter('all') }}><option value="all">全部模块</option>{modules.map((module) => <option key={module}>{module}</option>)}</select></label>
        <label>场景<select value={scenarioFilter} onChange={(event) => setScenarioFilter(event.target.value)}><option value="all">全部场景</option>{prompts.filter((item) => moduleFilter === 'all' || item.module === moduleFilter).map((item) => <option key={item.scenario_key} value={item.scenario_key}>{item.name}</option>)}</select></label>
      </div>
    </header>
    <div className="usage-metrics">
      <div><Activity size={18} /><span>调用次数</span><strong>{totals.calls}</strong></div>
      <div><Hash size={18} /><span>总 token</span><strong>{totals.tokens.toLocaleString()}</strong></div>
      <div><Clock3 size={18} /><span>平均耗时</span><strong>{totals.average}<small>ms</small></strong></div>
      <div className={totals.errors ? 'has-error' : ''}><TriangleAlert size={18} /><span>错误次数</span><strong>{totals.errors}</strong></div>
    </div>
    <div className="usage-grid">
      <div className="stats-table">
        <h3>按模块 / 场景聚合</h3>
        {visibleStats.length === 0 ? <p className="admin-empty">当前筛选范围还没有调用</p> : visibleStats.map((item) => <div className="stats-row" key={`${item.module}-${item.scenario_key}`}>
          <div><strong>{item.scenario_key}</strong><span>{item.module}</span></div>
          <span>{item.call_count} 次</span><span>{item.total_tokens} tok</span><span className={item.error_count ? 'status-error' : 'status-ok'}>{item.error_count ? `${item.error_count} 错误` : '全部成功'}</span>
        </div>)}
      </div>
      <div className="call-ledger">
        <h3>最近 trace</h3>
        {visibleCalls.length === 0 ? <p className="admin-empty">暂无调用日志</p> : visibleCalls.slice(0, 12).map((item) => <article key={item.id}>
          <i className={item.status} />
          <div><strong>{item.scenario_key}</strong><span>{item.provider} / {item.model}</span></div>
          <div className="trace-meta"><code>{item.trace_id.slice(0, 8)}</code><span>{item.total_tokens ?? '—'} tok · {item.duration_ms}ms</span></div>
          <time>{compactTime(item.created_at)}</time>
          {item.error_message && <p>{item.error_message}</p>}
        </article>)}
      </div>
    </div>
  </section>
}
