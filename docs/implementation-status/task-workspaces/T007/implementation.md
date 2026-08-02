# T007 实施记录：规范题、出现事实、人工修正边界与频率统计

状态：实现完成，验证与交接完成

## 已实现

- 新增 `migrations/006_canonical_questions.sql`，建立 `canonical_questions`、`question_occurrences`、`question_occurrence_mappings` 和 `question_mapping_revisions`，以外键、CHECK、唯一约束和查询索引固定不可污染 occurrence 与映射历史边界。
- 新增 `backend/app/intelligence/normalization/`：确定性文本归一化、规范题/出现事实 ORM、幂等刷新、频率查询、证据详情、合并/拆分/等价映射操作。
- 新增 `/api/intelligence/canonical-questions` 路由，支持刷新、列表/详情和三类人工修正；刷新同步执行，复用 T006 成功 extraction run，不新增 Worker 或 AI 调用。
- 新增面试情报页面规范题频率面板，显示出现数、文档数、人工映射标记、证据区间和原文链接，并提供合并、拆分、改映射入口。通过 `IntelligenceWorkspace` 包装现有 T006 页面，未继续膨胀已较大的 `IntelligencePage`。
- 新增归一化单测；保留 T006 抽取回归覆盖。

## 数据语义

`question_occurrences` 的唯一事实键按文档/轮次/规范化文本生成；同一文档/轮次重复刷新不重复计数。occurrence 不保存当前规范题外键，人工操作只更新 `question_occurrence_mappings` 并追加 `question_mapping_revisions`。频率从当前映射聚合，详情回链 document、submission、run、round、chunk 和 evidence span。

## 边界与未做事项

- 自动归一化保持保守，不做模型调用、语义相似度、embedding、pgvector、混合检索、频率快照或岗位/公司维度画像。
- 不进入八股/算法/项目/实习轨道，不做导出、定时任务或通用聊天。
- T005 robots/HTTPS/代理/DNS/隐藏文本/hash 四项延期风险未修改、未覆盖、未解决。
- 用户最新要求：本次交接后接下来的开发可跳过测试环节，直接进入实现；这属于后续执行偏好，不代表未执行的验证已通过。
