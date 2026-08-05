# 规则优先的准备评估与任务建议

状态：T014 已实现同步只读业务链路，T015 已实现页面主动触发入口（2026-08-06）。

## 解决的问题与调用契约

`POST /api/planning/assessments` 由调用方显式触发，接受：

- `mode`：`daily | weekly | pre_interview`；
- 必填 `as_of_date`：把日期相关规则变成请求输入，避免隐式系统时钟破坏复现性；
- 可选 `target_profile_id`；
- 仅 `pre_interview` 可选 `interview_context.application_id + interview_date`。

接口在 `REPEATABLE READ, READ ONLY` 事务中同步读取当前 PostgreSQL 事实并返回最小结果，避免多次领域查询看到并发写入造成的混合快照，同时从事务层阻止写入。它不持久化报告，不创建 `jobs`、Worker 任务、scheduler、cron、推送或 Agent。固定返回上限为 daily 5 条、weekly 12 条、pre-interview 8 条；响应携带 `planning.rules.v1`、显式触发标记、输入摘要和基于规范化响应的 `snapshot_fingerprint`。

## 规则与稳定排序

结果不生成跨量纲总分。每项使用 `critical | high | medium | low` 稳定档位，档位内按以下键排序：

1. 模式动作顺序；
2. 项目/实习岗位字段与所选目标画像的确定性文本匹配；
3. 各轨道自己的状态顺序；
4. 可信投递弱信号；
5. occurrence 频率档；
6. 稳定 item ID。

投递弱信号和频率均不能改变 priority tier。频率档仅由结构化规范题 occurrence 计数得到，只表示需求信号，不表示掌握度、难度、经历真实性或能力。相同业务事实、相同 `mode/as_of_date/target/interview_context` 因此得到相同顺序和 fingerprint。

## 四轨道状态边界

- 知识：`not_started | learning | familiar | mastered` 原样解释；已掌握且未到维护日期的卡片排除，已掌握到期项只进入 low 档。
- 算法：`not_started | in_progress | solved | revisit` 原样解释；已解决且未到维护日期的题排除，frequency 不覆盖用户状态。
- 项目/实习事实：只有 `confirmation_status=confirmed` 可作为确认事实引用；`draft` 和 `ai_draft` 只产生核实/补证据任务。
- 表达版本：与事实独立，即使确认也只表示表达版本已确认，不自动证明客观能力；缺少确认版本时生成表达核对任务。
- 实习材料：`missing | draft` 可生成准备任务；`ready | verified` 不作为未完成项。
- 显式规范题关联若没有绑定已确认项目/实习事实，只生成考点补证据任务，不把 association 或 occurrence 改写成经历事实。

无目标、轨道无数据、无可操作项、缺少证据和投递上下文不可靠都会返回稳定 warning/evidence status，不为填满列表编造任务。

## 投递弱信号边界

现有 `applications.key_date` 是未标注类型的通用关键日期，不能可靠证明面试日期，规则完全不读取它参与排序。只有同时满足以下条件才建立可信弱信号：

- 调用方在 `pre_interview` 请求中明确给出 application 与 interview date；
- application 当前 stage 为 `interview`；
- interview date 距 `as_of_date` 为 0 至 14 天。

即使可信，信号也只对 application role 与项目 `target_role` 或实习 `role_title` 存在确定性文本匹配的同档位条目提供次级 tie-break；不能抬升档位，不能影响没有显式岗位字段的知识/算法条目。仅有 stage、仅有 `key_date` 或窗口外日期均不启用。

## 来源、证据和正文边界

每项返回稳定 ID、轨道、可读建议、目标、priority tier/order、reason codes/解释、source types、业务 ID、frequency/application 信号、evidence status、最多三条 evidence ref 和限制说明。

结构化情报只读取规范题映射与 occurrence 聚合。只有最终选中的条目才查询展示证据，并在 SQL 中直接截取最多 240 字符的清洗纯文本片段；不会把 `raw_content` 或完整 `cleaned_content` 载入策略服务。证据保留 canonical question/occurrence/evidence span/document/submission/source URL 与字符区间。无回链证据时返回 `no_linked_evidence`，而不是生成依据。

T014 后端链路不调用 AI Gateway/LLM，不实现 semantic/synonym recall、embedding、pgvector、RAG、统一评分、多轮 Agent 或导出；T015 只增加下述人工页面入口，没有改变这些后端边界。

## 页面主动触发与展示契约

桌面工作台的“策略”入口复用既有目标画像与投递列表，只在用户提交表单时调用 `POST /api/planning/assessments`。页面打开、模式切换、日期/画像变更均不会生成策略；没有定时器、轮询、后台任务或推送。`as_of_date` 以可见的本地日期作为初值且允许修改，请求中始终显式传入。

页面支持三种模式和可选目标画像。`pre_interview` 可由用户主动提供现有 application 与明确 `interview_date`；两项不完整时省略整个 `interview_context`，仍请求通用面试前模式。页面不读取、不展示为面试日期，也不自动回填 `applications.key_date`。返回的 `application_context.reliable/reason_code` 决定弱信号状态；界面明确说明该信号最多只做同档经历岗位匹配的次级排序。

建议条目直接按响应 `items` 数组顺序呈现，不在前端重新排序。每项显示 API `order`、priority tier、轨道、建议与目标、reason codes/解释、source types、业务 ID、frequency/application signal、evidence status/refs 和 limitations。frequency 被标记为“结构化需求信号”，不显示或推导统一分数；草稿、AI 起草来源、表达版本、情报关联、无证据内容均保持原类别，不渲染成已确认能力。

规则版本、显式触发标记、输入摘要、排序契约、完整 snapshot fingerprint 与 warnings 保留在结果区。首次进入、API 错误、无可操作项、无证据以及面试弱信号未启用都有独立降级说明；旧结果在新请求失败时保留，用户可调整输入后再次主动提交。

## 验证边界与限制

按用户最高优先级规则，T014/T015 没有编写或执行测试、静态语法检查、迁移验证、API/数据库运行态验证、页面/浏览器验收或构建。T014 仅完成数据/状态、排序、事实分类、投递上限、证据读取、显式触发与非范围的逻辑检查；T015 仅完成提交路径、请求参数、API order 保留、展示文案、降级状态和无自动化的逻辑检查。运行时兼容性与真实视觉行为仍未验证，不能据此宣称 API、数据库或页面链路已运行通过。
