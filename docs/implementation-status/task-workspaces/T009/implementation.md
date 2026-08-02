# T009 实现记录

## 进度

- 已读取阶段治理、产品、架构、M002 交接与 T009 计划文档。
- 计划实现知识卡片、用户掌握状态、复习入口及面试情报证据回链；不引入语义召回或 AI 覆盖用户事实。

## 变更记录

- 新增 `migrations/008_knowledge_track.sql`：`knowledge_cards` 与 `knowledge_card_evidence`，外键回链 `evidence_spans`。
- 新增 `KnowledgeCard` / `KnowledgeCardEvidence` SQLAlchemy 模型及 `/api/knowledge` 路由：卡片 CRUD、due/status 过滤、单题式复习记录、证据关联增删。
- 新增桌面知识复习入口 `KnowledgeWorkspace`、API 封装与样式；用户掌握状态由按钮推进，情报仅显示为证据数量。
- 更新技术事实源 `docs/tech-architecture/implementation/knowledge-track.md` 及实现目录索引。
