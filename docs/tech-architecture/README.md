# 技术架构文档

本目录记录系统级技术设计、关键决策、已落地的实现机制，以及可用于项目复盘和面试表达的技术材料。

## 文档入口

- [总体技术架构](overview.md)
- [关键技术决策](decisions/README.md)
- [模块实现记录](implementation/README.md)
- [项目技术案例](project-case-study.md)

## 维护原则

- `overview.md` 只描述仍然有效的系统级设计，不记录每次开发过程。
- `decisions/` 记录有替代方案、有明确权衡、会影响后续实现的技术决定。
- `implementation/` 记录已经落地的模块机制、数据流、可靠性设计和验证方式。
- `project-case-study.md` 从面试视角提炼经过实现和验证的技术亮点，不把计划描述成成果。
- 文档采用增量维护，不因格式调整重写已有的有效决策。
