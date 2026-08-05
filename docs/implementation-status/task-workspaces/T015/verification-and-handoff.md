# T015 逻辑检查与交接：页面主动触发的策略工作台

更新时间：2026-08-06

## 完成结果与用户价值

已在既有沉静式桌面工作台增加“策略”入口。用户可选择每日、每周或面试前模式，显式确认规则基准日期、可选目标画像，并在面试前模式中选择是否提供现有投递与明确面试日期。只有点击“生成/刷新本次建议”才调用 T014 assessment API；结果把规则优先档位、API 顺序、建议目标、原因、来源分类、业务关联、需求/投递信号、证据状态/引用、限制、warnings 和快照契约集中呈现。

页面明确说明它是当前事实的规则投影，不是 AI 自动规划器。没有定时生成、后台调度、轮询、推送、多轮 Agent 或持久化报告。

## `@frontend-design` 使用与影响

开始前已完整读取 `C:/Users/zengw/.codex/skills/frontend-design/SKILL.md`。实现选择“克制、精确的编辑型策略工作台”，延续 T013 暖灰/森林绿、宋体标题、细边界、低饱和语义色和受控留白；用“请求控制台 + 规则案卷”区分输入与结果，用序号/档位/证据层级建立辨识度。技术元数据和完整引用按需展开，关键边界直接可见；没有引入图片、泛紫渐变、炫技动效、新设计系统或全站重设计。

## 修改文件与契约范围

- 页面与样式：`src/components/PlanningWorkspace.jsx`、`src/components/planning.css`。
- API client/type 边界：`src/api/planning.js`，以 JSDoc 固定请求 mode/date/可选上下文和主要响应条目字段。
- 壳层与既有数据复用：`src/main.jsx` 增加策略导航和页面切换；`src/hooks/useJobData.js` 暴露已由既有接口读取的全部目标画像；`src/styles.css` 引入局部样式。
- 稳定事实：增量更新 `docs/tech-architecture/implementation/planning.md`；过程、逻辑检查与交接只留在 T015 工作区。
- 未修改后端、迁移、数据库、T014 规则、M004 计划、current/queue/program-status/roadmap 或 M004 handoff。

## 主动触发、模式、日期与面试上下文

- assessment client 只有一个调用点：表单 `onSubmit -> submitAssessment -> createPlanningAssessmentRequest`。组件 `useEffect` 只为已加载画像设置默认选项，不调用 assessment。
- 模式切换、日期/目标变更、页面 mount 均不生成策略；T015 源码不存在 timer、轮询、前端排序或后台触发路径。
- `as_of_date` 使用界面可见的本地日期初值，允许用户修改，并作为必填字段随每次请求传入。
- 目标画像可选；不选择时请求通用建议。
- `pre_interview` 只有在用户勾选上下文且 application/interview date 成对完整时才发送 `interview_context`；不完整时省略整个字段并仍允许请求通用面试前模式。
- 投递下拉只展示公司、岗位和阶段。页面不读取、不显示为面试日期或自动回填 `key_date`，并显式提示其日期类型未标注。
- 返回的 `application_context.reliable/reason_code` 决定弱信号展示；即使启用也只说明同档经历岗位匹配的次级排序，不宣称提升档位或证明面试临近。

## priority、frequency、事实/草稿、证据与 warnings 边界

- 条目直接 `assessment.items.map`，没有 `sort`；展示 API `priority.order` 和 tier，明确 tier 是规则优先档位而非统一能力分。
- frequency 显示 occurrence 数量和“结构化需求信号”，明确只用于同档排序，不是掌握度、难度、经历真实性或能力分数。
- source types 同时显示用户可读标签和原始类型码；已确认事实、待核实草稿、AI 起草来源、表达版本、材料状态、情报关联/频率与目标/投递上下文保持分类。
- reason message/code 直接显示；业务 ID 完整保留，并提供进入对应轨道的关联入口。
- evidence status 直接显示；面经 quote/来源 URL/文档与片段 ID、外部题目 URL、业务参考的 origin/confirmation/source/material 状态均可按需展开。`supports_capability=false` 明确显示为“不单独证明能力”。
- 无证据时证据详情默认展开，显示不能外推能力事实的降级；每项 limitations 始终有可见入口，无额外限制时也说明结果仅代表本次规则快照。
- warnings 独立展示 message/code；规则版本、trigger、目标/日期、input summary、sorting contract、完整 fingerprint 和固定条目上限均保留。

## 空态、错误态与无自动化结论

