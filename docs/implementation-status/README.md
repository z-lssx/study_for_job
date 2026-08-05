# 实施状态目录

本目录是跨对话传递开发状态的唯一入口。内容可按阶段、领域和任务继续拆分，不要求所有进度放在同一个文件中。

- 本目录的状态文档：记录对应范围的已完成内容、阻塞和下一步依赖。
- `tasks/`：总管 Agent 创建的子任务说明和完成记录。
- `roadmap.md`：由项目大总管维护的宏观阶段路线图、进入/退出边界和跨阶段依赖。
- `queue.md`：由当前阶段总管维护的开发任务队列、依赖和状态。
- `task-workspaces/`：从 T002 起保存每个任务的计划、实施/审查过程和验证交接文档。
- `management-plans/`：每个阶段总管在派发任务前维护的阶段任务规划、完成边界和交接条件。
- `handoffs/`：阶段总管完成或中断阶段工作时提交给唯一项目大总管的正式交接文档。
- `program-status.md`：项目大总管维护的唯一宏观控制面，记录大总管状态、当前阶段、活跃阶段总管、验收证据和下一项允许动作。
- `archive/`：按阶段保存已被稳定事实源替代、但仍需追溯的过程文档。

项目大总管维护宏观控制状态与路线图；阶段总管维护当前阶段状态、队列、计划和交接；开发 Agent 只更新与本次任务相关的事实，不重新规划阶段或项目。

当前阶段四的首选入口：

- 阶段计划：`management-plans/M004-phase-four.md`
- 当前状态与队列：`current.md`、`queue.md`
- 正式交接：`handoffs/M004-phase-four-handoff.md`
- 稳定实现事实：`../tech-architecture/implementation/planning.md`、`../tech-architecture/implementation/export.md`
