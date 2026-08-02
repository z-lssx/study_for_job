# T005 独立安全与数据一致性审查

审查日期：2026-08-02

审查角色：只读独立审查 Agent

固定比较范围：`f4f5a97..85d21b800bac36fc1ff5037763d4a5b94260ccc0`（仅 T005 业务改动、测试与文档）

明确排除：`2ee397b` 及其后的治理状态提交、阶段一既有代码（除非被 T005 新调用路径直接触达）。

## Skill 约束与审查方法

- 已完整读取 `code-reviewer/SKILL.md`。本次按其 OWASP A01/A03/A07、输入验证、错误脱敏、性能/资源上限、数据库唯一约束与测试充分性清单执行；没有可用的 SonarQube、CodeQL 或 Snyk 结果，故以差异人工审查和现有测试为主。
- `build-web-apps:supabase-postgres-best-practices` 未在当前线程暴露，按任务约定未等待安装；改用仓库既有 PostgreSQL 决策、迁移、ORM 和 T004 队列规范核对 `ON CONFLICT`、唯一事实、事务边界、FK/CHECK、行锁和至少一次语义。
- Codex Security 插件工具已暴露并登记了同一差异范围，但桌面扫描停留在等待用户 Start scan/关闭设置，未启动后续扫描阶段；本报告不把该交互状态当作业务结论，也不声称完成 Codex Security 全量扫描。

## 结论

**退回 T005，阻塞验收。** 发现 4 个 P1/P2 级问题会破坏来源许可、安全网络边界或 T006 的可靠事实输入；修复并补齐边界测试后再验收。

## Findings（P0 → P3）

### P1 — robots 对不匹配 User-Agent 规则 fail-open，可能绕过来源许可

- **位置**：`backend/app/intelligence/fetcher.py:176-183`。
- **触发场景**：`robots.txt` 仅包含 `User-agent: Googlebot\nDisallow: /`（或其他与 `study-for-job/...` 不匹配的组），没有 `*` 或本 UA 的 Allow。`urllib.robotparser` 对不匹配组默认返回允许；当前代码只检查“存在任意 User-agent”，随后 `can_fetch` 返回 `True`，仍会抓取文章。
- **影响**：与 T005/M002 明确的“robots 许可不明确即拒绝”相反，可在站点未授权自动处理时持久化原始 HTML，违反来源边界并使 T006 依赖未获许可的事实。
- **最小修复方向**：解析并要求与完整 UA token 匹配或 `*` 组；没有匹配组、只有不相关组、Allow/Disallow 语义不明确时统一 `source_policy_unavailable` fail-closed。保留 429/5xx 的 retryable 分类。
- **验证缺口**：现有 `test_robots_denial_is_permanent_and_safe` 只覆盖 `User-agent: * / Disallow: /`；应增加“仅不相关 UA”“空规则/无匹配组”“明确 Allow 与路径覆盖”测试，并断言文章请求未发生。

### P1 — 每跳仍可 HTTPS→HTTP 降级，且 HTTP 客户端信任环境代理/未核验实际 peer IP

- **位置**：`backend/app/intelligence/fetcher.py:47-52, 76-82, 125-141`。
- **触发场景**：初始 URL 被规范化为 HTTPS，但站点返回到同一 allowlist 主机的 `http://...` 重定向；`_assert_supported_target` 接受 `http`，随后 `httpx.Client` 直接发起明文请求。客户端未设置 `trust_env=False`，会读取 `HTTP_PROXY`/`HTTPS_PROXY` 等环境代理；DNS 预解析结果只用于 `is_global` 检查，实际连接由 httpx 再解析，未绑定解析地址或检查连接 peer IP。
- **影响**：TLS 完整性/机密性和“HTTP→HTTPS 规范化”保证失效；代理或 DNS 重绑定时，预检查的公网地址不等于实际连接目标，无法证明 SSRF 防线覆盖真实 socket。对原始事实而言，明文/错误 peer 可返回被篡改页面，污染 T006 输入。
- **最小修复方向**：每跳强制 `https`（至少拒绝文章和 robots 的 HTTP 降级）；禁用环境代理或显式注入受控代理；将请求绑定到已校验的解析地址（或使用连接后 peer-IP 校验的 transport），并覆盖 IPv4/IPv6 全部地址。若产品接受 allowlist 域名级残余 TOCTOU，需在文档和运行时配置中显式记录该边界，而不是默认为已解决。
- **验证缺口**：现有测试只覆盖不支持主机、私网 resolver 和一次重定向；没有 HTTPS→HTTP、代理环境、DNS 变更/实际 peer、robots 重定向的测试。应增加拒绝降级、`trust_env` 约束和绑定/peer 校验的可观测断言。

### P2 — HTML 清洗保留不可见文本，可能污染原始事实与 T006 输入

- **位置**：`backend/app/intelligence/content.py:62-70, 83-95`。
- **触发场景**：`hidden` 属性、`aria-hidden="true"`、`style="display:none"`/`visibility:hidden` 等节点不在 `_IGNORED_TAGS`，只要位于 `article/main` 或带 focus marker，就会进入 `focused`/`visible`；当前仅排除 script/style 等标签。
- **影响**：页面作者或注入内容可把用户不可见的提示、诱导文本、旧版本内容写入 `cleaned_content`，虽然 React 以文本渲染不会直接 XSS，但会破坏“安全纯文本事实”并给 T006 结构化/证据链带来污染。
- **最小修复方向**：在解析 start tag 时拒绝 `hidden`、`aria-hidden=true` 和明确隐藏 CSS；对 `meta/input/object/embed` 等非正文元素采用 fail-safe 忽略，并把规则版本递增，避免同一 hash 混用清洗语义。
- **验证缺口**：现有清洗测试只断言 script、nav、footer 被移除；应增加上述不可见属性、实体文本和危险链接文本的测试，并断言清洗结果不含隐藏标记内容。

