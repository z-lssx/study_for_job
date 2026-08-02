# T005 验证与交接

更新时间：2026-08-02

## 最终状态

已完成。核心能力、真实公开来源、失败恢复、并发/重放幂等、双库迁移和桌面 Web 均已验证。唯一未形成有效证据的是小屏 viewport；移动端不是本任务正式范围，桌面验收不受影响。

## 用户能力

- 提交博客园公开文章 URL 或直接正文，二者进入同一个来源—submission—job—文档链路。
- 在台账查看采集方式、修订、处理状态、稳定失败原因、来源回链、内容哈希和安全纯文本预览。
- 重复 URL/正文会打开既有记录；失败 URL 可保留来源并补正文恢复；可重试终态失败可重新触发。

## 修改范围

- 数据库：`migrations/004_interview_intake.sql` 和对应 ORM，新增四类最小事实及约束/索引。
- 后端/API：`backend/app/intelligence/`、`backend/app/api/intelligence.py`、路由注册和测试。
- Worker：注册固定 `interview.ingest` handler，复用 T004 的 jobs/job_attempts、租约和退避。
- 前端：导航、API、数据 hook、`IntelligencePage` 和独立样式文件。
- 文档：T005 工作区、本文档和 `docs/tech-architecture/implementation/intelligence-pipeline.md`。

## 验证矩阵

| 类别 | 结果 | 证据摘要 |
| --- | --- | --- |
| Python 编译/单元 | 通过 | `py_compile`；`unittest discover` 41 个，33 通过、8 个显式 PG 用例按开关跳过 |
| PostgreSQL 集成 | 通过 | 只读挂载测试目录到临时 API 容器；8/8 通过 |
| 队列/租约 | 通过 | 双 Worker 只领取一次、租约恢复、迟到 job 结果拒绝、退避终态均通过 |
| 业务重放 | 通过 | 同 job 重放同文档；迟到写回不会覆盖成功内容或留下孤立文档 |
| 参数漂移 | 通过 | job idempotency 参数漂移和 handler 快照漂移均拒绝 |
| 去重 | 通过 | 规范化 URL、相同手动正文、并发竞争、不同 URL 相同正文均收敛 |
| API | 通过 | URL/正文、XOR 校验、列表、详情、重复、补正文和 retry；拒绝内容不回显 |
| URL/SSRF | 通过 | 协议、凭据、端口、主机/路径、私网 DNS、重定向、robots、超时、体积、类型和脱敏错误 |
| 真实来源 | 通过 | `https://www.cnblogs.com/sqdtss/p/15992705.html`：robots 200、页面 200、清洗预览 3631 字符并成功入库 |
| 失败与补正文 | 通过 | 不存在博客园 URL 得到 `upstream_http_error`；同 submission 补正文后 R2 成功且保留来源 |
| 全新迁移 | 通过 | 临时空库连续应用 `001`–`004`，四类 T005 业务表为空；验证后删除临时库 |
| development 升级 | 通过 | `001`–`004` 一致；验证时来源 3、submission 5、文档 5 |
| usage 升级/隔离 | 通过 | `001`–`004` 一致；来源、submission、文档、jobs 均为 0 |
| API 敏感字段 | 通过 | 列表不含 `raw_content`、`lease_token`、job `payload` 或 HTML 标签 |
| 页面 | 通过 | 可见浏览器完成 URL、失败、补正文、直接正文、重复提示、来源和安全预览；控制台 0 warning/error |
| 视觉 | 通过（桌面） | 1280px 完整页面截图核对，保持现有编辑部视觉系统 |
| 生产构建 | 未执行 | 用户明确禁止未经许可运行 `npm run build`；使用 Vite dev 与可见浏览器验证 |
| 小屏 viewport | 未形成证据 | in-app Browser viewport 覆盖未生效；仅保留基础 CSS 断点，移动端非正式范围 |

## 失败过的验证尝试

- 第一次容器内运行测试因生产镜像不复制 `tests/` 而未发现测试模块；随后采用只读 volume 挂载并通过 8/8。该失败不表示业务用例失败。
- 宿主机直连 PostgreSQL 时，既有数据卷的实际口令与 compose 当前声明不一致；最终验证全部在容器网络内使用数据库身份完成，不依赖该宿主路径。
- 一次 PowerShell 中文 JSON 样例受终端编码影响出现问号；浏览器直接中文提交、预览和恢复均正常。

## T006 可依赖事实与禁止假设

T006 可以依赖：成功 submission 关联唯一 `interview_documents`；`cleaned_content` 是确定性、安全纯文本；`content_hash` 是内容身份；来源关联可能多于一个；成功内容不可覆盖；失败可能由后续 `manual_fallback` 修订恢复。

T006 不得假设：每个文档都有 URL、只有一个来源、raw content 一定是 HTML、当前清洗正文已经包含轮次/问题结构、错误 code 可自由扩展、任何站点都可抓取，或可绕过 robots/登录/验证码。T006 也不得修改本任务的 URL/content 唯一事实语义来制造第二套文档身份。

## 风险与审查触发

该任务涉及 SSRF、来源许可、原始 HTML 和至少一次 Worker 幂等，属于适合独立安全/数据一致性审查的高风险边界。当前 allowlist、robots、DNS/IP、重定向和事务重放均有测试，但新增来源前仍必须逐来源重新审查。

## Git 与线程

- T005 Thread：`019fc0e8-de74-72b0-827c-3218a8f51f3e`
- 阶段总管 M002：`019fc0db-6ec7-7e72-a3bb-932bb078c328`
- 基线：`f4f5a97`，并保留其下 `4f0a99d`；实现前 `main` 相对 `origin/main` 领先 2。
- 最终提交为本文档所属提交；具体 SHA、推送结果和提交后工作树状态记录在发给 M002 的结构化消息中（提交对象不能稳定地在自身内容中记录自己的 SHA）。

## 对 M002 的唯一下一步建议

验收 T005；在验收结论前不要派发 T006。
