# T006 计划：原文标注、结构化抽取与证据链

状态：进行中

## 目标

在 T005 已成功持久化的 `interview_documents.cleaned_content` 上，建立可重放、可追溯的标注/抽取链：抽取运行版本 → 轮次 → 内容块 → 结构化问题/追问字段 → 证据字符区间。

## 实施边界

- 复用 `interview_documents` 作为唯一文档身份，不复制正文，不修改 T005 抓取、清洗、hash、SSRF 或 robots 逻辑。
- 使用确定性本地抽取器作为默认实现，并保留现有 AI Gateway/fake 契约的可替换边界；不声称真实远程模型质量。
- 复用 `jobs`/`job_attempts`，新增固定 `interview.extract` job type；主动触发，无定时任务。
- 通过数据库唯一约束保证同一文档/版本/输入指纹重放幂等；成功结果与失败运行分层保存。

## 交付物

- T006 迁移、ORM、抽取服务、Worker handler、API 及面经页面最小展示。
- 改动相关单测/冒烟和必要的浏览器人工验证。
- `implementation.md`、`verification-and-handoff.md`、技术架构实现记录。

## 验收重点

1. 轮次/块顺序稳定，类型至少区分 question、author_answer、interviewer_feedback、follow_up、process_description，未知保留待确认。
2. 每个块、问题和追问有稳定 `start_char`/`end_char` 回链 cleaned_content；无证据不伪造。
3. 失败可重试且不覆盖成功运行/用户修订；重复触发不产生重复事实。
4. 页面可主动触发、查看状态、轮次、类型标签、问题/追问和原文证据。
