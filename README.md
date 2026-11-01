# CSP 初赛刷题 · CCF CSP-J/S 第一轮认证刷题平台

面向 CCF CSP-J/S 第一轮认证（初赛）考生的 Web 刷题平台：社区贡献题目 → 管理员审核 → 公共题库 → 作答诊断 → 错题复习 → 模拟组卷。

考试形式为选择题（单选、阅读程序、完善程序），不涉及在线运行代码，**不需要评测沙箱**。

![首页](docs/screenshots/01-home.png)

## 一、技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | Vue 3 + Vite + Element Plus + Pinia + Vue Router |
| 后端 | FastAPI + SQLAlchemy 2.x + PostgreSQL |
| 认证 | JWT（HS256），密码 SHA-256 哈希存储（已封装 `hash_password()`） |
| Markdown | markdown-it + @chyi13/markdown-it-katex + highlight.js + DOMPurify |
| 部署 | Web 应用（不做 .exe / Electron） |

## 二、功能清单

**第一版（必须完成，已全部实现）**

- 注册 / 登录 / JWT 鉴权，SHA-256 密码存储，初始化管理员 `admin / adminmagnet`
- 三种题型投稿（单选 / 阅读程序 / 完善程序），阅读与完善题支持多条小题
- 管理员审核：待审列表 → 查看完整内容（题干、选项、正确答案、解析）→ 通过 / 驳回（必填原因）
- 驳回后作者可修改并重新提交（状态回到 `pending`）；管理员投稿直接通过
- 公共题库列表 + 按题型 / 标签 / 来源 / 年份 / 试卷 / 关键词筛选（筛选条件同步到 URL，可分享）
- 题目详情：题干 + 代码高亮 + KaTeX 公式 + 小题作答 + 逐题判分与解析
- 题单：创建、公开/私有、收录/移除题目、上下移动排序
- 标签系统：知识点 / 来源两类，管理员维护，作者投稿时可新建知识点标签
- 自定义 `ConfirmDialog` + `useConfirmDialog`（**全站无原生 alert/confirm/prompt，也不直接使用 ElMessageBox**）

**第二版（已全部实现）**

- 错题本闭环：做错自动入库、标记错因、复习队列（1 / 3 / 7 天）、连续答对两次标记掌握
- 做题统计：知识点维度正确率、题型维度正确率（来源 `submissions` 聚合）
- 模拟考试：15 单选（30 分）+ 3 阅读（40 分）+ 2 完善（30 分），限时 120 分钟，随机组卷不重复，交卷自动判分、逐题解析、知识点得分率

## 三、目录结构

```
cspjs/
├── README.md                      # 本文档
├── .gitignore
├── render.yaml                    # Render Blueprint（Web Service + PostgreSQL 一键创建）
├── scripts/
│   ├── dev.ps1                    # Windows 一键启动前后端
│   └── dev.sh                      # macOS / Linux 一键启动
├── docs/
│   ├── API.md                     # 接口详解（请求/响应示例）
│   └── screenshots/                # 真实运行截图（Edge 自动化截取）
├── backend/
│   ├── requirements.txt
│   ├── .env.example               # 后端环境变量模板
│   ├── smoke_test.py              # 端到端接口冒烟测试（39 个断言）
│   ├── sql/
│   │   └── schema.sql             # PostgreSQL 建表 SQL（与模型一一对应）
│   └── app/
│       ├── main.py                # FastAPI 入口：CORS、路由挂载、启动建表/播种
│       ├── config.py              # pydantic-settings 配置（全部可被环境变量覆盖）
│       ├── database.py            # 引擎 / Session / SQLite 自动降级
│       ├── models.py              # SQLAlchemy 模型（users/tags/problems/...）
│       ├── schemas.py             # Pydantic 请求响应模型与校验
│       ├── security.py            # hash_password / verify_password / JWT 签发解析
│       ├── deps.py                # get_current_user / get_optional_user / require_admin
│       ├── serializers.py         # ORM → 响应模型（含标签、答案可见性控制）
│       ├── services.py            # 判分归一化、错题间隔调度、模拟考试分值结构
│       ├── seed.py                # 管理员、标签、21 道演示题、公开题单
│       ├── passwd.py              # 运维脚本：重置用户密码（SHA-256）
│       └── routers/
│           ├── auth.py            # 注册 / 登录 / 当前用户
│           ├── problems.py        # 题库、投稿、编辑、审核、作答判分
│           ├── tags.py            # 标签读取与维护
│           ├── problem_lists.py   # 题单 CRUD、收录、排序
│           ├── wrong_questions.py # 错题本、错因、复习推进
│           ├── stats.py           # 个人做题统计聚合
│           └── mock_exams.py      # 组卷、考试详情、交卷判分、结果
└── frontend/
    ├── package.json
    ├── vite.config.js             # 代理 /api → :8000；build / preview 配置
    ├── pnpm-workspace.yaml        # 允许 esbuild 安装脚本（pnpm 11）
    ├── vercel.json                # Vercel 构建配置 + SPA rewrites
    ├── .env.example
    ├── index.html
    ├── public/
    │   └── _redirects             # Netlify / Cloudflare Pages 的 SPA 回退
    └── src/
        ├── main.js                # 应用装配（Element Plus 中文包、KaTeX/高亮样式）
        ├── App.vue                # 布局 + 全局 ConfirmDialog 挂载
        ├── api/
        │   ├── client.js          # fetch 封装：JWT 注入、错误归一、401 登出
        │   └── index.js           # 各资源接口
        ├── stores/auth.js         # token / user / 登录态
        ├── router/index.js        # 路由与登录、管理员守卫
        ├── composables/
        │   └── useConfirmDialog.js
        ├── components/
        │   ├── ConfirmDialog.vue  # 统一确认 / 输入弹窗（el-dialog 封装）
        │   ├── MarkdownView.vue   # markdown-it + KaTeX + highlight.js + DOMPurify
        │   ├── MarkdownEditor.vue # 编辑 / 预览双栏
        │   ├── SubQuestionBlock.vue # 圆形序号徽章 + 选项 + 判分结果 + 解析
        │   ├── ProblemCard.vue
        │   ├── StatBar.vue        # 知识点/题型正确率条形图
        │   ├── AppHeader.vue
        │   └── EmptyState.vue
        ├── styles/main.css        # 墨绿主色、卡片阴影、Markdown 阅读样式
        ├── utils/format.js        # 标签文案、日期、百分比、模拟考分值
        └── views/
            ├── HomeView.vue           # 首页（今日待复习入口）
            ├── LoginView.vue
            ├── RegisterView.vue
            ├── ProblemsView.vue       # 题库筛选
            ├── ProblemDetailView.vue  # 题目详情 + 作答 + 审核入口
            ├── ProblemEditView.vue    # 投稿 / 编辑（三种题型 + 小题编辑器）
            ├── MyProblemsView.vue     # 我的投稿（状态筛选）
            ├── AdminReviewView.vue    # 审核列表 + 审核弹窗
            ├── TagsAdminView.vue
            ├── ListsView.vue
            ├── ListDetailView.vue
            ├── WrongBookView.vue      # 错题本 + 重做弹窗
            ├── StatsView.vue
            ├── MockExamView.vue       # 组卷入口 + 考试进行中（倒计时/答题卡）
            ├── MockExamResultView.vue # 成绩 + 逐题解析
            └── NotFoundView.vue
```

