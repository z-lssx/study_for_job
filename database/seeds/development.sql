INSERT INTO target_profiles (title, location, focus, summary)
SELECT
  'Agent 工程 / Java 后端',
  '上海 · 杭州 · Remote',
  '系统设计 · RAG 工程 · Java 性能',
  '开发环境样例画像：用于验证投递节奏、岗位聚焦和面试准备联动。'
WHERE NOT EXISTS (
  SELECT 1 FROM target_profiles WHERE title = 'Agent 工程 / Java 后端'
);

INSERT INTO applications (company, role, stage, key_date, next_action, channel, notes, url)
VALUES
  ('北纬云', 'Java 平台工程师', 'saved', '2026-08-06', '补齐 JVM 性能案例', '官网', '关注高并发链路与故障恢复。', 'https://example.com/jobs/north-cloud'),
  ('回声智能', 'Agent 工程师', 'applied', '2026-08-04', '跟进内推进度', '内推', '简历已突出工具调用与评估体系。', 'https://example.com/jobs/echo-agent'),
  ('栈桥科技', '后端开发工程师', 'applied', '2026-08-09', '准备项目深挖版本', '招聘平台', '重点整理数据一致性取舍。', 'https://example.com/jobs/bridge-backend'),
  ('雾灯实验室', 'RAG 应用工程师', 'interview', '2026-08-03', '完成召回评估复盘', '内推', '二面将关注检索质量与可观测性。', 'https://example.com/jobs/fog-rag'),
  ('折线网络', '高级 Java 工程师', 'offer', '2026-08-12', '确认团队方向与入职时间', '猎头', '等待薪酬细节确认。', 'https://example.com/jobs/polyline-java'),
  ('海盐数据', '平台开发工程师', 'closed', '2026-07-28', '沉淀面试复盘', '官网', '流程结束，保留系统设计薄弱点。', 'https://example.com/jobs/salt-platform')
ON CONFLICT (company, role) DO NOTHING;
