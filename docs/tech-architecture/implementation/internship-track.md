# 实习经历与材料资产轨道

状态：T012 已实现最小闭环（2026-08-06）。

## 事实、表达、材料与情报分层

- `internships` 保存组织、岗位、起止日期、用户摘要和归档状态。
- `internship_facts` 保存职责、团队边界、技术/协作背景、困难、结果和量化指标等事实，同时独立记录来源类型、来源定位、`user | ai_draft` 来源和 `draft | confirmed` 核实状态。
- `internship_expression_versions` 保存 STAR 四段、量化表达和轻量追问树。版本号在同一实习内递增，可引用同实习基准版本；确认版本不可覆盖，只能创建后续版本。
- `internship_materials` 保存简历条目、工作样例、证明材料和参考链接的定位、备注及准备状态。
- `internship_intelligence_links` 显式关联阶段二规范题，可选绑定同一实习事实，并返回 occurrence 次数与最多三条原始面经证据回链。

实习事实、表达、材料和面经情报没有共享可改写字段。情报关联不会更新事实；AI 草稿只能先以待核实状态保存，当前实现不调用模型，也不会自动确认或生成指标。

## 一致性与用户修订边界

起止日期由 API 与数据库约束共同校验。表达版本创建前锁定实习行，唯一约束负责最终版本号防重；数据库复合外键保证表达基准版本和情报关联事实属于同一实习。子资产创建、修订、确认或解除关联都会刷新实习更新时间。

用户可修订基本事实、事实资产和材料状态；事实 `origin` 创建后不能经 PATCH 改写。表达草稿可修订，确认动作单独发生且幂等，确认后的内容保持历史不可变。当前没有事实删除入口，实习可归档，减少经历证据被误删的风险。

## API 与桌面入口

- `GET/POST/PATCH /api/internships[/{id}]`：实习列表、创建、详情与基本事实修订。
- `POST/PATCH /api/internships/{id}/facts[/{fact_id}]`：事实创建和修订。
- `POST/PATCH /api/internships/{id}/versions[/{version_id}]` 与 `POST .../confirm`：STAR/量化表达版本创建、草稿修订和确认。
- `POST/PATCH /api/internships/{id}/materials[/{material_id}]`：材料创建和准备状态修订。
- `POST/DELETE /api/internships/{id}/intelligence[/link_id]`：显式建立或移除规范题关联。

桌面“实习资产”入口提供经历选择、事实修订、STAR 版本历史、材料状态和规范题/原文来源回链。次要创建与编辑表单通过折叠收纳；T013 可继续统一全局视觉层级，但不得改变本轨道数据流。

## 验证与限制

已执行 Python `py_compile`、TypeScript `--noEmit --noCheck` 静态语法解析和限定范围 `git diff --check`。未执行 PostgreSQL 迁移、API 运行态或页面人工验证，未运行 `npm run build`，未编写页面访问脚本。

当前不包含事实生成、统一评分、岗位爬取、策略导出、Agent/RAG、semantic recall、embedding/pgvector、多轮模拟面试或移动端专属导航。规范题关联依赖用户显式选择，不能视为岗位适配评分或实习事实证明。
