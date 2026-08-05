# T009 任务计划：知识轨道最小闭环

## 目标

在现有阶段二情报输入之上，提供知识点/卡片、轻量掌握状态、复习入口和可解释的情报证据关联；用户可以独立维护真实状态，AI/情报只能作为带来源的建议，不能覆盖用户事实。

## 进入条件与事实源

- 读取根 `AGENTS.md`、`README.md`、`docs/product-overview/README.md`、`docs/decision-log/README.md`、`docs/tech-architecture/README.md`、`overview.md`、`implementation/intelligence-*.md`、`implementation/retrieval.md`、`docs/implementation-status/program-status.md`、`current.md`、`queue.md` 和 `handoffs/M002-phase-two-handoff.md`。
- semantic recall、embedding/pgvector、RAG 均为 `unproven`，不得假设存在。

## 范围

- 复用现有 API/数据流，建立知识点/卡片与掌握状态的最小可维护边界。
- 支持用户编辑/合并/归档或等价的明确修订入口；保留原始情报来源、证据 span、submission/document 引用。
- 提供桌面最小入口与轻量复习动作；不得扩张为百科式标准答案或虚假单值评分。

## 非范围

不实现语义召回、向量索引、RAG、通用 Agent、定时推送、复杂知识图谱、移动端专属导航、在线判题或跨轨道策略报告；不运行 `npm run build`，不写页面访问脚本。

## 验收与验证边界

- Agent 自行选择与现有栈匹配的最小增量实现，并记录数据/状态边界及用户修订不污染原始事实的证据。
- 至少执行相关静态/单元验证和 `git diff --check`；API、迁移、页面行为验证按用户偏好非默认阻塞，未执行项必须如实记录。
- 完成 `implementation.md`、`verification-and-handoff.md`，提交并推送仅限本任务范围，回传 Thread/SHA/推送状态/遗留风险。
