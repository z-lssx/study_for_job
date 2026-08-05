# T015 任务计划：页面主动触发的策略工作台

更新时间：2026-08-06

## 目标与成功标准

在既有沉静式桌面工作台中增加策略入口，用户可显式选择 `daily | weekly | pre_interview`、`as_of_date`、目标画像和可选面试上下文，并只在提交表单时调用 `POST /api/planning/assessments`。响应按 API `items` 原顺序展示 priority tier/order、建议目标、原因、来源、业务 ID、frequency/application signal、证据、限制、warnings、规则版本、快照摘要与排序契约。

完成标准：主动触发与模式边界清楚；`as_of_date` 可见且随请求传入；`key_date` 不作为面试日期；frequency 明确为结构化需求而非评分；事实、草稿、表达、情报和未证实能力边界不被改写；空态、错误态和弱信号未启用状态可恢复；只做 T015 最小前端与稳定文档增量。

## Skill 与设计方向

已完整读取 `C:/Users/zengw/.codex/skills/frontend-design/SKILL.md`。采用“克制、精确的编辑型策略工作台”：延续暖灰、森林绿、宋体标题、细边界与受控留白，用序号、档位和证据层级形成辨识度；不引入图片、炫技动画、新设计系统或全站重设计。

## 实施步骤与逻辑检查

1. 复用现有目标画像和投递列表，增加 planning API client/type 边界；逻辑检查请求只在表单提交路径出现。
2. 增加策略页面、导航入口和必要 CSS；逻辑检查三模式、显式日期、可选面试上下文与 `key_date` 禁用说明。
3. 映射 T014 响应全部解释字段；逻辑检查 API order 原样保留、无统一评分、frequency/证据/草稿边界文案准确。
4. 更新稳定 planning 实现文档和索引，完成 `implementation.md` 与 `verification-and-handoff.md`。
5. 只做 scoped diff、敏感信息与工作树提交控制，显式暂存 T015 文件并提交、尝试推送。

## 验证边界与非范围

按用户最高优先级要求，不编写或执行 pytest、单元/集成/E2E、测试脚本、静态语法/类型检查、迁移验证、API/数据库运行态验证、页面行为测试、浏览器/截图验收或 `npm run build`。编码后只做提交触发、请求参数、排序保留、事实文案、证据/warning/limit、状态降级、无自动化和桌面风格的逻辑检查。

不修改 T014 后端规则，不实现 T016 导出、定时生成、后台调度、推送、通知、Agent、RAG、semantic recall、embedding/pgvector、岗位爬取、登录、多用户、在线判题、LeetCode 同步、移动端专属能力或 T005 延期风险修复。
