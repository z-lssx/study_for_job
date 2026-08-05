# T012 实施记录：实习经历与材料资产轨道

## 完成结果

在 T011 项目证据轨道之后新增独立的实习资产边界。用户可维护实习基本事实、职责/团队边界/技术与协作背景、困难、结果和量化指标；可按来源与核实状态修订事实，组织 STAR、量化表达和追问树版本，并维护简历条目、工作样例、证明材料和参考链接的准备状态。

## 数据与一致性

- `internships` 保存组织、岗位、起止日期、事实摘要和归档状态；结束日期不能早于开始日期。
- `internship_facts` 保存独立事实陈述、来源定位、`user | ai_draft` 来源和 `draft | confirmed` 核实状态。`origin` 创建后不允许 PATCH 改写，AI 草稿不能在创建时直接标为已确认。
- `internship_expression_versions` 保存 STAR 四段、量化表达和轻量追问树。创建版本前锁定实习行并分配经历内递增版本号；基准版本必须属于同一实习；确认后的版本不能覆盖，只能创建新版本保留历史。
- `internship_materials` 独立保存材料类型、定位、备注与 `missing | draft | ready | verified` 准备状态。
- `internship_intelligence_links` 显式关联阶段二规范题，可选绑定同一实习的一条事实。复合外键保护跨经历误绑；关联只返回 occurrence 频率和最多三条面经证据，不改写实习事实。

## API 与桌面入口

- `/api/internships` 提供实习列表、创建、详情和基本事实修订。
- `/api/internships/{id}/facts` 提供事实创建与修订。
- `/api/internships/{id}/versions` 提供表达版本创建、草稿修订和单独确认。
- `/api/internships/{id}/materials` 提供材料创建与状态修订。
- `/api/internships/{id}/intelligence` 提供规范题关联与解除，并保留 submission/document/source URL、轮次、字符区间和原文 quote 回链。
- 桌面顶部新增“实习资产”入口。工作区以左侧经历选择和右侧基本事实、事实资产、STAR 版本、材料、情报关联分区组织；次要创建和修订表单使用折叠收纳。

## 边界

本任务不调用模型，不自动生成或确认事实，不提供统一评分、岗位爬取、策略导出、Agent/RAG、semantic recall、embedding/pgvector、多轮模拟面试或移动端专属导航。规范题出现次数不表示能力、岗位匹配或经历真实性。

## 验证

- 已通过 `python -m py_compile`：实习模型、Schema、service、API 和应用入口。
- 已通过 TypeScript `--noEmit --noCheck`：实习 API 客户端、工作区及应用入口的 JSX/JS 静态语法解析。
- 提交前执行限定 T012 范围的 `git diff --check`。
- 未执行 PostgreSQL 迁移、API 运行态或页面人工验证；未运行 `npm run build`，未编写页面访问脚本。
