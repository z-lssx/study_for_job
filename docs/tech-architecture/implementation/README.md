# 模块实现记录

本目录按领域记录已经实现的技术机制。一个模块形成稳定链路后再创建对应文件，例如：

- [AI Gateway 与调用账本](ai-gateway.md)
- [PostgreSQL 任务队列与 Worker](job-queue-worker.md)
- `intelligence-pipeline.md`
- `retrieval.md`
- `planning.md`
- `experience-coach.md`
- `interview-simulation.md`

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
