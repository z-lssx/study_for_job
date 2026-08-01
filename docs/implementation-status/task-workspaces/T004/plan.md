# T004 实施计划

更新时间：2026-08-02

## 现状判断

- FastAPI、SQLAlchemy 2、psycopg 3、编号 SQL 启动迁移器和开发/usage 双数据库边界已经存在；API 与 AI Gateway 均通过同一环境配置选择数据库。
- AI Gateway 已把 prompt 读取、provider 调用和调用日志拆成短事务，适合作为固定异步诊断处理器复用。
- 当前没有任务表、任务处理器、独立 Worker、任务管理 API 或 Worker Compose 服务。
- 工作树中 `54af16b` 之后的改动仅包含总管已授权的治理、阶段规划和 T004 文档基线，没有发现其他未说明改动。

## 设计范围与数据流

```text
受限管理 API
  -> 校验固定诊断模式与幂等键
  -> PostgreSQL 原子创建/返回既有任务
  -> Worker 短事务原子领取（FOR UPDATE SKIP LOCKED）
  -> 事务外执行注册处理器
  -> 短事务按任务 ID + lease token 条件写入成功/重试/终止
  -> API 查询任务与逐次运行记录
```

- 新增通用 `jobs` 事实表和逐次领取/执行事实 `job_attempts`；payload/result/error 均限制为脱敏摘要，不保存密钥、任意 prompt 或正文。
- 状态采用 `queued | running | retry_wait | succeeded | failed`。`next_run_at` 只在创建时取当前时间、可重试失败时写入退避时间、手动重试时重置为当前时间。
- 领取时同时恢复过期租约；同一原子语句通过 `FOR UPDATE SKIP LOCKED` 选择一条任务、递增尝试次数、生成新 lease token 并创建 attempt 记录，提交后才执行处理器。
- 完成写入以 `id + status=running + lease_token` 做条件更新，避免旧 Worker 覆盖租约恢复后的新执行结果。
- 固定诊断类型只允许代码定义的 `success`、`retryable_failure`、`permanent_failure` 三种模式；处理器注册边界允许 T005 后续增加明确任务类型。

## 拟修改范围

- `migrations/003_job_queue.sql`：任务/尝试表、约束、幂等唯一索引、活跃领取部分复合索引、查询索引。
- `backend/app/models.py`：迁移对应 ORM 模型。
- `backend/app/jobs/`：错误分类、处理器注册、PostgreSQL repository、执行器和 Worker 入口。
- `backend/app/api/admin_jobs.py` 与 `backend/app/main.py`：受限创建、列表、详情、允许状态下手动重试。
- `backend/app/config.py`、`.env.example`、Compose：Worker 标识、轮询、租约、退避与独立服务；usage 覆盖 API 与 Worker 到同一 usage 数据库。
- `backend/tests/`：状态机、处理器边界、API 约束和 repository 行为测试。
- README、技术架构、T004 任务/工作区和实施状态文档。

## 实施步骤

1. 落迁移与 ORM，确保约束和索引与查询谓词一致。
2. 实现 repository 的幂等创建、原子领取、lease-token 条件完成、退避、终止、过期租约恢复和手动重试。
3. 实现固定诊断处理器、注册表和单次执行/持续轮询 Worker，加入信号驱动的优雅停止。
4. 提供受限管理 API，并确保响应不回显内部敏感数据。
5. 加入 Compose Worker 与双环境数据库覆盖。
6. 执行 Python 测试、迁移、真实 PostgreSQL 并发领取、生命周期、幂等、租约恢复、双库隔离和 Compose 验证；清理或明确保留开发诊断数据。
7. 完成实现、架构、验证交接和状态文档；范围与敏感信息检查通过后提交、推送并反馈来源管理对话。

## 验证计划

- `python -m unittest discover -s tests -v`（后端单元/契约测试）。
- `python -m app.migrations` 分别应用到开发库和 usage 库，核对历史数据与迁移版本。
- 真实 PostgreSQL 上并发执行两个领取者，确认单任务只被一个租约领取且领取事务立即结束。
- 通过 API 创建固定成功/可重试失败/永久失败诊断，运行独立 Worker，查询任务与 attempts。
- 人工调整租约到期并由另一 Worker 恢复，确认旧 lease token 无法覆盖新结果。
- 重复幂等键创建、达到最大尝试、手动重试允许/拒绝路径。
- Compose 分别启动 development 与 usage 配置，核对 Worker/API `POSTGRES_DB` 一致且 usage 任务/attempt 为零。
- 对 payload、错误与 API 响应做密钥/密码/prompt/正文关键词和高风险字段扫描。

## 风险与控制

- PostgreSQL 队列为至少一次执行语义；租约超时后原执行仍可能完成，因此未来业务处理器必须幂等，当前通过 lease token 防止旧执行覆盖任务状态。
- 退避测试若使用生产秒级配置会变慢；测试通过注入时钟/极短配置验证公式，真实 PostgreSQL 只做短退避诊断。
- Worker 与 API 共用现有连接配置；Compose 明确覆盖 usage Worker，避免只切 API 导致跨库领取。
- 不在外部或 AI 调用期间保留数据库事务或行锁。

## 非范围

- 不实现阶段二抓取、解析、抽取、embedding、RAG、统计或调度业务。
- 不实现用户定时任务、Cron、周期推送、自动采集、Redis/Celery/Kafka/RabbitMQ、微服务或 Kubernetes。
- 不新增前端视觉页面，不调用 ImageGen，不执行 `npm run build`，不调用真实付费模型。
