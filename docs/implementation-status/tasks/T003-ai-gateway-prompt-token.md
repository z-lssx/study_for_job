# T003：AI Gateway、关键 prompt 配置与 token 日志闭环

状态：已完成（本地 fake 与双数据库验证通过；SophNet key 兜底已接入，真实 DeepSeek 因模型标识未配置而未验证）

## 任务提示词

Skills: @build-web-apps:react-best-practices @build-web-apps:supabase-postgres-best-practices

你负责实现阶段一的第二条开发链路：在现有 T001 本地应用基础上，建立可替换的 AI Gateway、少量关键 prompt 配置、AI 调用日志与 token 统计，并提供桌面管理页面。开始前必须完整读取并遵守 `build-web-apps:react-best-practices`（React 性能与工程最佳实践）和 `build-web-apps:supabase-postgres-best-practices`（Postgres 建模与性能最佳实践）的 `SKILL.md`。

### 任务目标

- 建立业务层只依赖自有接口的 AI Gateway，当前供应方按已确认决策支持 DeepSeek V4/OpenAI-compatible 调用，同时保留可替换边界。
- 在 PostgreSQL 中管理少量关键 prompt 场景、模板和参数，并记录每次 AI 调用的模块、场景、模型、token、耗时、状态、prompt 哈希与 trace 信息。
- 提供桌面管理页面，用于查看/编辑关键 prompt 配置和按模块/场景查看 token 使用统计。
- 在没有真实 API 凭据时仍可通过安全的本地替代实现完成确定性验证，不把外部权限升级为产品阻塞。

### 必读规则和文档

- 根目录 `AGENTS.md`、`README.md`，以及相关子目录最近的 `AGENTS.md`。
- `docs/project-governance/AGENTS.md`。
- `docs/product-overview/README.md`、`docs/decision-log/README.md`。
- `docs/tech-architecture/AGENTS.md`、`README.md`、`overview.md`、`decisions/README.md`、`implementation/README.md`。
- `docs/implementation-status/AGENTS.md`、`README.md`、`current.md`、`roadmap.md`、`queue.md`。
- `docs/implementation-status/tasks/T001-foundation-application-loop.md`、本任务文件、`task-workspaces/README.md` 和 `task-workspaces/T003/README.md`。

### 范围

- 读取规则后、修改代码前创建 `task-workspaces/T003/plan.md`；开发过程中维护 `implementation.md`；完成后创建 `verification-and-handoff.md`。
- 新增增量数据库迁移，覆盖关键 prompt 场景/模板与 AI 调用日志；兼容开发库和使用库，不破坏 T001 数据。
- 设计并实现自有 Gateway/Provider 接口、DeepSeek OpenAI-compatible 适配、超时与错误映射、结构化调用结果、token 记录和 trace 关联。
- 提供本地可验证的 fake/stub provider 或等价测试路径；真实密钥只从环境配置读取，绝不写入数据库、日志、仓库或前端。
- 管理 API 支持关键 prompt 配置的查看与编辑，以及 token 日志/聚合统计查询。
- 桌面管理页面融入现有视觉与导航，支持配置少量关键场景、查看调用状态和 token 统计。
- 可以提供受限的管理员诊断调用以验证 Gateway，但不得演变成通用聊天入口。

### 非范围

- 不实现面经抓取、结构化抽取业务链路、embedding、RAG、任务队列或 Worker。
- 不实现通用聊天框、模型供应商管理平台、prompt 发布/回滚系统、复杂费用结算或多用户权限。
- 不提前实现模拟面试、项目/实习 Agent 或 LangGraph。
- 不开发移动端专属能力，不把移动视口作为正式验收项。
- 不调用 ImageGen，不执行项目规则禁止的 `npm run build`。

### 已知事实

- T001 已完成 React/Vite、FastAPI/SQLAlchemy、PostgreSQL、迁移和 Docker Compose 本地边界。
- 开发库为 `study_for_job_dev`，自动加载幂等样例；使用库为 `study_for_job`，不得自动加载测试数据；两库共用迁移和 ORM/API 模型。
- 项目大模型服务已确定使用 DeepSeek V4；具体模型档位和参数可按实际接口与可用性自主决定并配置化。
- 管理端只服务单用户的关键 prompt/参数配置和 token 统计，不扩展为通用运营后台。
- 动态 prompt 只开放少量关键场景；输入输出 Schema、安全规则、工具权限和工作流拓扑仍由代码控制。
- token 统计必须按模块和场景拆分，后续面经分析要能单独统计；任何调用都应可追溯但不得泄露密钥。

