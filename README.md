# CSP 初赛训练系统

面向 CCF CSP-J/S 第一轮认证（初赛）的社区化刷题与比赛平台。支持题目投稿与审核、P/T/S 题库隔离、错题复习、模拟考试、官方/个人比赛、防切屏、排行榜、讨论区与申诉中心。

> CSP-J/S 初赛全部为选择题（单选、阅读程序、完善程序），不涉及在线运行代码，因此本项目不需要评测沙箱。

---

## 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | Vue 3 + Vite + Element Plus + Pinia + Vue Router + markdown-it + KaTeX + highlight.js |
| 后端 | FastAPI + SQLAlchemy 2.x（同步 ORM）+ Pydantic 2 |
| 数据库 | PostgreSQL（Neon Serverless） |
| 运行时 | Cloudflare Workers Python（Pyodide/WASM）+ `workers.asgi` |
| 连接层 | Cloudflare Hyperdrive + 纯 Python 驱动 `pg8000` |
| 前端托管 | Cloudflare Pages（`public/_worker.js` 反向代理 `/api/*`） |
| 认证 | JWT（HS256，Bearer Token） |

---

## 核心功能

### 题库与做题
- P / T / S 三套题库隔离：普通用户只访问 P 池，管理员可切换 T / S。
- 题目类型：单选、阅读程序、完善程序；支持 Markdown、KaTeX、代码高亮。
- 社区投稿 → 管理员审核（通过 / 驳回并说明原因）→ 进入公共题库。
- 题目编号 `problem_number` 唯一，便于比赛与题单引用。
- 每次作答写入 `submissions`，记录 `time_spent` 与来源比赛。

### 错题本
- 做错自动收录；按 1 / 3 / 7 天间隔安排复习。
- 连续答对 2 次标记为掌握。
- 题目被删除、关联数据异常时降级为空数组 / 友好 JSON，不再 500。

### 比赛
- 官方赛计入小猴值，个人赛不计入。
- 比赛详情含倒计时、题目、实时排名。
- 防切屏：绑定 `visibilitychange` + `blur`，每次上报 `/anti-cheat`；第 3 次强制交卷。
- 管理员可判定作弊：封号、清零小猴值、信用分 50、棕名、关闭出题权限。
- 申诉中心：用户提交录像链接，管理员通过后恢复账号与信用分。

### 社区
- 讨论区：站务 / 学术 / 题目三个分类；站务版仅管理员可发。
- 评论、Markdown + KaTeX 渲染、举报按钮。
- 管理员可查看并处理举报。

### 用户与权限
- 用户字段：小猴值、信用分（100 / 50）、状态（normal / banned）、封禁到期时间、称号、出题权限。
- 封禁用户访问受保护接口返回 403；`/auth/me` 仍可读取自身状态，前端渲染棕名。
- 管理员用户管理：搜索、解封（信用分恢复 100）、封禁、禁用/恢复出题权限。

### 排行榜
- 按小猴值排序，前三名使用 SVG 领奖台。
- 展示称号颜色（棕名等）、通过题数、信用分、状态。

---

## 系统架构

```mermaid
flowchart LR
    U[Browser<br/>Vue 3 + Element Plus] -->|HTTPS| P[Cloudflare Pages<br/>静态资源 + _worker.js]
    P -->|/api/* 反向代理| W[Cloudflare Worker<br/>FastAPI + workers.asgi]
    W -->|env.HYPERDRIVE| H[Cloudflare Hyperdrive<br/>连接池 / TLS]
    H -->|pg8000| N[(Neon PostgreSQL)]
    W -->|JWT / RBAC| W
    P -->|SPA 回退| P
```

请求链路：

```text
Pages /api/auth/login
  → _worker.js（保留 method/headers/body，OPTIONS 直接 204）
  → Worker /api/auth/login
  → FastAPI 路由（/api + /auth）
  → get_db(request) 读取 scope["env"].HYPERDRIVE.connectionString
  → SQLAlchemy + pg8000 + NullPool
  → Neon
```

---

## 目录结构

