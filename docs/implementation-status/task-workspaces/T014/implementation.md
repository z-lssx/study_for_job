# T014 实施记录：规则优先的准备评估与任务建议业务链路

状态：编码、稳定文档和唯一逻辑检查已完成，等待 Git 收口。

## 已确认设计

- 采用同步、只读、显式请求的 planning API，不创建计划表、任务表、Worker job、scheduler 或 Agent。
- 输出使用稳定 priority tier、排序键和 reason codes，不生成跨量纲统一评分。
- 四轨道保持原状态语义；项目/实习的 confirmed 事实、draft/ai_draft 和表达版本分别解释。
- 结构化情报只读取规范题、occurrence 聚合和受限证据片段；频率仅是需求信号。
- 现有投递字段不能可靠证明面试日期。弱信号必须由明确请求的 application 与 interview date 共同建立，并保持有上限的次级影响。

## 实施进度

- 已完成治理、阶段、稳定实现文档和相关数据/API 边界读取。
- 新增 `POST /api/planning/assessments`，`daily | weekly | pre_interview` 均由调用方显式请求；`as_of_date` 是必填规则输入。
- 新增同步只读规则服务；请求事务使用 `REPEATABLE READ, READ ONLY` 固定跨领域事实快照，固定模式上限分别为 5/12/8；没有迁移、计划持久化、Worker job、scheduler、推送或 Agent。
- 输出包含稳定 item ID、轨道、可读建议、目标、priority tier/order、reason codes/解释、source types、业务 ID、frequency/application 信号、evidence status/ref、限制和响应 fingerprint。
- 知识/算法用户状态、项目/实习 confirmed 事实、draft/ai_draft、表达版本、材料状态和结构化情报保持分层。
- 只有显式 application + interview date、stage=`interview` 且日期在 0 至 14 天窗口内时启用投递弱信号；`applications.key_date` 不参与排序。弱信号不能改变档位，只能对岗位字段确定性匹配的经历条目进行同档位 tie-break。
- 结构化频率只来自规范题 occurrence，不能改变档位或充当能力评分；展示证据只为最终返回项读取，并在 SQL 中截取最多 240 字符清洗文本。
- 稳定工程事实已写入 `docs/tech-architecture/implementation/planning.md` 并更新实现索引。

## 关键取舍

- 没有新增迁移：报告是同一事实快照上的即时只读投影，不需要复制或制造第二事实源。
- 没有调用 LLM：当前契约需要可复现排序和事实保护，确定性规则已经覆盖；模型解释并非必要依赖。
- 没有默选最近目标画像：调用方不传目标时明确降级为通用建议，避免把“最近更新”误当用户当前目标。
- 没有使用投递 `key_date`：字段缺少面试日期类型，无法单独形成可靠临近面试证据。

## 唯一逻辑检查结论

- 数据/状态：知识、算法、项目、实习分别读取原状态；confirmed、draft/ai_draft、表达版本和材料状态没有互相覆盖。
- 复现性：`as_of_date` 显式输入；请求使用 `REPEATABLE READ, READ ONLY`；所有候选、证据和最终 item 都有稳定排序键，响应不包含生成时钟。
- tie-break：档位、模式动作、目标文本匹配、轨道状态、投递弱信号、频率档和稳定 ID 的顺序与返回契约一致。
- 投递：仅明确 application + interview date、stage=`interview`、0 至 14 天窗口可启用；只能对经历岗位字段匹配项作同档位次级排序，`key_date` 不使用。
- 事实保护：频率仅是需求；draft/ai_draft 只产生核实任务；表达版本不是事实；已掌握/已解决未到期项排除，到期维护项只按本轨道降级进入。
- 证据：只为最终返回项读取最多三条引用，正文由 SQL 截取最多 240 字符；无证据返回明确状态和限制。
- 主动触发/非范围：只有 POST 请求生成；没有持久化、调度、推送、Worker job、LLM/RAG/Agent、全量正文输入、页面或导出。

以上是代码与数据契约的逻辑检查，不是测试或运行态通过结论。
