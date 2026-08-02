# M002 阶段二正式交接：面试情报闭环

状态：待验收。

本交接已按 `docs/project-governance/DOCUMENT_LIFECYCLE.md` 完成稳定事实盘点、重复入口检查、索引修复和推送记录。阶段任务已完成，但退出条件 6 未满足；退出条件 7 按用户已确认的验证偏好不因 T008 未执行 API/数据库/页面验证单独阻塞。唯一下一步建议：项目大总管选择“退回同一阶段补齐”或“暂停”。

## 进入条件复核

阶段一已验收并通过 `handoffs/M001-phase-one-handoff.md` 交接；React/FastAPI/PostgreSQL/Compose、本地 development/usage 双库隔离、AI Gateway、至少一次 Worker 语义和手动正文降级入口均已存在。阶段二没有未决产品选择需要重新确认。

## 任务、Thread、提交与推送

| 任务 | Thread ID | 提交 SHA | 推送状态 | 结论 |
| --- | --- | --- | --- | --- |
| T005 原始事实与可恢复入库 | `019fc0e8-de74-72b0-827c-3218a8f51f3e` | `85d21b800bac36fc1ff5037763d4a5b94260ccc0` | 已推送 `origin/main` | 业务能力完成；4 项安全/数据边界风险延期 |
| T006 原文标注、结构化抽取与证据链 | `019fc15b-ad7b-7033-8342-fb81094ebcbb` | `7aef78460d21bc0d2c1f4830c8ab034c6742947d` | 已推送 `origin/main` | 业务能力完成 |
| T007 规范题、出现事实与频率统计 | `019fc264-355c-7082-a46c-e9e44d164951` | `57a0e58f41aa25ebbc5f2210e9cb11a201e7dfe6` | 已推送 `origin/main` | 业务能力完成 |
| T008 混合检索与质量状态 | `019fc2a1-fa11-7240-8ba2-ff56f39245f6` | `ce39915892db0b9eaba5c06ca1afa45d9ef39037` | 已推送 `origin/main` | 业务能力完成；同义召回仍未证实 |

## 稳定事实源

- [intelligence-pipeline.md](../../tech-architecture/implementation/intelligence-pipeline.md)：来源、原文、清洗正文、幂等、失败与补正文链路。
- [intelligence-extraction.md](../../tech-architecture/implementation/intelligence-extraction.md)：轮次、内容块、问题/追问、证据定位和抽取边界。
- [intelligence-normalization.md](../../tech-architecture/implementation/intelligence-normalization.md)：规范题、occurrence、映射修订和频率聚合。
- [retrieval.md](../../tech-architecture/implementation/retrieval.md)：结构化过滤、exact/FTS/pg_trgm 候选检索与质量状态。
- [current.md](../current.md)、[queue.md](../queue.md)：阶段级当前状态与任务队列。

阶段三可优先读取以上稳定事实源和本交接；任务工作区仅作为按需追溯证据，不再作为跨阶段首选入口。

## 阶段退出条件逐条结论

1. **公开来源或手动正文进入同一可追溯链路：满足。** T005 已形成统一 submission/document/source 处理链路，失败可补正文降级。
2. **重复 URL、相同内容和 Worker 重放不产生重复业务事实：满足（按已提供验证摘要）。** T005/T007 的唯一约束、upsert、occurrence 幂等和映射层修订边界已记录。
3. **失败状态、重试分类、脱敏原因和补正文/重新触发可用：满足（按 T005 交接）。**
4. **结构化题目、轮次、追问和证据来源明确，修订不污染原始频率事实：满足（按 T006/T007 交接）。**
5. **归一化与频率基于 occurrence，计数可回链文档和证据：满足（按 T007 交接）。**
6. **检索覆盖精确术语和不同措辞同义问题：未满足。** T008 提供 exact/FTS/pg_trgm 的可解释候选路径，但质量状态明确为 `synonym recall=unproven`；没有真实证据证明不同措辞的语义召回，不能用 trigram 候选替代证明。
7. **风险相称验证和情报质量结论：满足（按用户已确认偏好）。** T008 仅执行 `py_compile` 与 `git diff --check`，未执行 API、数据库/迁移、页面行为验证；用户已明确不需要补修或补做这些验证，后续业务开发优先，因此这组未执行项不单独阻塞条件 7。情报质量边界仍必须以 `insufficient_data`、`exact_and_candidate`、`unproven` 等已披露状态为准。
8. **DOCUMENT_LIFECYCLE 收口、交接、提交与推送：满足。** 稳定事实已集中到技术实现文档和本交接；任务文档保留唯一过程/验证证据；经盘点没有需要移动到 `archive/` 的材料，原因是现有 T005-T008 工作区仍含唯一验证、失败和决策追溯信息；阶段 README/索引已补充本交接入口；治理提交已推送且工作树干净。

## 未解决风险与明确禁止假设

- T005 独立审查登记的 robots UA fail-open、HTTPS→HTTP/代理/DNS peer、隐藏文本、截断 hash 四项风险仍未解决，未在本次收口修复。
- 不得假设同义召回已证明、embedding/pgvector 已选型、岗位/公司过滤存在、频率快照已建立，或原作者回答是标准答案。
- 前端后续优化方向保留：降低装饰、改善纵向版面节奏、使用折叠/抽屉/弹窗收纳次要内容；本次不追加实现。

## 当前工作树与治理提交

- 治理收口主提交：`4cd2344`；推送事实修正提交：`c714e64`；大总管暂停并完成推送提交：`c676e33`。
- 目标分支：`main`，已推送 `origin/main`。
- 交接时状态：工作树干净；`HEAD=origin/main=c676e33`，本地无领先提交。本次收口文档及事实修正已随大总管暂停提交到达远端。

## 唯一下一步建议

请项目大总管基于退出条件 6 未满足这一事实，选择：**退回同一阶段补齐同义召回证据，或暂停阶段**。M002 不创建 T009、下一阶段总管或新的管理权威。
