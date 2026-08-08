# M004 阶段四正式交接：策略闭环、导出与 MVP 收口

更新时间：2026-08-08

来源阶段总管：M004，Thread `019fd2f6-a4d3-75e1-99cc-567f59760538`

接收方：唯一项目大总管，Thread `019fc0d0-5d8a-7e80-b5c5-93de2eb2bd53`

状态：请求项目大总管验收；阶段逻辑、文档收口及远端同步均已完成。本文不标记项目完成，也不授权创建阶段五。

## 阶段目标、范围与进入条件

阶段四在阶段一至三的目标/投递、结构化面试情报和知识/算法/项目/实习四轨道之上，建立规则优先、证据可解释、由页面主动触发的准备评估与任务建议；提供覆盖 MVP 事实和必要关系的 Markdown/JSON 导出；完成跨模块逻辑与文档生命周期收口。

进入条件已满足：阶段一至三均由项目大总管验收；M003 正式交接 `M003-phase-three-handoff.md` 和最终记录提交 `4ccba2746b94789cb73eedcce00e73b1715d406a` 已推送；阶段三验收提交 `907f7e3` 已推送；四轨道独立状态、用户修订、版本确认和证据边界稳定，算法随机练习保持单题。既有未执行迁移、API、数据库、页面与构建项按授权不作为阶段四补测任务。

阶段未扩入 semantic/synonym recall、embedding/pgvector、RAG、通用聊天、多轮模拟面试、经历深挖 Agent、LangGraph checkpoint、岗位爬取、登录/多用户、定时推送、在线判题、LeetCode 同步、移动端专属能力、重型备份恢复或 T005 延期风险修复。

## 任务与提交

| ID | 结果 | Thread | 提交 | 推送 |
| --- | --- | --- | --- | --- |
| T014 | 规则优先的准备评估与任务建议业务链路 | `019fd301-282e-7172-96d2-a589245e6e51` | `3ad145367c80dd0cf3a48d87cbc4501ec5f6e63c` | 已推送 |
| T015 | 页面主动触发的策略工作台 | `019fd31b-7911-73d3-ace8-797624fafd6e` | 实现 `2ebc938e29d234d9201705752b2083d3343e8b64`；交接 `75cc996cc6821d3dacba5641ec75472a2af7debc` | 已推送，包含于 `origin/main` 的 `cd989f43306f066c5a5fe8808bde33c0108ca652` |
| T016 | MVP Markdown/JSON 事实关系导出 | `019fd332-4058-73f3-997a-b53918471c8d` | 实现 `bf9777b2dbe6de424cc3d665bdf6c93c38daf955`；交接 `d620854cd097e50750d910861b7c16125bb08714` | 已推送，包含于 `origin/main` 的 `cd989f43306f066c5a5fe8808bde33c0108ca652` |

阶段治理提交包括：`f561381`（M004 计划）、`3a23de6`（T014 派发）、`72cd624`（T014 验收）、`3384649`（T015 派发）、`787f3a8`（T015 验收与 T016 派发）、`2899cf7`（M004 收口）与 `7977187`（收口 SHA 记录）。项目大总管已在暂停检查点将当前 `main` 推送至 `cd989f43306f066c5a5fe8808bde33c0108ca652`，上述阶段四任务与治理提交均已到达 `origin/main`。

## 退出条件逐条结论

1. **主链路闭合：满足（逻辑结论）。** 目标画像、结构化情报与四轨道用户状态/事实/版本进入 T014；输出使用固定档位与稳定 tie-break，T015 保留 API order 并解释来源、目标、原因、证据与限制。
2. **投递保持弱信号：满足。** 仅显式 `pre_interview` application + interview date、数据库 stage=interview、日期距 `as_of_date` 0–14 天时启用；只影响岗位确定性匹配的同档经历条目。`applications.key_date` 完全不参与。
3. **每日/每周/面试前由用户主动触发：满足。** 页面 mount、模式/日期/画像变化不请求；没有定时生成、后台调度、轮询、推送或多轮 Agent。
4. **建议规则可复现且证据可回链：满足。** priority 仅为 `critical|high|medium|low` 规则档位，无统一能力总分；frequency 不能改变档位；证据最多三条，正文片段最多 240 字符，无证据明确降级。
5. **Markdown/JSON 覆盖 MVP 事实关系：满足。** 两格式来自同一 `REPEATABLE READ, READ ONLY` 规范快照，覆盖目标、投递、情报、知识/算法状态、项目/实习事实与表达、确认/版本/材料、用户修订、证据和稳定关系 ID，共享 fingerprint。
6. **事实边界保护：满足。** confirmed、draft、ai_draft/AI 起草来源、expression、material、structured intelligence signal 和未证实能力分离；知识/算法状态不等于客观能力；frequency/association/occurrence 不写成经历事实。
7. **导出关系完整且不伪造：满足。** 所有持久化关联使用稳定 ID 回链；现有 applications 与 target_profiles 无持久化关系，导出固定 warning，不用文本匹配猜测。
8. **只做逻辑检查且如实披露未执行项：满足。** 三个开发任务均记录编码后逻辑检查，未伪造测试、构建或运行态通过。
9. **文档生命周期收口：满足。** 稳定事实、状态、索引、归档盘点和本正式交接已完成并同步至远端。
10. **提交与推送：满足。** T014–T016、M004 阶段收口及项目大总管暂停检查点均已提交并到达 `origin/main`；2026-08-08 修正前核对 `HEAD=origin/main=cd989f43306f066c5a5fe8808bde33c0108ca652`，工作树干净。

