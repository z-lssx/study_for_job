# 项目实践证据轨道

状态：已实现当前 MVP 闭环。

## 事实、表达与情报的分层

- `projects` 保存项目名称、目标岗位、用户摘要和归档状态。
- `project_evidence` 保存背景目标、个人职责、团队边界、技术选择、取舍和可核实指标等事实陈述，同时独立记录来源类型、来源定位、`user | ai_draft` 来源标记和 `draft | confirmed` 核实状态。
- `project_expression_versions` 保存 30 秒、2 分钟表达和轻量追问树。每次创建分配项目内递增版本号，可引用同项目的基准版本；已确认版本不可覆盖，只能基于历史创建新版本。
- `project_intelligence_links` 显式关联规范题，可选绑定一条同项目证据，并保存用户编写的关联说明。返回 occurrence 次数和最多三条原始面经证据回链，但频率只作解释参考。

项目事实、表达版本和面经情报不共用同一事实字段。情报关联不会更新项目证据；AI 草稿只能先以待核实状态保存，当前实现不调用模型，也不自动生成或确认事实。

## 一致性与用户修订边界

版本号创建前锁定项目行，降低同项目并发创建冲突；唯一约束仍负责最终防重。数据库复合外键保证表达版本的基准版本、情报关联的项目证据必须属于同一项目。子资产创建、修订、确认或解除关联都会更新项目的 `updated_at`。

用户可修订项目基本事实和证据；证据的 `origin` 创建后不经 PATCH 改写。表达草稿可修订，确认动作单独发生且幂等，确认后的内容保持历史不可变。当前没有事实删除入口，项目可归档，避免轻易丢失经历证据。

## API 与桌面入口

- `GET/POST/PATCH /api/projects[/{id}]`：项目列表、创建、详情与基本事实修订。
- `POST/PATCH /api/projects/{id}/evidence[/{evidence_id}]`：创建和修订证据。
- `POST/PATCH /api/projects/{id}/versions[/{version_id}]` 与 `POST .../confirm`：创建、修订和确认表达版本。
- `POST/DELETE /api/projects/{id}/intelligence[/link_id]`：显式建立或移除岗位考点关联。

桌面“项目证据”入口提供项目证据包、事实修订、表达版本历史、确认动作和规范题/原文来源回链。列表、详情和长编辑使用当前工作台统一视觉层级，但不得改变本轨道的数据流。

## 验证与限制

已执行 Python `py_compile`、TypeScript `--noEmit --noCheck` 语法解析和限定范围 `git diff --check`。未执行 PostgreSQL 迁移、API 运行态或页面人工验证，未运行 `npm run build`，未编写页面访问脚本。

当前不包含 AI 生成调用、语义召回、embedding/pgvector、RAG、策略导出、多轮模拟面试或移动端专属导航。规范题关联依赖用户显式选择，不能视为岗位适配评分或项目事实证明。
