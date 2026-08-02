# T009 验证与交接

## 结果

知识轨道最小闭环已完成：用户可创建、修改知识卡片，维护四级掌握状态，记录一次轻量复习并查看 due 列表；可将阶段二 `evidence_spans` 关联到卡片，API 返回 submission/document/source URL 与 quote 回链。用户字段与情报证据分离，未引入自动覆盖。

## 验证摘要

- 通过：`python -m py_compile backend/app/models.py backend/app/api/knowledge.py backend/app/main.py`。
- 未通过/未执行：`python -m pytest backend/tests -q`（环境缺少 pytest，报 `No module named pytest`）。
- 未执行：数据库迁移、API 运行态、页面人工验证；遵循阶段约束未执行 `npm run build`，未编写页面访问脚本。
- 应执行：`git diff --check`（提交前）。

## 交接边界

- 可依赖：`008_knowledge_track.sql` 会在应用启动迁移流程中创建知识轨道表；API 前缀为 `/api/knowledge`；证据仅能引用已存在的 `evidence_spans`。
- 禁止假设：semantic recall、embedding、pgvector、RAG、评分真相、定时推送均未实现；情报关联不等同于知识正确性。
- 下一步依赖：T010 可复用掌握状态过滤与桌面导航；T013 可在不改变 API/数据流的前提下沉静化视觉层级。
