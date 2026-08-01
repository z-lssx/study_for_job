# T004：PostgreSQL 任务队列与 Worker 最小可靠机制

状态：已完成（本地 PostgreSQL、Compose、并发领取、租约恢复、失败退避和双数据库隔离验证通过）

## 任务提示词

Skills: @build-web-apps:supabase-postgres-best-practices

你负责实现阶段一最后一条开发链路：在已有 FastAPI、PostgreSQL、迁移和 AI Gateway 基础上，建立“页面/API 主动创建任务 → PostgreSQL 队列 → 独立 Worker 领取执行 → 状态与失败原因可查询 → 失败延迟重试”的最小可靠机制。开始前必须完整读取并遵守 `build-web-apps:supabase-postgres-best-practices`（Postgres 建模、并发与性能最佳实践）的 `SKILL.md`。

### 任务目标

- 使用 PostgreSQL 作为唯一任务事实源，不引入 Redis、Celery、独立 Scheduler 或其他消息中间件。
- 建立独立 Worker 进程，使用安全并发领取机制执行任务，并支持失败重试、退避、租约恢复或等价的崩溃恢复机制。
- 提供受限管理 API 创建和查询任务，使用固定诊断任务验证完整生命周期，同时为 T005 面经抓取/分析任务预留稳定扩展边界。
- 保持 `next_run_at`/等价时间字段只服务失败重试和退避，不实现面向用户的定时任务或定时推送。

### 必读规则和文档

- 根目录 `AGENTS.md`、`README.md`，以及相关子目录最近的 `AGENTS.md`。
- `docs/project-governance/AGENTS.md`。
- `docs/product-overview/README.md`、`docs/decision-log/README.md`。
- `docs/tech-architecture/AGENTS.md`、`README.md`、`overview.md`、`decisions/README.md`、`implementation/README.md`，以及 T003 新增的 AI Gateway 实现文档。
- `docs/implementation-status/AGENTS.md`、`README.md`、`current.md`、`roadmap.md`、`queue.md`。
- `docs/implementation-status/management-plans/M001-phase-one.md`。
- `docs/implementation-status/tasks/T003-ai-gateway-prompt-token.md`、本任务文件、`task-workspaces/README.md` 和 `task-workspaces/T004/README.md`。

### 范围

- 读取规则后、修改代码前创建 `task-workspaces/T004/plan.md`；开发过程中维护 `implementation.md`；完成后创建 `verification-and-handoff.md`。
- 新增安全的增量迁移，覆盖任务状态、类型、payload、结果摘要、优先级、尝试次数、最大尝试、可执行/重试时间、领取者/租约、错误信息、幂等键和审计时间等必要事实；具体拆表由你自主决定。
- Worker 使用 PostgreSQL 原子领取任务，优先采用 `FOR UPDATE SKIP LOCKED` 或等价可靠机制；多个 Worker 不应重复执行同一领取周期的任务。
- 实现任务注册/处理器边界，未知任务类型必须安全失败；业务模块以后可以注册面经抓取、抽取和聚合处理器，但本任务不实现这些业务。
- 实现成功、业务失败、可重试失败、达到最大尝试、租约超时恢复、优雅停止和错误记录的最小机制。
- 将 Worker 加入本地 Compose；开发环境与 usage 环境连接各自数据库，不能跨库领取或写入。
- 提供受限 API 用于创建固定诊断任务、查看任务列表/详情和在允许条件下手动重试失败任务；不得允许任意代码、任意 URL 或自由 prompt 执行。
- 可复用 T003 的 fake Gateway 诊断作为一种固定处理器来验证异步调用与 AI 日志关联，但不得发起通用聊天或真实付费调用。

### 非范围

- 不实现公开面经抓取、正文解析、题目抽取、embedding、RAG、频率统计或任何阶段二业务。
- 不实现面向用户的定时任务、Cron、周期调度、定时推送或自动采集。
- 不引入 Redis、Celery、RabbitMQ、Kafka、独立 Scheduler、微服务或 Kubernetes。
- 不新增前端视觉设计或移动端能力；本任务以后台机制和受限 API 为主，因此不绑定 `frontend-design`。
- 不调用 ImageGen，不执行项目规则禁止的 `npm run build`。

### 已知事实

- T001 已建立开发库 `study_for_job_dev` 与使用库 `study_for_job`，两库共用迁移/模型但数据隔离；只有开发库加载样例数据。
- T003 已建立自有 AI Gateway、fake/DeepSeek-compatible provider、prompt 配置和调用日志；SophNet 收尾提交为 `54af16b`，工作树已确认干净。
- `54af16b` 之后，总管已新增/更新治理规则、M001 阶段规划、当前状态、队列和 T004 任务/工作区文档；这些文档改动是已授权的 T004 基线，不是无关用户改动。实现前先确认其范围，最终可与 T004 一并提交；若发现除此之外的未说明改动，应停止并报告。
- 当前真实 DeepSeek 模型标识未配置，不应成为本任务阻塞；异步诊断默认使用 fake provider。
- 产品要求所有长任务由页面/API 主动创建，Worker 只执行和为失败任务延迟重试。
- PostgreSQL 是唯一业务事实源，MVP 本地运行且不引入 Redis/Celery。

