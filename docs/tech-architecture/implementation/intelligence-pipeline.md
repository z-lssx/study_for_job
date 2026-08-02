# 面经原始事实与可恢复入库链路

更新时间：2026-08-02

## 解决的问题

该模块把用户主动提交的公开面经 URL 和直接粘贴的正文接入同一条可追溯链路。它只负责保存来源、原始响应/输入、清洗正文、稳定处理状态和失败恢复事实，不负责结构化抽取、分块、检索或统计。

## 数据流

```text
URL 或正文提交
  -> 规范化并在短事务中创建/命中 submission 与 interview.ingest job
  -> Worker 校验 submission_id + revision + input_fingerprint
  -> URL 路径在事务外检查 robots、DNS/IP、重定向和资源限制后只读 GET
  -> HTML/文本清洗为纯文本并计算 SHA-256
  -> 锁定 submission 并再次校验快照
  -> content_hash upsert 文档、upsert 来源关联、关联 submission
  -> T004 Worker 以 lease token 写回 job 结果
```

外部副作用只有公开 robots 和文章页面的只读 GET。数据库事务不跨越网络 I/O。

## 持久化事实

- `interview_sources`：安全展示 URL、规范化 URL、主机、首次/最近提交时间；`normalized_url` 唯一。
- `interview_submissions`：用户逻辑输入、初始/当前采集方式、原始输入/响应、输入指纹、修订、当前 job、错误事实、处理时间和成功文档关联。
- `interview_documents`：首个成功原始内容、类型、清洗正文、清洗版本、内容哈希、采集方式和时间；`content_hash` 唯一。
- `interview_document_sources`：内容事实和来源的多对多关联；复合主键避免重复关联。
- `jobs`/`job_attempts`：沿用 T004 的队列、尝试、租约、退避和恢复事实。

状态由当前 job 映射为 `queued | processing | retry_wait | succeeded | failed`。submission 的原始输入先于执行持久化；失败不会删除输入，成功后不允许补正文覆盖。

## 幂等与并发边界

- URL 身份是去除 query/fragment、统一主机/协议/路径后的规范化 URL。
- 手动正文身份是规范化纯文本的 SHA-256；部分唯一索引只约束初始手动提交。
- 业务内容身份是清洗正文的 SHA-256；不同来源可以关联同一文档。
- job 身份是 submission 与修订组合，payload 还携带输入指纹；同一幂等键出现不同参数由 T004 队列拒绝。
- handler 在外部 I/O 前校验快照；完成事务先 `SELECT ... FOR UPDATE` 锁定 submission，再次校验修订和指纹，然后才 upsert 文档。重复或迟到写回只能返回既有成功文档，不能覆盖内容或留下孤立事实。

## 公开来源与 SSRF 边界

当前仅支持博客园公开文章路径。输入只允许 HTTP(S)，拒绝 URL 凭据、非默认端口、不支持主机和路径。持久化及返回的来源 URL 已移除查询参数和 fragment。

抓取要求运行时 `robots.txt` 明确允许；robots 不明确或拒绝即停止，并保留补正文能力。每个目标和重定向都重新执行来源规范化与 DNS 解析，所有解析地址必须为公网地址；私网、本机、链路本地、保留和其他非公网地址均拒绝。重定向最多 3 次；连接/读取超时为 5/12 秒；页面最大 2 MiB、robots 最大 64 KiB；仅接受受支持文本类型；原始 HTML 从不直接渲染。

来源 allowlist 显著缩小 DNS 解析与实际连接之间的 TOCTOU 风险，但当前 HTTP 客户端未绑定预解析 IP。开放第二个来源前必须重新审查其许可/robots、域名控制和这一解析边界，不能把现有适配器假设为通用爬虫。

## 错误与恢复

错误以固定 code、脱敏 message 和 retryable 持久化及返回。网络、超时、限流和临时上游失败可沿用 T004 退避，也允许终态后手动重试；来源/robots 限制、协议/地址、内容类型、体积、正文过短/无效和解析失败属于永久失败，只允许补正文。补正文递增原 submission 修订并切换为 `manual_fallback`，来源关联仍保留。

API 不返回完整原始输入/HTML、job payload、lease token、凭据、敏感查询参数或内部异常。页面只使用清洗纯文本预览。

## 已验证事实

- 全新库、已有 development 和 usage 均应用 `001` 至 `004`；usage 的来源、提交、文档和 jobs 均为 0。
- Python 测试 41 个：33 通过，8 个显式 PostgreSQL 用例默认跳过；显式 PostgreSQL 矩阵 8/8 通过。
- PostgreSQL 用例覆盖并发相同正文、跨 URL 相同内容、Worker 重放、租约恢复、参数漂移、API 重试和迟到写回不留孤立文档。
- 真实公开博客园文章在运行时 robots 允许后抓取、清洗并入库；不存在页面稳定失败后通过补正文恢复。
- 可见桌面浏览器完成 URL、正文、失败、补正文、重复输入、详情、来源回链和安全预览验证，控制台无 warning/error。

## 当前限制

- 只有博客园一个来源适配器；其他站点安全拒绝并提示补正文。
- 正文清洗是确定性 HTML 到纯文本，不做 T006 的轮次或问题结构化。
- 已验证 1280px 桌面布局；基础响应式 CSS 存在，但当前浏览器 viewport 覆盖未生效，因此没有正式小屏截图证据。
