# T014 逻辑检查与交接

## 完成结果与用户价值

已完成规则优先的准备评估与任务建议后端链路。调用方可显式 POST 请求 `daily | weekly | pre_interview`，得到确定性 priority tier/order、稳定 item ID、目标、可读建议、reason codes/解释、source types、业务 ID、频率/投递边界、证据状态和最多三条可回链引用。系统不把不同量纲压成总分，也不会为缺数据填充虚构任务。

## 修改范围

- 后端：新增 planning API 请求契约与只读规则服务，并在 FastAPI 入口注册。
- 数据：未新增迁移、ORM 表或持久化计划；复用既有 PostgreSQL 事实，事务设为 `REPEATABLE READ, READ ONLY`。
- 文档：T014 plan/implementation/本交接；稳定事实 `docs/tech-architecture/implementation/planning.md` 及实现索引。
- 未修改前端、M004 计划、current/queue、program-status、roadmap 或 M004 handoff。

## 规则、tie-break 与证据契约

- 固定档位：`critical | high | medium | low`，不返回统一能力总分。
- 固定档位内顺序：模式动作 → 显式目标岗位文本匹配 → 轨道状态 → 有界投递弱信号 → occurrence 频率档 → 稳定 item ID。
- `as_of_date` 必填；单次请求使用固定只读快照且不返回生成时钟；响应包含 `planning.rules.v1` 与 `snapshot_fingerprint`。
- frequency 只取规范题 occurrence 聚合，只表示结构化需求；不能改变 priority tier，也不是掌握度、难度、经历真实性或能力评分。
- 只为最终返回项读取展示引用，每项最多三条；正文在 SQL 中截取最多 240 字符，保留 canonical/occurrence/evidence span/document/submission/source URL/字符区间。没有回链证据时明确返回 `no_linked_evidence`。

## daily / weekly / pre_interview 主动触发

- 入口：`POST /api/planning/assessments`。
- 请求：`mode`、必填 `as_of_date`、可选 `target_profile_id`；仅 pre-interview 可选 `interview_context={application_id, interview_date}`。
- 固定返回上限：daily 5、weekly 12、pre-interview 8；模式只改变稳定动作顺序、经历缺口档位和上限。
- API 同步返回，不创建 scheduler、cron、推送、自动循环、Worker job 或 Agent；响应显式标记 `trigger=explicit_request`。

## 事实、草稿、表达和情报边界

- 知识/算法只使用用户维护状态；mastered/solved 未到维护日期即排除，到期时只作为低档维护项或按本轨道到期规则处理。
- 项目/实习只有 confirmed 事实可作为确认事实引用；draft/ai_draft 只形成核实或补证据任务。confirmed 且 AI 起草的事实仍保留 `ai_draft_origin` 来源分类。
- 表达版本独立于事实；缺少确认版本可形成表达任务，但表达版本即使确认也不证明客观能力。
- 实习材料使用自身 `missing | draft | ready | verified` 语义；ready/verified 不作为未完成材料任务。
- 情报关联若没有绑定 confirmed 事实，只形成考点补证据任务；association、occurrence 和 frequency 均不会写成经历事实。

## 投递弱信号结论

现有 `applications.key_date` 是未标注日期类型的通用字段，完全不参与排序。只有请求明确提供 application 与 interview date、数据库 stage 为 `interview`，且 interview date 距 `as_of_date` 为 0 至 14 天时，投递上下文才可靠。可靠信号也只能对 application role 与项目 `target_role`/实习 `role_title` 确定性文本匹配的条目进行同档位次级排序；不能抬升档位，不能影响没有岗位字段的知识/算法任务。仅有 stage 或窗口外日期不会启用。

## 唯一逻辑检查逐项结论

1. 数据/状态边界：四轨道分别查询、分别解释；事实、草稿、表达、材料和情报字段没有交叉改写。
2. 规则复现性：日期显式、事务固定快照、查询和 tie-break 均有稳定末级 ID；无当前时间或随机数输入。
3. tie-break：实现顺序与响应 `sorting_contract`、稳定文档一致；投递和 frequency 都不能跨 priority tier。
4. 事实/草稿/情报分类：confirmed、draft、ai_draft origin、expression、material、frequency source types 明确；未证实内容不支持能力结论。
5. 投递弱信号上限：仅可靠临近面试启用，且只做经历岗位匹配后的同档次级排序；`key_date` 不使用。
6. 证据回链：展示引用有业务 ID、证据/文档/来源和安全片段；无证据显式降级。
7. 主动触发：只有调用方 POST 才生成；无持久化、调度、推送、循环或 Agent。
8. 无全量正文：策略候选只读结构化聚合；证据查询只返回最多 240 字符 SQL substring，不加载 raw/full cleaned content。
9. 非范围：未引入页面、导出、semantic recall、embedding/pgvector、RAG、LLM、多轮 Agent、四轨道统一改模或 T005 风险修复。

以上均为逻辑检查结论，不是测试、迁移或运行态验证通过。

## 明确未执行项目

未编写或执行 pytest、单元测试、集成测试、E2E、测试脚本、静态语法检查；未执行迁移验证、API 运行态、数据库运行态、页面行为、浏览器验收、`npm run build` 或任何其他构建。未用静态检查替代并宣称测试通过。

## 对 T015 / T016 的可依赖事实与禁止假设

可依赖：T015 可按上述 POST 契约显式选择模式、日期、目标和可选面试上下文，并直接展示 items/warnings/sorting contract；T016 可把该响应视为规则投影，但不应把它替代底层业务事实导出。模式、上限、reason/source/evidence 字段和弱信号边界已在稳定文档固定。

禁止假设：API/数据库已运行验证；投递 key_date 是面试日期；pre-interview 模式本身证明存在临近面试；frequency 是能力评分；表达版本或 AI 草稿是事实；无证据项拥有隐含证据；系统已实现定时生成、RAG、semantic recall、pgvector、Agent、页面或导出。

## 遗留风险与 Git

- 运行时兼容性、数据库查询计划和真实数据规模表现均未验证；当前同步聚合面向单用户本地规模，数据增长后才可基于真实瓶颈评估分页或预聚合。
- 当前情报表没有岗位/公司维度，frequency 只能作为显式关联规范题的通用需求信号，不能宣称目标岗位专属频率。
- 提交 SHA、push 结果、敏感信息检查和最终工作树状态在完成 Git 收口后向 M004 结构化回传；本文件所在提交只包含 T014 范围。
