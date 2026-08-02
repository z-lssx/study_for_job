# T007 验证与交接

更新时间：2026-08-02

## 状态与用户能力

T007 业务能力已完成。用户可以在面试情报页查看规范题、出现次数和文档数量，下钻到具体文档、轮次、内容块、字符区间与 evidence span；可以人工合并规范题、将单条出现拆到新的规范题，或改映射到已有等价题。所有操作不覆盖原始候选、出现文本、位置或证据。

## 验证矩阵

| 项目 | 结果 | 证据 |
| --- | --- | --- |
| 归一化单测 | 通过 | `test_normalization.py` 2/2；覆盖标点/空白等价、大小写和有意义标点保留、文档/轮次 scope |
| T006 抽取回归 | 通过 | `test_extraction.py` 6/6；类型、轮次、offset、fingerprint、失败边界和 handler 契约 |
| Python 编译 | 通过 | T007 新增模块与 API 编译通过 |
| 首次规范化刷新 | 通过 | development fixture 创建 2 canonical、2 occurrence、2 mapping |
| 重复规范化刷新 | 通过 | 第二次创建 occurrence/canonical/mapping 均为 0 |
| 频率列表 API | 通过 | 初次发现一个 NULL 参数类型推断 500，修复显式 cast 后列表 200 |
| 频率详情回链 | 通过 | 返回 document、submission、run、round、chunk、evidence span 区间和 evidence text |
| 人工映射边界 | 通过 | 回滚事务内改映射后 raw/candidate/evidence/document 字段保持不变，并追加 revision |
| 合并/拆分边界 | 通过 | 回滚事务内分别验证 merge 与 split 只移动映射层 |
| usage 迁移隔离 | 通过 | `canonical_questions/question_occurrences/question_occurrence_mappings` 为 0/0/0；006 已应用 |
| Vite 模块解析 | 通过 | 前端入口及新增 JSX/Hook/API 模块由开发服务器返回 200 |
| 浏览器点击式人工验收 | 未执行 | `agent-browser` CLI 未安装；影响是未取得真实点击截图，不影响 API/模块解析结论 |
| `npm run build` | 未执行 | 按项目规则未运行 |

## 测试中发现并修复的问题

频率查询首次使用未显式声明类型的 NULL 参数，PostgreSQL 返回 `AmbiguousParameter` 并导致 500。查询已改为显式 `CAST(:search AS text)` 与 `CAST(:round_ordinal AS integer)`，重建 API 容器后列表和详情验证通过。

宿主机直接运行可选 PostgreSQL 集成测试时出现数据库认证配置不一致；容器内 API/数据库冒烟已覆盖同一业务路径，该环境问题不计为产品缺陷。浏览器 CLI 缺失导致点击式验收未执行。

## T005 延期风险声明

T005 独立审查登记的 robots UA fail-open、HTTPS→HTTP/代理/DNS peer、不可见文本和截断 hash 四项安全/数据边界风险仍未解决；T007 未修改、未覆盖，也不应在阶段交接中写成已解决事实。

## T008 可依赖事实与禁止假设

T008 可以依赖：规范题、occurrence、当前映射、修订历史、按 occurrence 聚合的频率列表，以及 document/submission/run/round/chunk/evidence 回链。T008 不得假设：自动归一化覆盖语义同义、岗位/公司维度已存在、embedding/pgvector 已选择、频率快照已建立、原作者回答是标准答案、T005 延期安全风险已解决。

## 后续执行偏好

用户已明确要求：接下来的开发过程不需要集成测试，后续开发可跳过测试环节直接实现。该要求仅作为后续工作流偏好记录；若未来需要对外声明“已验证”，仍须以实际执行证据为准。

## 交接信息

- T007 Thread：`019fc264-355c-7082-a46c-e9e44d164951`
- 阶段总管 M002：`019fc0db-6ec7-7e72-a3bb-932bb078c328`
- 修改范围：`006_canonical_questions.sql`、normalization ORM/service/API、面试情报页面面板与样式、归一化单测、技术与任务文档。
- 提交 SHA、推送结果和最终工作树状态：以完成提交后的实际 Git 输出为准。
- 唯一下一步建议：M002 复核 T007 或续发同一 T007 补齐，不由本任务自行派发 T008。
