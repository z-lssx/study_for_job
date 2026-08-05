import React, { useEffect, useState } from 'react'
import { AlertTriangle, ArrowUpRight, CalendarDays, CheckCircle2, ClipboardList, RefreshCw, ShieldCheck } from 'lucide-react'
import { createPlanningAssessmentRequest } from '../api/planning'
import './planning.css'

const modes = [
  ['daily', '每日', '聚焦今天可推进的少量动作'],
  ['weekly', '每周', '审视本周跨轨道准备缺口'],
  ['pre_interview', '面试前', '优先核对表达、事实与材料'],
]

const trackLabels = { knowledge: '知识', algorithm: '算法', project: '项目', internship: '实习' }
const trackViews = { knowledge: 'knowledge', algorithm: 'algorithms', project: 'projects', internship: 'internships' }
const tierLabels = { critical: '关键', high: '高', medium: '中', low: '低' }
const evidenceLabels = {
  linked_interview_evidence: '已回链面经证据',
  confirmed_business_fact: '包含已确认业务事实',
  reference_only_or_unverified: '仅参考或尚未核实',
  no_linked_evidence: '没有可回链证据',
}
const sourceLabels = {
  user_mastery_state: '用户维护的掌握状态',
  user_algorithm_state: '用户维护的算法状态',
  confirmed_fact: '已确认经历事实',
  unverified_draft: '待核实草稿',
  ai_draft_origin: 'AI 起草来源',
  missing_confirmed_fact: '缺少已确认事实',
  expression_version: '表达版本',
  missing_expression_version: '缺少确认表达版本',
  user_material_state: '用户维护的材料状态',
  structured_intelligence_link: '结构化情报关联',
  structured_intelligence_frequency: '结构化需求频率',
  intelligence_suggestion_origin: '情报建议来源',
  target_profile: '目标画像',
  reliable_application_context: '可信临近面试上下文',
}
const businessLabels = {
  knowledge_card_id: '知识卡片', algorithm_problem_id: '算法题', canonical_question_id: '规范题',
  project_id: '项目', internship_id: '实习', fact_ids: '事实', expression_version_ids: '表达版本',
  internship_material_id: '实习材料', intelligence_link_id: '情报关联', fact_id: '关联事实',
}
const tieBreakLabels = {
  priority_tier: '优先档位', mode_action_rank: '模式动作顺序', explicit_target_role_match: '显式目标岗位匹配',
  track_state_rank: '轨道状态', bounded_application_rank: '有界投递弱信号', frequency_band: '需求频率档', stable_item_id: '稳定条目 ID',
}

function localDateValue() {
  const now = new Date()
  const offset = now.getTimezoneOffset() * 60_000
  return new Date(now.getTime() - offset).toISOString().slice(0, 10)
}

function ValueList({ values }) {
  const list = Array.isArray(values) ? values : [values]
  return <span>{list.filter(Boolean).join('、') || '—'}</span>
}

function EvidenceRef({ reference }) {
  const label = reference.kind?.startsWith('interview_') ? '面经证据' : '业务参考'
  const metadata = [
    reference.origin && `来源类型：${reference.origin}`,
    reference.confirmation_status && `确认状态：${reference.confirmation_status}`,
    reference.source_kind && `事实来源：${reference.source_kind}`,
    reference.preparation_status && `材料状态：${reference.preparation_status}`,
    reference.locator && `材料位置：${reference.locator}`,
  ].filter(Boolean)
  return <li className="planning-evidence-ref">
    <div><strong>{label}</strong><span>{reference.supports_capability ? '可支持已确认事实' : '不单独证明能力'}</span></div>
    {reference.quote && <blockquote>{reference.quote}</blockquote>}
    {reference.source_reference && <p>{reference.source_reference}</p>}
    {metadata.length > 0 && <p className="planning-ref-meta">{metadata.join(' · ')}</p>}
    <p className="planning-ref-ids">
      {reference.document_id && <>文档 {reference.document_id} · </>}
      {reference.submission_id && <>提交 {reference.submission_id} · </>}
      {reference.evidence_span_id && <>片段 {reference.evidence_span_id}</>}
      {!reference.evidence_span_id && reference.id && <>记录 {reference.id}</>}
    </p>
    {reference.source_url && <a href={reference.source_url} target="_blank" rel="noreferrer">打开原始来源<ArrowUpRight size={13} /></a>}
    {reference.url && <a href={reference.url} target="_blank" rel="noreferrer">打开外部题目<ArrowUpRight size={13} /></a>}
  </li>
}

