# T001：本地运行骨架与目标岗位/投递记录最小闭环

状态：已完成

## 任务提示词

Skills: @build-web-apps:frontend-app-builder @build-web-apps:react-best-practices @build-web-apps:supabase-postgres-best-practices

你负责 study_for_job 阶段一的首条纵向开发链路：建立可本地运行的前后端分离骨架，并打通“目标岗位/公司 → 投递记录 → 看板查看与维护”的最小闭环。开始前必须读取并遵守以下 Skill 的 `SKILL.md`：`build-web-apps:frontend-app-builder`（Build Web Apps 前端应用构建）、`build-web-apps:react-best-practices`（React/Next.js 性能最佳实践）、`build-web-apps:supabase-postgres-best-practices`（Postgres 性能与建模最佳实践）。

### 必读规则和文档

- 根目录 `AGENTS.md`、`README.md`。
- `docs/project-governance/AGENTS.md`。
- `docs/product-overview/README.md`、`docs/decision-log/README.md`。
- `docs/tech-architecture/AGENTS.md`、`docs/tech-architecture/README.md`、`docs/tech-architecture/overview.md`。
- `docs/implementation-status/AGENTS.md`、`README.md`、`current.md`、`roadmap.md`、`queue.md`。

### 任务目标

- 让项目具备清晰、可本地启动的前端、API、PostgreSQL 和迁移边界。
- 实现目标岗位画像和投递记录的最小真实数据流：创建/编辑/列表/详情或等价的最小操作集。
- 页面展示投递看板，体现阶段、关键日期、下一步动作和备注/链接等已确认字段。
- 保持 PostgreSQL 为唯一业务事实源，前端不维护第二份持久化事实。

### 范围

- 项目启动骨架、环境示例、数据库迁移和基础健康检查。
- `target_profiles` 与 `applications` 的必要字段、约束、访问层、API 契约和前端页面。
- 单用户、本地优先场景下的基础错误处理和人工可验证交互。
- 为后续 AI Gateway、任务队列和面经情报层保留模块边界，但只需接口/目录级可扩展性。

### 非范围

- 面经抓取、正文解析、embedding、RAG、AI Gateway 实现或 token 统计。
- 登录、多用户权限、定时任务、岗位爬取、在线判题、模拟面试 Agent。
- 重型运营后台、发布回滚和复杂知识图谱。

### 已知事实

- 产品是单用户、本地优先 Web 应用，PostgreSQL 是唯一业务事实源。
- 投递记录是手动维护的求职流程看板，不是情报输入主源；临近面试才作为弱信号。
- DeepSeek V4 已确定，但本任务不需要调用模型。
- MVP 只要求本地运行，同时保持未来替换模型、存储和部署的空间。

### 可自主决策项

- 前后端具体目录、框架细节、字段命名、API 风格、状态枚举和表单/看板布局。
- 迁移工具、验证库、错误响应格式和本地编排方式，只要符合架构文档并在技术文档中记录必要取舍。
- 是否先提供少量种子数据或空状态体验，只要不伪造用户事实。

### 验收标准

1. 按文档说明可在本地启动依赖服务、API 和前端；健康检查能证明 API 到数据库的连通性。
2. 目标岗位画像和投递记录均有迁移、持久化访问和 API 契约，刷新页面后数据仍来自 PostgreSQL。
3. 用户可以通过页面完成至少一条投递记录的新增、编辑和查看；看板显示公司、岗位、阶段、关键日期、下一步动作及备注/链接。
4. 投递阶段流转和必填约束有明确处理；错误不会静默丢失或写入重复事实。
5. 实现没有越过已确认 MVP 边界，并为后续阶段保留清晰模块接口。

### 验证要求

- 开发 Agent 负责执行与本任务相称的自动化检查、迁移验证和 API/UI 人工验证，并在摘要中给出命令、结果和未覆盖部分。
- 不要求总管复查源码；若发现环境或权限阻塞，先记录可复现原因和最小下一步。

### 文档更新要求

- 按 `docs/tech-architecture/AGENTS.md`，只在确实产生非显而易见的架构、数据流、可靠性或工程取舍时增量更新 `docs/tech-architecture/overview.md`、`decisions/` 或 `implementation/`。
- 更新 `docs/implementation-status/tasks/T001-foundation-application-loop.md` 的状态和完成记录，并在 `docs/implementation-status/current.md` 或相关状态文档补充已验证事实；不要重写无关规划。

### 必须返回的结构化摘要

请严格按以下字段返回：

- 完成内容：
- 修改范围：
- 验证结果（命令/人工步骤/结果）：
- 关键技术决定：
- 遗留问题与风险：
- 文档更新：
- 下一步建议：

不要只返回“已完成”，也不要要求总管通过读取源码来补全上下文。

## 派发记录

- 计划派发方式：Codex 桌面任务工具
- Thread ID：019fbda1-2385-7a01-a603-873ba3fbe188
- 派发时间：2026-08-01

## 完成记录

已完成本地运行骨架、数据库迁移、健康检查、目标岗位画像与投递记录 API，以及 React 投递看板。实现投递记录新增、编辑、详情查看、筛选和阶段展示；数据库唯一约束阻止重复公司/岗位事实。前端提交采用 API 字段白名单并将可空字段规范化为 `null`，保证新增和编辑符合严格契约。

后续按本地参考项目收敛 PostgreSQL 配置：改为 SQLAlchemy Engine/Session 单一访问边界，支持拆分式 `POSTGRES_*` 配置、连接池和失效连接探测，并新增与迁移一致的 `TargetProfile`、`Application` ORM 表模型；原始 SQL 迁移继续作为建表事实源。

验证记录：`python -m py_compile backend/app/main.py backend/app/config.py backend/app/db.py backend/app/models.py`、`docker compose config --quiet` 通过；Docker Compose 三项服务均运行，`/api/health` 返回 `{"status":"ok","database":"ok"}`，迁移创建 `target_profiles` 与 `applications`。通过 API 完成临时记录的新增、编辑、详情、列表及 API 容器重启后的持久化读取，随后删除临时数据；前端返回 HTTP 200。内置浏览器此前验证了主屏错误态、空看板、新增投递表单及 390px 移动端无水平溢出。Docker Hub 访问通过 Docker Desktop 重启后恢复，API 构建代理仅在 `pip install` 阶段使用；Image Gen 概念图调用因网络错误未生成。

2026-08-02 增量完成：新增开发库 `study_for_job_dev` 与使用库 `study_for_job` 的隔离配置；二者共用 `001_initial.sql`，仅开发库加载幂等样例数据。实际切换验证中，使用环境健康检查返回 `environment=usage`、目标画像/投递记录均为 0；切回开发环境后返回 `environment=development`、1 条画像和 6 条投递记录，前端 `/api` 代理结果一致。

前端按 `frontend-design` 方向重构为非对称“求职作战台 × 编辑部排期墙”：保留 PostgreSQL 单一事实源，新增详情侧栏和紧凑阶段切换交互，拆分数据 Hook、API 白名单和页面组件。内置浏览器验证 1440px 桌面布局、390px 移动布局、搜索过滤、新增投递表单、画像表单以及阶段从待评估到已投递再恢复的真实持久化流程；页面无整页水平溢出，移动看板使用自身横向滚动。未调用 Image Gen，未执行项目规则禁止的 `npm run build`。
