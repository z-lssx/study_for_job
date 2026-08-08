# 技术架构

本文档描述当前系统结构和长期边界。模块级字段、状态机、API 和限制由 `implementation/` 下的稳定实现文档维护。

## 架构结论

- 单用户、本地优先、桌面 Web。
- React/Vite 负责页面、真实路由和交互状态。
- FastAPI/SQLAlchemy 提供领域 API，不把业务事实持久化在浏览器。
- PostgreSQL 16 是唯一业务事实源，同时承担增量迁移、检索扩展和任务队列。
- 独立 Worker 执行面经等长任务；API 只创建任务、查询状态和执行短事务。
- AI 访问统一经过自有 Gateway 契约，业务层不直接依赖供应商 SDK。
- 情报证据、用户修订、AI 草稿、表达版本和策略投影保持不同语义，不合并成统一事实或评分。

## 领域关系

```text
公开面经 / 用户正文
          │
          ▼
面试情报层 ── 原文、抽取块、规范题、频率、证据
          │
          ├──────────────┐
          ▼              ▼
目标与投递          四条准备轨道
          │      知识 / 算法 / 项目 / 实习
          └──────────────┘
                  │
                  ▼
         规则优先准备策略与导出
```

面试情报提供需求信号和证据；四条准备轨道保存用户可维护资产；投递只在明确临近面试时作为策略同档弱信号。策略是可解释投影，不替代底层事实。

## 运行拓扑

```text
Browser
  │
  ▼
Vite / React frontend
  │ /api
  ▼
FastAPI API ───────────────┐
  │                        │ create/query jobs
  │ SQLAlchemy             ▼
  ├────────────────── PostgreSQL 16
  │                        ▲
  │ AI Gateway             │ lease / result
  ▼                        │
Fake or DeepSeek API   Independent Worker
```

### 前端

- `AppShell` 统一可收起侧栏、目标上下文、数据环境和内容宽度。
- History API 路由支持刷新、前进后退和按 ID 深链，不依赖组件内 `activeView` 模拟多页面。
- 页面只保存临时表单、展开/收起和导航偏好；业务详情刷新后重新从 API 读取。
- 投递快速详情使用抽屉，情报和四轨道深层内容使用独立 URL，项目/实习长编辑使用独立页面。
- 设计职责见 `docs/design/frontend-redesign.md`，实现事实见 `implementation/frontend-workbench.md`。

### API

- FastAPI 路由按目标画像、投递、情报、知识、算法、项目、实习、策略、导出和管理端领域组织。
- SQLAlchemy session 统一事务提交/回滚；网络和模型调用不持有数据库事务。
- 局部状态变化优先使用 PATCH 或动作接口，避免整对象覆盖用户并发修订。
- API 错误使用稳定 code、可读安全信息和明确 retryable 边界，不返回凭据、原始异常或 Worker 租约信息。

### Worker

- Worker 与 API 使用同一业务数据库，但运行在独立进程。
- 任务在短事务内通过 `FOR UPDATE SKIP LOCKED` 领取，事务外执行，再用 lease token 条件写回。
- 租约恢复提供至少一次执行语义；处理器必须依赖领域唯一键和输入指纹实现业务幂等。
- 重试只用于临时错误；来源许可、无效输入和不支持类型等永久失败进入稳定终态。

## PostgreSQL 数据边界

### 环境隔离

- `study_for_job_dev`：默认开发环境，可加载幂等样例数据。
- `study_for_job`：个人使用环境，不自动写入样例。
- 两个数据库共用同一 PostgreSQL 实例和同一套编号迁移，前端只访问当前 API，不感知另一数据库。
- `/api/health` 返回当前环境和数据库名，避免静默写错环境。

### 主要事实组

- 目标与投递：目标画像、投递记录、阶段、关键日期和下一步动作。
- 情报输入：submission、来源、文档、处理状态、内容身份和来源关联。
- 情报结构：抽取运行、轮次、内容块、证据区间、规范题、出现事实、映射和人工修订。
- 知识与算法：个人题卡、资料、掌握/练习状态、卡点、复盘和证据关联。
- 项目与实习：不可编造的事实资产、表达版本、材料、确认状态和情报关联。
- AI 与任务：prompt 模板、调用日志、token/trace、jobs 和 job attempts。

用户事实、原始情报、AI 草稿和规则投影分别持久化或计算，不能为了页面展示方便复制成第二套事实源。

