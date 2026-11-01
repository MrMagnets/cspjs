"""FastAPI 应用入口。

启动：
    cd backend
    uvicorn app.main:app --reload --port 8000
接口文档：http://127.0.0.1:8000/docs

Serverless（Vercel）：
    由 backend/vercel.json 的 @vercel/python 构建器加载本文件，
    入口是下面的模块级变量 `app`（ASGI 应用），不要改名或包进函数。
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .routers import auth, mock_exams, problem_lists, problems, stats, tags, wrong_questions
from .seed import seed as run_seed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("cspjs")


def _check_security_settings() -> None:
    """部署前的配置自检：占位符密钥 / 临时 SQLite 绝不允许进生产环境。"""
    if settings.is_production and settings.allow_sqlite_fallback:
        raise RuntimeError(
            "生产环境必须设置 ALLOW_SQLITE_FALLBACK=false：Serverless/云托管的本地磁盘是临时的，"
            "SQLite 会导致重启即丢数据。"
        )
    if settings.is_production and not settings.database_url:
        raise RuntimeError("生产环境必须设置 DATABASE_URL（托管 PostgreSQL 连接串）。")

    if settings.uses_placeholder_jwt_secret:
        message = (
            "JWT_SECRET 仍是占位符 your-secret-here。请设置随机长字符串，例如："
            'python -c "import secrets; print(secrets.token_urlsafe(48))"'
        )
        if settings.is_production:
            raise RuntimeError(message)
        logger.warning(message)

    if settings.uses_placeholder_admin_password:
        logger.warning(
            "ADMIN_PASSWORD 仍是占位符；首次建库会用它创建管理员，请立即在环境变量中设置强密码"
        )

    if settings.seed_demo_student and not settings.demo_student_password:
        logger.warning("SEED_DEMO_STUDENT=true 但未设置 DEMO_STUDENT_PASSWORD，将跳过演示学生账号")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _check_security_settings()
    Base.metadata.create_all(bind=engine)
    if settings.auto_seed:
        run_seed()
    # 只打印隐藏密码后的连接串，避免把数据库密码写进平台日志
    logger.info(
        "CSP 刷题平台后端已启动，数据库：%s",
        engine.url.render_as_string(hide_password=True),
    )
    yield


# 全局 ASGI 应用：uvicorn、gunicorn 与 Vercel 的 @vercel/python 都通过这个变量加载。
# 必须保持模块级 `app`，不要改成别的名字或包进函数/if 语句里。
app = FastAPI(
    title=settings.app_name,
    description="CCF CSP-J/S 第一轮认证刷题平台后端 API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (auth, tags, problems, problem_lists, wrong_questions, stats, mock_exams):
    app.include_router(module.router, prefix=settings.api_prefix)


@app.get("/api/health", tags=["系统"])
def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "database": engine.dialect.name,
        "mock_exam_minutes": settings.mock_exam_minutes,
    }