- 首次进入显示“尚未生成”，不伪装成后台生成中。
- 请求中只显示本次同步读取状态；失败显示 API 错误与再次主动提交提示，已有成功结果不因后续失败被清空。
- 无可操作项明确说明规则不会为填满列表编造建议。
- 无证据、无目标、轨道无数据和面试弱信号未启用均由专门状态或 T014 warning 清楚降级。
- 没有 mount assessment、timer、轮询、scheduler、cron、Worker job、通知、推送、聊天或 Agent。

## 唯一逻辑检查逐项结论

1. 提交触发路径：assessment API 只从表单提交函数调用；各控件 `onChange` 只更新本地状态，结论满足。
2. 请求参数与模式边界：mode/date 必传，目标可选，仅 pre-interview 且上下文完整时传成对字段；不完整可通用请求，结论满足。
3. API order 保留：条目直接按响应数组映射，T015 源码无 `sort`；priority order/tier 原样展示，结论满足。
4. priority/frequency/事实文案：无统一分数字段或推导；规则档位、需求信号、事实/草稿/表达/情报分类均有显式说明，结论满足。
5. 证据/warning/limit：状态、引用、支持能力边界、来源、业务 ID、warnings、limits 均有展示与无证据降级，结论满足。
6. 空态/错误态：首次、加载、错误、无可操作项和弱信号未启用分别处理；错误可通过再次提交恢复，结论满足。
7. 无定时/轮询/Agent：限定 T015 源码检查未发现相关调用或概念实现，结论满足。
8. 桌面风格与可访问性：复用现有 token/按钮/焦点体系，fieldset/legend、label、button、details/summary、`aria-live` 和外链安全属性完整；保持基础窄屏降级，没有移动端专属能力，逻辑结论满足。
9. 非范围：未修改规则后端、迁移/数据库、导出、语义检索/RAG、统一评分、Agent 或 T005 风险，结论满足。

以上均为源码与契约的逻辑检查结论，不是测试、静态检查、构建或运行态验证通过。

## 明确未执行项目

未编写或执行 pytest、单元测试、集成测试、E2E、测试脚本；未执行静态语法检查、类型检查、lint；未执行迁移验证、API 运行态、数据库运行态、页面行为测试、浏览器/截图验收；未运行 `npm run build`、`npm run check` 或任何其他构建。未用编译、类型或静态检查替代并宣称测试通过。

Git scoped diff、敏感信息和工作树检查仅用于提交控制，不作为业务验证证据。

## 稳定事实、遗留风险与 T016 边界

稳定事实唯一入口为 `docs/tech-architecture/implementation/planning.md`，其中追加页面人工触发、面试上下文和解释展示契约；T015 过程与唯一逻辑检查保留在本工作区。

遗留风险：T014/T015 均未做 API/数据库/页面运行态与真实浏览器视觉检查，不能宣称实际请求、响应兼容、长引用布局或交互已运行通过；策略页依赖既有根级目标/投递加载成功；组件卸载后不持久化当前快照，符合 T014 不持久化报告的边界。

T016 可依赖 T015 已提供的人工策略入口、复用画像/投递边界和解释文案，但不得假设 assessment 快照等同底层业务事实导出，不得把 priority/frequency/表达/草稿改写为事实，不得依赖页面定时生成或持久化结果。T016 仍需从其导出契约覆盖底层 MVP 事实与关系。

## Git 与回传

- 不回退或重写 `72cd624`；实际开发基线包含其后的 M004 T015 派发提交 `3384649`。
- T015 实现提交：`2ebc938e29d234d9201705752b2083d3343e8b64`；只包含 T015 直接相关前端、稳定 planning 文档和 T015 工作区。
- 首次 `git push origin main` 被受限网络代理阻止（连接被导向 `127.0.0.1:9`）；随后通过正式提权审批重试时，因外部 GitHub origin 未被安全审查确认为可信目标、且会写入默认 `main`，审批明确拒绝。未改写代理、远端或使用其他路径绕过。
- 提交前限定 T015 路径的敏感模式扫描无命中；暂存文件列表与预期 10 个 T015 文件一致；`git diff --cached --check` 仅作为提交控制无输出，不作为业务验证。
- 实现提交完成后的工作树干净；`main` 相对 `origin/main` 为 ahead 3（包含此前未推送的治理提交及本 T015 实现提交）。本次补充 Git 交接记录将另做仅限这两个 T015 文档的提交，最终 SHA 与工作树状态由结构化回传记录。