```text
cspjs/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI 入口 + Workers ASGI 适配 + 同步端点 shim
│   │   ├── config.py          # pydantic-settings
│   │   ├── database.py        # Hyperdrive / pg8000 / NullPool / 请求级 Session
│   │   ├── deps.py            # JWT、封禁校验、管理员权限
│   │   ├── models.py          # 全部 ORM 模型
│   │   ├── schemas.py         # Pydantic 请求/响应
│   │   ├── serializers.py     # ORM → ProblemSummary/Detail
│   │   ├── seed.py            # 演示数据
│   │   ├── routers/
│   │   │   ├── auth.py users.py problems.py wrong_questions.py
│   │   │   ├── contests.py discussions.py appeals.py
│   │   │   ├── problem_lists.py stats.py tags.py mock_exams.py
│   │   └── ...
│   ├── sql/migrations/        # 增量迁移 SQL
│   ├── cleanup_test_data.py   # 清理演示/测试题
│   ├── pyproject.toml
│   ├── wrangler.jsonc
│   └── smoke_test.py
├── frontend/
│   ├── public/_worker.js      # Pages /api 反向代理
│   └── src/
│       ├── router/index.js
│       ├── views/             # Rankings/Contests/Discussions/Appeals/AdminUsers...
│       └── components/        # Markdown、ConfirmDialog、EmptyState...
└── README.md
```

---

## 本地开发

### 1. 后端

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# 编辑 .env：DATABASE_URL 可留空（本地 SQLite），JWT_SECRET 必须是随机长串
uvicorn app.main:app --reload --port 8000
```

- 未配置 `DATABASE_URL` 时自动使用 `backend/cspjs.db`（SQLite）。
- 首次启动自动建表并写入 21 道演示题（`AUTO_SEED=true`）。
- 管理员默认 `admin`，密码由 `ADMIN_PASSWORD` 控制；占位符仅限本地。
- 健康检查：`GET http://127.0.0.1:8000/api/health`。

### 2. 前端

```bash
cd frontend
pnpm install
cp .env.example .env.local
# VITE_API_BASE=/api 或 http://127.0.0.1:8000/api
pnpm dev
```

打开 `http://localhost:5173`。Vite 已配置 `/api` 代理到本地 8000 端口。

### 3. 修改管理员密码

```bash
cd backend
python -m app.passwd --username admin
```

### 4. 清理演示/测试题

```bash
cd backend
export DATABASE_URL='postgresql://...'
python cleanup_test_data.py --dry-run
python cleanup_test_data.py            # 输入 y 确认
python cleanup_test_data.py --ids 12,34 --yes
```

只删除标题包含“演示/测试”或 `--ids` 指定的题目，不删除用户、比赛、讨论和手工题目。

---

## 云端部署（Cloudflare + Neon）

### 1. Neon

1. 创建 Neon 项目，复制连接串（含 `sslmode=require`）。
2. 初始化表结构：
   - 全新库：本地设置 `DATABASE_URL` 后执行 `python -m app.seed`（`create_all` + 演示数据，推荐）；或先执行 `backend/sql/schema.sql`，再执行增量迁移 `backend/sql/migrations/2026_11_community.sql`。
   - 已有库：执行 `backend/sql/migrations/2026_11_community.sql`（见下文迁移）。

### 2. Hyperdrive

```bash
cd backend
npx wrangler hyperdrive create cspjs-hyperdrive \
  --connection-string="postgresql://user:pass@ep-xxx.neon.tech/db?sslmode=require"
```

把返回的 id 写入 `wrangler.jsonc` 的 `hyperdrive[0].id`。

### 3. 后端 Worker

```bash
cd backend
uv lock
uv sync
uv run pywrangler secret put JWT_SECRET
uv run pywrangler deploy
```

- `wrangler.jsonc` 的 `main` 必须是 `app/main.py`。
- `CORS_ORIGINS` 填 Pages 域名（如 `https://cspjs.pages.dev`），多个用逗号分隔。
- Workers 上不会执行 `create_all`；表结构必须提前迁移。
- 入口使用顶层绝对导入；`app/main.py` 与 `app/__init__.py` 会把 `app/` 加入 `sys.path`。

### 4. 前端 Pages

1. Cloudflare Pages 连接仓库，Root Directory 选 `frontend`。
2. Build command：`pnpm build`；Output：`dist`。
3. 环境变量：`VITE_API_BASE=/api`（走同域代理）。
4. 部署后确认 `dist/_worker.js` 存在；Pages 高级模式 Worker 会把 `/api/*` 转发到后端。
5. 可选：Pages 环境变量 `API_ORIGIN` 指定后端 Worker 地址；不配置则使用 `_worker.js` 内置默认地址。

### 5. 验证

```bash
curl -i https://<pages>/api/health
curl -i -X POST https://<pages>/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"..."}'
```

---

## 数据库迁移说明

模型新增了用户信用/封禁字段、P/T/S 题库、比赛、讨论、举报、申诉、防作弊日志等。已有 Neon 库不能只靠 `create_all` 自动补列，需要执行增量 SQL：

