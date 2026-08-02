# T008 验证与交接

## 已完成能力

- 混合检索 API 与质量状态 API 已实现，结果保留 document/submission/source、round、chunk、evidence span 回链。
- 面试情报页面提供搜索词、轮次、字段类型、来源 host 过滤及来源/证据展示。
- 未选择 embedding/pgvector；同义问题仅通过 FTS/trigram 的可解释候选路径提示，未生成覆盖结论。

## 本轮未执行

按用户最新指示，未执行 API 冒烟、数据库查询冒烟、页面/浏览器冒烟、`npm run build` 或访问脚本。

已执行静态检查：`python -m py_compile backend/app/api/intelligence_search.py backend/app/intelligence/search.py` 与 `git diff --check` 均通过。

## 质量结论

质量状态固定披露数据量与证据覆盖事实：数据不足时标记 `insufficient_data`；当前检索能力为 `exact_and_candidate`；同义召回为 `unproven`。阶段三只能把规范题与证据链作为候选输入，不能把 trigram 候选当作语义事实。

## 延期风险与依赖

T005 已登记的 robots UA、HTTPS/HTTP、代理/DNS peer、隐藏文本和截断 hash 风险仍未解决，本任务未改动。阶段收口依赖 M002 复核本交接、汇总阶段退出条件并决定待验收状态。