function PlanningItem({ item, onOpenTrack }) {
  const limitations = item.limitations || []
  return <article className={`planning-item tier-${item.priority.tier}`}>
    <header className="planning-item-head">
      <span className="planning-order">#{String(item.priority.order).padStart(2, '0')}</span>
      <span className="planning-track">{trackLabels[item.track] || item.track}</span>
      <span className="planning-tier">{tierLabels[item.priority.tier] || item.priority.tier}档</span>
      <button type="button" onClick={() => onOpenTrack(trackViews[item.track])}>进入{trackLabels[item.track] || item.track}轨道<ArrowUpRight size={13} /></button>
    </header>
    <div className="planning-item-main">
      <div>
        <p className="planning-item-id">{item.id}</p>
        <h3>{item.recommendation}</h3>
        <p className="planning-target">建议目标：<strong>{item.target.entity_label}</strong><span>画像：{item.target.profile_label}</span></p>
      </div>
      <dl className="planning-signal-grid">
        <div><dt>priority tier</dt><dd>{tierLabels[item.priority.tier] || item.priority.tier}档 · API 顺序 {item.priority.order}</dd></div>
        <div><dt>结构化需求信号</dt><dd>{item.frequency_signal ? `${item.frequency_signal.occurrence_count} 次 occurrence` : '本条未使用'}</dd><small>仅用于同档排序，不是能力分数。</small></div>
        <div><dt>投递弱信号</dt><dd>{item.application_signal?.applied ? '已应用' : '未应用'}</dd><small>{item.application_signal?.effect === 'same-tier tie-break only' ? '只影响同档岗位匹配次序。' : '没有改变本条排序。'}{item.application_signal?.application_id ? ` 投递 ${item.application_signal.application_id}` : ''}</small></div>
        <div><dt>证据状态</dt><dd>{evidenceLabels[item.evidence_status] || item.evidence_status}</dd></div>
      </dl>
    </div>

    <div className="planning-explanation-grid">
      <section>
        <h4>为什么现在做</h4>
        <ol>{item.reasons.map((reason) => <li key={reason.code}><p>{reason.message}</p><code>{reason.code}</code></li>)}</ol>
      </section>
      <section>
        <h4>来源分类</h4>
        <ul className="planning-source-list">{item.source_types.map((source) => <li key={source}><strong>{sourceLabels[source] || source}</strong><code>{source}</code></li>)}</ul>
        <p className="planning-boundary-note">草稿、表达版本、情报关联与频率不会被写成已确认能力。</p>
      </section>
    </div>

    <details className="planning-details" open={item.evidence_status === 'no_linked_evidence'}>
      <summary>证据、限制与业务关联 <span>{item.evidence_refs.length} 条引用</span></summary>
      <div className="planning-detail-body">
        <section>
          <h4>证据引用</h4>
          {item.evidence_refs.length ? <ul className="planning-evidence-list">{item.evidence_refs.map((reference, index) => <EvidenceRef reference={reference} key={`${reference.kind}-${reference.id || reference.evidence_span_id || index}`} />)}</ul> : <p className="planning-no-evidence">没有可回链证据。本建议只依据当前业务状态，不能外推能力事实。</p>}
        </section>
        <section>
          <h4>限制</h4>
          <ul className="planning-limit-list">{limitations.length ? limitations.map((limit) => <li key={limit}>{limit}</li>) : <li>没有额外条目限制；结果仍只代表本次规则快照。</li>}</ul>
          <h4>业务 ID</h4>
          <dl className="planning-business-ids">{Object.entries(item.business_ids).map(([key, value]) => <div key={key}><dt>{businessLabels[key] || key}</dt><dd><ValueList values={value} /></dd></div>)}</dl>
        </section>
      </div>
    </details>
  </article>
}

