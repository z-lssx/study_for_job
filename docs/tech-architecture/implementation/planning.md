# 规则优先的准备评估与任务建议

状态：T014 已实现同步只读业务链路（2026-08-06）。

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

本链路不调用 AI Gateway/LLM，不实现 semantic/synonym recall、embedding、pgvector、RAG、统一评分、多轮 Agent、页面或导出。

## 验证边界与限制

按用户最高优先级规则，本任务没有编写或执行测试、静态语法检查、迁移验证、API/数据库运行态验证、页面/浏览器验收或构建。仅完成数据/状态、排序、事实分类、投递上限、证据读取、显式触发与非范围的逻辑检查；运行时兼容性仍未验证，不能据此宣称 API 或数据库链路已运行通过。
