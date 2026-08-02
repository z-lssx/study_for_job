# T005 实施计划

更新时间：2026-08-02

## 现状判断

- 当前工作树干净；`main` 位于 `f4f5a97`，相对 `origin/main` 领先 2 个已授权治理提交（`4f0a99d`、`f4f5a97`），必须原样保留。
- 现有 FastAPI、SQLAlchemy 2、psycopg 3、编号 SQL 启动迁移器和 development/usage 双数据库边界可直接复用。
- T004 已提供 `jobs`/`job_attempts`、短事务 `FOR UPDATE SKIP LOCKED` 领取、lease token、心跳、过期恢复、有界退避和 `HandlerRegistry`；队列是至少一次语义，不能替代业务幂等。
- 前端是 React/Vite 的桌面单页应用，采用高对比编辑部/作战台视觉语言与原生 CSS；本任务只增加“面试情报”入口，不重做全局导航或视觉系统。
- 当前依赖已经包含 `httpx`；HTML 到纯文本可用标准库解析器完成，暂无新增依赖的必要。

## Skill 对本任务的约束

- `frontend-design`：保持现有纸张、墨色、酸性强调色和编辑部排版语言，用“情报档案/采集台”形成明确页面语义；复杂度服从普通业务页面，不引入位图或全局重构。
- `supabase-postgres-best-practices`：唯一事实由约束和唯一/部分索引保证；并发创建使用 `INSERT ... ON CONFLICT`；外键列建立匹配索引；等值列在复合索引前；HTTP I/O 不持有事务或行锁。
- `frontend-testing-debugging`：页面完成后优先使用已提供的 in-app Browser，按“面试情报入口 → 提交 URL/正文 → 查看状态/详情 → 失败补正文或重试”的目标流执行页面身份、非空、错误遮罩、控制台、截图与交互核对。

## 最小数据模型与唯一事实

1. `interview_sources`：保存经来源适配器清理后的展示 URL、规范化 URL、主机和首次/最近提交时间；`normalized_url` 唯一，作为 URL 去重事实源。
2. `interview_documents`：保存首次成功写入的原始内容、内容类型、安全清洗正文、清洗算法版本、内容 SHA-256、采集方式和时间；`content_hash` 唯一，重复处理不得覆盖已成功原文。
3. `interview_submissions`：保存用户的一次逻辑输入、来源、手动正文或抓取响应、输入指纹、修订号、当前业务 job、稳定错误码/脱敏说明/可重试性、文档关联和审计时间。重复规范化 URL 或重复手动正文返回既有逻辑提交；失败补正文在同一提交上递增修订。
4. `interview_document_sources`：保存文档与来源的多对多关联；不同 URL 得到相同正文时只新增来源关联，不新增文档事实。

数据库约束限定输入方式、字段组合、哈希长度、修订号和错误字段组合；外键与列表/状态查询建立匹配索引。API 提交、输入事实持久化和业务 job 创建在同一短事务内完成，避免“有输入无任务”或“有任务无输入”。

## 状态与幂等边界

```text
提交 URL 或正文
  -> 规范化/校验并原子创建或返回既有 submission
  -> 创建 interview.ingest job（立即执行）
  -> Worker 按 submission_id + revision + input_fingerprint 校验快照
  -> URL：事务外执行 robots/网络/重定向/体积/类型校验与抓取
     正文：直接读取已持久化输入
  -> 纯文本清洗、内容规范化与 SHA-256
  -> 文档 ON CONFLICT(content_hash) 收口
  -> 来源关联 ON CONFLICT 收口
  -> 仅在 revision/fingerprint 仍匹配时关联 submission
```

- 用户状态由当前 `jobs` 持久事实映射为 `queued | processing | retry_wait | succeeded | failed`；submission 保存当前 job 与最近业务失败事实。
- job 幂等键为 `interview.ingest:{submission_id}:r{revision}`，payload 固定包含 `submission_id`、`revision`、`input_fingerprint`；处理器发现快照漂移时永久失败，不静默接受参数变化。
- 外部副作用只有公开页面和 robots 的只读 GET；租约恢复可能重复 GET，但数据库副作用由 URL、内容哈希和关联唯一约束幂等收口。
- 补正文只允许当前处理失败且尚未关联成功文档的 submission；成功原文和成功文档均不覆盖。

## 公开来源与安全边界

