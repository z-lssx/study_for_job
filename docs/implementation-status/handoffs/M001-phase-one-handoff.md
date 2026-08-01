# M001 阶段一交接

交接日期：2026-08-02

## 当前阶段

阶段一“数据底座与投递闭环”已完成。当前没有进行中子任务；用户下一步应启动项目大总管，由大总管创建阶段二总管。阶段二总管应先建立自己的阶段管理规划，再从 T005 开始派发面试情报闭环开发。

## 已完成事项

### T001：本地骨架与投递闭环

- Thread：`019fbda1-2385-7a01-a603-873ba3fbe188`（已归档）。
- 已实现 React/Vite、FastAPI/SQLAlchemy、PostgreSQL、迁移和 Docker Compose 本地运行边界。
- 目标画像与投递记录支持新增、编辑、详情、阶段切换和搜索。
- 开发库 `study_for_job_dev` 与使用库 `study_for_job` 共用迁移但数据隔离；只有开发库加载幂等样例。
- 桌面 Web 是唯一正式支持端，不规划移动端专属能力。

### T002：独立审查

- Thread：`019fbe64-e12b-7fd2-bff3-c0c8f24a66be`（已归档）。
- 用户终止该任务并确认接受开发 Agent 自验证；后续不为少量增量固定插入独立审查。

### T003：AI Gateway、Prompt 与 Token 日志

- Thread：`019fbe6d-5c81-7d41-afea-e81b7ca54184`（已归档）。
- 提交：`54af16b`，已推送 `origin/main`。
- 已实现自有 AI Gateway/Provider、DeepSeek-compatible/SophNet 环境适配、确定性 fake、关键 prompt 白名单管理、调用日志、token/trace 聚合和桌面 AI 管理页。
- 真实 DeepSeek 因 `DEEPSEEK_MODEL` 尚未配置而未调用，不构成功能阻塞。

### T004：PostgreSQL 队列与 Worker

- Thread：`019fbeba-4b4e-7743-9c4a-3c8a3f7dcaf5`（交接后归档）。
- 提交：`16ea6c0dd82fabb1aea37a2dfdf143aee8285386`，已推送 `origin/main`。
- 已实现 `jobs`/`job_attempts`、幂等创建、`FOR UPDATE SKIP LOCKED` 短事务领取、lease token/心跳/过期恢复、有界指数退避、独立 Worker 和受限管理 API。
- 21 项常规测试和 4 项显式 PostgreSQL 集成测试通过；开发/usage 双库隔离通过，任务 Agent 确认工作树干净。

## 已确认的长期协作规则

- 每任总管派发子任务前先在 `management-plans/` 建立自己的阶段任务规划，明确本任目标、边界、子任务顺序、完成条件和交接条件。
- 总管只消费结构化摘要与状态文档，不读取源码、diff 或亲自测试。
- 开发任务自行验证；独立审查只在高风险、验证不足、摘要矛盾或用户明确要求时派发。
- 前端设计/视觉实现任务必须绑定 `@frontend-design`，并保持现有项目前端风格。
- 子任务可在完整完成、验证、范围和敏感信息检查通过后自动提交推送，并主动反馈来源管理对话。
- 普通页面默认不调用 ImageGen；只有明确需要位图素材时使用。

## 未决事项

- T005 尚未派发：面经公开来源入库、幂等去重和手动正文降级入口。
- DeepSeek/SophNet 的真实模型标识、远程 token 口径、限流错误体和真实调用仍待受控验证。
- embedding 供应方式尚未锁定，应等检索任务出现真实需求后决定。
- 后续面经来源许可必须按来源确认，只尝试公开、无需登录的内容。

## 风险

- Worker 提供至少一次执行语义；T005 必须使用规范化 URL、内容哈希或等价业务唯一键保证外部副作用幂等。
- T005 需要明确网络错误的可重试分类、原文/错误脱敏摘要和失败后手动补正文流程。
- 当前未做队列吞吐压测、数据库故障注入、取消、进度、DAG 或归档；这些不是阶段一缺陷，不应在 T005 首任务中无边界扩张。
- 本地免登录配置不得直接暴露公网；公网部署前需要认证与 HTTPS。

## 下一步建议

1. 用户使用 `docs/project-governance/prompts/program-manager.md` 启动项目唯一大总管。
2. 项目大总管先检查并登记 `program-status.md` 的唯一控制状态，复核宏观路线图，再通过桌面任务工具创建唯一活跃的阶段二总管。
3. 阶段二总管阅读必读文档并建立自己的阶段管理规划，不直接沿用 M001。
4. 阶段二总管细化并派发 T005，先完成“公开 URL 或手动正文 → 原文持久化 → URL/内容哈希幂等 → 状态/失败原因 → Worker 处理”的纵向链路。
5. T005 只注册现有 Worker 处理器，不扩展 `next_run_at` 为用户定时任务。
6. 在原文与状态链路稳定后，再拆分结构化抽取、题目归一化、证据回链和检索任务。

## 后续管理角色分层必读

- 根目录 `AGENTS.md`、`README.md`。
- `docs/project-governance/PROGRAM_MANAGER.md`、`docs/implementation-status/program-status.md`（项目大总管必读）。
- `docs/project-governance/AGENTS.md`。
- `docs/product-overview/README.md`。
- `docs/decision-log/README.md`。
- `docs/tech-architecture/README.md`、`overview.md`。
- `docs/tech-architecture/decisions/0002-postgres-job-queue-leases.md`。
- `docs/tech-architecture/implementation/job-queue-worker.md` 以及 T003 AI Gateway 实现记录。
- `docs/implementation-status/README.md`、`current.md`、`roadmap.md`、`queue.md`。
- `docs/implementation-status/program-status.md`。
- `docs/implementation-status/tasks/T003-ai-gateway-prompt-token.md`。
- `docs/implementation-status/tasks/T004-postgres-job-worker.md`。
- `docs/implementation-status/task-workspaces/T004/verification-and-handoff.md`。
- 本交接文档。
