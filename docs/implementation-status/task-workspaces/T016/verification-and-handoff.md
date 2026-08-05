# T016 逻辑检查与交接：MVP Markdown/JSON 事实关系导出

更新时间：2026-08-06

## 完成结果与用户价值

已完成由用户主动触发的 MVP 事实关系导出。用户可在沉静式桌面工作台选择 JSON 或 Markdown、确认可见快照日期、主动生成一次同步只读快照，并在结果就绪后下载。两种格式共享同一规范关系模型和 fingerprint，使用户能带走底层业务事实、用户修订、确认/版本/材料状态、证据和必要关系，同时保留草稿、AI 起草、表达、情报信号与未证实能力边界。

导出不依赖页面内存或 T014 assessment 建议列表，不持久化报告，不定时生成，不推送，也不建立备份/恢复机制。

## `@frontend-design` 使用与影响

开始任何设计和编码前已完整读取 `C:/Users/zengw/.codex/skills/frontend-design/SKILL.md`。实现采用“克制、精确的档案式导出工作台”：延续暖灰/森林绿、宋体标题、细边界、低饱和语义色和受控留白；以输入控制、事实边界、快照摘要、warning 档案和下载动作建立层级。

格式选择使用两张克制的档案卡，成功结果用深色快照题头和森林绿下载动作建立单一视觉焦点；分类计数、limitations 和 fingerprint 按需展开。没有引入图片、泛紫渐变、炫技动效、新设计系统或全站重设计。

## 后端、前端修改范围与导出契约

- 后端：新增 `backend/app/api/exports.py`、`backend/app/export_service.py`，并在 `backend/app/main.py` 注册路由。
- 契约：`POST /api/exports/snapshots`；请求 `format=json|markdown`、必填 `as_of_date`；响应返回 file name、media type、manifest 和对应内容。
- 事务：在首个业务查询前设置 `REPEATABLE READ, READ ONLY`，同步聚合同一 PostgreSQL 当前状态快照。
- 前端：新增 `src/api/exports.js`、`src/components/ExportWorkspace.jsx`、`src/components/export.css`，并在 `src/main.jsx` 增加“导出”入口和页面切换。
- 稳定事实：新增 `docs/tech-architecture/implementation/export.md` 并更新 implementation 索引；过程与逻辑检查留在 T016 工作区。
- 未修改迁移、数据库表、T014 规则、T015 策略页面、四轨道现有 API/数据流、M004 管理计划、current/queue/program-status/roadmap 或 M004 handoff。

## Markdown/JSON 覆盖集合与关系

规范集合覆盖：

1. 目标画像、结构化字段、created/updated 时间。
2. 投递公司、岗位、stage、原始 `key_date`、动作、渠道、备注、链接和时间。
3. 面经来源、去正文的文档/提交元数据、抽取 run、轮次、chunk、用户标注、问题候选、有界 evidence ref。
4. 规范题、occurrence、当前 occurrence mapping、mapping origin/status/revision 及 merge/split/equivalent 修订历史。
5. 知识卡可述版本、用户笔记、掌握/复习状态、origin 和证据关联。
6. 算法题外部来源、平台、难度/标签、用户状态、卡点、复盘、练习/维护时间、规范题关联和 occurrence 需求信号。
7. 项目基本事实、project evidence、source kind/reference、origin、confirmation、表达版本、版本基线、确认状态和情报关联。
8. 实习基本事实、事实资产、source kind/reference、origin、confirmation、STAR/量化表达版本、版本基线、材料 `missing|draft|ready|verified` 和情报关联。

统一 relationships 使用集合名、稳定业务 ID 和稳定 relation ID。关系覆盖来源—提交—文档—抽取结构—证据、occurrence—规范题当前映射和修订、知识证据、算法规范题、项目/实习事实所有权、表达版本与基线、实习材料和情报关联。

当前 `applications` 与 `target_profiles` 没有持久化外键或关联表。导出分别保留两类事实，固定返回 `NO_EXPLICIT_APPLICATION_TARGET_RELATION`，不通过文本匹配猜测或制造关系。

## 事实、草稿、AI、表达、情报与未证实能力分类

- 目标/投递/项目/实习壳层：`user_maintained_fact`。
- 知识/算法：`user_maintained_state`，并固定 `supports_objective_capability=false`。
- 项目/实习事实：按 confirmation + origin 区分 `confirmed_fact`、`draft`、`ai_draft`；confirmed 且 AI 起草时保留 `confirmed_fact_with_ai_draft_origin`。
- 项目/实习表达：独立标记 confirmed/draft expression 和 AI 起草来源；即使 confirmed 仍固定不证明客观能力。
- 实习材料：保留原始准备状态，不改写为能力或经历完成结论。
- canonical/occurrence/mapping/association/frequency：`structured_intelligence_signal` / `structured_demand_signal_only`，不等同掌握度、难度、经历真实性或统一评分。
- 缺数据、缺关系、缺证据：空集合或 warning，不补写、不推断、不声明未证实能力。

## 主动触发、日期、稳定排序/指纹与无自动化结论