## 四、快速开始

> 本节是**本地开发 / 演示**的启动方式。正式上线请用第十一节「云托管部署」：前后端分离托管在 Vercel + Render，不需要自己的服务器，也不用一直开着电脑。

### 4.1 环境要求

- Python 3.11+（已在 3.12 验证）
- Node.js 20+（已在 24 验证）、pnpm 9+（已在 11 验证）
- PostgreSQL 14+（可选：本地没有 PostgreSQL 时会自动降级为 SQLite，见下文）

### 4.2 后端

```bash
cd backend

# 1) 创建虚拟环境并安装依赖（示例用 venv）
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt

# 2) 准备数据库（二选一）
#    A. PostgreSQL（推荐，符合技术栈）
createdb cspjs
cp .env.example .env    # 修改 DATABASE_URL
#    B. 不装 PostgreSQL：保持 ALLOW_SQLITE_FALLBACK=true，自动使用 ./cspjs.db

# 3) 启动（首次启动自动建表 + 写入管理员与演示数据）
uvicorn app.main:app --reload --port 8000
```

- 接口文档：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/api/health>
- 仅执行初始化（不启服务）：`python -m app.seed`；清空重建：`python -m app.seed --reset`

> 也可以直接对 PostgreSQL 执行 `backend/sql/schema.sql` 手写建表；应用启动时的 `create_all` 与它等价。

### 4.3 前端

```bash
cd frontend
pnpm install
pnpm dev          # http://127.0.0.1:5173 ，已配置 /api → 127.0.0.1:8000 代理
# 生产构建与本地预览
pnpm build
pnpm preview      # http://127.0.0.1:4173
```

### 4.4 一键启动（可选）

```powershell
# Windows PowerShell
./scripts/dev.ps1
```

```bash
# macOS / Linux
./scripts/dev.sh
```

### 4.5 演示账号

| 角色 | 用户名 | 密码 | 说明 |
| --- | --- | --- | --- |
| 管理员 | `admin` | `adminmagnet` | 由 seed 写入，可审核 / 编辑任意题目 / 管理标签 |
| 学生 | `student` | `student123` | 演示账号，拥有一个公开题单 |

演示数据包含 **21 道已通过题目**（16 道单选 + 3 道阅读程序 + 2 道完善程序）与 16 个标签，足够直接开始一场 20 题的模拟考试。

> 云托管部署时请设置 `SEED_DEMO_STUDENT=false`：只播种管理员与题库，不创建已知密码的演示学生账号（见 11.5）。

## 五、环境变量

### 后端（`backend/.env`，见 `.env.example`）

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/cspjs` | PostgreSQL 连接串；平台注入的 `postgresql://` / `postgres://` 会自动补成 `postgresql+psycopg://` |
| `ALLOW_SQLITE_FALLBACK` | `true` | 本地无 PG 时降级 SQLite；**云托管必须 `false`**（免费实例磁盘是临时的，重启即丢数据） |
| `SQLITE_PATH` | `./cspjs.db` | 降级后的 SQLite 文件 |
| `JWT_SECRET` | `change-me-in-production-please` | **生产必须替换为随机长字符串** |
| `JWT_EXPIRE_MINUTES` | `10080` | token 有效期（7 天） |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173,...` | 逗号分隔的完整 origin（`https://`，无末尾 `/`）。本地开发填 localhost；**前后端分离部署时必须加前端实际域名**（如 `https://cspjs.vercel.app`），否则浏览器报 CORS |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | `admin` / `adminmagnet` | 初始化管理员；云托管首次部署请用强密码覆盖 `ADMIN_PASSWORD` |
| `AUTO_SEED` | `true` | 启动时建表 + 播种（幂等）；云托管首次 `true`，确认数据后改 `false` |
| `SEED_DEMO_STUDENT` | `true` | 是否创建演示学生 `student` 与示例题单；**云托管设为 `false`**，避免已知密码账号上线 |
| `MOCK_EXAM_MINUTES` | `120` | 模拟考试时长 |

### 前端（`frontend/.env`，见 `.env.example`）

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `VITE_API_BASE` | `/api` | 后端地址前缀，**构建期内联**。同域部署（Nginx 反代 / 本地 Vite 代理）填 `/api`；**前后端分离部署填后端完整地址且必须带 `/api`**，如 `https://cspjs-api.onrender.com/api`；改完需重新构建/部署 |

## 六、数据模型

完整 DDL 见 [backend/sql/schema.sql](backend/sql/schema.sql)，ORM 定义见 [backend/app/models.py](backend/app/models.py)。表：`users`、`tags`、`problems`、`problem_tags`、`sub_questions`、`problem_lists`、`problem_list_items`、`wrong_questions`、`wrong_reviews`、`mock_exams`、`submissions`。

