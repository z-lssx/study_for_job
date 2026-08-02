# T006 实施记录：原文标注、结构化抽取与证据链

状态：实现完成，验证与交接完成

## 已实现

- 新增 `005_interview_extraction.sql`：`extraction_runs`、`interview_rounds`、`document_chunks`、`question_candidates`、`evidence_spans` 和 `extraction_chunk_annotations`，以外键、CHECK、唯一约束和查询索引保证版本、顺序、区间和幂等边界。
- 新增 `deterministic-lines.v1` 确定性抽取器。先识别“一面/二面”等轮次边界，再按非空行生成块；支持 `question`、`author_answer`、`interviewer_feedback`、`follow_up`、`process_description`、`unknown`。问题/追问候选保存稳定 key、字符区间和可选主题候选。
- 新增固定 `interview.extract` Worker handler。输入仅来自成功文档的 `cleaned_content`、内容 hash 和清洗版本；运行保存 schema/processor/input fingerprint，成功事实原子写入，失败保存脱敏错误，重放命中成功运行不会重复生成。
- 新增主动 API：触发/查询抽取运行、查询轮次/块/候选/证据正文、保存块级个人备注与人工校验状态。原作者回答展示为经验内容提示，不宣称标准答案。
- 面经详情页加入抽取状态、版本、类型标签、轮次、问题/追问、证据字符区间和纯文本证据；人工备注与机器结果分层保存。
- 抽取序列化与证据面板已拆为独立模块，避免路由/页面文件继续膨胀。

## 边界

- 默认不调用远程 DeepSeek；当前已知可配置模型名为 `DeepSeek-V4-Flash`、`DeepSeek-V4-Pro`，本任务使用可重放的确定性处理器，未以 fake 结果声称真实远程质量。T005 抓取、robots、SSRF、清洗和 hash 延期风险未修改、未解决。
- 不新增来源、定时任务、规范题合并、频率统计、embedding/RAG 或通用聊天。

## 验证进度

- `python -m py_compile`：通过（含新增模型、API、抽取器、仓储、handler）。
- `python -m unittest discover -s backend/tests -v`：47 通过、8 个显式 PostgreSQL 用例按开关跳过；T006 专项 6/6 通过。
- Docker API/Worker 冒烟：`005` 在 development/usage 均应用；usage 的抽取运行/块/证据为 0/0/0；development fixture 首次失败不留子事实，修复外键 flush 后重触发成功，生成 2 轮、8 块、2 候选、10 证据，重复触发保持同 run/同修订。
- API 备注回读通过，机器 `author_answer` 类型保持不变；页面首屏人工检查通过，控制台无 warning/error，未执行 `npm run build`。
- 首次 Worker 冒烟暴露并修复了轮次 FK 写入顺序问题；这是本任务实现中的已解决问题，不改变 T005 延期风险结论。
