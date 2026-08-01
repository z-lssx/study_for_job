# T003 实施计划

## 现状判断

- T001 已形成 React/Vite、FastAPI/SQLAlchemy、PostgreSQL 与 Docker Compose 的本地闭环；默认开发库为 `study_for_job_dev`，使用库为 `study_for_job`。
- 当前迁移仅在 PostgreSQL 数据卷首次初始化时执行。T003 必须同时覆盖已有数据卷，因此除新增幂等 SQL 外，还需要 API 启动时的增量迁移入口。
- 前端是单页投递工作台，无路由库；管理页应复用现有头部、色彩与表单语言，以顶层视图切换融入导航，不引入通用后台框架。
- 后端现有业务入口保持不变；AI 能力将进入独立 `app.ai` 包和独立管理路由，业务调用方只依赖自有 Gateway 契约。

## 拟修改范围

- 数据库：新增 `prompt_scenarios`、`prompt_templates`、`ai_call_logs`，补充约束、外键和面向模块/场景/时间查询的索引；默认关键 prompt 属于产品配置，两库均加载，但不注入调用日志。
- 迁移：新增 `002_ai_gateway.sql`；增加带 advisory lock 和 `schema_migrations` 记录的启动迁移器；更新开发库初始化脚本，使全新双库与已有双库使用同一组 SQL。
- 后端：增加 Provider 协议、DeepSeek OpenAI-compatible 适配、确定性 Fake Provider、Gateway、错误映射、prompt 渲染/哈希、token 与 trace 日志、管理 API 和受限诊断 API。
- 前端：增加 AI 管理数据 Hook、prompt 编辑面板、token 聚合/最近调用面板和受限诊断操作；不增加聊天输入或供应商管理能力。
- 配置与文档：补充环境变量、README、架构实现记录、T003 状态与交接文档。

## 数据流与边界

```text
固定业务场景 + 代码控制变量/Schema
  -> PromptRepository 短事务读取当前模板
  -> Gateway 校验变量并渲染，计算 SHA-256 prompt 哈希
  -> Provider（fake 或 DeepSeek compatible）在数据库事务外调用
  -> CallLogRepository 独立短事务记录成功/失败、token、耗时与 trace
  -> 管理 API 只返回配置白名单、聚合统计和脱敏日志元数据
```

- API key 只由环境配置读取，使用 Secret 类型承载；不进入数据库、日志、API 响应或前端。
- 页面只可改 system/task 模板以及 `temperature`、`max_tokens`；场景 key、模块、变量白名单、Schema、安全规则、provider/base URL/API key 均由代码或环境控制。
- 诊断入口只有固定场景和成功/失败模拟开关，不接受自由文本，避免形成通用聊天入口。

## 实施步骤

1. 建立幂等增量迁移、ORM 模型和已有数据卷迁移入口。
2. 实现 Gateway、Provider、配置仓储、调用日志与错误类型。
3. 实现 prompt 管理、运行时状态、日志/聚合查询和受限诊断 API。
4. 实现桌面 AI 管理视图并接入现有导航。
5. 执行 Python 单元检查、迁移与双库验证、API 成功/失败与敏感信息检查、桌面人工验证。
6. 根据真实验证结果更新架构、状态、实施与交接文档。

## 验证方式

- `python -m unittest discover -s backend/tests -v`：Gateway fake 成功/失败、DeepSeek 错误映射、prompt 校验与哈希。
- `python -m py_compile ...`：后端新增模块语法检查。
- `docker compose config --quiet`，随后启动/重建服务（不执行 `npm run build`）。
- 在开发库和使用库分别检查迁移、原 T001 行数、prompt 默认配置和空调用日志；确认两库隔离。
- 通过管理 API 验证配置读写、参数白名单、fake 成功/失败、日志与按模块/场景聚合。
- 人工打开桌面页面，验证视图切换、编辑保存、诊断反馈、错误状态、统计和最近调用展示。
- 对仓库、API 响应和日志字段进行敏感配置检查。

## 主要风险

- 现有数据卷不会自动执行新增 init SQL：由 API 启动迁移器补齐，并用 advisory lock 避免并发启动重复执行。
- 外部调用不应持有数据库事务：配置读取、远程调用、日志写入严格分段。
- prompt 可编辑范围过大可能破坏未来业务契约：变量和参数白名单由代码校验，页面不暴露 Schema/安全/工具配置。
- DeepSeek V4 的实际模型标识和凭据当前未知：model/base URL 均由环境变量提供，默认 fake 完成本地确定性验证，不硬编码未验证型号。

## 非范围

- 不实现面经抓取/抽取业务、embedding、RAG、Worker、通用聊天、provider 管理、prompt 发布回滚、费用结算、多用户权限、Agent 或移动端专属能力。
- 不调用 ImageGen，不执行 `npm run build`。