**对需求模型的两处必要扩展**（已在模型与 SQL 中注明）：

1. `mock_exams.answers_json JSONB`：交卷后需要回显"逐题解析"，必须持久化考生作答；
2. `submissions.mock_exam_id`（可空外键）：模拟考试作答也写入 `submissions`，靠该字段与普通做题统计隔离，保证"模拟成绩不混入普通统计"。

其它实现约定：

- `options_json` 在 PostgreSQL 使用 **JSONB**（`JSON().with_variant(JSONB, "postgresql")`），SQLite 降级时自动退回 JSON；
- 时间统一以 UTC 存储、以带时区 UTC 返回（自定义 `UTCDateTime` 类型），避免时区漂移；
- 多选题答案统一归一化（去空格、大写、按字符排序）后比较，因此 `"ba"` 与 `"AB"` 等价。

## 七、权限规则

| 操作 | 游客 | 普通用户 | 管理员 |
| --- | --- | --- | --- |
| 浏览 approved 题目 / 题单 / 标签 | ✅ | ✅ | ✅ |
| 查看 pending / rejected 题目 | ❌ | 仅自己的 | 全部 |
| 投稿题目 | ❌ | ✅（→ pending） | ✅（→ approved） |
| 编辑题目 | ❌ | 仅自己的 pending/rejected | 任意 |
| 删除题目 | ❌ | 仅自己的非 approved | 任意 |
| 审核（通过/驳回） | ❌ | ❌ | ✅ |
| 创建题单 / 收录题目 | ❌ | ✅ | ✅ |
| 编辑他人题单 | ❌ | ❌ | ✅ |
| 标签管理 | 读取 | 仅新建知识点标签 | 全部 |
| 做题 / 错题本 / 统计 / 模拟考试 | ❌ | ✅ | ✅ |

后端权限由 `deps.get_current_user` / `require_admin` 与各路由内的资源归属校验共同完成（前端隐藏按钮不构成安全边界）。

## 八、接口一览

统一前缀 `/api`，除公开读取外均需 `Authorization: Bearer <token>`。详细示例见 [docs/API.md](docs/API.md)。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/auth/register` | 注册并直接返回 token |
| POST | `/api/auth/login` | 登录 |
| GET | `/api/auth/me` | 当前用户 |
| GET | `/api/problems` | 题库列表：`type` `tag` `source_tag` `year` `exam` `keyword` `status` `mine` `page` `page_size` |
| GET | `/api/problems/{id}` | 题目详情（含小题答案与解析） |
| POST | `/api/problems` | 投稿 |
| PUT | `/api/problems/{id}` | 编辑（驳回后自动回到 pending） |
| DELETE | `/api/problems/{id}` | 删除 |
| POST | `/api/problems/{id}/review` | 审核：`{action:"approve"\|"reject", reason}` |
| GET | `/api/admin/pending` | 待审列表 |
| POST | `/api/problems/{id}/answer` | 作答判分：`{answers:{sub_id:"A"}}`，做错自动入错题本 |
| GET | `/api/problems/{id}/submissions` | 我的该题作答记录 |
| GET | `/api/tags` / POST `/api/tags` / DELETE `/api/tags/{id}` | 标签 |
| GET | `/api/problem-lists` | 题单（`scope=visible\|public\|mine`） |
| POST | `/api/problem-lists` | 创建题单 |
| GET | `/api/problem-lists/{id}` | 题单详情（仅 approved 题目） |
| PUT / DELETE | `/api/problem-lists/{id}` | 编辑 / 删除 |
| POST | `/api/problem-lists/{id}/items` | 收录题目 |
| DELETE | `/api/problem-lists/{id}/items/{problem_id}` | 移除题目 |
| PUT | `/api/problem-lists/{id}/reorder` | 重新排序 |
| GET | `/api/wrong-questions?scope=due\|all\|mastered` | 错题列表 |
| GET | `/api/wrong-questions/today-count` | 今日待复习 / 总数 / 已掌握 |
| GET | `/api/wrong-questions/{id}/detail` | 重做所需题干与选项 |
| PATCH | `/api/wrong-questions/{id}` | 标记错因 `{error_type:1..4}` |
| POST | `/api/wrong-questions/{id}/review` | 重做结果 `{review_result:1\|0}` |
| DELETE | `/api/wrong-questions/{id}` | 移出错题本 |
| GET | `/api/stats/me` | 个人统计（排除模拟考试） |
| POST | `/api/mock-exams` | 组卷 `{exam_type:"J"\|"S"}` |
| GET | `/api/mock-exams` | 我的模拟考试历史 |
| GET | `/api/mock-exams/{id}` | 试卷（进行中不下发答案） |
| POST | `/api/mock-exams/{id}/submit` | 交卷判分 `{answers:{sub_id:"A"}}` |
| GET | `/api/mock-exams/{id}/result` | 成绩与逐题解析 |

## 九、关键实现说明

### 9.1 密码与 JWT

`app/security.py` 把密码逻辑收敛为两个函数，日后换 bcrypt/argon2 只改这里：

```python
def hash_password(raw_password: str) -> str:
    return hashlib.sha256(raw_password.encode("utf-8")).hexdigest()
