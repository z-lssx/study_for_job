# 已知问题与延期能力

本文件只记录会影响未来补丁判断的未解决事实。优先级表示风险而不是自动派发顺序；是否修复由用户在具体补丁中决定。

## 面经抓取与事实完整性

### 高：robots User-Agent 匹配可能 fail-open

当 `robots.txt` 只有与本应用 User-Agent 不匹配的规则组、且没有 `*` 或本应用规则时，当前解析路径可能默认允许抓取。这与“许可不明确即拒绝”的产品边界不一致。修复应要求匹配完整 UA token 或 `*` 组，无法确认时 fail-closed。

### 高：HTTPS 降级、环境代理与实际连接 peer 未完全受控

重定向仍可能从 HTTPS 降级到 HTTP；HTTP 客户端可能读取宿主环境代理；DNS 预检查结果没有绑定实际连接 peer。未来修复应拒绝 HTTP 降级、明确代理策略，并将请求绑定到已验证地址或校验实际 peer IP。

### 中：HTML 清洗可能保留隐藏文本

带 `hidden`、`aria-hidden="true"`、`display:none` 或 `visibility:hidden` 的节点可能进入 `cleaned_content`，污染后续抽取与证据。修复时应忽略这些节点和非正文元素，并递增清洗规则版本，避免同一内容身份混用不同清洗语义。

### 中：超长正文截断后计算 hash 可能误合并文档

当前长正文可能先截断再计算内容 hash；两个前缀相同但尾部不同的页面可能被误认为同一文档。修复应基于完整规范化内容计算身份，或将截断事实纳入指纹并禁止不完整内容互相合并。

上述四项风险详细历史可从 Git 中恢复已删除的 `docs/implementation-status/task-workspaces/T005/independent-review.md`；未来实现判断以本文件和 `tech-architecture/implementation/intelligence-pipeline.md` 为当前入口。

## 检索与 AI

- 同义/语义召回仍为 `unproven`。当前只有结构化过滤、精确匹配、FTS 和 `pg_trgm` 候选检索；embedding、pgvector 与真实召回质量评估尚未实现。
- RAG、多轮模拟面试、项目/实习深挖 Agent 和 LangGraph checkpoint 不属于当前已实现 MVP。
- DeepSeek-compatible 远程 provider 边界已实现，但真实模型标识、真实远程调用质量与计费仍未验证；密钥只能通过本机环境变量提供。

## 策略与首页

- 准备评估是用户显式触发的同步计算，没有持久化最近策略快照、`generated_at` 或 latest/detail 读取接口。
- 今日重点因此不会伪造可恢复策略，只展示真实轨道数量和投递临近节点。若未来需要跨刷新恢复，必须在 planning 领域增加明确的 PostgreSQL 持久化设计，不能借用浏览器存储或任务结果摘要。

## 运行与界面验证边界

- 最近一轮整版前端重设计只完成代码逻辑检查和 `git diff --check`，没有执行测试、构建、lint、类型检查、迁移、API/数据库运行态、页面启动、浏览器或截图验证。
- 1024×768 与 1440×900 的最终视觉效果、真实数据规模、浏览器下载和长内容布局仍未运行确认。
- 这些未执行项是用户确认的开发方式，不代表已经运行通过；未来只有用户对具体补丁明确要求时才补充相应验证。

