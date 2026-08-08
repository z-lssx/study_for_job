import { useEffect, useMemo, useState } from 'react'
import { ArrowRight, CalendarClock, CircleAlert, Clock3, RefreshCw, Sparkles } from 'lucide-react'
import { requestJson } from '../api'
import { PageHeader } from './AppShell'

const trackMeta = [
  ['知识', '/knowledge', '/api/knowledge/cards', '把题目练成能口述、能追问的回答。'],
  ['算法', '/algorithms', '/api/algorithms', '在外部平台练习，在这里记录卡点与复盘。'],
  ['项目', '/projects', '/api/projects', '围绕真实事实整理证据包与表达版本。'],
  ['实习', '/internships', '/api/internships', '校准职责边界、STAR、材料与量化结果。'],
]

function formatDate(value) {
  if (!value) return '未设置日期'
  return new Intl.DateTimeFormat('zh-CN', { month: 'long', day: 'numeric', weekday: 'short' }).format(new Date(`${value}T00:00:00`))
}

export function TodayPage({ applications, loading, profile, navigate }) {
  const [trackCounts, setTrackCounts] = useState({})
  const [trackError, setTrackError] = useState('')
  const [refreshing, setRefreshing] = useState(false)

  async function loadTrackCounts() {
    setRefreshing(true)
    setTrackError('')
    try {
      const results = await Promise.all(trackMeta.map(([, , endpoint]) => requestJson(endpoint, undefined, '读取准备轨道摘要失败')))
      setTrackCounts(Object.fromEntries(trackMeta.map(([label], index) => [label, Array.isArray(results[index]) ? results[index].length : 0])))
    } catch (caught) {
      setTrackError(caught.message)
    } finally {
      setRefreshing(false)
    }
  }

  useEffect(() => { loadTrackCounts() }, [])

  const milestones = useMemo(() => applications
    .filter((item) => item.key_date && item.key_date >= new Date(Date.now() - new Date().getTimezoneOffset() * 60_000).toISOString().slice(0, 10) && item.stage !== 'closed')
    .sort((a, b) => a.key_date.localeCompare(b.key_date))
    .slice(0, 3), [applications])

  return <div className="today-page page-stack">
    <PageHeader
      eyebrow="今日重点"
      title="先看清现在，再开始推进。"
      description={<><span>{new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' }).format(new Date())}</span>{profile && <span>当前目标：{profile.title}</span>}</>}
      navigate={navigate}
    />

    <section className="focus-hero snap-section">
      <div className="focus-kicker"><Sparkles size={17} /><span>下一步行动</span></div>
      <div className="focus-empty-copy">
        <p>尚无可恢复的策略快照</p>
        <h2>主动生成一次评估，<br />再决定今天最值得做什么。</h2>
        <p>当前策略接口只在页面内返回本次结果，并不持久化。为保护事实可信，首页不会把旧内存、投递日期或虚构任务包装成“今日建议”。</p>
      </div>
      <button className="button-primary" type="button" onClick={() => navigate('/planning')}><Sparkles size={17} />前往生成策略<ArrowRight size={17} /></button>
      <div className="focus-meta"><Clock3 size={15} /><span>生成时间：尚未生成</span><span>候选行动：等待本次策略结果</span></div>
    </section>

    <section className="today-support-grid snap-section">
      <article className="calm-panel milestone-panel">
        <header><div><p>临近节点</p><h2>投递时间线</h2></div><button className="button-quiet" onClick={() => navigate('/applications')}>查看全部<ArrowRight size={15} /></button></header>
        {loading ? <div className="skeleton-list" aria-label="正在加载投递节点"><i /><i /><i /></div> : milestones.length ? <div className="milestone-list">
          {milestones.map((item) => <button key={item.id} onClick={() => navigate(`/applications/${item.id}`)}>
            <span className="milestone-date"><CalendarClock size={16} />{formatDate(item.key_date)}</span>
            <strong>{item.company} · {item.role}</strong>
            <small>{item.next_action || '下一步动作待补充'}</small>
            <ArrowRight size={16} />
          </button>)}
        </div> : <div className="quiet-empty"><CalendarClock size={22} /><strong>没有临近节点</strong><p>投递记录里还没有带日期的进行中事项。</p><button onClick={() => navigate('/applications')}>维护投递事实</button></div>}
      </article>

      <article className="calm-panel track-overview">
        <header><div><p>准备轨道</p><h2>四条线，各自推进</h2></div><button className="icon-button" aria-label="刷新轨道摘要" onClick={loadTrackCounts} disabled={refreshing}><RefreshCw size={16} /></button></header>
        {trackError && <div className="inline-error"><CircleAlert size={16} />{trackError}</div>}
        <div className="track-summary-list">
          {trackMeta.map(([label, to, , description]) => <button key={label} onClick={() => navigate(to)}>
            <span>{label}</span><strong>{trackCounts[label] ?? '—'}</strong><p>{description}</p><ArrowRight size={15} />
          </button>)}
        </div>
      </article>
    </section>
  </div>
}
