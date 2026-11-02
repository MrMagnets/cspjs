"""FastAPI 应用入口（Cloudflare Workers + 本地开发双模式）。

Workers
-------
- 通过 ``from workers import asgi`` 提供的 ASGI 适配器把 FastAPI 挂到 Worker 上；
- 文件末尾的 ``Default = asgi.entrypoint(app)`` 是 Workers 的入口；
- Worker 的绑定（Hyperdrive、Secrets、Vars）不在进程环境里，而是在 ASGI
  ``scope["env"]`` 中。中间件会把其中的运行时配置同步到 ``settings``，数据库依赖则直接
  从 ``scope["env"].HYPERDRIVE`` 读取连接串（见 database.py）。
- Workers 不支持 threading：FastAPI 对 ``def`` 端点默认使用线程池，这里在 Worker 上
  把同步端点/依赖包装成协程，直接在事件循环里执行（pg8000 的 socket 操作本身是异步的）。

导入约定
--------
Cloudflare Workers 的 entrypoint 不是以 package 形式加载的，因此本目录内统一使用
顶层绝对导入（``from config import settings``）。为了让本地 ``uvicorn app.main:app``
与 ``python -m app.seed`` 也能工作，``app/__init__.py`` 和本文件都会把 ``app/`` 目录
加入 ``sys.path``。
"""
from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager

# 关键：Workers 直接加载 app/main.py 时，保证 app/ 在 sys.path 中，
# 这样 `from config import settings` 这类顶层导入才能解析。
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.responses import JSONResponse, Response  # noqa: E402

from config import settings  # noqa: E402
from database import Base, dialect_name_for_request, engine  # noqa: E402
from routers import appeals, auth, contests, discussions, mock_exams, problem_lists, problems, stats, tags, users, wrong_questions  # noqa: E402
from seed import seed as run_seed  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("cspjs")


def _is_workers() -> bool:
    """Pyodide 运行时一定能 import js；本地 CPython 没有。"""
    try:
        import js  # noqa: F401

        return True
    except Exception:  # noqa: BLE001
        return False


IS_WORKERS = _is_workers()

# Worker 的 vars / secrets → pydantic settings 字段（数据库连接串单独处理）
_STR_SETTINGS = {
    "JWT_SECRET": "jwt_secret",
    "CORS_ORIGINS": "cors_origins",
    "ENVIRONMENT": "environment",
    "APP_NAME": "app_name",
    "ADMIN_USERNAME": "admin_username",
}
_INT_SETTINGS = {
    "JWT_EXPIRE_MINUTES": "jwt_expire_minutes",
    "MOCK_EXAM_MINUTES": "mock_exam_minutes",
}


def _env_value(env, key: str):
    try:
        return getattr(env, key, None)
    except Exception:  # noqa: BLE001 - Pyodide JsProxy 对缺失属性可能抛错
        return None


def _apply_workers_env(env) -> None:
    """把 env 上的 vars / secrets 应用到全局 settings。

    settings 是进程内单例，security.py 等模块在使用时读取它，因此这里在每次请求
    前同步即可（同一个 isolate 内值通常不变）。
    """
    for env_key, attr in _STR_SETTINGS.items():
        value = _env_value(env, env_key)
        if value is None or value == "":
            continue
        setattr(settings, attr, str(value))

    for env_key, attr in _INT_SETTINGS.items():
        value = _env_value(env, env_key)
        if value is None or value == "":
            continue
        try:
            setattr(settings, attr, int(value))
        except (TypeError, ValueError):
            logger.warning("环境变量 %s 不是合法整数，已忽略", env_key)

    if settings.uses_placeholder_jwt_secret:
        raise RuntimeError(
            "JWT_SECRET 未配置。请执行 `npx wrangler secret put JWT_SECRET` "
            "或 `uv run pywrangler secret put JWT_SECRET`。"
        )


def _cors_headers(origin: str) -> dict[str, str]:
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Authorization, Content-Type, Accept",
        "Access-Control-Max-Age": "86400",
        "Vary": "Origin",
    }


