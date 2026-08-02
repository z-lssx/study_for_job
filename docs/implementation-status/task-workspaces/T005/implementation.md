# T005 实施记录

更新时间：2026-08-02

## 已完成范围

- 新增 `004_interview_intake.sql`，以来源、逻辑提交、内容文档和文档—来源关联四类最小事实承载原始入库链路。
- 新增 `interview.ingest` 固定业务任务，复用 T004 的 `jobs`、`job_attempts`、租约、心跳、退避和迟到结果拒绝机制。
- 新增 URL/正文提交、列表、详情、补正文和重试 API；响应不返回原始 HTML、完整原始输入、job payload、lease token 或内部异常。
- 新增“面试情报”桌面页面，支持两种提交方式、状态台账、来源回链、安全纯文本预览、失败补正文、可重试失败重新触发和重复输入提示。
- 首个公开来源适配器仅接受博客园公开文章路径。抓取前要求运行时 robots 明确允许，并实施协议、凭据、端口、DNS/IP、重定向、超时、体积、内容类型和正文有效性检查。

## Skill 对实现的实际影响

- `frontend-design`：没有重做应用；新页面继续使用现有纸张纹理、黑色墨块、酸绿色强调和编辑部式大标题，把提交区、事实台账和详情预览组织成桌面三栏工作台。没有调用 ImageGen。
- `build-web-apps:supabase-postgres-best-practices`：URL、正文和内容事实都由 PostgreSQL 唯一/部分唯一约束收口；并发创建使用 `INSERT ... ON CONFLICT`；外键和列表查询具有匹配索引；HTTP I/O 不持有数据库事务。最终审阅还据此把提交行锁与快照校验移动到文档 upsert 之前，避免迟到 Worker 留下孤立文档事实。
- `build-web-apps:frontend-testing-debugging`：通过可见 in-app Browser 按真实用户流程检查页面身份、非空渲染、URL 成功、失败详情、补正文恢复、直接正文、重复提示、来源回链、安全预览、截图和控制台。没有编写页面访问脚本，也没有执行 `npm run build`。

## 核心技术决定

### 事实与幂等

- `interview_sources.normalized_url` 唯一；常见博客园 `http/https`、裸域/`www`、query、fragment 和尾斜杠等价形式统一为不含参数的 HTTPS URL。
- 手动正文先做 Unicode NFKC、换行和空白规范化，再以 SHA-256 指纹由部分唯一索引去重。
- 成功清洗正文以 `interview_documents.content_hash` 唯一；不同 URL 得到相同正文时只建立新的 `interview_document_sources` 关联，不复制文档。
- submission 保存初始/当前采集方式、原始输入或抓取响应、修订号、当前 job、稳定错误事实和成功文档。失败补正文仍在原 submission 上递增修订，保留来源。
- job payload 固定为 `submission_id + revision + input_fingerprint`，幂等键为 `interview.ingest:{submission_id}:r{revision}`。handler 在任何外部读取前校验快照；写入时再次锁定 submission 并校验，成功事实不可覆盖，迟到/重复写回不产生孤立文档。

### 来源与失败分类

- 首个适配路径为 `cnblogs.com`/`www.cnblogs.com` 的 `/用户/p/文章` 或 `/用户/articles/文章` 公共文章。
- robots 缺失、无法确认、拒绝，或响应声明 `noindex/none` 时安全拒绝；不登录、不解验证码、不执行浏览器绕过、不发现式爬取。
- 每跳重定向重新规范化、重新检查 allowlist 和 DNS/IP；任何解析地址不是公网地址即拒绝。连接/读取超时为 5/12 秒，页面上限 2 MiB，robots 上限 64 KiB，只接受允许的文本类型。
- 网络、超时、限流和临时上游错误可重试；来源不支持、robots/来源限制、协议/地址、内容类型、体积、无效正文和解析错误永久失败。所有错误只暴露固定 code、脱敏说明和 retryable。

## 实施中发现与处理

- 共享工作树启动时干净，但实际 `main` 相对 `origin/main` 领先 2 个授权治理提交，而任务描述写的是领先 1；全程保留 `4f0a99d` 和 `f4f5a97`，未执行 reset/restore/rebase/pull。
- PowerShell 直接构造中文 JSON 的一次开发样例受终端编码影响而被写成问号；后续浏览器输入中文正常，问题只影响该开发验证样例，不影响代码或 usage 库。
- 浏览器 viewport 覆盖没有在当前 in-app Browser 生效；桌面 1280px 与完整页面视觉已核对，移动端不是本任务正式范围，基础 CSS 断点保留但未形成真实小屏证据。
- 首次复跑容器测试时发现生产镜像不包含 `tests/`；改用只读挂载测试目录的临时 API 容器连接同一 PostgreSQL，最终显式集成测试通过。宿主机直连还遇到既有数据卷密码与 compose 当前声明不一致，未依赖该路径作结论。

## 范围控制

未实现自动发现、批量抓站、登录态、验证码绕过、岗位爬取、Scheduler、取消/DAG、AI 抽取、轮次/内容块、规范题、embedding、RAG、检索或频率统计；没有新增依赖或第二套迁移系统。
