# T012 验证与交接

## 结果

实习经历与材料资产轨道最小闭环已完成：用户可维护实习事实及来源/核实状态，创建和修订 STAR/量化表达草稿，确认后以不可覆盖版本保留历史，维护材料准备状态，并显式关联阶段二规范题和原始面经证据。事实、表达、材料与情报关联保持独立。

## 修改范围

- 数据/后端：`011_internship_track.sql`、实习 ORM/Schema/service、`/api/internships` 路由和应用注册。
- 桌面入口：实习 API 客户端、`InternshipsWorkspace`、分区组件、局部样式及现有顶栏入口。
- 文档：T012 实施记录、本交接、稳定实现文档 `internship-track.md` 和实现索引。

## 验证摘要

- 通过：`python -m py_compile backend/app/internship_models.py backend/app/internship_schemas.py backend/app/internships_service.py backend/app/api/internships.py backend/app/main.py`。
- 通过：`node node_modules/typescript/bin/tsc --noEmit --noCheck --allowJs --jsx react-jsx --target es2022 --module esnext --moduleResolution bundler src/api/internships.js src/components/InternshipsWorkspace.jsx src/components/internships/InternshipDetail.jsx src/components/internships/InternshipAssets.jsx src/components/internships/InternshipExpression.jsx src/components/internships/InternshipIntelligence.jsx src/components/internships/options.js src/main.jsx`。
- 提交前执行：限定 T012 文件的 `git diff --check`。
- 未执行：PostgreSQL 迁移、API 运行态、页面人工验证；遵循阶段边界未运行 `npm run build`，未编写页面访问脚本。

## 可依赖事实与风险

- 可依赖：实习基本事实、事实资产、表达版本、材料和情报关联拥有独立表/API；跨实习归属由 API 和复合外键共同保护；已确认表达版本不可 PATCH 覆盖。
- 可依赖：AI 草稿创建时只能是待核实；用户可通过事实 PATCH 或版本确认动作保留最终修订权。
- 可依赖：情报关联返回规范题 occurrence 数量、最多三条原始面经证据和来源 URL，并明确标记频率仅供参考。
- 风险：迁移/API/页面尚未运行态验证；列表按本地个人规模返回完整详情，未来资产和 occurrence 明显增大时再评估摘要列表与批量查询。
- 禁止假设：没有事实生成模型、统一评分、semantic recall、embedding/pgvector、RAG、岗位匹配评分、策略导出、多轮模拟面试或移动端专属导航；AI 草稿和面经频率均不是事实真相。

## 交接

- 任务：T012；恢复 Agent `/root/t012_internships_resume`。
- 前序真实基线：T011 提交 `36d62055204d17c7b7a80e844668fd5db7c5edfb`。
- 下一步依赖：T013 可在不修改 API、事实/表达分层和情报回链的前提下统一收纳与视觉节奏。
- 提交 SHA 与推送状态：提交完成后回报阶段总管。