- 只开放代码 allowlist 中路径规则明确的公开文章来源适配器；URL 必须为 HTTP(S)，禁止凭据、非默认端口、私网/本机/链路本地/保留地址和不受支持路径。
- 来源适配器移除 fragment、跟踪参数和不影响文章身份的查询参数，输出不含敏感参数的展示/规范化 URL。
- robots 许可不明确或明确拒绝时不抓取，并保留补正文；不做登录、验证码、动态浏览器绕过或发现式爬虫。
- 每次请求前校验 DNS/IP，重定向逐跳重新校验并限制次数；设置连接/读取超时、最大响应字节、允许内容类型和最小正文长度。
- 原始 HTML 只进入数据库，不以 HTML 渲染；API 只返回规范化来源链接和清洗纯文本预览。日志、任务结果和错误只使用固定代码与脱敏说明。

错误分类至少覆盖：不支持来源、来源策略不可确认/拒绝、DNS/网络、超时、限流/临时上游、上游拒绝、重定向拒绝、体积、内容类型、正文过短、解析、输入漂移和未知错误；每类明确可重试性。

## 拟修改范围

- `migrations/004_interview_intake.sql` 与 `backend/app/models.py`：最小来源、提交、文档和来源关联事实及约束/索引。
- `backend/app/intelligence/`：URL 规范化、安全抓取、纯文本清洗、错误分类、仓储/服务和 Worker handler。
- `backend/app/api/intelligence.py`、`backend/app/main.py`、现有 handler 注册：提交 URL/正文、列表、详情、补正文、重新触发和固定 job type。
- `backend/tests/`：规范化/SSRF/解析/错误契约、API/仓储、并发去重、Worker 重放和参数漂移。
- `src/`：面试情报导航、数据 hook、API 调用、提交/列表/详情/补正文交互和现有风格内的页面 CSS。
- T005 工作区、`docs/tech-architecture/implementation/intelligence-pipeline.md` 及其索引；不修改总管维护的宏观状态文件。

## 实施步骤

1. 落迁移、ORM 和领域常量，先用数据库约束固定唯一事实与并发边界。
2. 实现 URL 规范化、来源适配、robots 与 SSRF/资源限制、HTML 纯文本清洗和稳定错误映射。
3. 实现短事务提交/补正文/重试、业务 job 创建、处理器快照校验和文档/来源幂等写入。
4. 接入 API 与 Worker 注册，确保 API/任务结果不返回原始 payload、HTML、敏感查询参数或内部租约。
5. 在现有桌面视觉系统中加入面试情报入口、URL/正文二选一提交、状态/失败、来源回链、安全预览、重复结果、补正文和重试。
6. 执行 Python 编译/测试、两库迁移、真实 PostgreSQL 并发/重放/隔离、API/Worker 生命周期、SSRF 边界和敏感信息检查。
7. 按 Browser Skill 使用可见浏览器完成人工交互和视觉核对，不写页面访问脚本，不运行 `npm run build`。
8. 完成技术事实与验证交接，检查 scoped diff/链接/空白/运行产物/敏感信息；满足全部条件后显式暂存本任务范围、提交并推送。

## 验证矩阵

- 迁移：全新/已有开发库、usage 库升级、版本一致和业务数据隔离。
- API：URL/正文成功、XOR 校验、列表、详情、重复提交、补正文、重新触发、非法字段不回显。
- Worker：成功、可重试/永久失败、重放/迟到写回、参数漂移、租约恢复后的业务幂等。
- 去重：等价 URL、相同正文、不同 URL 相同正文、并发竞争。
- URL 安全：协议、凭据/端口、私网/本机/链路本地、DNS、重定向、robots、超时、体积、类型、过短/解析和错误脱敏。
- 页面：桌面入口、两种提交、状态、来源、安全预览、失败补正文/重试、重复提示、控制台和基本小屏不崩坏。
- 安全：usage 无开发事实；API/日志/任务摘要无正文、HTML、lease token、凭据或敏感 URL 参数。

## 风险与控制

- 来源许可或外部网络仍可能阻止真实公开来源验证；若发生，只保留可审计 fixture/契约测试并明确标记“待补外部验证”，不声称真实成功。
- DNS 校验与 HTTP 客户端之间存在实现细节风险；默认来源 allowlist、逐跳校验、非公网拒绝和测试传输层共同缩小边界，不开放任意通用抓取。
- Worker 至少一次可能重复只读 GET；业务写入严格依赖唯一约束和条件更新，成功内容不覆盖。
- 不实现 T006-T008 的轮次、内容块、规范题、embedding、检索或频率统计。

## 非范围

- 不实现自动发现、批量抓站、登录/验证码/绕过、岗位爬取、用户定时能力、Scheduler、取消/DAG/吞吐自适应。
- 不实现 AI 结构化抽取、轮次/内容块/chunk、规范题、embedding/RAG、频率统计、准备轨道、策略报告、导出或 Agent。
- 不调用 ImageGen，不执行 `npm run build`，不无必要新增依赖或重构全项目。
