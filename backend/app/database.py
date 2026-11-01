"""数据库层：Cloudflare Workers + Hyperdrive + pg8000。

设计要点
--------
1. Workers（Pyodide/WASM）里没有 psycopg2 这类 C 扩展，因此驱动固定为纯 Python 的
   ``pg8000``，SQLAlchemy URL 使用 ``postgresql+pg8000://``。
2. Workers 没有进程级配置，连接串只能从请求的 ``scope["env"]`` 里取：
   ``env.HYPERDRIVE.connectionString``。本模块按连接串缓存 Engine（每个 isolate 一份），
   绝不使用导入时创建的全局 Engine 连接 Hyperdrive。
3. Serverless 场景统一使用 ``NullPool``：Hyperdrive 本身负责连接池，Worker 侧不能
   长期持有连接，否则会打满 Neon 的连接数。
4. Hyperdrive 到 Neon 的 TLS 由 Hyperdrive 负责，Worker → Hyperdrive 走本地回环，
   因此连接串里的 ``sslmode`` / ``channel_binding`` 等参数需要剥离，否则 pg8000 会报
   未知参数。本地直连 Neon 时（非 Workers）则用 ``ssl_context`` 显式开启 TLS。

本地开发（uvicorn + SQLite 或本地 PostgreSQL）仍可使用 ``settings.database_url``，
未配置时回退到 SQLite 文件；这条路径不会在 Workers 上被使用。
"""
from __future__ import annotations

import logging
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

from fastapi import Request
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from .config import settings

logger = logging.getLogger("cspjs.database")

# pg8000.connect 不认识的连接参数（由 Hyperdrive 或本模块的 ssl_context 处理）
_UNSUPPORTED_QUERY_KEYS = {
    "sslmode",
    "ssl",
    "channel_binding",
    "target_session_attrs",
    "options",
}

# 每个 isolate 缓存少量 Engine；Hyperdrive 连接串在同一个 isolate 内是稳定的
_ENGINE_CACHE: dict[str, Engine] = {}
_ENGINE_CACHE_LIMIT = 8
_SSL_REQUIRED_MODES = {"require", "verify-ca", "verify-full"}


class Base(DeclarativeBase):
    pass


def _on_workers() -> bool:
    """Pyodide 运行时一定可以 import js；本地 CPython 没有该模块。"""
    try:
        import js  # noqa: F401

        return True
    except Exception:  # noqa: BLE001
        return False


def normalize_database_url(url: str) -> str:
    """把各种 PostgreSQL URL 统一成 SQLAlchemy + pg8000 形式。"""
    if not url:
        return url
    raw = url.strip()
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://") :]
    if raw.startswith("postgresql+psycopg2://"):
        raw = "postgresql://" + raw[len("postgresql+psycopg2://") :]
    if raw.startswith("postgresql+psycopg://"):
        raw = "postgresql://" + raw[len("postgresql+psycopg://") :]
    if raw.startswith("postgresql://"):
        return "postgresql+pg8000://" + raw[len("postgresql://") :]
    if raw.startswith("postgresql+pg8000://") or raw.startswith("sqlite"):
        return raw
    raise ValueError("不支持的数据库连接串，请使用 postgresql:// 或 sqlite:///")


def _split_query(url: str) -> tuple[str, dict[str, str]]:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", parts.fragment)), query


def _strip_unsupported_query(url: str) -> str:
    parts = urlsplit(url)
    kept = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in _UNSUPPORTED_QUERY_KEYS
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment))


def build_connection_url(raw: str) -> tuple[str, str]:
    """返回 (pg8000 URL, sslmode)。sslmode 已从 URL 中剥离。"""
    normalized = normalize_database_url(raw)
    if normalized.startswith("sqlite"):
        # SQLite URL（sqlite:///path）交给 SQLAlchemy 原样处理；urlunsplit 会破坏它
        return normalized, ""
    without_query, query = _split_query(normalized)
    sslmode = (query.get("sslmode") or "").lower()
    return _strip_unsupported_query(without_query), sslmode


def create_engine_from_url(raw: str) -> Engine:
    """由 Hyperdrive / 本地连接串创建 Engine（NullPool，绝不缓存连接）。"""
    url, sslmode = build_connection_url(raw)

    kwargs: dict = {
        "poolclass": NullPool,
        "pool_pre_ping": False,
        "future": True,
    }

    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    elif sslmode in _SSL_REQUIRED_MODES and not _on_workers():
        # Workers 侧由 Hyperdrive 终止 TLS；本地直连 Neon 时才需要 Python ssl
        import ssl

        kwargs["connect_args"] = {"ssl_context": ssl.create_default_context()}

    return create_engine(url, **kwargs)


