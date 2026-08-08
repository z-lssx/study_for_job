# 算法准备轨道

状态：已实现当前 MVP 闭环。

## 数据与用户事实

`algorithm_problems` 独立保存外部算法题、来源平台/URL、难度、标签、刷题状态、卡点、复盘文本和最近练习信息。状态为 `not_started | in_progress | solved | revisit`；所有状态和复盘均由用户创建或修订，不存在自动评分。

题目可选关联一个 `canonical_questions` 记录。API 返回规范题文本和基于 occurrence 的出现次数，并显式标记频率仅供参考；关联不会改写题目、状态或复盘事实，也不表示题目难度或用户能力得分。

## API 与轻量练习

- `GET/POST /api/algorithms`：列出或创建题目；列表支持 `status`、`difficulty`、`due_only` 过滤。
- `GET/PATCH /api/algorithms/{id}`：查看或修订题目。
- `POST /api/algorithms/{id}/practice`：记录一次练习，更新用户给出的状态、卡点、复盘和下次复盘日期，并递增练习次数。
- `GET /api/algorithms/random`：优先从到期且未解决的题目中随机返回一题；没有候选时从全部题目返回一题，题单为空时返回 404。接口始终保持单题边界。

## 边界与验证

当前没有在线编辑器/判题、账号同步、定时推送、统一评分、多轮模拟面试、语义召回、embedding、pgvector、RAG 或通用 Agent。已执行 Python 静态编译与 `git diff --check`；本地环境缺少 pytest，未执行数据库迁移、API 运行态和页面人工验证，未运行 `npm run build`。