```

登录成功签发 HS256 JWT（`sub`=用户 id，`role`），`deps.get_current_user` 解出用户并校验存在性，`require_admin` 做角色校验。

### 9.2 错题复习调度

`app/services.py`：

- 首次做错：`next_review_at = now + 1 天`，`redo_status=0`，`consecutive_pass=0`
- 重做答对：`consecutive_pass += 1`，间隔阶梯 `[1, 3, 7]` 天；**连续答对两次** → 标记掌握（`next_review_at=None`，移出队列）
- 重做答错：`consecutive_pass=0`，回到 1 天后
- 每次重做写一条 `wrong_reviews` 记录

首页 `今日待复习 N 题` 来自 `/api/wrong-questions/today-count`。

### 9.3 模拟考试组卷与判分

- 结构：15 单选 + 3 阅读 + 2 完善；`ORDER BY random()` 从 approved 池抽题，按题型分批抽取，同卷不重复
- 分值还原真实试卷：单选每题 2 分（30），阅读 3 题 13/13/14 分（40），完善 2 题各 15 分（30）；大题内部按小题均分
- 题量不足时返回 400 并明确提示缺哪类题，避免产出不完整试卷
- 进行中接口**不下发** `correct_answer` 与 `analysis_md`；交卷后写入 `mock_exams.answers_json`，并落 `submissions`（带 `mock_exam_id`）
- 成绩页展示：总分、小题正确率、用时、题型得分率、知识点得分率、逐题解析

### 9.4 Markdown / 公式 / 安全

```js
const md = new MarkdownIt({ html: false, linkify: true, breaks: true, highlight })
md.use(katexPlugin, { throwOnError: false, errorColor: '#cc0000' })
const html = DOMPurify.sanitize(md.render(src), {
  USE_PROFILES: { html: true, mathMl: true, svg: true },
  FORBID_TAGS: ['style', 'script', 'iframe', 'object', 'embed', 'form', 'input', 'button', 'textarea'],
})
```

`html:false` 直接禁用原始 HTML，DOMPurify 作为第二道防线；KaTeX 的 MathML 与 SVG 输出被显式放行，保证公式与无障碍信息完整。

### 9.5 弹窗规范

```js
const { confirm, prompt } = useConfirmDialog()

if (await confirm('确定删除该题单？')) { /* ... */ }

const reason = await prompt({
  title: '驳回题目',
  message: '请填写驳回原因，作者可据此修改后重新提交。',
  required: true,
  danger: true,
})
```

`ConfirmDialog.vue` 基于 `el-dialog` 封装，统一圆角 / 主色 / 危险态红色 / 文本域校验，全站仅此一处弹窗实现；纯告知信息使用 `ElMessage`。

## 十、测试与验证

```bash
# 端到端接口冒烟测试（需先启动后端；覆盖注册登录、投稿、审核驳回重提、判分、
# 错题调度、统计、题单、模拟考试、权限校验等 39 个断言）
cd backend
python smoke_test.py http://127.0.0.1:8000
```

前端已用 Edge 无头浏览器走完整流程（登录 → 筛选 → 作答 → 审核弹窗 → 驳回 → 模拟考试 → 交卷），**控制台无报错**，截图见 [docs/screenshots](docs/screenshots)：

| 页面 | 截图 |
| --- | --- |
| 首页 | ![首页](docs/screenshots/01-home.png) |
| 题库筛选 | ![题库](docs/screenshots/03-problems.png) |
| 题目详情（公式 + 代码高亮） | ![详情](docs/screenshots/04-problem-detail.png) |
| 作答后逐题解析 | ![判分](docs/screenshots/05-problem-result.png) |
| 投稿编辑器 | ![投稿](docs/screenshots/11-problem-edit.png) |
| 审核弹窗 | ![审核](docs/screenshots/14-review-dialog.png) |
| 统一输入弹窗 | ![弹窗](docs/screenshots/15-confirm-prompt.png) |
| 考试中（倒计时 + 答题卡） | ![考试](docs/screenshots/18-mock-exam.png) |
| 交卷判分结果 | ![成绩](docs/screenshots/20-mock-result.png) |
| 逐题解析 | ![逐题解析](docs/screenshots/20b-mock-result-analysis.png) |
| 错题本 | ![错题](docs/screenshots/09b-wrong-book-all.png) |
| 做题统计 | ![统计](docs/screenshots/10-stats.png) |
| 移动端首页 | ![移动端](docs/screenshots/21-mobile-home.png) |

## 十一、云托管部署（推荐生产方案）

> 适用场景：没有长期在线的 Linux 服务器，也不想为网站一直开着个人电脑。
> 前端、后端、数据库全部托管在平台上，**本地设备关机不影响访问**，也不需要自己维护 Nginx、systemd 和证书。

### 11.1 目标架构

```text
                         HTTPS
访客浏览器 ──────────────────────────────► Vercel
                                          （Vue 3 静态站点 dist/，全球 CDN）
                                              │
                                              │ fetch https://cspjs-api.onrender.com/api/...
                                              │ 跨域请求，需后端 CORS 放行前端域名
                                              ▼
                                    Render Web Service
                                    （FastAPI + uvicorn，监听 0.0.0.0:$PORT）
                                              │
                                              │ postgresql://（同区域内网连接串）
                                              ▼
                                    Render PostgreSQL
                                    （托管数据库，唯一需要备份的状态）
```

- 前端是纯静态产物，不跑 Node 服务端；构建一次后由 CDN 分发。
- 后端无状态：会话靠 JWT，进程随时可重启；所有业务数据都在 PostgreSQL。
- 因此**只有数据库需要备份**，前后端都可以随时删除重建。

### 11.2 平台选型

主推组合（下面的步骤以这两家为准）：

| 部分 | 主推 | 免费档要点 |
| --- | --- | --- |
| 前端 | **Vercel** | 100 GB/月流量、100 万 CDN 请求；**Hobby 仅限个人非商业用途** |
| 后端 | **Render Web Service** | 0.1 CPU / 512 MB，15 分钟无流量休眠、唤醒约 1 分钟，750 免费实例小时/月（[官方说明](https://render.com/docs/free)） |
| 数据库 | **Render PostgreSQL** | 1 GB 存储、单工作区 1 个、**创建 30 天后过期**、无自动备份 |

备选（切换只涉及环境变量与 DNS，代码不用改）：

| 部分 | 备选 | 说明 |
| --- | --- | --- |
| 前端 | Netlify / Cloudflare Pages | Netlify 免费档 100 GB 带宽 + 300 构建分钟；Cloudflare Pages 带宽不计费、500 次构建/月。两者都读 `frontend/public/_redirects`，仓库已提供 |
| 后端 | Railway / Fly.io | Railway 目前以试用额度 + 按量计费为主，没有永久免费档；Fly.io 需要自己写 `fly.toml`，免费额度经常调整。迁移时只要保证启动命令监听 `0.0.0.0:$PORT` 并配好同样的环境变量 |
| 数据库 | Neon / Supabase | 免费 PostgreSQL 有存储上限和闲置暂停，但**不会 30 天删库**，适合做长期零成本方案（见 11.8） |

> 成本参考：**完全零成本** = Vercel 免费 + Render 免费 Web Service + Neon 免费 PG（接受冷启动）；
> **省心** = Render 付费 Web Service（$7/月起）+ Render 付费 PostgreSQL（$6/月起），约 $13/月，无休眠、无 30 天过期。

### 11.3 前置准备（只做一次）

1. 把项目推送到 GitHub（公开或私有均可，平台需要授权读取）。
2. 确认仓库里有 `frontend/pnpm-lock.yaml`（Vercel 据此选择 pnpm 并复现依赖）。
3. 本地先跑通一次构建：`cd frontend && pnpm build`，确认能产出 `dist/`。
4. 注册并登录平台，建议直接用 GitHub 账号登录：
   - Render：<https://dashboard.render.com/register>
   - Vercel：<https://vercel.com/signup>
5. 先记下两个目标地址（平台会自动分配默认域名，之后可绑自定义域名）：
   - 后端：`https://cspjs-api.onrender.com`
   - 前端：`https://cspjs.vercel.app`

