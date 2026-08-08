# AI Gateway 与调用账本

状态：已实现并完成本地确定性验证；SophNet key 已接入环境兜底，真实 DeepSeek 远程调用因模型标识尚未配置而未验证。

## 解决的问题

业务模块不直接依赖 DeepSeek、OpenAI SDK 或供应商响应格式，而只调用自有 `AiGateway`。系统提供少量关键 prompt 的可控配置、成功/失败调用日志和按模块/场景拆分的 token 账本；外部凭据缺失时由明确标识的 fake provider 完成同一契约的本地行为。

## 实际调用链

```text
业务模块 + 代码批准的 scenario/变量
  -> SqlPromptStore 短事务读取模板
  -> Gateway 校验变量、参数和启用状态
  -> 渲染实际 prompt 并计算 SHA-256 哈希
  -> Provider 在数据库事务外执行
  -> SqlCallLogStore 独立短事务记录成功或失败
  -> 管理 API 返回脱敏元数据与聚合统计
```

`AiProvider` 协议隔离供应商，当前实现包括确定性 `FakeProvider` 与 `DeepSeekCompatibleProvider`。后者只依赖 OpenAI-compatible `/chat/completions` 契约，默认 base URL 为 SophNet `https://www.sophnet.com/api/open-apis/v1`，model 由环境配置；API key 优先读取 `DEEPSEEK_API_KEY`，为空时兜底读取 `SOPHNET_API_KEY`。业务调用方在两者之间切换无需修改。

## 数据与查询

- `prompt_scenarios` 保存代码批准的模块、场景和变量白名单；`prompt_templates` 保存当前 system/task 模板、启用状态以及仅含 `temperature`、`max_tokens` 的参数对象。
- `ai_call_logs` 保存模块、场景、provider、model、状态、可用 token、耗时、prompt 哈希、trace ID、安全参数和脱敏错误；不保存 prompt 正文、请求正文、响应正文或凭据。
- `(module, scenario_key, created_at DESC, id DESC)` 组合索引覆盖状态、token、耗时和 model，服务于模块/场景时间账本；另有全局时间索引与 trace 索引。
- 开发库和使用库共用迁移与三条产品级 prompt 配置；只有开发库产生验证调用日志，使用库不注入样例或诊断日志。

## 失败处理与安全边界

- Provider 超时、认证、限流、上游 HTTP/响应格式和缺少配置均映射为稳定错误码；未知 provider 异常统一映射为安全错误，不把原始异常或请求内容写入响应和日志。
- 失败调用与成功调用使用同一 trace 和日志链路；token 不可用时保持 `NULL`，不伪造为真实计量。
- prompt 页面只能编辑模板、启停和两个参数。变量白名单由代码再次校验，输入输出 Schema、安全规则、工具权限、工作流和 provider 配置均不开放给页面。
- 受限诊断固定使用 `gateway_diagnostic` 和代码内置变量，只开放 fake 失败模拟布尔值，不接收自由文本。
- `SecretStr` 承载 `DEEPSEEK_API_KEY` 与 `SOPHNET_API_KEY`；运行时 API 不返回 base URL 或 key，日志参数也不包含它们。

## 增量迁移取舍

PostgreSQL init 目录只在数据卷首次创建时运行，不能覆盖已有数据卷。轻量启动迁移器维护 `schema_migrations` 与 SHA-256 校验，并在事务级 advisory lock 内串行应用编号 SQL。全新数据库仍由同一批 SQL 初始化，已有数据库由 API 启动补齐，因此开发库和使用库不会分叉。后续迁移出现复杂回滚或多服务独立部署需求时，再评估引入 Alembic；在此之前不维护第二套迁移事实源。

## 已执行验证

- 9 个 Gateway/provider/config 单元测试通过：fake 成功/失败、无正文泄露、非法模板、未知异常、OpenAI-compatible 结构化响应、超时、缺配置、SophNet key 兜底和显式 key 优先级。
- 开发库样例包含目标画像、投递记录、3 个 AI 场景及模板；fake 诊断日志和模拟 token 不代表远程服务故障或真实计费。
- 使用库为 0 条目标画像、0 条投递、0 条 AI 日志，仅包含同一迁移产生的 3 个场景和 3 个模板。
- 管理 API 对 `{api_key}` 未开放变量返回 422；仓库敏感值扫描无命中，日志参数中的 `api_key`、`authorization`、`base_url` 键计数为 0。
- 桌面页人工确认 provider、三个场景、编辑器、模块/场景筛选、聚合指标、错误数和最近 trace 正常展示；配置经页面成功写回 PostgreSQL。

## 当前限制

- SophNet base URL 与 key 注入已在 API 容器内验证，但 DeepSeek V4 模型标识、token 口径和远程错误体尚未通过真实请求验证。
- 当前只实现同步单次调用和少量关键场景，不包含重试、费用结算、发布回滚、聊天、批处理、Worker、RAG 或 Agent。
