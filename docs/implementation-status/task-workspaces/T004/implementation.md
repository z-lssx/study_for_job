# T004 实施记录

更新时间：2026-08-02

## 已实现事实

- 新增 `003_job_queue.sql`，以 `jobs` 保存任务当前状态、payload/结果摘要、优先级、尝试上限、重试时间、租约、错误、幂等键和审计时间，以 `job_attempts` 保存每次领取与执行结果。
- 数据库约束保证运行态必须具备完整租约、等待态必须具备 `next_run_at`、终态必须具备 `completed_at`，并限制状态、尝试次数、JSON 对象和错误长度。
- `(job_type, idempotency_key)` 部分唯一索引提供数据库级幂等；领取查询使用只覆盖活跃状态的部分复合索引，列表和 attempt 查询使用匹配排序的索引。
- `JobRepository` 在短事务内使用 `FOR UPDATE SKIP LOCKED` 领取一条到期任务；过期租约在同一事务内关闭旧 attempt，并在剩余尝试允许时生成新 lease token 与 attempt。
- 成功/失败写回必须匹配 `job_id + running + lease_token`，旧 Worker 即使迟到也不能覆盖新租约结果。可重试错误采用指数退避并受最大值约束，永久错误或耗尽尝试进入明确失败终态。
- 独立 Worker 提供处理器注册表、固定诊断处理器、租约心跳、未知任务类型/非法 payload 安全失败、未映射异常脱敏、信号驱动的优雅停止。
- 固定诊断 API 只允许 `success`、`retry_then_success`、`permanent_failure` 和有限整数参数；幂等键限制为安全字符，不接受任意 URL、prompt、正文或代码。
- 新增任务列表、详情（含 attempts）和受限手动重试 API；手动重试只允许尚有尝试余量的失败任务。
- API 不返回原始 payload 或内部 lease token；全局请求校验错误移除原始 `input`/`ctx`，避免 prompt、正文或凭据通过查询或 422 响应回显。
- Compose 新增独立 `worker` 服务；默认与 API 连接开发库，usage overlay 同时覆盖 API 与 Worker 到 `study_for_job`。

## 非显而易见的决定

- 队列采用至少一次执行语义。租约与心跳处理 Worker 崩溃，但未来有外部副作用的 T005 处理器仍必须自身幂等；lease token 只能保护任务状态写回，不能撤销已经发生的外部动作。
- `next_run_at` 不接受 API 输入：创建和手动重试固定写当前时间，只有可重试失败由 Worker 写退避时间，因此不会形成产品定时调度入口。
- 当前固定诊断使用无外部依赖的确定性处理器，不调用真实或 fake AI Gateway，避免用户把 provider 切为远程配置后由 Worker 意外产生付费调用。
- 过期租约已经耗尽最大尝试时，领取事务会把 attempt 标为 `lease_expired`、任务标为 `failed` 并记录固定原因，然后继续寻找下一任务；任务不会静默滞留在 running。

## 计划偏差

- 首次真实 PostgreSQL 生命周期测试发现 SQLAlchemy 默认把可空 JSONB 的 Python `None` 编码为 JSON `null`，被“只能是 SQL NULL 或 JSON 对象”的数据库约束正确拒绝。ORM 已对两个 `result_summary` 字段启用 `none_as_null=True`，保留严格数据库约束。
- 同时增强 Worker 主循环：单次 repository/数据库异常会被记录，当前租约留给恢复机制处理，进程继续轮询，不因一条任务退出。
- 修复后常规 21 项测试和显式 PostgreSQL 4 项集成测试全部通过；Compose API/Worker 正常运行，development/usage 迁移版本一致且 usage 任务/attempt 为 0/0。
- 实时 API 验证 422 不回显敏感 prompt，任务详情不返回 payload 或 lease token；仓库模式扫描只有 `.env.example` 的公开本地示例 DSN 命中，没有真实 key 或凭据。