### 11.4 第一步：创建托管 PostgreSQL（Render 控制台）

1. 打开 <https://dashboard.render.com> → 右上角 **New +** → **Postgres**。
2. 按下表填写：

   | 字段 | 填什么 |
   | --- | --- |
   | **Name** | `cspjs-db` |
   | **Database** | `cspjs` |
   | **User** | `cspjs` |
   | **Region** | `Singapore`（或离用户最近的区域；**必须与后端同区域**，否则用不了内网连接） |
   | **PostgreSQL Version** | 16（默认即可） |
   | **Instance Type** | `Free`（30 天过期，见 11.8；有真实用户就选付费） |

3. 点 **Create Database**，等待状态变为 `Available`（约 1–3 分钟）。
4. 进入实例页，找到 **Connections**，复制两条连接串备用：
   - **Internal Database URL**：给 Render 后端用（同区域、走内网，不耗公网带宽）
   - **External Database URL**：给本地 `psql` / 备份 / 重置密码用（带 `?sslmode=require`）
5. **不需要手动建表**：后端首次启动会 `create_all` 建表并写入演示数据（`AUTO_SEED=true`）。

> 连接串形如 `postgresql://cspjs:密码@dpg-xxxx-a.singapore-postgres.render.com/cspjs`。
> 项目会自动把 `postgresql://` 规范成 `postgresql+psycopg://`（[backend/app/database.py](backend/app/database.py) 的 `normalize_database_url`），**不要**手写驱动前缀，也不要把密码提交进仓库。

### 11.5 第二步：部署后端（Render Web Service）

**方式 A：手动创建（推荐第一次照着做）**

1. **New +** → **Web Service** → **Build and deploy from a Git repository** → 连接 GitHub → 选择本项目仓库。
2. 按下表填写：

   | 字段 | 填什么 |
   | --- | --- |
   | **Name** | `cspjs-api`（决定默认域名 `https://cspjs-api.onrender.com`） |
   | **Region** | 与数据库一致（Singapore） |
   | **Root Directory** | `backend` ← **必填**，仓库根目录不是 Python 项目 |
   | **Runtime** | `Python 3`（自动识别 `requirements.txt`） |
   | **Build Command** | `pip install -r requirements.txt` |
   | **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
   | **Instance Type** | `Free` |
   | **Health Check Path** | `/api/health` |

   > 启动命令必须监听 `0.0.0.0` 与平台注入的 `$PORT`，否则健康检查失败、部署被判为不健康。

3. 展开 **Advanced** → **Add Environment Variable**，逐条添加：

   | Key | Value | 说明 |
   | --- | --- | --- |
   | `DATABASE_URL` | 11.4 复制的 **Internal Database URL** | 平台注入的 `postgresql://` 即可 |
   | `JWT_SECRET` | 随机长串：`python -c "import secrets;print(secrets.token_urlsafe(48))"` | 不要用默认值 |
   | `ALLOW_SQLITE_FALLBACK` | `false` | 禁止降级到临时磁盘 SQLite |
   | `AUTO_SEED` | `true` | 首次启动建表 + 播种，成功后再改 `false` |
   | `SEED_DEMO_STUDENT` | `false` | 不创建已知密码的演示学生账号 |
   | `CORS_ORIGINS` | `https://cspjs.vercel.app` | 前端域名，多个用英文逗号分隔 |
   | `PYTHON_VERSION` | `3.12.7` | 固定 Python 版本，避免平台默认版本漂移 |
   | `ADMIN_PASSWORD` | 自己设定的强密码 | 首次播种时生效，覆盖默认 `adminmagnet` |
   | `MOCK_EXAM_MINUTES` | `120` | 可选 |

4. 点 **Create Web Service**，在 **Logs** 里确认依次出现：

   ```text
   数据库已连接：postgresql+psycopg://...
   [seed] 管理员已创建：admin（密码来自 ADMIN_PASSWORD）
   [seed] 已写入 21 道演示题目、16 个标签
   CSP 刷题平台后端已启动，数据库：postgresql+psycopg://...
   ```

5. 访问 `https://cspjs-api.onrender.com/api/health`，应返回：

   ```json
   { "status": "ok", "app": "CCF CSP 第一轮认证刷题平台", "database": "postgresql", "mock_exam_minutes": 120 }
   ```

6. 打开 `https://cspjs-api.onrender.com/docs` 能看到 Swagger 文档即部署成功。
7. 回到 **Environment**，把 `AUTO_SEED` 改为 `false` → **Save Changes**（会自动重启，几秒完成）。

**方式 B：Blueprint 一键创建（可选）**