### 可自主决策项

- 任务表/运行记录表的具体拆分、状态枚举、租约长度、轮询间隔、退避算法、幂等键约束和索引设计。
- Worker 进程结构、处理器注册方式、事务边界、日志格式、优雅停止方式和测试策略。
- 固定诊断任务是否调用 T003 fake Gateway，或使用更小的确定性处理器；只要能够验证成功、主动失败、重试与恢复，且不会生成伪造业务事实。
- API 路径和响应契约，只要保持受限、可追溯且不会暴露内部任意执行能力。

### 验收标准

1. 增量迁移可在开发库和使用库安全应用，不破坏 T001/T003 数据；usage 库不自动创建诊断任务或测试运行记录。
2. API 创建任务后，独立 Worker 能领取并完成；状态变化、结果摘要、尝试次数和时间戳可查询。
3. 多 Worker 或并发领取验证中，同一任务不会在同一租约周期被重复领取；事务不会在外部/长耗时执行期间长期持有行锁。
4. 可重试失败按有界退避进入下一次执行，达到最大尝试后终止；`next_run_at` 或等价字段不被用于产品定时调度。
5. Worker 异常退出或租约过期后任务能够安全恢复，且不会静默丢失；未知任务类型和非法 payload 有明确失败原因。
6. 同一幂等键的重复创建不会产生重复业务任务，或采用等价、可解释的去重契约。
7. Compose 能独立启动 API、Worker 与 PostgreSQL；Worker 只访问当前环境数据库，开发/usage 数据互不污染。
8. 受限诊断覆盖成功、失败、重试/终止和查询链路；不提供任意 URL、任意 prompt 或任意代码执行入口。
9. 任务实现、验证、过程文档和技术架构记录完整，没有越过阶段一边界。

### 验证要求

- 自行执行与迁移、Python 单元/集成测试、Compose、API、真实 PostgreSQL 领取并发、失败重试、租约恢复、幂等和双数据库隔离相称的验证。
- 可以使用固定且可清理的开发环境诊断数据；不得污染 usage 数据库。完成后说明保留或清理了哪些诊断记录。
- 检查 payload、错误日志和 API 响应不包含 API key、数据库密码或不必要的完整 prompt/正文。
- 不新增独立审查任务作为完成前提；你需要对自己的验证结论负责并在交接中明确未覆盖项。

### 文档更新要求

- 增量更新 `README.md` 的 Worker 启动、开发/usage 环境和受限诊断说明。
- 按 `docs/tech-architecture/AGENTS.md` 记录已实现并验证的任务状态机、领取/租约/重试机制、事务边界、幂等与失败处理；必要时新增重要技术决策文件。
- 更新本任务文件、T004 工作区文档、`docs/implementation-status/current.md` 和 `queue.md`；不得提前把阶段二写成已完成。

### Git 与主动反馈授权

当且仅当任务完整完成、全部必要验证通过、提交范围清晰且敏感信息检查通过时，你可以自动提交并推送本任务代码到当前远端分支。提交前必须排除无关改动、临时文件、运行产物和敏感信息；无法安全区分重叠改动时不得提交，应向管理 Agent 报告。总管在 `54af16b` 后创建的治理、M001 阶段规划和 T004 任务文档属于已授权提交范围；保持其语义并随 T004 最终提交。

提交/推送完成后，主动向来源管理对话发送结构化完成反馈，包含提交 SHA、推送结果、工作树状态和下列全部交接字段。

### 必须返回的结构化摘要

- 完成内容：
- 修改范围：
- 验证结果（命令/集成步骤/结果）：
- 任务状态机与可靠性决定：
- 开发/usage 数据隔离结果：
- Git 提交与推送结果：
- 遗留问题与风险：
- 文档更新：
- 下一步建议：

不要只返回“已完成”，也不要要求总管读取源码或 diff 补全理解。

## 派发记录

- 计划派发方式：Codex 桌面任务工具
- Thread ID：019fbeba-4b4e-7743-9c4a-3c8a3f7dcaf5
- 派发时间：2026-08-02

## 完成记录

- 完成时间：2026-08-02
- 已实现 `jobs`/`job_attempts` 增量迁移、数据库幂等、短事务 `SKIP LOCKED` 领取、lease token 与心跳、过期租约恢复、有界指数退避、处理器注册、独立 Worker 和固定诊断管理 API。
- 真实 API/Worker 覆盖成功、永久失败、失败后成功、达到最大尝试、手动重试、查询、重复创建与非法字段拒绝；显式 PostgreSQL 集成测试覆盖两 Worker 单租约、迟到写回拒绝、退避终止和幂等漂移。
- 开发库保留 4 条固定诊断任务与 7 条 attempt；usage 库为 0 任务、0 attempt，且 API/Worker 均确认连接 `study_for_job`。
- 详细实施、命令、结果与限制见 `task-workspaces/T004/implementation.md` 和 `task-workspaces/T004/verification-and-handoff.md`。