## 迁移与一致性

- `migrations/` 是 development 与 usage 的唯一结构事实源。
- API 启动迁移器通过 `schema_migrations`、SHA-256 checksum 和事务级 advisory lock 串行应用编号 SQL。
- 全新数据库和已有数据卷使用同一批迁移，不维护第二套 ORM 自动建表或初始化 schema。
- 当前复杂度下不引入 Alembic；只有迁移回滚、分支协作或多服务独立部署证明需要时再评估。

## 面试情报链路

```text
提交 URL/正文
  -> 保存 submission 与输入修订
  -> 创建幂等 Worker 任务
  -> 来源策略、DNS/IP、重定向和资源限制检查
  -> 清洗纯文本、内容去重、来源关联
  -> 确定性轮次/内容块抽取与 evidence span
  -> 保守规范题归一化与 occurrence 计数
  -> exact / FTS / pg_trgm 候选检索
  -> 页面回链 document / round / chunk / evidence
```

- 高频来自 occurrence，不由 RAG 或模型总结直接生成。
- 用户合并、拆分或等价修订改变映射层，不改写原始 occurrence。
- 当前没有 embedding/pgvector 语义召回；不同措辞召回质量仍标记为 `unproven`。
- 抓取和内容身份的已知安全风险见 `docs/maintenance/known-issues.md`。

实现细节见：

- `implementation/intelligence-pipeline.md`
- `implementation/intelligence-extraction.md`
- `implementation/intelligence-normalization.md`
- `implementation/retrieval.md`

## 四条准备轨道

- 知识轨道保存题卡、口述版本、追问、资料、复习状态和证据。
- 算法轨道保存外部题目链接、练习状态、卡点和复盘，不执行代码或判题。
- 项目轨道保存事实证据包、表达历史、确认版本和追问树。
- 实习轨道保存职责边界、STAR、量化结果、材料与表达版本。

四轨道共享来源回链和用户修订原则，但不强制共用单一模型、评分或页面模板。详见对应 `implementation/*-track.md`。

## 策略与导出

- 准备评估由用户显式 POST 触发，读取目标、情报摘要和四轨道状态，按固定档位与稳定 tie-break 返回建议。
- 策略不调用 LLM，不读取全量面经正文，不把投递阶段或频率写成客观能力。
- 当前评估结果不持久化，因此首页不伪造“最近策略快照”。
- Markdown 与 JSON 导出来自同一 `REPEATABLE READ, READ ONLY` 快照，使用显式 `as_of_date`、稳定关系 ID 和 fingerprint。
- 导出直接读取底层业务事实，不把策略 assessment 当作事实源。

详见 `implementation/planning.md` 与 `implementation/export.md`。

## AI Gateway

- 业务依赖自有 `AiGateway`、provider、prompt store 和 call log 契约。
- 默认 fake provider 提供确定性本地行为；DeepSeek-compatible provider 由环境变量配置。
- prompt、远程调用和日志落库分段执行；日志保存 trace、token、耗时、状态和 prompt hash，不保存凭据或完整 prompt/响应正文。
- 动态 prompt 只开放批准场景和有限参数；安全规则、工具权限和 schema 由代码控制。
- 真实模型标识和远程调用质量仍未验证，详见 `implementation/ai-gateway.md` 和已知问题。

## 部署边界

- Docker Compose 编排 PostgreSQL、API、Worker 和 frontend。
- 当前免登录设计只适合可信本地环境；部署到公网前必须增加身份认证、HTTPS、密钥管理和访问控制。
- 备份以 PostgreSQL `pg_dump` 为基础，不在当前 MVP 内建设重型备份平台。
- 不部署独立 Scheduler；面向用户的定时生成和推送不属于当前产品边界。

## 延期与演进原则

- 只有真实查询样本证明 exact/FTS/pg_trgm 不足时，才评估 embedding、pgvector 和 RAG。
- 只有用户明确需要跨刷新恢复策略时，才在 planning 领域设计持久化快照。
- 多轮模拟面试和经历深挖 Agent 必须使用受限工具、预算和独立事实边界，不能扩展成全局聊天 Agent。
- 只有真实吞吐证明 PostgreSQL 轮询成为瓶颈时，才评估消息中间件。
- 所有当前延期能力与未解决风险统一维护在 `docs/maintenance/known-issues.md`。