仓库根目录已提供 [render.yaml](render.yaml)。在 Render 里 **New +** → **Blueprint** → 选择仓库 → **Apply**，
会同时创建 `cspjs-api`（Web Service）和 `cspjs-db`（PostgreSQL），并自动生成 `JWT_SECRET`；
创建过程中只需补填 `CORS_ORIGINS` 与 `ADMIN_PASSWORD`。之后同样把 `AUTO_SEED` 改回 `false`。

### 11.6 第三步：部署前端（Vercel）

1. 打开 <https://vercel.com/new> → **Import Git Repository** → 选择本仓库。
2. 在 **Configure Project** 页面填写：

   | 字段 | 填什么 |
   | --- | --- |
   | **Project Name** | `cspjs`（决定默认域名 `https://cspjs.vercel.app`） |
   | **Framework Preset** | `Vite`（自动识别） |
   | **Root Directory** | 点 **Edit** → 选 `frontend` ← **必填**，否则会去构建仓库根目录 |
   | **Build Command** | `pnpm build`（`frontend/vercel.json` 也已声明，保持一致） |
   | **Output Directory** | `dist` |
   | **Install Command** | `pnpm install --frozen-lockfile`（默认） |
   | **Environment Variables** | `VITE_API_BASE = https://cspjs-api.onrender.com/api` |

   > `VITE_API_BASE` **必须带 `/api` 后缀**（代码里是 `${VITE_API_BASE}/auth/login` 这种拼法）。
   > 它是**构建期**变量，之后修改必须重新 Deploy 才生效；在 Environment Variables 里至少勾选 **Production**，只勾 Preview 的话线上不会生效。

3. 点 **Deploy**，等待 1–2 分钟，得到 `https://cspjs.vercel.app`。
4. 回到 Render → `cspjs-api` → **Environment**，把 `CORS_ORIGINS` 改成 `https://cspjs.vercel.app`（有多个域名用逗号分隔）→ **Save Changes**。
5. 打开前端域名，注册/登录、浏览题库、做一套模拟卷，确认读写都正常。

