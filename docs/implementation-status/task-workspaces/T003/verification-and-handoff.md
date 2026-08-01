# T003 验证与交接

验证日期：2026-08-02  
结论：本地 fake、迁移、双数据库隔离、管理 API、调用账本和桌面管理页达到 T003 验收边界；SophNet key 兜底已完成后续接入，真实 DeepSeek 因模型标识未配置而未验证。

## 完成内容

- 自有 `AiGateway` 和 `AiProvider` 协议，业务调用方不依赖供应商 SDK/响应结构。
- 确定性 fake provider 与 DeepSeek OpenAI-compatible 适配；远程配置只读服务端环境。
- 三个代码批准场景：Gateway 受限诊断、面经结构化抽取、备战计划生成；仅开放模板、启停、`temperature` 和 `max_tokens`。
- PostgreSQL prompt 配置、成功/失败调用日志、token/耗时/hash/trace 与模块/场景聚合。
- 桌面 AI 管理页、固定诊断、错误反馈、统计筛选和最近 trace。

## 自动与 API 验证

### Python 契约测试

命令：

```powershell
cd backend
python -m unittest discover -s tests -v
python -m py_compile app\main.py app\config.py app\migrations.py app\models.py app\api\admin_ai.py app\ai\contracts.py app\ai\errors.py app\ai\factory.py app\ai\gateway.py app\ai\prompting.py app\ai\providers.py app\ai\repository.py
```

结果：9/9 通过，语法检查通过。覆盖 fake 成功/失败、失败日志不含 prompt、非法模板、未知 provider 异常安全映射、OpenAI-compatible token 解析、超时、缺配置、SophNet key 兜底和显式 key 优先级。

### Compose 与运行时

执行过：

```powershell
docker compose config --quiet
docker compose up -d --build api
docker compose restart frontend
docker compose logs --no-color --tail 80 frontend api
```

结果：Compose 配置有效；API 启动迁移后健康；Vite 8.2.0 正常启动，npm audit 为 0 vulnerability；近期容器日志无 Python traceback 或 Vite 编译错误。最终 `/api/health` 返回 `development / study_for_job_dev / ok`。遵守项目规则，未执行 `npm run build`。

### Gateway、日志与白名单

- `POST /api/admin/ai/diagnostics` 成功路径返回 fake、`local-deterministic-v1`、48 input + 8 output = 56 token、64 位 prompt hash 和 UUID trace。
- 失败模拟返回 HTTP 502、`fake_provider_failure` 和独立 trace；没有返回 prompt、请求正文或内部异常。
- 最终开发库聚合：6 次 fake 调用，3 成功、3 次主动失败模拟，144 input、24 output、168 total 模拟 token，平均 11.2 ms；失败是验收动作，不代表真实远程调用异常。
- 最近调用查询同时显示成功与失败状态、耗时、hash、trace 和安全错误码。
- 包含 `{api_key}` 的模板更新返回 HTTP 422 `模板包含未开放变量：api_key`，未修改持久化模板。

## 数据库与隔离验证

开发库 `study_for_job_dev`：

| 项目 | 数量 |
|---|---:|
| schema migrations | 2 |
| target profiles | 1 |
| applications | 6 |
| prompt scenarios/templates | 3 / 3 |
| AI call logs | 6（3 成功 / 3 失败） |

使用库 `study_for_job`：

| 项目 | 数量 |
|---|---:|
| schema migrations | 2 |
| target profiles / applications | 0 / 0 |
| prompt scenarios/templates | 3 / 3 |
| AI call logs | 0 |

结论：两个数据库共用结构和产品 prompt 配置；开发验证没有污染使用库，T001 开发数据仍为 1 条目标画像和 6 条投递。

## 桌面人工验证

在 `http://localhost:5173` 的桌面宽度人工操作并辅以浏览器工具：

- 主导航可切换到“AI 管理”，页面显示 fake provider、`local-deterministic-v1`、三个场景、配置编辑器、模块/场景筛选、指标卡、聚合行和最近 trace。
- 页面初次检查 `clientWidth = scrollWidth = 1265`，无横向溢出；错误数和成功/失败 trace 可见。
- 通过页面编辑器恢复并保存 Gateway 诊断模板，API 日志确认 PATCH 200，最终 PostgreSQL 中文内容正确。
- 容器重启后浏览器工具因本地 URL 安全策略拒绝再次访问，因此稳定 key 修复后的“配置已写入 PostgreSQL”瞬时提示未做第二次目测；源码、容器挂载和 Vite 启动日志已确认修复加载。此项作为剩余 UI 风险，不绕过浏览器安全策略。

## 敏感信息验证

- 仓库扫描真实 key/Bearer/非空 `DEEPSEEK_API_KEY`、`SOPHNET_API_KEY` 形式：0 命中。
- `ai_call_logs.request_parameters` 中 `api_key`、`authorization`、`base_url` 键：0 条。
- runtime、prompt、call API 不返回 API key；runtime 也不返回 base URL。
- `.env.example` 只有空占位，真实凭据未写入仓库、数据库、日志或前端。
- 最终同一固定输入的成功/失败日志使用相同实际 prompt 哈希；模板无法合法渲染时才记录模板级哈希。

## 关键技术决定

- 用自有协议隔离 provider，先以 `httpx` 实现最小 OpenAI-compatible 适配，不引入供应商 SDK 或 LangChain 依赖。
- 远程调用位于数据库事务之外；prompt 读取和日志写入分别是短事务。
- token 不可用时保存 NULL；不把失败调用伪造成 0 token 的真实计量。
- 实际渲染 prompt、参数和 model 共同参与 SHA-256；日志只留 hash 和安全元数据。
- 用启动迁移器覆盖已有 T001 数据卷，并以 advisory lock/checksum 防止并发重复和已执行 SQL 漂移。
- fake 是明确的本地 provider，固定输出不能作为真实业务事实；诊断 API 不接收自由聊天文本。

## DeepSeek 真实调用状态

因模型标识尚未配置而未验证。默认 base URL 已设为 SophNet，API 容器确认能够读取 `SOPHNET_API_KEY`，但没有输出或持久化密钥值。待 `DEEPSEEK_MODEL` 确认后，选择性执行一次固定诊断，确认远程 token 字段和错误体；`DEEPSEEK_API_KEY` 可作为显式覆盖。

## 遗留问题与风险

- 真实 DeepSeek 模型标识、接口兼容细节、token 口径、限流错误体与网络超时尚未外部验证。
- 当前没有自动重试；这是刻意的阶段一边界，避免诊断重试重复花费。未来业务接入时应按幂等性与错误码逐场景决定。
- 桌面保存成功提示在稳定 key 修复后未因浏览器安全策略二次目测，但持久化写入、组件源码和运行日志已验证。
- 管理端仍是单用户本地免登录边界；部署公网前必须增加认证和 HTTPS。

## 下一步建议

1. 有可用凭据时执行一次受控 DeepSeek 固定诊断，记录模型标识、token 口径与错误映射差异，不扩大成聊天入口。
2. 阶段一下一条链路优先建立 PostgreSQL 任务队列与 Worker；让未来面经抽取业务只依赖现有 Gateway。
3. 首个真实 AI 业务场景接入时补结构化输出 Schema 验证与场景级重试策略，继续保持代码控制契约。
