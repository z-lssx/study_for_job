# T003 实施记录

## 已确认的实现约束

- 已完整读取 `build-web-apps:react-best-practices` 与 `build-web-apps:supabase-postgres-best-practices` 的 `SKILL.md`，并针对本任务补读并行请求、稳定渲染、数据类型、约束、组合/覆盖/部分索引、游标分页与短事务规则。
- 现有 T001 工作树未提交且包含大量已有修改；T003 仅做增量修改，不清理或重置任何既有内容。
- AI 远程调用必须位于数据库事务之外；prompt 读取与调用日志分别使用短事务。
- 默认运行 provider 为确定性 fake；DeepSeek 的 base URL、model 与 API key 全部由环境提供，缺少配置时返回明确配置错误。

## 实施进度

- 已完成需求、规则、决策、架构、实施状态、T001/T003 任务文档和现有前后端/数据库结构盘点。
- 已新增 `002_ai_gateway.sql`：`prompt_scenarios`、`prompt_templates`、`ai_call_logs` 及面向模块/场景/时间、全局时间和 trace 的索引；三条 prompt 属于产品配置，两库共享且不包含样例调用。
- 已新增带 advisory lock、迁移 checksum 和 `schema_migrations` 的 API 启动迁移器；初始化脚本改为依次应用全部编号 SQL，覆盖全新和已有数据卷。
- 已实现 `AiGateway`、自有 provider/store 契约、fake provider、DeepSeek OpenAI-compatible provider、prompt 校验/渲染/哈希、错误映射与成功/失败日志。
- 已实现 `/api/admin/ai` 的运行时、prompt 查看/编辑、日志、聚合统计和固定诊断 API；响应与日志不返回凭据、base URL、prompt/响应正文。
- 已实现桌面 AI 管理视图并融入现有导航：三个关键场景编辑、成功/失败诊断、模块/场景筛选、30 天 token 指标与最近 trace。
- 已补充 9 个 Gateway/provider/config 单元测试。开发库、使用库、真实 API、容器日志和桌面视图均按风险完成验证；SophNet key 已接入容器，真实 DeepSeek 因模型标识未配置而未调用。
- 后续增量采用 SophNet 默认 base URL；API key 优先读取 `DEEPSEEK_API_KEY`，为空时兜底读取本地 `SOPHNET_API_KEY`，两者均使用 `SecretStr`。

## 开发中修正的问题

- 管理 API 最初没有把模板变量校验错误映射为 HTTP 422，非法变量会表现为 500；已在写入前捕获 `GatewayError` 并返回稳定 422，复测 `{api_key}` 被拒绝且数据库未变更。
- Prompt 编辑器最初用 `updated_at` 作为组件 key，保存响应更新后可能重挂载并清空反馈；已改为稳定的 `scenario_key`。
- 一次旧版 PowerShell 人工“原样回写”因本机 JSON 中文解码造成开发库单条诊断模板乱码；确认迁移源和另外两条模板正常后，已通过桌面编辑器恢复，最终数据库三条中文模板均正确。此问题未进入迁移或使用库。

## 最终实现边界

- 没有实现面经抓取/抽取业务、embedding、RAG、Worker、通用聊天、provider 管理、prompt 发布回滚、费用结算、多用户、Agent 或移动端专属能力。
- 未调用 ImageGen，未执行 `npm run build`。
