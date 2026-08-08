import { useEffect, useState } from 'react'
import {
  BookOpenText, Bot, BriefcaseBusiness, ChevronLeft, ChevronRight, ClipboardList,
  Code2, Database, Download, FileSearch, FolderKanban, House, PanelLeftClose,
  PanelLeftOpen, Sparkles, Target,
} from 'lucide-react'
import { AppLink } from '../app/router'

const navigation = [
  { label: '今日重点', items: [['today', '/', '今日重点', House]] },
  { label: '工作流', items: [
    ['intelligence', '/intelligence', '面试情报', FileSearch],
    ['planning', '/planning', '准备策略', Sparkles],
    ['applications', '/applications', '投递记录', BriefcaseBusiness],
  ] },
  { label: '准备轨道', items: [
    ['knowledge', '/knowledge', '知识', BookOpenText],
    ['algorithms', '/algorithms', '算法', Code2],
    ['projects', '/projects', '项目', FolderKanban],
    ['internships', '/internships', '实习', ClipboardList],
  ] },
  { label: '工具', items: [
    ['exports', '/exports', '导出', Download],
    ['ai', '/settings/ai', 'AI 设置', Bot],
  ] },
]

function initialCollapsed() {
  const saved = window.localStorage.getItem('study-for-job.sidebar-collapsed')
  if (saved !== null) return saved === 'true'
  return window.innerWidth < 1180
}

function Sidebar({ route, profile, environment, navigate, collapsed, onToggle }) {
  const isDevelopment = environment === 'development'
  return <aside className={`app-sidebar ${collapsed ? 'collapsed' : ''}`}>
    <div className="sidebar-brand">
      <span className="brand-mark">秋</span>
      {!collapsed && <div><strong>秋招工作台</strong><small>Study for job</small></div>}
    </div>

    <nav className="sidebar-navigation" aria-label="工作台导航">
      {navigation.map((group) => <section key={group.label}>
        {!collapsed && <h2>{group.label}</h2>}
        {group.items.map(([key, to, label, Icon]) => <AppLink
          key={key}
          to={to}
          navigate={navigate}
          className={route.section === key ? 'active' : ''}
          aria-current={route.section === key ? 'page' : undefined}
          aria-label={collapsed ? label : undefined}
          data-tooltip={collapsed ? label : undefined}
        ><Icon size={19} strokeWidth={1.8} />{!collapsed && <span>{label}</span>}</AppLink>)}
      </section>)}
    </nav>

    <AppLink to="/profile" navigate={navigate} className={`sidebar-profile ${route.section === 'profile' ? 'active' : ''}`} aria-label={collapsed ? '目标画像' : undefined} data-tooltip={collapsed ? '目标画像' : undefined}>
      <Target size={19} />
      {!collapsed && <div><small>当前目标</small><strong>{profile?.title || '定义目标画像'}</strong><span>{profile?.focus || '让准备有取舍依据'}</span></div>}
    </AppLink>

    <div className="sidebar-footer">
      <div className={`environment-note ${isDevelopment ? 'development' : 'usage'}`} data-tooltip={collapsed ? (isDevelopment ? '开发数据' : '使用数据') : undefined}>
        <Database size={17} />{!collapsed && <span>{isDevelopment ? '开发数据环境' : '使用数据环境'}</span>}
      </div>
      <button type="button" onClick={onToggle} aria-label={collapsed ? '展开导航' : '收起导航'} data-tooltip={collapsed ? '展开导航' : undefined}>
        {collapsed ? <PanelLeftOpen size={18} /> : <><PanelLeftClose size={18} /><span>收起导航</span></>}
      </button>
    </div>
  </aside>
}

export function PageHeader({ eyebrow, title, description, backTo, breadcrumbs = [], action, navigate }) {
  return <header className="page-heading">
    <div className="page-heading-main">
      {backTo && <button className="page-back" type="button" onClick={() => navigate(backTo)}><ChevronLeft size={18} />返回</button>}
      {breadcrumbs.length > 0 && <nav className="breadcrumbs" aria-label="面包屑">
        {breadcrumbs.map((crumb, index) => <span key={`${crumb.label}-${index}`}>
          {index > 0 && <ChevronRight size={13} />}
          {crumb.to ? <AppLink to={crumb.to} navigate={navigate}>{crumb.label}</AppLink> : <b>{crumb.label}</b>}
        </span>)}
      </nav>}
      {eyebrow && <p>{eyebrow}</p>}
      <h1>{title}</h1>
      {description && <div className="page-description">{description}</div>}
    </div>
    {action && <div className="page-heading-action">{action}</div>}
  </header>
}

export function AppShell({ route, profile, environment, navigate, children }) {
  const [collapsed, setCollapsed] = useState(initialCollapsed)

  useEffect(() => {
    window.localStorage.setItem('study-for-job.sidebar-collapsed', String(collapsed))
  }, [collapsed])

  return <div className={`workspace-shell ${collapsed ? 'sidebar-is-collapsed' : ''}`}>
    <Sidebar route={route} profile={profile} environment={environment} navigate={navigate} collapsed={collapsed} onToggle={() => setCollapsed((value) => !value)} />
    <div className="workspace-main">
      <main id="main-content" className="workspace-content">{children}</main>
      <footer className="workspace-footer"><span>本地优先 · PostgreSQL 唯一事实源</span><span>安静推进，保留证据</span></footer>
    </div>
  </div>
}