- 唯一 API 调用点为 `ExportWorkspace` 表单 `onSubmit -> submitExport -> createExportSnapshotRequest`。
- 页面 mount、格式 `onChange`、日期 `onChange` 均只更新本地状态；下载使用已返回内容创建临时 Blob，不调用第二次 API。
- `as_of_date` 可见、可编辑、必填并进入请求、文件名、manifest、规范快照和 fingerprint；服务不读取系统当前时钟决定导出内容。
- 集合按稳定 ID 排序，表达版本按父实体 + version number + ID 排序，关系按 type + stable relation ID 排序。
- fingerprint 对不含 fingerprint 自身的完整快照执行递归 key 排序的规范 JSON 后计算 SHA-256；format 位于外层响应，不进入快照，因此 JSON/Markdown 共享 fingerprint。
- 未发现 timer、轮询、scheduler、cron、Worker、job、通知、推送、Agent、持久化报告或自动备份路径。
- 日期表示“当前 PostgreSQL 状态针对该显式日期的声明”，不是历史时点重建；该限制两格式均可见。

## 证据回链、正文边界、空态与错误态

- `interview_documents` 导出剔除 raw/full cleaned content，`interview_submissions` 剔除原始正文。
- evidence ref 只在 SQL 中截取 `[start_char,end_char)` 对应的最多 240 字符，保留 quote hash、run/chunk/candidate/document/submission/source ID、source URL/host 和字符区间。
- 手动正文或无 URL 时仍保留文档/提交/片段回链并返回 `EVIDENCE_WITHOUT_SOURCE_URL`；没有 evidence ref 时返回 `NO_EVIDENCE_REFS`。
- 首次进入、同步加载、API 错误、空数据、warnings 和成功摘要分别呈现；失败不清空已有成功结果。
- 空快照仍保留 schema/export version、事实边界、warnings、limitations 和 fingerprint，不为填充文件创建事实。

## 唯一逻辑检查逐项结论

1. **导出集合/关系覆盖：满足。** 迁移中目标、投递、情报、知识、算法、项目、实习直接业务表均有规范集合；所有显式外键/复合关联均有稳定端点关系，未持久化的投递—目标关系明确缺失。
2. **两格式同源：满足。** 服务先生成一次 `snapshot`；JSON 返回该对象，Markdown 只接收该对象并投影，无第二套查询或分类。
3. **稳定排序/指纹：满足。** 查询、版本顺序和关系排序均有稳定末级 ID；规范 JSON 递归排序；无当前时钟和随机输入。
4. **事实/草稿/表达/情报/未证实能力分类：满足。** confirmation、origin、expression、material、mapping/frequency 的原字段和 boundary class 同时保留；表达和状态不宣称客观能力。
5. **用户修订与确认保护：满足。** 当前用户字段、mapping 修订、事实 origin/confirmation、版本历史/基线/confirmed_at、材料状态均原样导出；未用 assessment 或前端状态覆盖。
6. **证据回链和正文边界：满足。** 关系端点覆盖证据链；只查询有界 substring；没有 raw/full cleaned 正文进入响应。
7. **主动触发与无自动化：满足。** 唯一网络调用来自表单提交；无 mount 请求、timer、轮询、后台任务、持久化或推送。
8. **空态/错误态：满足。** 首次、加载、失败、空数据、warnings 与下载就绪分别处理，且失败保留旧结果。
9. **非范围：满足。** 未修改 T014/T015、迁移或四轨道数据模型；未引入 semantic recall、embedding/pgvector、RAG、LLM/Agent、自动备份/恢复、在线判题、同步、登录、多用户、岗位爬取、移动端专属能力或 T005 风险修复。

以上均为源码、迁移字段和契约的逻辑检查结论，不是测试、静态检查、构建、迁移或运行态验证通过。

## 明确未执行的全部项目

未编写或执行 pytest、单元测试、集成测试、E2E、测试脚本；未执行 Python/JS 静态语法检查、类型检查、lint、格式化验证；未执行迁移验证、API 运行态、数据库运行态、SQL 查询运行、页面行为测试、浏览器/截图验收；未运行 `npm run build`、`npm run check` 或任何其他构建。未用编译、类型、静态或构建检查替代并宣称测试通过。

Git scoped diff、敏感模式、暂存文件和工作树检查只用于提交控制，不是业务验证证据。

## 稳定事实文档、遗留风险与依赖边界

- 唯一稳定实现事实源：`docs/tech-architecture/implementation/export.md`；索引已更新。
- 可依赖：两格式同源模型、显式请求/日期契约、稳定排序/fingerprint、事实分类、关系 ID 和正文上限已在代码与稳定文档固定。
- 禁止假设：API/数据库/浏览器已运行验证；`key_date` 是面试日期；投递和目标存在隐式关系；frequency 是能力评分；confirmed expression 证明客观能力；AI 起草已成为用户事实；无证据项存在隐含证据；导出是历史恢复点或持久化备份。
- 遗留风险：SQL/响应运行时兼容性、真实数据规模、浏览器下载与长文件布局未验证；当前同步全量聚合面向单用户本地 MVP 规模，真实瓶颈出现后才可评估流式响应或分片。

## Git、推送、安全与工作树

- T016 实现提交：`bf9777b`（`feat: add explicit MVP fact exports`），只包含 11 个 T016 后端、前端、稳定文档和工作区文件。
- 提交前明确暂存文件列表与预期一致；限定 T016 路径的敏感模式扫描无命中；`git diff --cached --check` 仅作为提交控制无输出。
- 按正式流程执行一次 `git push origin main`，安全策略拒绝：当前 origin 是此前已标记为未验证的外部 GitHub 目标，推送会传输仓库累积提交。已立即停止，未重试、未改写远端/代理，也未使用替代路径绕过。
- 本交接记录将作为仅限 T016 工作区的本地提交；其最终 SHA、main 相对 origin/main 的 ahead 数和最终工作树状态由结构化回传记录，避免在提交内自引用不可知 SHA。

完成后等待 M004 验收；不创建下一任务、阶段总管、项目大总管或任何管理角色。