def _origin_allowed(origin: str) -> bool:
    allowed = settings.cors_origin_list
    # CORS_ORIGINS=* 时反射实际 Origin（不使用 *，便于以后加 cookie）
    return "*" in allowed or origin in allowed


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Workers 的 ASGI 适配器会为每个请求驱动一次 lifespan；绝不能在这里建表/播种。
    if not IS_WORKERS:
        Base.metadata.create_all(bind=engine)
        if settings.auto_seed:
            run_seed()
        if settings.uses_placeholder_jwt_secret:
            logger.warning("JWT_SECRET 仍是占位符，仅可用于本地开发")
        if settings.uses_placeholder_admin_password:
            logger.warning("ADMIN_PASSWORD 仍是占位符，请尽快设置强密码")
    yield


app = FastAPI(
    title=settings.app_name,
    description="CSP-J/S 初赛训练系统后端 API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def runtime_env_and_cors(request: Request, call_next):
    """同步 Worker 环境，并处理动态 CORS（CORS_ORIGINS 来自 env）。"""
    env = request.scope.get("env")
    if env is not None:
        try:
            _apply_workers_env(env)
        except RuntimeError as exc:
            logger.error("Worker 配置错误：%s", exc)
            return JSONResponse({"detail": "服务配置错误，请检查环境变量"}, status_code=500)

    origin = request.headers.get("origin")

    if request.method == "OPTIONS" and origin:
        headers = _cors_headers(origin) if _origin_allowed(origin) else {}
        return Response(status_code=204, headers=headers)

    response = await call_next(request)
    if origin and _origin_allowed(origin):
        response.headers.update(_cors_headers(origin))
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """兜底：任何未处理异常都返回 JSON，避免 Cloudflare 返回 text/plain 错误页。"""
    logger.exception("未处理异常：%s %s", request.method, request.url.path)
    return JSONResponse({"detail": "服务器内部错误，请稍后重试"}, status_code=500)


for module in (auth, tags, problems, problem_lists, wrong_questions, stats, mock_exams, users, contests, discussions, appeals):
    app.include_router(module.router, prefix=settings.api_prefix)


@app.get("/api/health", tags=["系统"])
def health(request: Request):
    return {
        "status": "ok",
        "app": settings.app_name,
        "database": dialect_name_for_request(request),
        "mock_exam_minutes": settings.mock_exam_minutes,
    }


def _install_workers_sync_shim(fastapi_app: FastAPI) -> None:
    """Workers 不支持 threading：把同步端点/依赖改成在事件循环中直接执行。

    FastAPI 对 ``def`` 端点使用 ``run_in_threadpool``，在 Pyodide 里会失败。
    这里在路由注册完成后，把 Dependant 树里非生成器的同步 callable 包成协程，
    并重建 route.app，使 FastAPI 直接 await 它们。
    """
    if not IS_WORKERS:
        return

    import inspect

    from fastapi.dependencies.models import Dependant
    from fastapi.routing import APIRoute, request_response

    def wrap(dependant: Dependant) -> None:
        for sub in dependant.dependencies:
            wrap(sub)

        call = dependant.call
        if call is None:
            return
        if inspect.iscoroutinefunction(call) or inspect.isasyncgenfunction(call):
            return
        if inspect.isgeneratorfunction(call):
            return

        async def _async_call(*args, __call=call, **kwargs):
            return __call(*args, **kwargs)

        dependant.call = _async_call

    for route in fastapi_app.routes:
        if isinstance(route, APIRoute):
            wrap(route.dependant)
            # get_request_handler() 在创建时就把 is_coroutine 捕获进闭包，
            # 因此包装完 dependant 后必须重建 route.app。
            route.app = request_response(route.get_route_handler())


_install_workers_sync_shim(app)

# Workers 入口。本地没有 workers 模块时保持为普通 FastAPI 应用（uvicorn app.main:app）。
try:
    from workers import asgi
except ModuleNotFoundError:  # pragma: no cover - 本地开发
    asgi = None

if asgi is not None:
    Default = asgi.entrypoint(app)
