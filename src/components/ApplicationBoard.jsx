import { ArrowUpRight, CalendarDays, ChevronRight, Link2, MoveRight, PencilLine, X } from 'lucide-react'
import { STAGES } from '../constants'

function compactDate(value) {
  if (!value) return '未排期'
  const [, month, day] = value.split('-')
  return `${month}.${day}`
}

function ApplicationCard({ item, order, onSelect }) {
  return <button
    className="application-ticket"
    style={{ '--ticket-delay': `${order * 45}ms` }}
    onClick={() => onSelect(item.id)}
  >
    <span className="ticket-index">{String(order + 1).padStart(2, '0')}</span>
    <span className="ticket-company">{item.company}</span>
    <strong>{item.role}</strong>
    <span className="ticket-rule" />
    <span className="ticket-date"><CalendarDays size={13} />{compactDate(item.key_date)}</span>
    <span className="ticket-next">{item.next_action || '补充下一步动作'}<ChevronRight size={14} /></span>
  </button>
}

function EmptyLane({ stage, onCreate }) {
  return <button className="empty-lane" onClick={onCreate}>
    <span>{stage.index}</span>
    <strong>此轨道为空</strong>
    <small>建立一条记录</small>
  </button>
}

export function ApplicationBoard({ applications, loading, query, onSelect, onCreate }) {
  const normalizedQuery = query.trim().toLowerCase()
  const filtered = applications.filter((item) => (
    `${item.company} ${item.role} ${item.notes || ''} ${item.next_action || ''}`
      .toLowerCase()
      .includes(normalizedQuery)
  ))

  if (loading) return <div className="board-loading"><span />正在同步事实轨道</div>

  return <div className="stage-board">
    {STAGES.map((stage) => {
      const stageItems = filtered.filter((item) => item.stage === stage.key)
      return <section className={`stage-lane lane-${stage.tone}`} key={stage.key}>
        <header className="lane-heading">
          <div><span>{stage.index}</span><h3>{stage.label}</h3></div>
          <strong>{String(stageItems.length).padStart(2, '0')}</strong>
        </header>
        <div className="lane-track">
          {stageItems.map((item, index) => <ApplicationCard
            key={item.id}
            item={item}
            order={index}
            onSelect={onSelect}
          />)}
          {stageItems.length === 0 && <EmptyLane stage={stage} onCreate={onCreate} />}
        </div>
      </section>
    })}
  </div>
}

export function DetailSheet({ item, onClose, onEdit, onStageChange }) {
  if (!item) return null
  const currentStage = STAGES.find((stage) => stage.key === item.stage)

  return <div className="detail-scrim" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
    <aside className="detail-sheet" aria-label={`${item.company} 投递详情`}>
      <div className="sheet-topline">
        <span>APPLICATION / {currentStage?.index}</span>
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
        <span>NOTE / CONTEXT</span>
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