> **SPA 路由回退（容易踩坑）**：Vite 是纯前端路由，直接刷新 `/problems/12` 时平台默认会 404。
>
> - Vercel：由仓库里的 [frontend/vercel.json](frontend/vercel.json) 的 `rewrites` 处理
>   （Vercel 官方文档明确说明 Vite SPA 需要这样配置，见 [Vite on Vercel](https://vercel.com/docs/frameworks/frontend/vite)）；
> - Netlify / Cloudflare Pages：由 [frontend/public/_redirects](frontend/public/_redirects) 处理（构建时被复制进 `dist`）。
>
> 如果深链仍然 404，检查 **Root Directory 是否设为 `frontend`**、`vercel.json` 是否在 `frontend/` 下。
> 另外，若以后在 Vercel 上再加 `/api` 代理，记得把 `/api` 从 `rewrites` 的匹配范围里排除，否则接口请求会被改写成 `index.html`。

### 11.7 前后端联调注意点

| 主题 | 要点 |
| --- | --- |
| CORS | 后端只放行 `CORS_ORIGINS` 里的**完整 origin**（`https://`、不带末尾 `/`）。前端换域名或新增 Vercel 预览域名（`cspjs-git-xxx-你的名字.vercel.app`）后，必须同步更新并重启后端，否则浏览器报 CORS |
| `VITE_API_BASE` | 构建期内联，必须是 `https://<后端域名>/api`。写成 `http://` 会被浏览器按混合内容拦截，漏掉 `/api` 会 404（末尾多写 `/` 会被前端自动去掉，但不建议） |
| 预检请求 | 前端带 `Authorization` 头，浏览器会先发 `OPTIONS`；项目的 CORS 中间件已放行所有方法与头，不需要再配 Nginx |
| SPA 回退 | Vercel 用 `vercel.json`，Netlify/CF Pages 用 `_redirects`（见 11.6 末尾） |
| 免费休眠 | 后端 15 分钟无请求会休眠，唤醒约 1 分钟；首屏转圈较久属于正常现象，不是故障（见 11.8） |
| 数据库区域 | 后端与数据库必须同区域才能用 Internal URL；跨区域只能用 External URL，会绕公网且更慢 |
| 时间与统计 | 后端统一 UTC 存储，页面按浏览器本地时区显示；"今日做题"按 UTC 自然日统计 |

自检命令（把域名换成自己的）：

```bash
# 1) 后端存活
curl -s https://cspjs-api.onrender.com/api/health

# 2) CORS 是否放行前端域名（应出现 access-control-allow-origin）
curl -s -D - -o /dev/null -H "Origin: https://cspjs.vercel.app" \
  "https://cspjs-api.onrender.com/api/problems?page_size=1" | grep -i access-control

# 3) 前端深链是否回退到 index.html（应返回 200 且是 HTML）
curl -s -o /dev/null -w "%{http_code}\n" https://cspjs.vercel.app/problems/1
```

### 11.8 免费档的真实限制（不美化）

| 限制 | 具体表现 | 影响 | 应对 |
| --- | --- | --- | --- |
| Render 免费 Web Service 休眠 | 15 分钟无入站流量即停机；下次请求约 1 分钟唤醒；0.1 CPU / 512 MB | 第一个访客要等几十秒，并发很低 | 接受冷启动；或每 10 分钟 ping `/api/health` 保温（会消耗实例小时）；或升级 $7/月实例 |
| Render 免费实例小时 | 每工作区 750 小时/月，休眠不计；用尽后所有免费服务暂停到月底 | 单个服务全天常开约 744 小时，已接近上限，**再开一个免费服务就会超** | 只跑一个免费后端；或升级 |
| Render 免费 PostgreSQL 过期 | **创建 30 天后过期**；过期后 14 天内可升级付费，之后**连数据一起删除**；无备份、无 PITR、无连接池 | 到期不处理会直接丢库 | 有真实数据就别用免费库：升级付费 PG（$6/月起），或换 Neon/Supabase 免费库并定期 `pg_dump` |
| Render 免费 PG 容量 | 1 GB 存储、单工作区仅 1 个免费库、256 MB 内存、100 连接 | 大量提交/测试数据会顶到上限 | 本项目只存文本，1 GB 够用较久；定期清理测试数据 |
| Render Hobby 额度 | 每月 5 GB 出站带宽、500 构建分钟 | 超带宽会计费或暂停免费服务 | 静态资源交给 Vercel，不要从后端返回大文件 |
| Vercel Hobby 用途 | **仅限个人、非商业用途**；100 GB/月流量、100 万 CDN 请求 | 机构/商业化运营不合规 | 商业用途升级 Pro（$20/月），或换 Cloudflare Pages（带宽不计费） |
| Vercel 构建变量 | 环境变量在构建时写死进 bundle | 改了 `VITE_API_BASE` 不重新部署不生效 | 改完手动 **Redeploy** |
| 免费库重建后 | 新库为空，没有表和数据 | 页面空白或 500 | 新库把 `AUTO_SEED` 设回 `true` 跑一次，再改回 `false` |

**关于"免费又长期在线"的现实建议**：Render 免费 PostgreSQL 的 30 天过期绕不开。想零成本长期用，推荐：

1. 前端 Vercel（免费、无休眠）；
2. 后端 Render 免费 Web Service（接受冷启动）；
3. 数据库改用 **Neon** 或 **Supabase** 的免费 PostgreSQL（不会 30 天删库，但有存储上限与闲置暂停），把 `DATABASE_URL` 填成它们的连接串（通常要带 `?sslmode=require`）。

代价是三家平台的免费策略都可能变，上线前以官网为准；重要数据始终自己留一份 `pg_dump`。

> 还有两个容易忽略的点：
> - **Render 免费实例没有 Shell / SSH**，不能在控制台执行命令；改密码、备份、跑脚本都要在本机用 External Database URL 完成（见 11.10）。
> - Render 免费 Web Service 的本地磁盘是**临时的**：即使部署了代码，写进容器的文件在重启/休眠后会消失——所以必须用托管 PostgreSQL，不能靠 SQLite（这正是 `ALLOW_SQLITE_FALLBACK=false` 的意义）。
> - 首次播种在 `SEED_DEMO_STUDENT=true`（默认）时会创建 `student / student123` 这个**已知密码**账号；云托管必须设为 `false`，否则任何人都能拿它登录和投稿。

### 11.9 部署检查清单（上线前逐项确认）

- [ ] `JWT_SECRET` 已替换为随机长字符串（不是 `change-me-in-production-please`）
- [ ] `ALLOW_SQLITE_FALLBACK=false`（避免后端悄悄用临时磁盘 SQLite，重启即丢数据）
- [ ] `AUTO_SEED` 首次启动为 `true`，确认建表与播种成功后已改回 `false`
- [ ] `SEED_DEMO_STUDENT=false`（不要保留 `student / student123` 这类已知密码账号）
- [ ] 管理员默认密码已修改（用 `ADMIN_PASSWORD` 首次注入，或部署后用 `python -m app.passwd` 重置，见 11.10）
- [ ] `CORS_ORIGINS` 包含前端实际域名（含 `https://`、无末尾 `/`；有预览域名则一并加入）
- [ ] `VITE_API_BASE` 指向后端实际地址且带 `/api`，修改后已重新部署
- [ ] 前端能正常调通后端 `/api/health`（浏览器 Network 中 200，且无 CORS 报错）
- [ ] 深链刷新（如 `/problems/1`）返回页面而不是 404
- [ ] 已在 Render 控制台确认数据库到期日，并设置日历提醒（免费库 30 天）
- [ ] 已手动导出一份数据库备份（免费库不提供自动备份）

### 11.10 上线后的运维

运维脚本：[backend/app/passwd.py](backend/app/passwd.py)（重置任意用户密码）。

**改管理员密码**（三种方式任选）：

1. **首次部署时**：在 Render 环境变量里把 `ADMIN_PASSWORD` 设为强密码，再让 `AUTO_SEED` 首次运行。`seed` 只在用户不存在时创建，所以密码在创建那一刻生效。
2. **部署后重置（推荐）**：在本机用**外部**连接串执行：

   ```bash
   # 先复制 Render 控制台的 External Database URL（没有 ?sslmode=require 就手动补上）
   export DATABASE_URL="postgresql://cspjs:密码@dpg-xxxx.singapore-postgres.render.com/cspjs?sslmode=require"
   cd backend
   python -m app.passwd --username admin
   ```

   也可以非交互：`python -m app.passwd --username admin --password '新的强密码'`。

3. **直接改库**（不推荐，容易手抖）：先本地算出 SHA-256：

   ```bash
   python -c "import hashlib;print(hashlib.sha256('新的强密码'.encode()).hexdigest())"
   ```

   再到 Render 数据库的 **Connect → PSQL Command** 里执行：

   ```sql
   UPDATE users SET password_hash = '<上一步的 64 位十六进制>' WHERE username = 'admin';
   ```

**备份**（免费库唯一靠谱的兜底）：

```bash
# 本机执行。Render 的外部连接强制 SSL；若连接串没带 ?sslmode=require，请手动补上
export DATABASE_URL="postgresql://cspjs:密码@dpg-xxxx.singapore-postgres.render.com/cspjs?sslmode=require"

# 备份
pg_dump "$DATABASE_URL" -Fc -f "cspjs-$(date +%F).dump"

# 恢复
pg_restore --clean --no-owner -d "$DATABASE_URL" cspjs-2026-11-01.dump
```

**绑定自定义域名**：

1. Vercel 项目 → **Settings → Domains** → 添加 `csp.example.com`，按提示加 `CNAME → cname.vercel-dns.com`；
2. Render 服务 → **Settings → Custom Domains** → 添加 `api.csp.example.com`，按提示加 `CNAME`；
3. 两端证书会自动签发；然后把 `CORS_ORIGINS` 改成 `https://csp.example.com`、`VITE_API_BASE` 改成 `https://api.csp.example.com/api`，**重新部署前端并重启后端**；
4. 用 11.7 的 `curl` 再验一次 CORS 与深链。

**日常排障**：

- 后端 502 / 超时 → 看 Render 的 **Logs** 与 **Events**，确认服务是否在休眠或重启；
- 前端接口 404 → 检查 `VITE_API_BASE` 是否漏了 `/api`；
- 浏览器 CORS 报错 → 逐字符比对 `Origin` 与 `CORS_ORIGINS`；
- 登录后立刻 401 → `JWT_SECRET` 是否在重启后变了（多实例必须固定同一个值）；
- 数据库连接数满 → 免费库上限 100 连接，后端默认连接池很小，异常时重启服务。

## 十二、本地开发与演示（仅用于开发 / 课堂演示 / 阶段性展示）

> **明确边界**：本节所有方案都依赖一台一直开着的机器（本地 PC 或虚拟机），**不作为长期在线方案**。
> 真实上线请用第十一节。这里保留虚拟机 + Nginx + systemd 的完整做法，方便课堂演示或内网使用。

### 12.1 本机开发

见第四节：`uvicorn app.main:app --reload --port 8000` + `pnpm dev`，前后端通过 Vite 代理打通，不需要 Nginx。
也可以用 `scripts/dev.ps1` 或 `scripts/dev.sh` 一键起两个进程。

### 12.2 本地虚拟机 + Nginx + systemd（原方案）

适用：Ubuntu 22.04 虚拟机、内网演示、断网机房。

**1) 系统依赖**

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv postgresql nginx curl git
# Node 20+（NodeSource）
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm i -g pnpm
```

**2) 数据库与后端**

```bash
sudo -u postgres psql -c "CREATE DATABASE cspjs;"
sudo -u postgres psql -c "CREATE USER cspjs WITH PASSWORD 'cspjs';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE cspjs TO cspjs;"