export function PlanningWorkspace({ profiles, applications, onOpenTrack }) {
  const [mode, setMode] = useState('daily')
  const [asOfDate, setAsOfDate] = useState(localDateValue)
  const [targetProfileId, setTargetProfileId] = useState('')
  const [useInterviewContext, setUseInterviewContext] = useState(false)
  const [applicationId, setApplicationId] = useState('')
  const [interviewDate, setInterviewDate] = useState('')
  const [assessment, setAssessment] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    setTargetProfileId((current) => current || profiles[0]?.id || '')
  }, [profiles])

  const interviewContextComplete = Boolean(applicationId && interviewDate)

  async function submitAssessment(event) {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const payload = { mode, as_of_date: asOfDate }
      if (targetProfileId) payload.target_profile_id = targetProfileId
      if (mode === 'pre_interview' && useInterviewContext && interviewContextComplete) {
        payload.interview_context = { application_id: applicationId, interview_date: interviewDate }
      }
      setAssessment(await createPlanningAssessmentRequest(payload))
    } catch (caught) {
      setError(caught.message)
    } finally {
      setLoading(false)
    }
  }

  const context = assessment?.application_context

  return <section className="planning-workspace">
    <header className="planning-heading">
      <div><p className="section-code">PLANNING / EXPLICIT REQUEST</p><h2>把下一步排清楚</h2><p>一次点击生成一次规则快照。这里不是 AI 自动规划器，也不会定时刷新、推送或在后台继续运行。</p></div>
      <span className="planning-rule-badge"><ShieldCheck size={16} />规则优先 · 可解释</span>
    </header>

    <div className="planning-layout">
      <aside className="planning-control">
        <form onSubmit={submitAssessment}>
          <fieldset className="planning-mode-field">
            <legend>建议模式</legend>
            {modes.map(([value, label, description]) => <label className={mode === value ? 'selected' : ''} key={value}>
              <input type="radio" name="planning-mode" value={value} checked={mode === value} onChange={() => setMode(value)} />
              <strong>{label}</strong><span>{description}</span>
            </label>)}
          </fieldset>

          <label className="planning-field"><span>规则基准日期</span><input type="date" value={asOfDate} onChange={(event) => setAsOfDate(event.target.value)} required /><small>日期显式进入请求；不会在后台使用隐藏时钟循环生成。</small></label>
          <label className="planning-field"><span>目标画像（可选）</span><select value={targetProfileId} onChange={(event) => setTargetProfileId(event.target.value)}><option value="">不指定，生成通用建议</option>{profiles.map((profile) => <option value={profile.id} key={profile.id}>{profile.title}{profile.focus ? ` · ${profile.focus}` : ''}</option>)}</select><small>只用于确定性的岗位文本匹配，不生成岗位能力分数。</small></label>

          {mode === 'pre_interview' && <div className="planning-interview-context">
            <label className="planning-context-toggle"><input type="checkbox" checked={useInterviewContext} onChange={(event) => setUseInterviewContext(event.target.checked)} /><span><strong>提供面试上下文</strong><small>可选；留空仍会生成通用面试前建议。</small></span></label>
            {useInterviewContext && <>
              <label className="planning-field"><span>现有投递</span><select value={applicationId} onChange={(event) => setApplicationId(event.target.value)}><option value="">暂不选择</option>{applications.map((application) => <option value={application.id} key={application.id}>{application.company} · {application.role}（{application.stage}）</option>)}</select></label>
              <label className="planning-field"><span>明确的面试日期</span><input type="date" value={interviewDate} onChange={(event) => setInterviewDate(event.target.value)} /></label>
              <p className={`planning-context-status ${interviewContextComplete ? 'ready' : ''}`}>{interviewContextComplete ? '将提交这组上下文；是否形成弱信号仍由阶段、日期窗口和岗位匹配规则判断。' : '上下文不完整，本次会省略 interview_context 并按通用面试前模式请求。'}</p>
            </>}
            <p className="planning-key-date-note">投递记录的 key_date 未标注日期类型，本页不会读取或自动回填为面试日期。</p>
          </div>}

          <button className="action-primary planning-submit" type="submit" disabled={loading}>{loading ? <><RefreshCw size={16} className="planning-spinner" />生成中</> : <><ClipboardList size={16} />{assessment ? '刷新本次建议' : '生成本次建议'}</>}</button>
          <p className="planning-submit-note">只有点击此按钮才会请求 assessment API；切换模式、日期和目标不会自动请求。</p>
        </form>
      </aside>

      <div className="planning-results" aria-live="polite">
        {error && <div className="planning-error"><AlertTriangle size={18} /><div><strong>本次建议未生成</strong><p>{error}</p><small>可调整输入后再次点击“生成本次建议”。既有结果不会被改写。</small></div></div>}
        {!assessment && !loading && !error && <div className="planning-pristine"><CalendarDays size={25} /><p className="section-code">WAITING FOR YOUR REQUEST</p><h3>尚未生成策略快照</h3><p>先确认模式与日期，再主动生成。页面不会在打开时、切换选项时或后台自动请求。</p></div>}
        {loading && <div className="planning-loading"><RefreshCw size={20} className="planning-spinner" /><span>正在读取当前事实并计算规则顺序…</span></div>}

        {assessment && !loading && <>
          <section className="planning-snapshot">
            <div><p className="section-code">RULE SNAPSHOT / {assessment.rule_version}</p><h3>{modes.find(([value]) => value === assessment.mode)?.[1]}建议</h3><p>{assessment.as_of_date} · {assessment.target_profile?.title || '通用目标'} · 返回 {assessment.input_summary.returned_count} / 候选 {assessment.input_summary.candidate_count}</p></div>
            <span><CheckCircle2 size={16} />{assessment.trigger === 'explicit_request' ? '用户主动触发' : assessment.trigger}</span>
          </section>

          <section className={`planning-context-result ${context?.reliable ? 'reliable' : ''}`}>
            <strong>{context?.reliable ? '临近面试弱信号已启用' : '临近面试弱信号未启用'}</strong>
            <div><p>{context?.reliable ? '仅用于同档位、经历岗位匹配条目的次级排序；不会提升 priority tier。' : '当前结果未使用投递信息改变排序。pre_interview 模式本身不证明存在临近面试。'}</p>{context?.requested && <small>{context.company || '未知公司'} · {context.role || '未知岗位'} · 阶段 {context.stage || '未知'} · 面试日期 {context.interview_date}{Number.isInteger(context.days_until_interview) ? ` · 相差 ${context.days_until_interview} 天` : ''}</small>}</div>
            <code>{context?.reason_code}</code>
          </section>

          {assessment.warnings.length > 0 && <section className="planning-warnings"><h4>边界与提醒</h4><ul>{assessment.warnings.map((warning) => <li key={warning.code}><AlertTriangle size={14} /><div><p>{warning.message}</p><code>{warning.code}</code></div></li>)}</ul></section>}

          <p className="planning-order-contract"><strong>阅读方式</strong> priority tier 是规则优先档位，不是统一能力分；下列条目严格沿用 API order，没有在页面重排。frequency 只表示结构化需求信号。</p>

          {assessment.items.length ? <div className="planning-item-list">{assessment.items.map((item) => <PlanningItem item={item} onOpenTrack={onOpenTrack} key={item.id} />)}</div> : <div className="planning-empty"><h3>当前没有可操作项</h3><p>规则不会为填满列表编造建议。可补充轨道事实、选择目标画像，或在合适日期再次主动生成。</p></div>}

          <details className="planning-snapshot-details">
            <summary>查看规则排序与输入摘要</summary>
            <div className="planning-contract-grid">
              <section><h4>排序契约</h4><p>档位顺序：{assessment.sorting_contract.priority_tiers.map((tier) => tierLabels[tier] || tier).join(' → ')}</p><ol>{assessment.sorting_contract.tie_break.map((key) => <li key={key}>{tieBreakLabels[key] || key}<code>{key}</code></li>)}</ol><p>{assessment.sorting_contract.application_effect_cap}</p><p>{assessment.sorting_contract.frequency_meaning}</p></section>
              <section><h4>输入摘要</h4><dl>{Object.entries(assessment.input_summary.scanned_by_track).map(([track, count]) => <div key={track}><dt>{trackLabels[track] || track}扫描</dt><dd>{count}</dd></div>)}{Object.entries(assessment.input_summary.excluded_completed_by_track).map(([track, count]) => <div key={`excluded-${track}`}><dt>{trackLabels[track] || track}排除已完成</dt><dd>{count}</dd></div>)}</dl><p>单次上限 {assessment.sorting_contract.item_limit} 条。</p></section>
            </div>
            <p className="planning-fingerprint"><span>snapshot fingerprint</span><code>{assessment.snapshot_fingerprint}</code></p>
          </details>
        </>}
      </div>
    </div>
  </section>
}