## 规则与导出组合逻辑结论

```text
目标画像 + 结构化情报 + 四轨道用户状态/事实/版本
                    ↓
        T014 可复现规则档位与证据建议
                    ↓
          T015 用户显式提交与解释展示

底层 PostgreSQL MVP 事实与持久化关系
                    ↓
       T016 同源 JSON / Markdown 只读快照
```

策略层与导出层职责分离：assessment 是规则投影，不替代底层事实；导出不使用 assessment 充当事实源。两者共同保护用户确认边界。投递既不作为统一强信号，也不在没有持久化关系时被导出层猜测关联。

## 明确未执行的全部项目

阶段四未编写或执行 pytest、单元测试、集成测试、E2E、测试脚本；未执行 Python/JavaScript 静态语法检查、类型检查、lint 或格式化验证；未执行迁移验证、API 运行态、数据库运行态、SQL 运行、页面行为测试、浏览器/截图验收；未运行 `npm run build`、`npm run check` 或其他构建。

M004 未读取源码或代码 diff、未检查代码、未亲自执行逻辑检查；只消费开发任务结构化摘要、`verification-and-handoff.md` 与稳定实现文档。Git 状态、限定文档路径、空白和敏感模式检查只用于提交控制，不是业务验证证据。

## 稳定事实源与按需追溯

下一位验收者的首选入口：

- 本交接：`docs/implementation-status/handoffs/M004-phase-four-handoff.md`
- 阶段计划：`docs/implementation-status/management-plans/M004-phase-four.md`
- 当前状态与队列：`docs/implementation-status/current.md`、`queue.md`
- 规则与策略页面稳定事实：`docs/tech-architecture/implementation/planning.md`
- MVP 导出稳定事实：`docs/tech-architecture/implementation/export.md`
- 既有目标/投递、情报、检索和四轨道稳定事实：`docs/tech-architecture/implementation/` 对应文档。

按需追溯而非跨阶段首选入口：`task-workspaces/T014/`、`T015/`、`T016/`。

## 文档生命周期结论

- 稳定事实：T014/T015 组合机制已去重汇入 `planning.md`；T016 汇入 `export.md`；implementation README 已索引。
- 当前状态：M004 计划、current、queue 和 handoffs/implementation-status 索引已更新。
- 过程材料：T014–T016 工作区分别保留任务计划、实施记录和唯一逻辑检查证据。
- 归档盘点：没有文件满足“稳定文档已替代且不再含唯一证据”的安全移动条件，因此本阶段不移动或删除任务工作区；不创建空归档目录。不存在因归档造成的引用改写。
- 去重：本交接只总结组合能力与跨阶段风险，不复制任务级完整实现或检查过程；详细字段和规则仍由两个稳定实现文档承载。

## 遗留风险、可依赖与禁止假设

可依赖：规则档位、tie-break、投递弱信号上限、显式触发契约、同源导出模型、稳定关系 ID/fingerprint、事实分类和 240 字符证据边界已由开发任务逻辑检查并进入稳定文档。

遗留风险：T014–T016 的 SQL/响应兼容、真实数据规模、API/数据库链路、页面交互、浏览器下载、长引用/长文件布局均未运行验证；同步聚合面向单用户本地 MVP。此前已披露的 T005 来源风险、真实模型、semantic recall/embedding/pgvector 等延期事项保持原边界。

禁止假设：不得声称任何测试或运行态已通过；不得把 `key_date` 当面试日期；不得假设投递与目标有隐式关系；不得把 frequency/association/occurrence 当能力分或经历事实；不得把 confirmed expression 当客观能力；不得把 AI 草稿自动当用户事实；不得假设无证据项存在隐含证据；不得把导出当历史恢复点、持久化备份或调度能力；不得声称 semantic recall、RAG、pgvector、Agent 或阶段五已实现。

## Git、远端与工作树状态

M004 阶段级文档收口提交为 `2899cf7415314df704e02f70f0cc66eb479f1223`，收口 SHA 记录提交为 `79771875e40f1cd0f88f20a58412fbe805ff4ac3`。项目大总管已按暂停检查点完成远端同步；2026-08-08 本次事实修正前核对 `HEAD=origin/main=cd989f43306f066c5a5fe8808bde33c0108ca652`、分支为 `main`、工作树干净。本次事实修正提交的新 SHA、推送结果与最终工作树状态由 M004 结构化回传。

## 唯一下一步

请求来源项目大总管 Thread `019fc0d0-5d8a-7e80-b5c5-93de2eb2bd53` 验收本交接。M004 到此停止，不创建阶段五或任何管理继任者，不标记项目完成；即使项目大总管认可所有 MVP 阶段，项目最终收口仍必须等待用户明确确认。
