import { useEffect } from 'react'
import { ArrowUpRight, CalendarDays, ChevronRight, Link2, MoveRight, PencilLine, Plus, X } from 'lucide-react'
import { STAGES } from '../constants'

function compactDate(value) {
  if (!value) return '未排期'
  const [, month, day] = value.split('-')
  return `${month}.${day}`
}

function ApplicationRow({ item, onSelect }) {
  const stage = STAGES.find((candidate) => candidate.key === item.stage)
  return <button
    className="application-row"
    onClick={() => onSelect(item.id)}
  >
    <span className={`stage-pill stage-${item.stage}`}>{stage?.label || item.stage}</span>
    <span className="application-identity"><strong>{item.company}</strong><small>{item.role}</small></span>
    <span className="application-date"><CalendarDays size={15} />{compactDate(item.key_date)}</span>
    <span className="application-next"><small>下一步</small><strong>{item.next_action || '补充下一步动作'}</strong></span>
    <ChevronRight size={17} />
  </button>
}

export function ApplicationBoard({ applications, loading, query, stage = 'all', onSelect, onCreate }) {
  const normalizedQuery = query.trim().toLowerCase()
  const filtered = applications.filter((item) => (
    (stage === 'all' || item.stage === stage)
    &&
    `${item.company} ${item.role} ${item.notes || ''} ${item.next_action || ''}`
      .toLowerCase()
      .includes(normalizedQuery)
  ))

  if (loading) return <div className="ledger-skeleton" aria-label="正在同步投递事实"><i /><i /><i /><i /></div>
  if (filtered.length === 0) return <div className="quiet-empty ledger-empty"><strong>{applications.length ? '当前筛选没有记录' : '还没有投递记录'}</strong><p>{applications.length ? '换一个阶段或搜索词继续查看。' : '新增第一条机会，开始维护阶段和下一步动作。'}</p><button className="button-primary" onClick={onCreate}><Plus size={16} />新增投递</button></div>

  return <div className="application-list">{filtered.map((item) => <ApplicationRow key={item.id} item={item} onSelect={onSelect} />)}</div>
}

export function DetailSheet({ item, onClose, onEdit, onStageChange }) {
  useEffect(() => {
    if (!item) return undefined
    const closeOnEscape = (event) => event.key === 'Escape' && onClose()
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [item, onClose])
  if (!item) return null
  const currentStage = STAGES.find((stage) => stage.key === item.stage)

  return <div className="detail-scrim" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
    <aside className="detail-sheet" role="dialog" aria-modal="true" aria-label={`${item.company} 投递详情`}>
      <div className="sheet-topline">
        <span>投递详情 · {currentStage?.label}</span>
        <button className="bare-icon" onClick={onClose} aria-label="关闭详情"><X size={20} /></button>
      </div>
      <div className="sheet-title">
        <p>{item.company}</p>
        <h2>{item.role}</h2>
      </div>

      <div className="stage-switcher" aria-label="调整投递阶段">
        {STAGES.map((stage) => <button
          key={stage.key}
          className={stage.key === item.stage ? 'active' : ''}
          onClick={() => stage.key !== item.stage && onStageChange(item, stage.key)}
          title={`移动到${stage.label}`}
        >
          <span>{stage.index}</span>{stage.short}
        </button>)}
      </div>

      <dl className="fact-grid">
        <div><dt>关键日期</dt><dd>{item.key_date || '未设置'}</dd></div>
        <div><dt>投递渠道</dt><dd>{item.channel || '未记录'}</dd></div>
        <div className="wide"><dt>下一步动作</dt><dd>{item.next_action || '待补充'}</dd></div>
      </dl>

      <div className="sheet-note">
        <span>备注与上下文</span>
        <p>{item.notes || '还没有补充备注。'}</p>
      </div>

      <div className="sheet-actions">
        <button className="action-secondary" onClick={onEdit}><PencilLine size={16} />编辑事实</button>
        {item.url && <a className="action-link" href={item.url} target="_blank" rel="noreferrer">
          <Link2 size={16} />岗位链接<ArrowUpRight size={15} />
        </a>}
      </div>
      <div className="sheet-foot"><MoveRight size={18} />阶段变化会立即写入 PostgreSQL</div>
    </aside>
  </div>
}