### P2 — 清洗截断后计算 content hash，长页面可能误合并为同一文档事实

- **位置**：`backend/app/intelligence/content.py:25-39, 46-50`；`backend/app/intelligence/repository.py:272-303`。
- **触发场景**：抓取正文允许至 2 MiB，但 `normalize_plain_text` 先截断到 500,000 字符，再由 `content_hash` 计算唯一键。两个页面前 500,000 字符相同、后续内容不同，会得到同一 `content_hash`；第二个 submission 复用首个 `interview_documents`，其独有内容只留在 submission 原文而不进入 T006 的文档事实。
- **影响**：跨 URL 的不同原文被错误合并，违反“不同来源同内容才共享文档”的唯一事实边界，造成可恢复链路的信息丢失。
- **最小修复方向**：在完整规范化文本上计算 hash，再按上限拒绝/分段；若产品必须截断，需把截断状态纳入指纹并禁止将不同未完整内容视为同一文档。增加超长相同前缀、尾部差异和跨来源关联测试。
- **验证缺口**：现有去重测试均为短文本/相同完整 HTML，没有超过 500,000 字符的边界用例。

## 分项结论

- **SSRF/来源许可**：allowlist、userinfo/端口/路径、私网地址分类和每跳主机检查方向正确；但 robots 非匹配 UA fail-open、HTTP 降级、环境代理与实际 peer 未绑定是阻塞问题。IDNA/尾点/大小写/路径混淆的常规输入未见直接绕过，但不能替代连接目标校验。
- **内容与错误泄露**：API 序列化未返回 raw HTML、job payload、lease token 或内部异常；React 以文本节点渲染预览。不可见文本仍会进入 cleaned_content，需修复为事实污染风险。流式读取在 2 MiB/64 KiB 上限内生效，`Content-Length` 不是唯一防线。
- **数据库并发/唯一事实**：`normalized_url`、手动 fingerprint、`content_hash` 使用部分唯一索引和 `ON CONFLICT`，submission/job 在请求事务中创建；`complete` 锁 submission 并对文档/来源关联 upsert，成功文档不会被失败或迟到重放覆盖。长文本截断 hash 是上述唯一事实例外。
- **Worker 重放/迟到写回**：revision/input_fingerprint/current_job_id 双重校验、行锁与文档唯一约束能拒绝参数漂移并收敛至少一次重放；未发现孤立文档写回路径。仍需在修复网络和清洗边界后保持这些不变量测试。
- **迁移/双库一致性**：`004_interview_intake.sql` 的表、FK、CHECK、唯一/部分索引与 ORM 字段基本对应，开发/usage 迁移文件同源；本次未运行迁移写入或修改数据库。真实 PostgreSQL 集成无法验证（本机 127.0.0.1:5432 账号 `study` 密码认证失败）。
- **验证充分性**：常规套件 41/41 通过，但其中 8 个 PostgreSQL 集成在默认运行中跳过；显式开启后 4 个 T005 PG 用例均因数据库认证失败而无法执行。现有测试未覆盖上述 P1/P2 边界，也未完成真实来源复核。

## 执行记录与未执行项

- 已执行：`python -m py_compile`（T005 后端改动，通过）；`PYTHONPATH=backend python -m unittest discover -s backend/tests -v`（41 通过、8 跳过）；`backend.tests.test_intelligence`（12/12 通过）；只读静态差异、迁移/ORM/Worker 链路检查；仅用本地 fixture 复核隐藏文本和 robots 解析行为。
- 未执行：`npm run build`（按仓库规则未执行）；页面访问脚本/批量抓取（按任务规则未执行）；真实公开博客园请求；PostgreSQL 集成（环境认证失败）；Codex Security 后续扫描阶段（桌面设置未提交）。这些未执行项不降低已确认 findings 的严重级别。

## T006 依赖边界、剩余风险与唯一下一步

T006 **不可**依赖当前 T005 作为已验收安全来源输入；修复并验证 P1/P2 后，T006 才可依赖：成功 submission 关联唯一 `interview_documents`、`cleaned_content` 为安全纯文本、`content_hash` 稳定、来源可多对一关联、成功内容不可覆盖、失败可通过 `manual_fallback` 恢复。T006 不得假设任意站点均可抓取、robots 已允许所有 UA、清洗文本没有隐藏内容，或同一前缀即代表完整相同文档。

**对 M002 的唯一下一步建议：退回 T005，要求原 T005 修复并补齐上述边界测试后重新验收；本审查不派发 T006、不修改业务代码。**

## 交接元数据

- T005 Thread：`019fc0e8-de74-72b0-827c-3218a8f51f3e`
- M002 Thread：`019fc0db-6ec7-7e72-a3bb-932bb078c328`
- 审查基线：`f4f5a97`
- T005 提交：`85d21b800bac36fc1ff5037763d4a5b94260ccc0`
- 当前审查分支：`main`，审查前工作树干净；审查文档提交 SHA、推送结果与最终工作树状态在发送给 M002 的结构化交接中记录。
