# T015 实施记录：页面主动触发的策略工作台

更新时间：2026-08-06

## 基线与边界

- 当前本地基线保留 M004 对 T014 的验收记录及 T015 派发记录，不回退或重写既有提交。
- T014 稳定契约为 `POST /api/planning/assessments`；`mode` 与 `as_of_date` 必填，目标画像可选，只有 `pre_interview` 可携带成对的 application/interview date。
- 现有 `applications.key_date` 未标注日期类型，页面不读取或回填它作为面试日期。
- 策略结果是同步、只读、规则优先的当前快照，不是 AI 自动规划器，不持久化报告，不创建 Worker、scheduler、cron、推送或 Agent。

## Skill 影响与现状判断

已完整读取 `frontend-design` Skill。任务采用与 T013 相同的沉静式工作台基因，将策略页设计为“规则案卷”：左侧是紧凑、显式的请求控制台，右侧按 API 顺序呈现建议；档位使用低饱和语义色，证据和技术元数据按需展开。不会用高饱和渐变、卡片堆叠动效或统一分数制造虚假确定性。

现有根级 `useJobData` 已在工作台加载目标画像与投递列表，策略页将复用这些事实。策略 assessment 不在 mount、模式切换或日期变更时请求，只在用户提交表单时请求一次。

## 实施结果

- 新增 `src/api/planning.js`：以 JSDoc 固定三种 mode、必填日期、可选目标和成对面试上下文，并集中调用 assessment API。
- 扩展 `useJobData` 暴露既有目标画像列表；策略页复用根级已加载的画像和投递，不新增策略结果的 mount 请求。
- 新增“策略”导航与 `PlanningWorkspace`：模式、日期、目标和可选面试上下文均显式可见；只有表单提交调用 assessment API。
- 新增局部 `planning.css`：延续 T013 暖灰/森林绿、宋体标题、细边界和折叠信息层级，没有改写全局 token 或其他页面。
- 结果按 API 数组原顺序映射，展示 priority/order/track、目标/建议、原因/代码、来源类型、业务 ID、frequency/application signal、证据状态/引用、限制、warnings、规则版本、输入摘要、排序契约与 fingerprint。
- 更新稳定事实 `docs/tech-architecture/implementation/planning.md`，不新增重复稳定文档。

## 关键实现决定

- `pre_interview` 的 application 与 interview date 只有成对完整且用户勾选时才写入请求；不完整时省略上下文并允许通用面试前请求。
- 投递选择只显示公司、岗位和阶段，不展示或读取 `key_date` 作为面试日期；页面固定提示该字段未标注日期类型。
- 页面不计算分数、不重排；frequency 只以 occurrence 数量和“结构化需求信号”呈现，投递信号只按后端 `applied/effect` 解释。
- 已确认事实、待核实草稿、AI 起草来源、表达版本、材料状态和结构化情报来源分别显示；证据引用显式标注是否支持已确认事实，无证据时展开降级说明。
- 技术元数据与完整引用使用原生 `details` 按需展开，核心建议、档位、排序原因、来源边界与弱信号状态直接可见。

## 当前进度

- [完成] planning API client 与目标画像列表边界。
- [完成] 策略页面、导航入口与样式。
- [完成] 稳定技术文档增量。
- [完成] 唯一逻辑检查与交接文档。
- [完成] Git scoped 提交；推送因未验证外部 origin 的安全策略拒绝而停止，未绕过。
