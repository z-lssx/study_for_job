# study_for_job

个人秋招面试准备工具。

当前定位：
- 单用户
- 本地优先
- Web 应用
- PostgreSQL 持久化
- 以面经情报层 + 策略层 + 四条准备轨道组织面试准备

文档入口：
- [产品定位](docs/product-overview/README.md)
- [决策记录](docs/decision-log/README.md)
- [技术架构](docs/tech-architecture/README.md)
- [实施状态](docs/implementation-status/README.md)
- [总管协作规则](docs/project-governance/AGENTS.md)

文档约定：产品边界以 `docs/decision-log/README.md` 中已经确认的决策为准；技术架构和代码实现可以在不突破这些边界的前提下由 AI 自主决策。

## 本地启动

默认启动开发环境，API 连接 `study_for_job_dev`，并加载一组仅用于开发验收的样例数据：

```powershell
docker compose up --build
```

打开 `http://localhost:5173`，健康检查为 `http://localhost:8000/api/health`。PostgreSQL 增量迁移位于 `migrations/`，API 启动时会在 advisory lock 内应用尚未执行的编号迁移；开发数据位于 `database/seeds/development.sql`，前端 `/api` 请求由 Vite 代理至 API。

实际使用时叠加使用环境配置，API 改连不自动写入样例的 `study_for_job`：

```powershell
docker compose -f docker-compose.yml -f docker-compose.usage.yml up -d
```

两个数据库共用同一个本地 PostgreSQL 实例和同一套迁移，但数据彼此隔离。需要回到开发环境时再次执行 `docker compose up -d --force-recreate api`。如果是在已有数据卷上升级到双数据库版本，可执行一次 `docker compose exec postgres bash /docker-entrypoint-initdb.d/000_create_development_database.sh`，脚本可重复运行且不会重复插入样例事实。

API 默认从 `POSTGRES_HOST`、`POSTGRES_PORT`、`POSTGRES_USER`、`POSTGRES_PASSWORD`、`POSTGRES_DB` 和连接池变量读取配置，示例见 `.env.example`；也兼容 `DATABASE_URL` 覆盖。SQLAlchemy Engine 统一处理连接池、失效连接探测和事务提交/回滚，表模型位于 `backend/app/models.py`。

## AI Gateway 配置

AI Gateway 默认使用确定性的本地 fake provider，不需要外部密钥即可验证成功、失败、token 和 trace 日志。桌面端顶部进入“AI 管理”，可以编辑三个代码批准场景的 system/task 模板、`temperature`、`max_tokens` 和启停状态，并查看按模块/场景聚合的 30 天 token 账本。诊断入口只接受成功/失败开关，不是通用聊天入口。

需要受控验证 DeepSeek OpenAI-compatible 接口时，在本机环境提供以下变量后重建或重建 API 容器；不要把真实值写入 `.env.example`、数据库或仓库：

```powershell
$env:AI_PROVIDER = "deepseek"
$env:DEEPSEEK_BASE_URL = "<OpenAI-compatible base URL>"
$env:DEEPSEEK_MODEL = "<已确认可用的模型标识>"
$env:DEEPSEEK_API_KEY = "<local secret>"
docker compose up -d --build api
```

`AI_REQUEST_TIMEOUT_SECONDS` 控制单次远程调用超时，默认 30 秒。当前不硬编码未经凭据验证的 DeepSeek V4 模型标识；运行时状态 API 只返回 provider、model 和是否配置完成，不返回 base URL 或密钥。

如果 Docker Desktop 能拉取基础镜像但容器内 `pip` 下载超时，可在当前 PowerShell 会话临时传入宿主机代理（不要提交到项目配置）：

```powershell
$env:DOCKER_BUILD_HTTP_PROXY = "http://host.docker.internal:7897"
$env:DOCKER_BUILD_HTTPS_PROXY = "http://host.docker.internal:7897"
docker compose up --build -d
```

MVP API：`GET /api/health`、`GET|POST /api/target-profiles`、`GET|PATCH /api/target-profiles/{id}`、`GET|POST /api/applications`、`GET|PATCH /api/applications/{id}`，以及 `/api/admin/ai` 下的 prompt 白名单管理、运行时状态、日志/聚合统计和受限诊断接口。健康检查同时返回当前环境和数据库名；阶段值为 `saved | applied | interview | offer | closed`，数据库用 `(company, role)` 唯一约束防止重复事实。
