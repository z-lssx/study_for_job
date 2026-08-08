import { CircleAlert, Home } from 'lucide-react'
import { routeFromPath, useAppRouter } from './router'
import { useJobData } from '../hooks/useJobData'
import { AppShell } from '../components/AppShell'
import { TodayPage } from '../components/TodayPage'
import { ProfilePage } from '../components/ProfilePage'
import { ApplicationsPage } from '../components/ApplicationsPage'
import { AiAdminPage } from '../components/AiAdminPage'
import { IntelligenceWorkspace } from '../components/IntelligenceWorkspace'
import { KnowledgeWorkspace } from '../components/KnowledgeWorkspace'
import { AlgorithmWorkspace } from '../components/AlgorithmWorkspace'
import { ProjectsWorkspace } from '../components/ProjectsWorkspace'
import { InternshipsWorkspace } from '../components/InternshipsWorkspace'
import { ProjectCreatePage } from '../components/ProjectCreatePage'
import { InternshipCreatePage } from '../components/InternshipCreatePage'
import { PlanningWorkspace } from '../components/PlanningWorkspace'
import { ExportWorkspace } from '../components/ExportWorkspace'

const trackPaths = {
  knowledge: '/knowledge', algorithms: '/algorithms', projects: '/projects', internships: '/internships',
}

function NotFound({ navigate }) {
  return <section className="not-found calm-panel"><CircleAlert size={28} /><p>页面不存在</p><h1>这个地址没有对应的工作区。</h1><button className="button-primary" onClick={() => navigate('/')}><Home size={17} />返回今日重点</button></section>
}

export function App() {
  const router = useAppRouter()
  const route = routeFromPath(router.pathname)
  const jobData = useJobData()
  const navigate = router.navigate

  let page
  if (route.name === 'today') page = <TodayPage applications={jobData.applications} loading={jobData.loading} profile={jobData.profile} navigate={navigate} />
  else if (route.name === 'profile') page = <ProfilePage profile={jobData.profile} loading={jobData.loading} onSave={jobData.saveProfile} navigate={navigate} />
  else if (route.name === 'applications') page = <ApplicationsPage applications={jobData.applications} loading={jobData.loading} error={jobData.error} selectedId={route.id} navigate={navigate} onSave={jobData.saveApplication} onPatch={jobData.patchApplication} onReload={jobData.loadData} />
  else if (route.section === 'intelligence') page = <IntelligenceWorkspace route={route} navigate={navigate} />
  else if (route.name === 'planning') page = <PlanningWorkspace profiles={jobData.profiles} applications={jobData.applications} onOpenTrack={(track) => navigate(trackPaths[track] || `/${track}`)} navigate={navigate} />
  else if (route.section === 'knowledge') page = <KnowledgeWorkspace selectedId={route.id} navigate={navigate} />
  else if (route.section === 'algorithms') page = <AlgorithmWorkspace selectedId={route.id} navigate={navigate} />
  else if (route.name === 'project-new') page = <ProjectCreatePage navigate={navigate} />
  else if (route.section === 'projects') page = <ProjectsWorkspace selectedId={route.id} mode={route.mode} navigate={navigate} />
  else if (route.name === 'internship-new') page = <InternshipCreatePage navigate={navigate} />
  else if (route.section === 'internships') page = <InternshipsWorkspace selectedId={route.id} mode={route.mode} navigate={navigate} />
  else if (route.name === 'exports') page = <ExportWorkspace navigate={navigate} />
  else if (route.name === 'ai') page = <AiAdminPage navigate={navigate} />
  else page = <NotFound navigate={navigate} />

  return <AppShell route={route} profile={jobData.profile} environment={jobData.environment} navigate={navigate}>{page}</AppShell>
}
