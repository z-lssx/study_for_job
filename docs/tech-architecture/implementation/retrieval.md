# 面试情报混合检索与质量状态

状态：T008 已实现（未执行本轮冒烟验证）

## 数据流与回链

`GET /api/intelligence/search` 只读 `question_occurrence_mappings`、`canonical_questions`、`question_occurrences`、`interview_documents`、`interview_submissions`、`interview_sources`、`interview_rounds`、`document_chunks` 与 `evidence_spans`。每条结果保留规范题、occurrence、submission、source、document、round、chunk ordinal/block type、evidence span 区间与从 cleaned content 截取的 evidence text。

## 检索路径

结构化过滤先应用 `round_ordinal`、`field_kind` 和 `source_host`。文本路径按以下稳定顺序返回：

1. `exact_term`：规范题、raw/normalized 文本的 `ILIKE` 包含匹配。
2. `full_text`：PostgreSQL `plainto_tsquery('simple')` 与 `to_tsvector`。
3. `trigram_candidate`：`pg_trgm` similarity 达到 0.18 的措辞相近候选。

结果带 `match_path` 和解释文本；trigram 不改写规范题或出现事实，也不代表已完成同义语义召回。未选择 embedding 供应商或 pgvector，待真实查询样本达到可评估质量后再单独决策。

迁移 `007_intelligence_search.sql` 建立 pg_trgm 扩展、规范题/出现原文 trigram GIN 索引和出现文本 FTS GIN 表达式索引。检索是只读幂等操作，重复请求不会产生写入或副作用。

## 质量状态

`GET /api/intelligence/quality` 返回文档、成功抽取 run、occurrence、canonical、evidence span 与 mapping 数量。当前以透明阈值（文档少于 3 或 occurrence 少于 10）标记 `insufficient_data`；无论数据量如何，embedding/pgvector 为 `not_configured/not_selected`，同义召回为 `unproven`。该状态是风险提示，不是对原作者答案或覆盖率的推断。

## 页面入口

面试情报工作区的 `04 / RETRIEVAL DESK` 提供查询词、轮次、问题/追问、来源 host 过滤，并在结果卡片内展示来源 URL、submission/document ID 前缀、round、block 和 evidence span 区间。
