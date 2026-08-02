# T008 计划：混合检索、情报质量验收与阶段收口准备

## 目标

在 T007 已持久化的规范题、出现记录和证据回链上增加可解释的精确检索入口，并给出不夸大语义覆盖的情报质量状态。

## 范围

- PostgreSQL `websearch_to_tsquery`/`to_tsvector` 与 `pg_trgm` 候选检索；保留 document、submission、source、round、chunk、evidence span。
- 结构化过滤：轮次、问题字段类型、来源 host。
- 质量状态 API 与面试情报页面最小检索面板。
- 维护幂等边界、文档和 T008 交接。

## 明确不做

不引入 embedding/pgvector、不锁定供应商、不修改原始文本或 question_occurrences、不做岗位爬取、Cron、导出、DAG、多轮 Agent、全量安全审查或 `npm run build`。

## 验收依据

以 `docs/implementation-status/management-plans/M002-phase-two.md`、T007 交接文档和 `docs/decision-log/` 已确认边界为准。用户明确本轮不执行 API/查询/页面冒烟验证，验证文档如实记录未执行。