### 可自主决策项

- Gateway 接口、Provider 适配层、配置对象、错误类型、重试边界和诊断方式的具体设计。
- prompt 表结构、当前模板表达、允许编辑的参数白名单、统计查询和管理页面布局。
- fake/stub provider 的实现方式及自动化测试框架，只要不会进入真实业务事实或伪装成真实模型结果。
- DeepSeek V4 的具体模型标识和 OpenAI-compatible 基础地址应通过配置提供；若当前官方标识无法在无凭据环境中确认，使用明确占位/环境变量并在交接中记录，不硬编码未经验证的名称。

### 验收标准

1. 增量迁移可在开发库和使用库安全应用，现有目标画像和投递数据不受影响；使用库不注入测试调用或样例日志。
2. 业务代码通过自有 AI Gateway 调用 provider；替换 fake 与 DeepSeek 适配时不需要修改业务调用方。
3. 每次成功或失败调用均形成可追溯日志，至少包含模块、场景、模型、token（可用时）、耗时、状态、prompt 哈希和 trace ID；日志不包含 API 密钥。
4. 关键 prompt 配置只能编辑允许的模板/参数范围，代码控制的 Schema、安全规则和工作流不可由页面任意改写。
5. 桌面管理页面可以查看/编辑配置，并按模块/场景查看调用与 token 统计；错误状态可见且不会静默失败。
6. 无真实 DeepSeek 凭据时，fake/stub 路径能够确定性验证成功、失败和 token 记录；有凭据时可选执行一次受控真实诊断并明确记录结果。
7. 未越过 MVP 范围，未引入通用聊天、prompt 发布回滚或多用户能力。

### 验证要求

- 子任务 Agent 自行执行与迁移、Python/API、Gateway 成功/失败路径、日志写入、双数据库隔离和桌面页面相称的验证，并在交接中记录命令、人工步骤、结果及未覆盖项。
- UI 按项目规则人工验证，可使用浏览器工具辅助，不新增访问脚本。
- 验证敏感配置不会出现在 API 响应、数据库日志、前端资源或提交文件中。
- 不因缺少外部 API key 停止本地实现；将真实远程调用列为可选外部验证。

### 文档更新要求

- 增量更新 `README.md` 的配置与启动说明，确保开发/usage 双环境仍清晰。
- 按 `docs/tech-architecture/AGENTS.md` 记录已实现且已验证的 Gateway 边界、日志数据流、失败处理和重要取舍；普通 CRUD 不单独包装成架构成果。
- 更新本任务文件、T003 工作区文档和 `docs/implementation-status/current.md`；不要重写无关路线图或把未验证内容写成完成。

### 必须返回的结构化摘要

- 完成内容：
- 修改范围：
- 验证结果（命令/人工步骤/结果）：
- 关键技术决定：
- DeepSeek 真实调用状态（已验证/因无凭据未验证）：
- 遗留问题与风险：
- 文档更新：
- 下一步建议：

不要只返回“已完成”，也不要要求总管读取源码或 diff 补全理解。

## 派发记录

- 计划派发方式：Codex 桌面任务工具
- Thread ID：019fbe6d-5c81-7d41-afea-e81b7ca54184
- 派发时间：2026-08-02

## 完成记录

- 完成时间：2026-08-02
- 已实现自有 Gateway/Provider、DeepSeek OpenAI-compatible 适配、确定性 fake、prompt 白名单管理、成功/失败调用日志、token/trace 聚合与桌面管理页。
- 后续增量接入 SophNet 默认 base URL 和 `SOPHNET_API_KEY` 环境变量兜底；保留 `DEEPSEEK_API_KEY` 显式覆盖优先级。
- `002_ai_gateway.sql` 与启动迁移器已在开发库、使用库验证；开发库原 T001 数据不变，使用库没有样例业务事实或调用日志。
- 详细实施、命令、人工步骤、结果与限制见 `task-workspaces/T003/implementation.md` 和 `task-workspaces/T003/verification-and-handoff.md`。
