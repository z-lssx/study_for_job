# study_for_job

单用户、本地优先的秋招准备桌面 Web 应用。系统以 PostgreSQL 为唯一业务事实源，将面试情报、准备策略、投递管理和知识/算法/项目/实习四条准备轨道组织为可追溯的准备闭环。

## 技术栈

- 前端：React、Vite
- API：FastAPI、SQLAlchemy
- 数据库：PostgreSQL 16，编号 SQL 增量迁移
- 后台任务：PostgreSQL 任务队列与独立 Worker
- AI：自有 AI Gateway 契约、本地确定性 fake provider、DeepSeek OpenAI-compatible provider
- 本地编排：Docker Compose

## 文档入口

- [产品定位](docs/product-overview/README.md)
- [已确认决策](docs/decision-log/README.md)
- [总体技术架构](docs/tech-architecture/overview.md)
- [模块实现事实](docs/tech-architecture/implementation/README.md)
- [前端设计规范](docs/design/frontend-redesign.md)
- [补丁开发方式](docs/maintenance/README.md)
- [已知问题与延期能力](docs/maintenance/known-issues.md)

产品边界以 `docs/decision-log/README.md` 为准；已落地机制以 `docs/tech-architecture/` 为准。历史阶段计划、任务工作区和管理交接已从当前文档树删除，需要时从 Git 历史恢复。

## 本地启动

默认开发环境使用 `study_for_job_dev`，并加载仅用于开发观察的样例数据：

```powershell
docker compose up --build
```

- 前端：`http://localhost:5173`
- API 健康检查：`http://localhost:8000/api/health`
- 前端 `/api` 请求由 Vite 代理至 API

实际个人使用时叠加 usage 配置，API 与 Worker 会连接不自动写入样例的 `study_for_job`：

```powershell
docker compose -f docker-compose.yml -f docker-compose.usage.yml up -d
```

回到开发环境：

```powershell
docker compose up -d --force-recreate api worker
```

两个数据库共用同一 PostgreSQL 实例和迁移文件，但数据彼此隔离。已有数据卷需要补建开发库时，可重复执行：

```powershell
docker compose exec postgres bash /docker-entrypoint-initdb.d/000_create_development_database.sh
```

数据库配置读取 `POSTGRES_HOST`、`POSTGRES_PORT`、`POSTGRES_USER`、`POSTGRES_PASSWORD`、`POSTGRES_DB` 与连接池变量，也支持 `DATABASE_URL` 覆盖。示例见 `.env.example`。

## AI 配置

默认 fake provider 不需要外部密钥，可用于观察 prompt、token 和 trace 边界。需要连接 DeepSeek-compatible 服务时，在本机环境提供：

```powershell
$env:AI_PROVIDER = "deepseek"
$env:DEEPSEEK_MODEL = "<已确认可用的模型标识>"
$env:SOPHNET_API_KEY = "<local secret>"
docker compose up -d --build api
```

- 默认 base URL：`https://www.sophnet.com/api/open-apis/v1`
- `DEEPSEEK_BASE_URL` 可覆盖默认地址
- `DEEPSEEK_API_KEY` 优先于 `SOPHNET_API_KEY`
- `AI_REQUEST_TIMEOUT_SECONDS` 默认 30 秒

不要把真实密钥写入 `.env.example`、数据库、日志或仓库。真实模型标识和远程调用质量目前仍属于未验证边界。

## Worker

Compose 默认包含独立 `worker`：

```powershell
docker compose ps
docker compose logs -f worker
```

Worker 使用短事务、`FOR UPDATE SKIP LOCKED`、租约和有界退避提供至少一次执行语义。业务处理器仍须以领域唯一事实保证幂等，详细机制见 [PostgreSQL 任务队列与 Worker](docs/tech-architecture/implementation/job-queue-worker.md)。

## 后续开发

MVP 已实现，后续默认采用单补丁直接开发，不再使用项目大总管、阶段总管和阶段任务队列。开始修改前阅读根目录 `AGENTS.md`、相关稳定技术文档和 [补丁开发方式](docs/maintenance/README.md)。
