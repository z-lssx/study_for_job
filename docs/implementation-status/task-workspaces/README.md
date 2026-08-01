# 子任务工作区

从 T002 起，每个子任务在独立目录中维护过程事实：

```text
task-workspaces/
  TXXX/
    plan.md
    implementation.md
    verification-and-handoff.md
```

职责：

- 总管 Agent 在派发前创建 `TXXX/` 目录并保存完整任务说明。
- 子任务 Agent 读取规则与任务文档后、修改代码前创建 `plan.md`，记录现状判断、拟修改范围、数据流或审查对象、步骤、验证方式、风险和非范围。
- 子任务 Agent 在执行中增量维护 `implementation.md`，记录已实现或已审查事实、非显而易见决定、迁移/兼容策略和计划偏差。
- 完成后创建 `verification-and-handoff.md`，记录命令、人工步骤、结果、未覆盖项、遗留风险、文档更新和下一步。
- 未完成任务要求的验证和交接文档时，不得将任务标记为完成。

T001 保留原有平面任务文档，不做迁移。