sudo mkdir -p /opt/cspjs && sudo chown -R $USER:$USER /opt/cspjs
git clone <你的仓库> /opt/cspjs/app
cd /opt/cspjs/app/backend
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env    # 填 DATABASE_URL / JWT_SECRET；同域部署时 CORS_ORIGINS 可留空或写 http://<虚拟机IP>
```

**3) systemd 常驻后端**

`/etc/systemd/system/cspjs-api.service`：

```ini
[Unit]
Description=CSP 刷题平台 API
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/cspjs/app/backend
EnvironmentFile=/opt/cspjs/app/backend/.env
ExecStart=/opt/cspjs/app/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
# 让服务用户能读取代码与 .env（后续以普通用户 git pull 后需重新执行一次）
sudo chown -R www-data:www-data /opt/cspjs/app/backend
sudo chmod 600 /opt/cspjs/app/backend/.env
sudo systemctl enable --now cspjs-api
sudo systemctl status cspjs-api
```

**4) 构建前端并交给 Nginx**

```bash
cd /opt/cspjs/app/frontend
pnpm install --frozen-lockfile
# 同域部署（Nginx 反代 /api）时，VITE_API_BASE 用默认的 /api 即可
pnpm build
sudo mkdir -p /var/www/cspjs
sudo rsync -a --delete dist/ /var/www/cspjs/
```

**5) Nginx 站点配置**

`/etc/nginx/sites-available/cspjs`：

```nginx
server {
    listen 80;
    server_name _;                 # 内网演示可直接用 IP 访问

    root /var/www/cspjs;
    index index.html;

    # 前端 history 路由回退
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 反代后端 API（同域，因此前端 VITE_API_BASE=/api 即可，无需 CORS）
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }

    # 带 hash 的静态资源可长缓存
    location /assets/ {
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/cspjs /etc/nginx/sites-enabled/cspjs
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

浏览器访问 `http://<虚拟机IP>/` 即可（虚拟机需桥接网络，或在宿主机做端口转发）。

> 该方案没有 HTTPS，只适合可信内网。要给局域网外的同学看，用 12.3 的临时隧道，**演示完立刻关闭**。

### 12.3 内网穿透临时暴露（cloudflared / ngrok）

> 仅用于演示：地址是临时的，关掉进程就失效。不要长期挂在公网，也不要在这类地址上存真实数据。

**cloudflared（免费，快速隧道无需账号）**

```bash
# Windows 下载 cloudflared.exe；macOS: brew install cloudflared
cloudflared tunnel --url http://127.0.0.1:8000     # 给后端一个 https 临时地址
```

**ngrok**

```bash
ngrok http 8000
```

**前端要跟着改**：把后端临时地址写进 `VITE_API_BASE` 再构建：

```bash
cd frontend
VITE_API_BASE="https://<随机名>.trycloudflare.com/api" pnpm build
pnpm preview --port 8080        # 需要的话再用第二条隧道暴露前端
```

同时把后端 `CORS_ORIGINS` 加上前端隧道地址（如果前端也走隧道）并重启服务。演示结束：

1. `Ctrl+C` 关闭隧道进程；
2. 把 `VITE_API_BASE` 改回正式地址；
3. 确认没有把临时域名写进 `.env` 后提交。

### 12.4 演示环境注意事项

- 演示前可 `python -m app.seed --reset && python -m app.seed` 得到干净数据；演示后同样清空，避免把演示账号带到正式环境。
- 虚拟机磁盘快照比 Nginx 配置更重要：演示前先打快照。
- 默认密码 `adminmagnet` 在演示环境也必须改，哪怕只开一天。
- 宿主机睡眠 / 虚拟机挂起会让站点立刻不可用；这是选择本地方案必须接受的代价。

## 十三、已知取舍

- 第一轮初赛全部为**单项选择**，故作答 UI 使用单选；数据层 `correct_answer` 仍支持 `"AB"` 这类多答案并按集合比较；
- 模拟考试进行中的作答保存在浏览器 localStorage 草稿（服务端仅在交卷时落库），刷新不丢、换设备不迁移；
- 统计中的"今日"按 UTC 自然日计算；
- Python 包与 pnpm 安装脚本策略以 `requirements.txt`、`pnpm-workspace.yaml` 为准；
- 云托管推荐组合（Vercel + Render + Render PostgreSQL）的免费档存在休眠与 30 天数据库过期，详见 11.8；长期在线需要至少数据库升级付费或改用外部免费 PG。
