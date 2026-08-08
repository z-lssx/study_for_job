# 面试情报规范题、出现事实与频率统计

状态：已实现本地业务闭环。

## 解决的问题

`question_candidates` 是原文抽取候选，不直接承担规范题身份或频率事实。规范题层使用确定性归一化形成可解释的初始聚合，原始出现记录负责计数，人工映射负责合并、拆分和等价修正。三者分层后，用户修订不会改写候选文本、字符区间或 evidence span。

## 数据流

```text
成功 extraction_runs
  -> question_candidates + evidence_spans
  -> canonical_questions（规范题身份）
  -> question_occurrences（不可覆盖的出现事实）
  -> question_occurrence_mappings（当前自动/人工映射）
  -> question_mapping_revisions（合并/拆分/等价修订历史）
  -> SQL 频率聚合 + 文档/轮次/块/evidence 回链
```

刷新由 `POST /api/intelligence/canonical-questions/refresh` 同步完成，输入只取 `extraction_runs.status = 'succeeded'` 的候选。它不调用远程模型，不创建 Worker 任务，不复制正文。

## 数据语义与幂等边界

- `canonical_questions` 以 `normalization_key` 唯一；自动规范题由 `created_by = automatic` 标记，人工拆分产生 `manual` 规范题。
- `question_occurrences` 同时保存 candidate、document、run、round、chunk、evidence span、原始文本、规范化文本和 `occurrence_key`。出现事实没有 `canonical_question_id`，因此不会被人工映射覆盖。
- `occurrence_key = sha256(document_id + round_ordinal（无轮次为 0） + normalization_key)`。同一文档/轮次的相同规范化问题只保留一条出现事实；不同文档或不同轮次可分别计数。
- `question_occurrence_mappings` 是出现事实到规范题的当前映射，自动刷新使用 `ON CONFLICT DO NOTHING`，不会覆盖已有人工映射。
- `question_mapping_revisions` 追加记录 `merge | split | equivalent` 操作、前后规范题和备注。合并只移动当前映射；拆分或等价修正也不更新 occurrence。
- 频率列表按当前映射聚合 occurrence 数量、文档数量、首末出现时间和人工映射数量；详情返回文档、submission、run、轮次、块序号、证据 span 区间及证据文本。

自动归一化仅执行 NFKC、大小写折叠、空白收敛、编号前缀和末尾问句标点处理，不执行语义相似度或 embedding 合并。无法确认的同义问题由用户通过页面人工合并或改映射。

## API 与页面

- `POST /api/intelligence/canonical-questions/refresh`：幂等刷新规范题和出现事实。
- `GET /api/intelligence/canonical-questions`：按规范题、出现数、文档数和时间返回频率列表，可按文本和轮次过滤。
- `GET /api/intelligence/canonical-questions/{id}`：查看出现证据和来源回链。
- `POST /{id}/merge`：将来源规范题的全部当前出现映射到目标规范题。
- `POST /{id}/split`：将选定 occurrence 映射到新的人工规范题。
- `PATCH /occurrences/{id}/mapping`：将单条 occurrence 改映射到已有等价规范题。

面试情报页新增“规范题与出现频率”面板。列表显示规范题和出现数，详情显示文档/轮次/块/evidence 区间，并提供合并、拆分和等价改映射入口。

## 验证与限制

历史实现验证覆盖 development/usage 迁移、重复刷新幂等、频率列表/详情、人工映射/合并/拆分和 occurrence 原始字段保护。

当前限制：尚未实现岗位/公司维度过滤、语义相似度、embedding、频率快照和批量治理。抓取许可、网络 peer、隐藏文本和长文本 hash 风险仍未解决，详见 `docs/maintenance/known-issues.md`。
