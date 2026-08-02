import { IntelligencePage } from './IntelligencePage'
import { CanonicalQuestionPanel } from './intelligence/CanonicalQuestionPanel'
import { IntelligenceSearchPanel } from './intelligence/IntelligenceSearchPanel'

export function IntelligenceWorkspace() {
  return <><IntelligencePage /><IntelligenceSearchPanel /><CanonicalQuestionPanel /></>
}