def engine_for_url(raw: str) -> Engine:
    """按连接串缓存 Engine（每个 isolate 内复用，最多 8 个）。"""
    key = raw.strip()
    engine = _ENGINE_CACHE.get(key)
    if engine is not None:
        return engine

    engine = create_engine_from_url(raw)
    if len(_ENGINE_CACHE) >= _ENGINE_CACHE_LIMIT:
        _ENGINE_CACHE.clear()
    _ENGINE_CACHE[key] = engine
    return engine


def _hyperdrive_connection_string(env) -> str | None:
    """从 Workers 绑定中读取 Hyperdrive 连接串。

    Cloudflare 的 Hyperdrive 绑定同时暴露 ``connectionString`` 与
    ``host/port/user/password/database``；优先用完整连接串，缺失时再拼接。
    """
    if env is None:
        return None

    try:
        hyperdrive = getattr(env, "HYPERDRIVE", None)
    except Exception:  # noqa: BLE001
        hyperdrive = None
    if hyperdrive is None:
        return None

    try:
        connection_string = getattr(hyperdrive, "connectionString", None)
        if connection_string:
            return str(connection_string)
    except Exception:  # noqa: BLE001
        pass

    try:
        host = str(getattr(hyperdrive, "host"))
        port = str(getattr(hyperdrive, "port"))
        user = quote(str(getattr(hyperdrive, "user")), safe="")
        password = quote(str(getattr(hyperdrive, "password")), safe="")
        database = quote(str(getattr(hyperdrive, "database")), safe="")
    except Exception:  # noqa: BLE001
        return None

    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def resolve_connection_string(request: Request | None = None) -> str:
    """解析当前请求应使用的连接串。

    - Workers：必须存在 ``env.HYPERDRIVE``，否则直接报错（绝不能静默用 SQLite）。
    - 本地：使用 settings.database_url，缺省则回退 SQLite 文件。
    """
    scope = getattr(request, "scope", None) or {}
    env = scope.get("env")

    if env is not None:
        connection_string = _hyperdrive_connection_string(env)
        if not connection_string:
            raise RuntimeError(
                "缺少 Hyperdrive 绑定：请确认 wrangler.jsonc 中配置了 "
                'hyperdrive: [{ "binding": "HYPERDRIVE", "id": "..." }]'
            )
        return connection_string

    if settings.database_url:
        return settings.database_url
    return f"sqlite:///{settings.sqlite_path}"


def dialect_name_for_request(request: Request) -> str:
    """供 /api/health 使用；只创建 Engine，不建立连接。"""
    try:
        return engine_for_url(resolve_connection_string(request)).dialect.name
    except Exception:  # noqa: BLE001
        return "unknown"


# ---------------------------------------------------------------------------
# FastAPI 依赖：每个请求一个 Session，连接由 Hyperdrive 负责池化
# ---------------------------------------------------------------------------
async def get_db(request: Request):
    engine = engine_for_url(resolve_connection_string(request))
    db = Session(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 本地兼容：uvicorn / seed.py 仍需要一个模块级 Engine 与 SessionLocal。
# Workers 上不会用到它们（lifespan 已跳过建表/播种），这里只创建不连接。
# ---------------------------------------------------------------------------
def _build_local_engine() -> tuple[Engine, str]:
    if _on_workers():
        # Workers 上不使用本地 Engine；用内存 SQLite 占位，避免读写 Worker 文件系统
        return create_engine("sqlite://", poolclass=NullPool, future=True), "sqlite://"

    url = settings.database_url or f"sqlite:///{settings.sqlite_path}"
    try:
        engine = create_engine_from_url(url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("数据库已连接：%s", engine.url.render_as_string(hide_password=True))
        return engine, url
    except Exception as exc:  # noqa: BLE001
        if not settings.allow_sqlite_fallback or url.startswith("sqlite"):
            raise
        fallback = f"sqlite:///{settings.sqlite_path}"
        logger.warning("无法连接 PostgreSQL（%s），已降级为 %s", exc.__class__.__name__, fallback)
        return create_engine_from_url(fallback), fallback


engine, active_database_url = _build_local_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
