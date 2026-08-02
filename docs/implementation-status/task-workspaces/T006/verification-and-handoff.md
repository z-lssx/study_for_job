# T006 验证与交接

更新时间：2026-08-02

## 状态与用户能力

已完成。用户可在已有成功面经文档详情中主动触发原文标注，查询版本化运行状态，查看轮次、内容块类型、问题/追问候选、字符区间和纯文本证据；可保存块级个人备注与人工校验状态。原作者回答在页面明确标记为经验内容，不作为标准答案。

## 数据模型与状态机

- `extraction_runs` 以 `(document_id, input_fingerprint)` 幂等；fingerprint 绑定 T005 `content_hash`、`cleaning_version`、`interview-extraction.v1` 与 `deterministic-lines.v1`。状态为 `queued | running | succeeded | failed`，失败重触发递增 `trigger_revision`，成功事实不被失败覆盖。
- `interview_rounds` 保存顺序和 `[start_char, end_char)`；`document_chunks` 保存 `question | author_answer | interviewer_feedback | follow_up | process_description | unknown`、顺序、轮次和区间。
- `question_candidates` 保存问题/追问文本、稳定 candidate key、可选主题候选和区间；`evidence_spans` 为块/字段提供 quote hash 与回链区间；`extraction_chunk_annotations` 只保存人工备注/校验，不覆盖机器字段。

## AI Gateway / Worker 边界

本任务采用确定性本地抽取器，无远程 DeepSeek 调用、无新增 token/trace 账本；真实可配置模型名已知为 `DeepSeek-V4-Flash`、`DeepSeek-V4-Pro`，但本次不声称远程质量已验证。`interview.extract` 复用 `jobs/job_attempts` 与租约，输入只读取已成功文档的 `cleaned_content`、内容 hash 和清洗版本，不把 raw HTML、payload、租约或凭据送入 prompt。

## API、页面与文档

- API：`POST/GET /api/intelligence/submissions/{submission_id}/extractions`；`PATCH /api/intelligence/submissions/{submission_id}/extractions/chunks/{chunk_id}/annotation`。
- 页面：`IntelligencePage` 详情区新增 T006 状态、版本、类型标签、轮次、候选、证据区间、原文证据和分层备注。
- 技术事实源：`docs/tech-architecture/implementation/intelligence-extraction.md`。

## 验证矩阵

| 项目 | 结果 | 证据 |
| --- | --- | --- |
| Python 编译 | 通过 | 新增模型/API/抽取器/仓储/handler 编译通过 |
| 直接相关单测 | 通过 | T006 专项 6/6；全量现有后端 47 通过、8 个显式 PG 用例跳过 |
| 抽取确定性/类型/区间 | 通过 | fixture 两轮、八块、问题/追问候选与稳定 offsets |
| 失败不覆盖/可重触发 | 通过 | 首次外键错误失败无子事实；修复后同 run 重触发成功 |
| API 幂等/证据/备注 | 通过 | 重复触发 `created=false`、run/revision 不变；10 条 evidence；备注回读且机器类型不变 |
| migration development | 通过 | `005_interview_extraction.sql` 已应用，development fixture 1/8/2/10（run/chunk/candidate/evidence） |
| migration usage 隔离 | 通过 | `005` 已应用，usage run/chunk/evidence 为 0/0/0，随后切回 development |
| 页面首屏/控制台 | 通过 | in-app Browser 页面非空、身份正确、无框架错误覆盖层、error/warn 日志为空；截图完成 |
| 生产构建 | 未执行 | 按用户规则未运行 `npm run build` |
| 真实 DeepSeek | 未执行 | 本任务不做远程质量声称；模型名保留给后续受控 Gateway 配置 |

## T005 延期风险声明

T005 独立审查登记的 robots UA fail-open、HTTPS→HTTP/代理/DNS peer、不可见文本和截断 hash 四项安全/数据边界风险仍未解决；T006 未修改、未覆盖，也不应被交接写成已解决事实。

## T007 依赖边界与唯一下一步

T007 可依赖：成功 `interview_documents` 唯一身份、`cleaned_content`、`content_hash`、`extraction_runs` 版本与状态、轮次/块类型、候选文本和 `[start_char, end_char)`、`evidence_spans` 与人工备注分层。T007 不得假设：原作者回答是标准答案、未知块有确定语义、轮次必然存在、远程 DeepSeek 已验证，或 T005 四项延期安全风险已解决；也不得复制第二套文档身份。

唯一下一步建议：由 M002 对 T006 做阶段验收并决定是否续发 T006 补证，不派发 T007。

## Git 与线程

- T006 Thread：`019fc15b-ad7b-7033-8342-fb81094ebcbb`。
- 阶段总管 M002：`019fc0db-6ec7-7e72-a3bb-932bb078c328`。
- 提交 SHA、推送状态、`main/origin` 关系和最终工作树状态以完成提交后的消息为准。
