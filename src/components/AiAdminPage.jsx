import { useState } from 'react'
import { Bot, CircleAlert, FlaskConical, RefreshCw, ShieldCheck } from 'lucide-react'
import { useAiAdminData } from '../hooks/useAiAdminData'
import { PromptPanel } from './ai-admin/PromptPanel'
import { UsagePanel } from './ai-admin/UsagePanel'

export function AiAdminPage() {
  const { runtime, prompts, statistics, calls, loading, error, loadData, savePrompt, runDiagnostic } = useAiAdminData()
  const [diagnosing, setDiagnosing] = useState(false)
  const [diagnosticMessage, setDiagnosticMessage] = useState('')
  const [diagnosticError, setDiagnosticError] = useState('')

  async function diagnose(simulateFailure) {
    setDiagnosing(true)
    setDiagnosticMessage('')
    setDiagnosticError('')
    try {
      const result = await runDiagnostic(simulateFailure)
      setDiagnosticMessage(`链路成功 · ${result.total_tokens ?? '—'} token · trace ${result.trace_id.slice(0, 8)}`)
    } catch (caught) {
      setDiagnosticError(caught.message)
    } finally {
      setDiagnosing(false)
    }
  }

  return <div className="ai-admin-page">
    <section className="admin-hero">
      <div>
        <p className="section-code">AI CONTROL ROOM / LOCAL FIRST</p>
        <h1>让模型可替换，<br /><em>让每次调用可追溯。</em></h1>
        <p>这里只管理少量关键 prompt 与用量事实。Schema、安全规则、工具权限和工作流仍由代码控制。</p>
      </div>
      <aside className="runtime-card">
        <div className="runtime-icon"><Bot size={25} /></div>
        <span>ACTIVE PROVIDER</span>
        <h2>{runtime?.provider || '读取中'}</h2>
        <code>{runtime?.model || '—'}</code>
        <p><ShieldCheck size={15} />密钥仅从服务端环境读取</p>
        <div className="diagnostic-actions">
          <button disabled={diagnosing || loading} onClick={() => diagnose(false)}><FlaskConical size={15} />成功诊断</button>
          {runtime?.supports_failure_simulation && <button className="failure" disabled={diagnosing || loading} onClick={() => diagnose(true)}>失败诊断</button>}
        </div>
        {diagnosticMessage && <small className="diagnostic-ok">{diagnosticMessage}</small>}
        {diagnosticError && <small className="diagnostic-error">{diagnosticError}</small>}
      </aside>
    </section>

    {error && <div className="error-ribbon"><CircleAlert size={17} /><span>{error}</span><button onClick={loadData}>重新连接</button></div>}
    <div className="admin-toolbar"><span>{prompts.length} 个代码批准场景</span><button onClick={loadData} disabled={loading}><RefreshCw size={15} />{loading ? '同步中' : '刷新配置与日志'}</button></div>
    <PromptPanel prompts={prompts} onSave={savePrompt} />
    <UsagePanel prompts={prompts} statistics={statistics} calls={calls} />
  </div>
}