```bash
psql "$DATABASE_URL" -f backend/sql/migrations/2026_11_community.sql
psql "$DATABASE_URL" -f backend/sql/migrations/2026_11_username_change.sql
psql "$DATABASE_URL" -f backend/sql/migrations/2026_11_avatar.sql
```

迁移脚本使用 `ADD COLUMN IF NOT EXISTS` / `CREATE TABLE IF NOT EXISTS`，可重复执行。主要变化：

| 表 | 变化 |
| --- | --- |
| `users` | `monkey_score`、`credit_score`、`status`、`ban_until`、`title`、`can_create_problem`、`last_username_change`、`avatar_url`、`avatar_status` |
| `problems` | `pool_type`（P/T/S）、`problem_number`（唯一） |
| `submissions` | `time_spent`、`contest_id` |
| 新增 | `contests`、`contest_problems`、`contest_results`、`cheat_logs` |
| 新增 | `discussions`、`comments`、`reports` |
| 新增 | `appeals`、`audit_logs` |

迁移前请备份 Neon 数据库；生产环境建议使用 Neon 分支先在预发验证。

### 一键同步缺失表 / 字段（推荐）

```bash
cd backend
export DATABASE_URL='postgresql://...'
python init_db.py --dry-run    # 打印将执行的 DDL
python init_db.py --yes        # 创建缺失表、补齐缺失字段
```

`init_db.py` 会读取 `models.py`，只做加法：`CREATE TABLE IF NOT EXISTS`、`ALTER TABLE ADD COLUMN`，不会删除数据或改类型。日常迭代加字段时优先用它，避免手动拼 SQL。

如果团队需要版本化迁移，可在 `backend/` 接入 Alembic：`alembic init migrations`，把 `env.py` 的 `target_metadata` 指向 `models.Base.metadata`，之后用 `alembic revision --autogenerate -m "..."` 生成版本。当前项目保留 SQL 迁移 + `init_db.py` 两套方案，Neon 上二者都可重复执行。

---

## API 速览

| 模块 | 端点 |
| --- | --- |
| 认证 | `POST /api/auth/register`、`POST /api/auth/login`、`GET /api/auth/me` |
| 题库 | `GET /api/problems?pool_type=P`、`GET /api/problems/{id}`、`POST /api/problems`、`POST /api/problems/{id}/answer` |
| 错题 | `GET /api/wrong-questions`、`GET /api/wrong-questions/{id}/detail`、`POST /api/wrong-questions/{id}/review` |
| 比赛 | `GET /api/contests`、`GET /api/contests/{id}`、`PUT/DELETE /api/contests/{id}`、`POST /api/contests/{id}/anti-cheat`、`POST /api/contests/{id}/submit`、`POST /api/contests/{id}/judge` |
| 讨论 | `GET/POST /api/discussions`、`GET /api/discussions/{id}`、`POST /api/discussions/{id}/comments`、`POST /api/reports`、`POST /api/admin/discussions/{id}/pin` |
| 头像 | `PUT /api/users/avatar`、`GET /api/admin/avatars`、`POST /api/admin/avatars/{id}/review` |
| 审计 | `GET /api/admin/audit-logs` |
| 申诉 | `POST /api/appeals`、`GET /api/appeals/me`、`GET /api/admin/appeals`、`POST /api/admin/appeals/{id}/review` |
| 排行榜 | `GET /api/rankings` |
| 用户管理 | `GET /api/admin/users`、`POST /api/admin/users/{id}/unban`、`POST /api/admin/users/{id}/toggle-create-problem` |
| 个人中心 | `PUT /api/users/change-name`（普通用户 30 天冷却，管理员无限制） |
| 健康检查 | `GET /api/health` |

---

## 安全与权限

- 密码使用 SHA-256 + 固定盐哈希（教学项目；生产建议 Argon2/bcrypt）。
- JWT 使用 `JWT_SECRET` 签名，必须通过 Worker Secret 注入，不要写进仓库。
- 管理员接口统一依赖 `require_admin`。
- 封禁用户访问受保护接口返回 403；`/auth/me` 不拦截，以便前端展示棕名与申诉入口。
- CORS 只放行 `CORS_ORIGINS` 中的完整 origin；Pages 同域代理时由 `_worker.js` 补充响应头。

---

## 免责声明

本项目仅用于 CSP-J/S 初赛知识点练习与教学演示。题目内容、比赛规则与判分逻辑不代表 CCF 官方；用户上传的题目、讨论与录像链接由上传者负责。请勿用于任何违反考试公平性的行为。

## License

MIT
