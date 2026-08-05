# T016 实施记录：MVP Markdown/JSON 事实关系导出

更新时间：2026-08-06

## 当前状态

进行中。已完整读取 `frontend-design` Skill、根与目录级规则、指定治理/产品/决策/架构/状态文档、T014/T015 稳定 planning 事实与交接，以及目标/投递、情报、知识、算法、项目、实习直接相关稳定实现文档。后端规范快照、导出路由和前端主动导出工作台已完成首轮编码，正在做逻辑检查与文档收口。

## 已确认实现边界

- PostgreSQL 底层 MVP 业务表是导出事实源；T014 assessment 只可作为规则投影附加信息，本任务不把它作为导出主体。
- JSON 是规范关系快照；Markdown 必须由同一快照生成，不建立第二套查询或分类逻辑。
- `as_of_date` 必须由用户可见输入随请求传入；快照不使用隐藏系统时钟、随机数或自动触发。
- `applications.key_date` 仅导出原始未标注日期，不解释为面试日期。
- occurrence/association/frequency 是情报需求信号；项目/实习表达版本和 AI 起草来源不证明客观能力。
- 证据只保留已有引用、来源 URL、稳定 ID、字符区间和有界片段，不读取或输出全量面经正文。
- 本任务完全不进行测试、静态检查、构建或运行态验证，完成后只做逻辑检查。

## `@frontend-design` 设计方向

采用“克制、精确的档案式导出工作台”：延续暖灰/森林绿、宋体标题、细边界、低饱和语义色和受控留白；输入控制、快照摘要、边界说明与下载动作建立明确层级。技术元数据可按需展开，关键事实边界始终可见；不引入图片、泛紫渐变、炫技动效、新设计系统或全站重设计。

## 后端实现

- `POST /api/exports/snapshots` 接受必填 `format=json|markdown` 与 `as_of_date`；只有该 POST 调用会生成同步结果。
- 服务开始即设置 `REPEATABLE READ, READ ONLY`，从底层业务表读取同一事务快照；不读取 T014 assessment、不持久化快照、不创建 job/Worker/scheduler/推送。
- 快照顶层包含 schema/export version、`trigger=explicit_request`、显式日期、当前状态快照范围、事实边界、集合、统一关系、计数、分类计数、warnings、limitations 和 SHA-256 fingerprint。
- 规范集合覆盖目标、投递；来源/文档/提交元数据；抽取 run、轮次、chunk、用户标注、问题候选、证据；规范题、occurrence、当前映射和修订历史；知识、算法；项目事实/表达/情报关联；实习事实/表达/材料/情报关联。
- 所有集合按稳定 ID 或父实体 + version number + ID 排序；统一关系再按 type + relation ID 排序。指纹使用递归 key 排序的规范 JSON，不含当前时钟或随机数。
- JSON `content` 是规范快照对象；Markdown 只从该对象按章节和稳定顺序投影，二者共享同一 fingerprint。
- 文档/提交元数据剔除原始正文；证据查询只在 SQL 中截取最多 240 字符，并保留 run/chunk/candidate/document/submission/source/字符区间和 quote hash。

## 事实与关系分类

- 目标、投递、项目/实习壳层标记为用户维护事实；知识/算法标记为用户维护状态并声明不证明客观能力。
- 项目/实习事实根据 confirmation + origin 分为 confirmed、draft、ai_draft，以及 confirmed 但仍保留 AI 起草来源。
- 项目/实习表达版本独立标记为 expression；即使 confirmed 也保留 `supports_objective_capability=false`。
- 实习材料保留 `missing | draft | ready | verified`；情报频率统一标记 `structured_demand_signal_only`。
- 关系使用稳定 relation ID 连接来源、提交、文档、抽取结构、occurrence、规范题、映射修订、知识证据、算法规范题、项目/实习事实/表达/材料/情报。
- 当前投递与目标画像没有持久化关系；导出不做文本匹配推断，并始终返回 `NO_EXPLICIT_APPLICATION_TARGET_RELATION`。

## 前端实现

- 工作流导航增加“导出”入口；页面提供 JSON/Markdown 选择、可见且可编辑的日期、主动生成与后续下载两个明确动作。
- 页面打开、格式变化、日期变化均只更新本地控件；唯一 API 调用位于表单 submit。
- 首次、同步读取中、错误、空数据、warnings 和成功摘要分别呈现；失败不会清空已有成功结果。
- 下载使用本次响应在浏览器创建临时 Blob；不会触发第二次 API、服务端备份、自动生成或后台任务。
