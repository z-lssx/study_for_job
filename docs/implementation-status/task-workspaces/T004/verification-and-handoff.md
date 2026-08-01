# T004 验证与交接

完成时间：2026-08-02

## 验证结论

T004 已完成“受限 API 主动创建 → PostgreSQL 队列 → 独立 Worker → 状态/失败查询 → 失败退避重试 → 租约恢复”的最小可靠闭环。PostgreSQL 是唯一任务事实源，没有引入 Redis、Celery、Scheduler 或用户定时能力。

## 自动化测试

### 常规测试

```powershell
cd backend
python -m py_compile app\config.py app\models.py app\main.py app\api\admin_jobs.py app\jobs\contracts.py app\jobs\errors.py app\jobs\handlers.py app\jobs\repository.py app\jobs\worker.py
python -m unittest discover -s tests -v
```

结果：编译通过；25 项被发现，21 项通过，4 项 PostgreSQL 测试因需要显式开关按预期跳过。覆盖原 T003 Gateway/config 回归、固定诊断契约、非法 payload、未知类型、异常脱敏、有界退避、Worker 成功/失败、HTTP 422 输入脱敏、payload/lease token 响应隐藏。

### 真实 PostgreSQL 集成

先停止常驻 Worker，避免它领取测试任务；测试结束后恢复：

```powershell
docker compose stop worker
docker compose run --rm --no-deps -v "${PWD}\backend\tests:/app/tests:ro" -e RUN_POSTGRES_INTEGRATION=1 api python -m unittest tests.test_jobs_postgres -v
docker compose start worker
```

结果：4/4 通过。

- 同幂等键相同参数返回既有任务，参数漂移抛出冲突。
- 两线程同时领取单任务只有一个得到租约。
- 第一租约到期后第二 Worker 创建新 attempt；第一 token 迟到成功写回返回 false，第二 token 成功。
- 可重试失败写入精确退避时间，第二次达到上限后终止且不能手动重试。
- 测试通过任务 ID 精确清理自身创建的任务和 attempts，没有留下集成测试数据。

本机通过 `127.0.0.1:5432` 首次运行该套件时，既有 Docker 数据卷的宿主机密码认证与当前示例密码不一致；这不是应用链路问题。随后使用临时 API 容器和 Compose 已生效的数据库环境完成同一测试。

## Compose 与 API 生命周期

```powershell
docker compose up -d --build api worker
docker compose ps
docker compose logs --no-color --tail=40 api worker
```

结果：API 与 Worker 独立进程均为 Up；API 迁移启动成功，Worker 正常轮询。未执行 `npm run build`。

通过 `POST /api/admin/jobs/diagnostics` 创建四种开发诊断并查询详情：

- 立即成功：`succeeded`，1 attempt，有结果摘要。
- 一次可重试失败后成功：`succeeded`，2 attempts；首次预修复异常退出后由租约恢复，旧 attempt 为 `lease_expired`。
- 永久失败：`failed`；手动重试 200 后再次固定失败，成功任务手动重试返回 409。
- 可重试失败达到最大次数：`failed`，2 attempts，继续手动重试返回 409。

同幂等键重复创建返回 `created=false`；相同键改变参数返回 409；请求增加任意 URL/prompt/code 字段返回 422。SIGTERM 验证日志为“收到信号 → 当前任务后停止 → Worker stopped”，之后已重启。

## 迁移与双数据库隔离

```powershell
docker compose -f docker-compose.yml -f docker-compose.usage.yml up -d --no-build --force-recreate api worker
docker compose exec -T postgres psql -U study -d study_for_job -c "SELECT version FROM schema_migrations ORDER BY version;"
docker compose exec -T postgres psql -U study -d study_for_job_dev -c "SELECT version FROM schema_migrations ORDER BY version;"
docker compose up -d --no-build --force-recreate api worker
```

结果：

- 两库迁移版本均为 `001_initial.sql`、`002_ai_gateway.sql`、`003_job_queue.sql`。
- usage 健康检查返回 `usage / study_for_job`；Worker 配置输出 `usage study_for_job`。
- usage 原始 API 响应中目标画像、投递、AI 调用和任务均为 `[]`；数据库任务/attempt 为 0/0。
- development 最终恢复为 `development / study_for_job_dev`，保留 T001/T003 数据与 4 条 T004 固定诊断任务、7 条 attempts。
- 最终开发任务状态为 2 succeeded、2 failed，没有 queued/running/retry_wait；`pg_stat_activity` 的 `idle in transaction` 为 0。

## 安全与敏感信息

- 实时 422 响应不含测试值 `sensitive-prompt-must-not-echo`。
- 实时任务详情不含 `payload` 或 `lease_token`；错误只使用代码固定消息，不写 Python 原始异常。
- API 创建契约不包含 URL、prompt、正文、代码或 `next_run_at`。
- `git diff --check` 通过；凭据模式扫描仅命中 `.env.example` 的公开本地示例 DSN `study:study`，没有真实 API key、Bearer token 或非示例数据库密码。
- 未调用真实 DeepSeek 或其他付费服务；固定诊断不依赖 AI provider。

## 已修复的验证期问题

首次真实可重试失败写回暴露 SQLAlchemy 将 Python `None` 编码为 JSONB `null` 的差异，严格 CHECK 约束拒绝该值并使 Worker 退出。已将可空结果字段设为 `JSONB(none_as_null=True)`，并让 Worker 主循环隔离单次数据库周期异常。修复后完整生命周期、租约恢复和测试均通过。

## 当前限制与风险

- 队列是至少一次执行，不是精确一次；T005 处理器必须用业务唯一键保证外部副作用幂等。
- 默认 1 秒轮询、60 秒租约，当前本地规模足够；尚未做吞吐/压测或数据库故障注入。
- 没有取消、进度百分比、DAG、归档或用户定时功能，这些均不属于 T004。
- 没有验证真实 DeepSeek；本任务不依赖它，也没有产生 AI 调用日志。

## 文档更新

- 根 README：Worker 启动、双环境切换、受限诊断与 API。
- 技术架构：新增决策 `0002` 和实现文档 `job-queue-worker.md`，并更新 overview/索引。
- 实施状态：更新 T004 任务、工作区、current、queue 和 M001 状态。

## 下一步

T005 注册面经入库处理器时，先定义 URL/内容哈希幂等键、网络错误的可重试分类、原文与错误的脱敏摘要，再复用当前 repository/Worker；不要把抓取时间参数扩展成用户定时调度。
