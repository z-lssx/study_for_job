# T011 验证与交接

## 结果

项目实践证据轨道最小闭环已完成：用户可以创建和修订项目基本事实，按来源与核实状态维护证据包，创建/修订表达草稿并确认不可覆盖的历史版本，以及显式关联阶段二规范题、项目证据和原始面经来源。用户事实、表达版本、情报 occurrence 三者保持分离。

## 修改范围

- 数据/后端：`010_project_track.sql`、项目 ORM/service、`/api/projects` 路由与应用注册。
- 桌面入口：项目 API 客户端、`ProjectsWorkspace`、局部样式和现有顶栏入口。
- 必要前序阻断修复：`src/api/intelligenceSearch.js` 两处字符串结束引号。
- 文档：T011 计划/实施/验证工作区、稳定实现文档 `project-track.md` 及实现索引。

## 验证摘要

- 通过：`python -m py_compile backend/app/project_models.py backend/app/projects_service.py backend/app/api/projects.py backend/app/main.py`。
- 通过：`node node_modules/typescript/bin/tsc --noEmit --noCheck --allowJs --jsx react-jsx --target es2022 --module esnext --moduleResolution bundler src/api/projects.js src/components/ProjectsWorkspace.jsx src/main.jsx`。
- 通过：限定 T011 文件的 `git diff --check`。
- 未执行：数据库迁移、API 运行态、页面人工验证；遵循阶段边界未运行 `npm run build`，未编写页面访问脚本。

## 可依赖事实与风险

- 可依赖：项目事实、证据、表达版本和情报关联拥有独立表/API；同项目归属由 API 与数据库复合外键共同保护；已确认表达版本不可 PATCH 覆盖。
- 可依赖：情报关联返回规范题 occurrence 数量与原始面经证据/来源 URL，且明确标记频率仅供参考。
- 风险：迁移/API/页面尚未运行态验证；列表按本地个人规模返回完整项目详情，若未来项目与 occurrence 大幅增长再评估摘要列表与批量查询。
- 禁止假设：当前没有事实生成模型、语义召回、embedding/pgvector、RAG、岗位匹配评分、策略导出、多轮模拟面试或移动端专属导航；AI 草稿和情报频率均不是事实真相。

## 交接

- 任务：T011；恢复 Agent `/root/t011_projects_resume`。
- 前序真实基线：T010 提交 `362a2fc`。
- 下一步依赖：T012 可复用“事实资产与表达版本分离、用户确认、来源回链”的边界实现实习轨道；T013 可在不修改 API/数据流的前提下统一收纳和视觉节奏。
- 提交 SHA 与推送状态：提交完成后回报阶段总管。
