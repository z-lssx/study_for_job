export const factCategories = [
  ['responsibility', '个人职责'], ['team_boundary', '团队边界'],
  ['technical_context', '技术背景'], ['collaboration_context', '协作背景'],
  ['challenge', '困难与约束'], ['result', '可核实结果'], ['metric', '量化指标'], ['other', '其他事实'],
]
export const sourceKinds = [
  ['user_recollection', '本人回忆'], ['document', '内部/交付文档'], ['work_item', '任务记录'],
  ['external_link', '外部链接'], ['metric_record', '指标记录'],
]
export const materialTypes = [
  ['resume_bullet', '简历条目'], ['work_sample', '工作样例'], ['evidence_document', '证明材料'],
  ['reference_link', '参考链接'], ['other', '其他材料'],
]
export const materialStatuses = [
  ['missing', '待准备'], ['draft', '草稿'], ['ready', '可使用'], ['verified', '已核实'],
]
export const optionLabel = (options, value) => options.find(([key]) => key === value)?.[1] || value
export const followUps = (value) => value.split('\n').map((line) => line.trim()).filter(Boolean).map((question) => ({ question }))
export const followUpText = (items) => (items || []).map((item) => item.question).filter(Boolean).join('\n')
