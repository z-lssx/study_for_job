import { IntelligenceDetailPage, IntelligencePage } from './IntelligencePage'
import { CanonicalQuestionPanel } from './intelligence/CanonicalQuestionPanel'
import { IntelligenceSearchPanel } from './intelligence/IntelligenceSearchPanel'
import { PageHeader } from './AppShell'

export function IntelligenceWorkspace({ route, navigate }) {
  if (route.name === 'intelligence-detail') {
    return <IntelligenceDetailPage submissionId={route.id} navigate={navigate} />
  }

  if (route.name === 'intelligence-search') {
    return <div className="page-stack">
      <PageHeader
        eyebrow="面试情报 / 证据检索"
        title="从原始证据中寻找问题"
        description="精确术语、结构化过滤与词法候选共同工作；每条结果都保留原文回链。"
        backTo="/intelligence"
        breadcrumbs={[{ label: '面试情报', to: '/intelligence' }, { label: '证据检索' }]}
        navigate={navigate}
      />
      <IntelligenceSearchPanel navigate={navigate} />
    </div>
  }

  if (route.name === 'intelligence-questions') {
    return <div className="page-stack">
      <PageHeader
        eyebrow="面试情报 / 规范题"
        title="规范题与出现频率"
        description="计数来自不可覆盖的出现记录；人工合并、拆分和改映射不会改写原始面经事实。"
        backTo="/intelligence"
        breadcrumbs={[{ label: '面试情报', to: '/intelligence' }, { label: '规范题' }]}
        navigate={navigate}
      />
      <CanonicalQuestionPanel selectedId={route.id} navigate={navigate} />
    </div>
  }

  return <IntelligencePage navigate={navigate} />
}
