# 知识准备轨道

状态：T009 已实现最小闭环（2026-08-02）。

## 解决的问题

知识轨道将用户自己的知识卡片、轻量掌握状态和复习记录集中维护。卡片事实由用户编辑；面试情报只通过显式证据关联提供参考，不会覆盖标题、笔记或掌握状态。

## 数据与 API

- `knowledge_cards` 保存标题、可述版本（`prompt`）、用户笔记、`mastery_status`、复习次数及下一次复习日期。状态为 `not_started | learning | familiar | mastered`。
- `knowledge_card_evidence` 显式关联阶段二 `evidence_spans`。API 返回 evidence span、document、submission、source URL、字符区间及从 cleaned content 截取的 quote，保留来源回链。
- `GET/POST/PATCH /api/knowledge/cards` 提供列表、创建和用户修订；`GET /api/knowledge/cards/{id}` 返回卡片及证据；`POST /api/knowledge/cards/{id}/review` 只记录一次轻量复习动作并递增 `review_count`；`POST/DELETE /api/knowledge/cards/{id}/evidence[/span_id]` 管理证据关联；列表支持 `status` 和 `due_only` 过滤。

## 边界与降级

卡片不会自动由语义召回、embedding、pgvector、RAG 或通用 Agent 生成；`origin=intelligence_suggestion` 仅是显式标记，不改变用户事实。关联证据必须来自已入库的 `evidence_spans`，删除证据源会被外键保护。复习不计算分数，也不自动定时推送。

## 验证

已执行 `python -m py_compile`（models、knowledge API、main）和 `git diff --check`。未执行数据库迁移、API 运行态和页面人工验证；当前环境缺少 pytest（`No module named pytest`），未运行 `npm run build`。
