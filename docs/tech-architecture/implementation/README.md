# 模块实现记录

本目录按领域记录已经实现的技术机制。一个模块形成稳定链路后再创建对应文件，例如：

- [AI Gateway 与调用账本](ai-gateway.md)
- [PostgreSQL 任务队列与 Worker](job-queue-worker.md)
- [面经原始事实与可恢复入库链路](intelligence-pipeline.md)
- [面试情报规范题、出现事实与频率统计](intelligence-normalization.md)
- [面试情报混合检索与质量状态](retrieval.md)
- [规则优先的准备评估与任务建议](planning.md)
- [MVP Markdown/JSON 事实关系导出](export.md)
- [桌面工作台壳层与真实路由](frontend-workbench.md)
- `experience-coach.md`
- `interview-simulation.md`
- [知识准备轨道](knowledge-track.md)
- [算法准备轨道](algorithm-track.md)
- [项目实践证据轨道](project-track.md)
- [实习经历与材料资产轨道](internship-track.md)

每份模块文档优先说明：

- 模块解决的问题
- 实际数据流与调用链
- 核心数据和状态
- 关键实现与失败处理
- AI 在何处使用、何处不使用
- 幂等、可追溯和降级方式
- 已执行的验证
- 当前限制与演进条件

只记录已落地事实，避免堆砌代码和未实现的设想。
