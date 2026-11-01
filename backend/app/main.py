"""FastAPI 应用入口。

启动：
    cd backend
    uvicorn app.main:app --reload --port 8000
接口文档：http://127.0.0.1:8000/docs
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    if settings.auto_seed:
        run_seed()
    # 只打印隐藏密码后的连接串，避免把数据库密码写进平台日志
    logger.info(
        "CSP 刷题平台后端已启动，数据库：%s",
        engine.url.render_as_string(hide_password=True),
    )
    yield


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
