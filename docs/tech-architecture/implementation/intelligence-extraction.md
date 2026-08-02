# 面经原文标注与证据链

状态：已实现本地确定性链路

## 实际数据流

```text
成功 interview_documents.cleaned_content
  -> extraction_runs（schema/processor/input fingerprint）
  -> interview.extract job
  -> 轮次边界
  -> document_chunks（类型 + 字符区间）
  -> question_candidates（问题/追问 + 稳定 key + 字符区间）
  -> evidence_spans（块/字段证据）
```

抽取输入只读取 T005 已成功文档的清洗纯文本、清洗版本和内容 hash，不复制 raw/cleaned 正文。轮次和块顺序由确定性行规则生成；轮次不明确时块仍保留且 `round_id` 为空，无法分类的块为 `unknown`/`needs_review`。

## 数据与状态

- `extraction_runs` 唯一约束 `(document_id, input_fingerprint)`；fingerprint 包含内容 hash、清洗版本、`interview-extraction.v1` 和 `deterministic-lines.v1`。状态为 `queued | running | succeeded | failed`，失败重触发递增 `trigger_revision` 并保留旧运行。
- `document_chunks` 保存 `question | author_answer | interviewer_feedback | follow_up | process_description | unknown`、顺序和 `[start_char, end_char)`。
- `question_candidates` 仅保存问题/追问文本、候选主题和证据区间；原作者回答不会被转换为标准答案。
- `evidence_spans` 记录块/字段的稳定区间及 quote hash；`extraction_chunk_annotations` 仅保存个人备注和人工校验状态，不覆盖机器字段。

## Worker 与失败处理

`interview.extract` 复用现有 `jobs/job_attempts` 和 lease token。handler 在数据库事务外执行确定性抽取，成功时在一个短事务内重建当前运行的子事实并标记成功；失败只写固定脱敏错误。成功运行重放返回已有计数，不产生重复块/候选/证据。

## API/页面

- `POST/GET /api/intelligence/submissions/{submission_id}/extractions`
- `PATCH /api/intelligence/submissions/{submission_id}/extractions/chunks/{chunk_id}/annotation`
- 面经详情显示运行版本、状态、类型/轮次、问题/追问、字符区间和安全纯文本证据。

## 验证与限制

已通过 T006 确定性抽取和 handler 契约单测，以及现有后端单测集合。真实远程 DeepSeek 未调用；PostgreSQL 迁移/Worker 端到端和页面人工验证需在本地服务可用时补做。此链路不提供规范题归一化、频率统计或语义检索。
