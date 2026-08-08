import { useState } from 'react'
import { Bot, CircleAlert, FlaskConical, RefreshCw, ShieldCheck } from 'lucide-react'
import { useAiAdminData } from '../hooks/useAiAdminData'
import { PromptPanel } from './ai-admin/PromptPanel'
import { UsagePanel } from './ai-admin/UsagePanel'
import { PageHeader } from './AppShell'

export function AiAdminPage({ navigate }) {
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

  return <div className="ai-admin-page page-stack">
    <PageHeader
      eyebrow="AI 设置"
      title="关键配置与调用账本"
      description="这里只管理少量代码批准的 Prompt 与用量事实；Schema、安全规则、工具权限和工作流仍由代码控制。"
      navigate={navigate}
    />
    <section className="runtime-card">
      <div className="runtime-summary">
        <div className="runtime-icon"><Bot size={25} /></div>
        <div><span>当前 Provider</span><h2>{runtime?.provider || '读取中'}</h2><code>{runtime?.model || '—'}</code></div>
        <p><ShieldCheck size={15} />密钥仅从服务端环境读取</p>
      </div>
      <div className="runtime-diagnostic">
        <strong>受限诊断</strong><span>只验证固定 Gateway、token 与 trace 链路，不是聊天入口。</span>
        <div className="diagnostic-actions">
          <button disabled={diagnosing || loading} onClick={() => diagnose(false)}><FlaskConical size={15} />成功诊断</button>
          {runtime?.supports_failure_simulation && <button className="failure" disabled={diagnosing || loading} onClick={() => diagnose(true)}>失败诊断</button>}
        </div>
        {diagnosticMessage && <small className="diagnostic-ok">{diagnosticMessage}</small>}
        {diagnosticError && <small className="diagnostic-error">{diagnosticError}</small>}
      </div>
    </section>

    {error && <div className="error-ribbon"><CircleAlert size={17} /><span>{error}</span><button onClick={loadData}>重新连接</button></div>}
    <section className="admin-config-section">
      <div className="admin-toolbar"><div><span>Prompt 配置</span><strong>{prompts.length} 个代码批准场景</strong></div><button onClick={loadData} disabled={loading}><RefreshCw size={15} />{loading ? '同步中' : '刷新配置与日志'}</button></div>
      <PromptPanel prompts={prompts} onSave={savePrompt} />
    </section>
    <details className="admin-usage-disclosure">
      <summary><span>调用与 token 账本</span><small>按模块与场景查看 30 天聚合及最近 trace</small></summary>
      <UsagePanel prompts={prompts} statistics={statistics} calls={calls} />
    </details>
  </div>
}
