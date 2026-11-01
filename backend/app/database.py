"""SQLAlchemy 引擎 / 会话 / Base。

连接串只从环境变量 `DATABASE_URL` 读取，代码里不含任何默认账号密码。
驱动为 psycopg2-binary（兼容 Vercel Serverless）。托管平台注入的
`postgresql://...` 或 `postgres://...` 会自动补成 `postgresql+psycopg2://`；
旧的 `postgresql+psycopg://`（psycopg3）写法也会被纠正。

本地未设置 DATABASE_URL 且 ALLOW_SQLITE_FALLBACK=true 时自动使用 SQLite 文件库，
保证 `uvicorn app.main:app` 开箱即可运行；云托管环境请把该开关设为 false。
"""
from __future__ import annotations

import logging
import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from .config import settings

logger = logging.getLogger("cspjs.database")


class Base(DeclarativeBase):
    pass


def normalize_database_url(url: str) -> str:
    """把平台注入的连接串规范成 SQLAlchemy + psycopg2 可识别的形式。

    postgres://...            → postgresql+psycopg2://...
    postgresql://...          → postgresql+psycopg2://...
    postgresql+psycopg://...  → postgresql+psycopg2://...（兼容旧配置）
    postgresql+psycopg2://... → 原样保留
    sqlite:///...             → 原样保留
    """
    if not url:
        return url
    raw = url.strip()
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://") :]
    if raw.startswith("postgresql+psycopg://"):
        raw = "postgresql+psycopg2://" + raw[len("postgresql+psycopg://") :]
    if raw.startswith("postgresql://"):
        raw = "postgresql+psycopg2://" + raw[len("postgresql://") :]
    return raw


def _make_engine(url: str):
    kwargs: dict = {"pool_pre_ping": True, "future": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    elif url.startswith("postgresql"):
        # 无本地 PG 时快速失败并可降级 SQLite，而不是长时间等待
        kwargs["connect_args"] = {"connect_timeout": 5}
    if os.environ.get("VERCEL"):
        # Serverless 下实例数量不可控：用 NullPool 避免每个实例各持有一批连接，
        # 把托管 PG 的连接数打满（配合 Neon 的连接池地址更稳）。
        kwargs["poolclass"] = NullPool
    return create_engine(url, **kwargs)


def _build_engine():
    url = normalize_database_url(settings.database_url)

    if not url:
        if not settings.allow_sqlite_fallback:
            raise RuntimeError(
                "DATABASE_URL 未设置。生产环境请提供托管 PostgreSQL 连接串，"
                "或显式设置 ALLOW_SQLITE_FALLBACK=true 使用本地 SQLite。"
            )
        fallback = f"sqlite:///{settings.sqlite_path}"
        logger.warning("未设置 DATABASE_URL，使用本地 SQLite：%s", fallback)
        return _make_engine(fallback), fallback

    try:
        engine = _make_engine(url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("数据库已连接：%s", engine.url.render_as_string(hide_password=True))
        return engine, url
    except Exception as exc:  # noqa: BLE001
        if not settings.allow_sqlite_fallback or url.startswith("sqlite"):
            raise
        fallback = f"sqlite:///{settings.sqlite_path}"
        logger.warning("无法连接 PostgreSQL（%s），已降级为 %s", exc.__class__.__name__, fallback)
        return _make_engine(fallback), fallback


engine, active_database_url = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
