import { useState } from 'react'
import { GitMerge, Scissors } from 'lucide-react'

export function OccurrenceCorrection({ question, occurrence, questions, onSplit, onRemap }) {
  const [splitText, setSplitText] = useState('')
  const [targetId, setTargetId] = useState('')
  const [busy, setBusy] = useState(false)

  async function run(action) {
    setBusy(true)
    try {
      if (action === 'split') {
        await onSplit(question.id, occurrence.id, splitText.trim())
        setSplitText('')
      } else {
        await onRemap(occurrence.id, targetId)
        setTargetId('')
      }
    } finally { setBusy(false) }
  }

  const targets = questions.filter((item) => item.id !== question.id)
  return <details className="occurrence-correction">
    <summary>人工修正映射 · 原始出现事实保持不变</summary>
    <div>
      <label><span>拆成新规范题</span><input value={splitText} onChange={(event) => setSplitText(event.target.value)} placeholder="输入新的规范题文本" /></label>
      <button disabled={busy || !splitText.trim()} onClick={() => run('split')}><Scissors size={13} />拆分</button>
    </div>
    <div>
      <label><span>映射为已有等价题</span><select value={targetId} onChange={(event) => setTargetId(event.target.value)}>
        <option value="">选择目标规范题</option>
        {targets.map((item) => <option key={item.id} value={item.id}>{item.canonical_text}</option>)}
      </select></label>
      <button disabled={busy || !targetId} onClick={() => run('remap')}><GitMerge size={13} />改映射</button>
    </div>
  </details>
}
