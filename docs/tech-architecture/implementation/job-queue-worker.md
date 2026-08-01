# PostgreSQL 任务队列与 Worker

状态：已实现并完成本地 PostgreSQL、Compose、并发领取、租约恢复、失败退避与双数据库验证。

## 解决的问题

页面/API 主动创建的长任务需要脱离 API 请求执行，同时保证状态、失败原因和每次执行事实可查询。当前机制只负责执行和失败延迟重试，不提供 Cron、周期调度、定时采集或定时推送。

## 实际数据流

```text
受限 API 创建固定任务
  -> INSERT ... ON CONFLICT（数据库幂等）
  -> Worker 短事务 SELECT ... FOR UPDATE SKIP LOCKED
  -> 标记旧租约/创建新 job_attempt 并提交
  -> 事务外运行注册处理器，心跳短事务续租
  -> 按 job_id + lease_token 条件写成功/重试/失败
  -> API 查询 jobs 当前事实与 job_attempts 历史
```

## 状态机与数据

- `queued`：API 创建或允许的手动重试，`next_run_at` 固定为当前时间。
- `running`：具有 `claimed_by`、lease token、到期时间和对应 `running` attempt。
- `retry_wait`：可重试失败且仍有尝试余量，`next_run_at` 为有界指数退避时间。
- `succeeded`：保存 JSON 对象结果摘要和完成时间。
- `failed`：永久失败、达到最大尝试或租约过期且已耗尽尝试，保存固定错误码、脱敏错误和完成时间。

数据库 CHECK 约束保证运行/等待/终态字段组合一致；尝试次数不能超过上限。`job_attempts` 记录 `running | succeeded | retry_scheduled | failed | lease_expired`，便于区分业务失败与进程崩溃恢复。

## 并发、事务与恢复

- 领取查询按优先级、到期时间和创建顺序排列，使用只覆盖活跃状态的部分复合索引。
- 多 Worker 用 `SKIP LOCKED` 跳过其他领取事务正在处理的行；外部处理器运行时任务行没有数据库锁。
- 每次领取生成唯一 lease token。续租和最终写回都校验 token；旧 Worker 的迟到结果不会覆盖新租约。
- Worker 收到 SIGTERM/SIGINT 后停止领取新任务，当前任务继续到写回；处理期间的心跳避免正常长任务被误恢复。
- Worker 进程在单次数据库周期异常时记录错误并继续轮询；若任务已处于 running，后续由租约机制恢复。

## 重试退避

精确公式、参数选择与演进条件见决策 [0002：PostgreSQL 任务队列采用短事务领取、租约与至少一次执行语义](../decisions/0002-postgres-job-queue-leases.md#退避公式与默认参数)。当前实现使用：

```text
delay_seconds = min(WORKER_BACKOFF_MAX_SECONDS,
                    WORKER_BACKOFF_BASE_SECONDS × 2 ^ max(0, attempt_number - 1))
```

默认基础间隔为 5 秒、最大间隔为 300 秒且没有 jitter；第一次可重试失败等待 5 秒。`next_run_at` 从失败写回时刻加上该延迟，只承担失败重试，不是用户定时调度字段。

## 处理器与安全边界

处理器通过 `HandlerRegistry` 按固定 `job_type` 注册。未知类型、非法 payload、非对象结果和未映射异常均转为固定脱敏失败，不执行 payload 中的代码或动态导入。

当前唯一开放类型是 `diagnostic.lifecycle`，只允许立即成功、固定次数可重试失败后成功或固定永久失败。

API 不接受任意 URL、prompt、正文、代码或 `next_run_at`，不返回原始 payload 或内部 lease token；422 校验响应不回显原始请求 input。

## 幂等与至少一次语义

`(job_type, idempotency_key)` 的部分唯一索引是创建去重事实源。完全相同参数返回既有任务；同键参数漂移返回 409。租约恢复意味着任务是至少一次执行，未来 T005 处理器仍需使用文档 URL/内容哈希等业务唯一事实实现副作用幂等。

## 已执行验证

- 21 项常规自动化测试通过，另有 4 项显式 PostgreSQL 集成测试通过。
- 真实 API/Worker 验证成功、永久失败、一次重试后成功、达到最大尝试终止、查询、重复创建、参数漂移和手动重试允许/拒绝。
- 两线程并发领取单任务只返回一个租约；租约恢复创建第二 attempt，旧 token 写回返回 false。
- `001`、`002`、`003` 在开发库和 usage 库版本一致；usage 原始响应中画像、投递、AI 日志、任务均为空，任务/attempt 聚合为 0/0。
- Compose Worker 的 usage 配置输出 `usage study_for_job`，切回开发后 SIGTERM 日志确认优雅停止。

## 当前限制

- 单 Worker 默认 1 秒轮询、60 秒租约；参数可由环境调整，但没有吞吐自适应。
- 当前没有任务取消、进度百分比、批量依赖/DAG 或队列归档；阶段一不需要这些能力。
- 诊断记录保留在开发库用于交接复核；usage 未写入诊断记录。
