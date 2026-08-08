# MVP Markdown/JSON 事实关系导出

状态：已实现同步只读导出链路。

## 解决的问题与调用契约

`POST /api/exports/snapshots` 由用户页面显式触发，请求必填：

- `format`：`json | markdown`；
- `as_of_date`：用户可见且可修改的快照声明基准日期。

响应返回文件名、媒体类型、manifest 和内容。JSON 内容是规范事实关系快照；Markdown 内容只由同一快照按章节投影。两种格式共享同一个 `snapshot_fingerprint`，不会分别查询或维护两套事实分类。

接口在 `REPEATABLE READ, READ ONLY` 事务内同步聚合 PostgreSQL 当前业务状态。它不持久化导出、不创建 job/Worker、scheduler、cron、轮询、推送、通知或 Agent。页面打开、格式切换和日期变化都不生成；只有表单提交调用 API，下载则使用该响应创建浏览器临时文件。

## 快照模型与稳定性

顶层固定包含：

- `schema_version=study-for-job.fact-relations.v1`；
- `export_version=mvp.export.v1`；
- `trigger=explicit_request`；
- 显式 `as_of_date` 与 `snapshot_scope`；
- `fact_boundaries`、`collections`、`relationships`、集合/关系/分类计数、warnings、limitations；
- 对不含 fingerprint 字段的完整规范快照进行递归 key 排序后计算的 SHA-256 fingerprint。

集合按稳定业务 ID 排序；表达版本按父实体、版本号和 ID 排序；关系按 type 和稳定 relation ID 排序。相同 PostgreSQL 事实和相同日期输入不依赖当前时钟、随机数或页面内存，因此得到相同顺序和 fingerprint。

`as_of_date` 是显式声明基准，不是假历史重建。当前业务表没有完整时态历史，导出不会依据日期回滚或猜测过去字段值；该限制在两种格式中都可见。

## 覆盖的事实与关系

规范集合覆盖：

- 目标画像和投递记录，包含原始 stage、`key_date`、字段值和更新时间；
- 面经来源、文档/提交元数据、抽取 run、轮次、chunk、用户标注、问题候选和有界 evidence ref；
- 规范题、occurrence、当前 occurrence mapping 及 merge/split/equivalent 修订历史；
- 知识卡、用户掌握/复习状态与证据关联；
- 算法题外部来源、用户练习/复盘状态、规范题关联和 occurrence 需求信号；
- 项目基本信息、事实/草稿、来源、表达版本、确认状态、版本基线和情报关联；
- 实习基本信息、事实/草稿、来源、STAR/量化表达版本、确认状态、材料状态和情报关联。

统一 `relationships` 使用集合名与稳定业务 ID 作为端点，并提供稳定 relation ID。关系覆盖来源—文档—提交—抽取证据链、occurrence—规范题映射、映射修订、知识证据、算法规范题、项目/实习事实所有权、表达版本/基线、材料和情报关联，使消费者无需根据文本猜测回链。

当前 `applications` 和 `target_profiles` 之间没有持久化外键或关联表。导出分别保留两类事实，并固定返回 `NO_EXPLICIT_APPLICATION_TARGET_RELATION`；不会用公司、岗位或文本相似度伪造关系。

## 事实、草稿、表达、材料与情报边界

- 目标、投递及项目/实习壳层是用户维护事实。
- 知识/算法是用户维护状态，不等于客观能力证明。
- 项目/实习条目按 confirmation 和 origin 显式分为 confirmed、draft、ai_draft；confirmed 但由 AI 起草的内容仍保留 AI 起草来源分类。
- 项目/实习表达版本独立于底层事实；即使表达 confirmed，也固定标记不证明客观能力。
- 实习材料原样保留 `missing | draft | ready | verified`，不把准备状态改写为经历能力。
- canonical question、occurrence、mapping、association 和 frequency 统一是结构化需求信号；频率只由 occurrence mapping 计数，不是掌握度、难度、经历真实性或统一评分。
- 缺集合、缺关系和缺证据都产生空集合或 warning，不补写、不推断、不声明未证实能力。

assessment 是规则投影，不是导出事实源，因此未作为主体导出，也不会替代上述底层业务事实。

## 证据与正文边界

面经文档元数据明确剔除 `raw_content` 和完整 `cleaned_content`；提交元数据剔除原始用户正文。evidence ref 只在 SQL 中从 cleaned content 截取 `[start_char, end_char)` 对应的最多 240 字符，返回 quote hash、run/chunk/candidate/document/submission/source ID、来源 URL/host 和字符区间。

手动正文或缺少 URL 时保留文档、提交、片段和区间回链，并返回 warning。证据片段、occurrence 或情报关联本身不证明用户客观能力。

## 页面与降级状态

桌面“导出”页延续暖灰/森林绿、宋体标题、细边界和低饱和语义色。页面提供 JSON/Markdown 选择、日期、主动生成、集合/关系摘要、warnings、分类计数、limitations、完整 fingerprint 和下载动作。

首次进入、同步读取中、API 错误、空数据和成功结果分别呈现；错误不会清空已有成功快照。空快照仍保留版本、边界、warnings 和 fingerprint，不为填满文件创建事实。

## 验证边界与限制

当前只完成集合/关系覆盖、两格式同源、排序/指纹、分类边界、证据正文上限、主动触发、空错态和非范围的逻辑检查；没有执行测试、构建、迁移、API/数据库或浏览器运行态验证。

运行时 SQL/响应兼容性、真实数据规模、浏览器下载与长 Markdown/JSON 文件布局尚未验证，不能宣称链路已运行通过。当前同步全量导出面向单用户本地 MVP 规模；数据显著增长后，应先基于真实瓶颈评估流式响应或分片，但不能因此改变事实边界或两格式同源原则。
