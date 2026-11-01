from __future__ import annotations
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from config import settings
from database import Base, dialect_name_for_request, engine
from routers import auth, mock_exams, problem_lists, problems, stats, tags, wrong_questions
from seed import seed as run_seed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("cspjs")

def _is_workers() -> bool:
    try:
        import js
        return True
    except Exception:
        return False

IS_WORKERS = _is_workers()

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
    except Exception:
        return None

def _apply_workers_env(env) -> None:
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
            pass
    if settings.uses_placeholder_jwt_secret:
        raise RuntimeError("JWT_SECRET 未配置。")

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
    return "*" in allowed or origin in allowed

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not IS_WORKERS:
        Base.metadata.create_all(bind=engine)
        if settings.auto_seed:
            run_seed()
    yield

app = FastAPI(
    title=settings.app_name,
    description="CSP-J/S 初赛训练系统后端 API",
    version="1.0.0",
    lifespan=lifespan,
)

@app.middleware("http")
async def runtime_env_and_cors(request: Request, call_next):
    env = request.scope.get("env")
    if env is not None:
        try:
            _apply_workers_env(env)
        except RuntimeError as exc:
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
    logger.exception("未处理异常：%s %s", request.method, request.url.path)
    return JSONResponse({"detail": "服务器内部错误，请稍后重试"}, status_code=500)

for module in (auth, tags, problems, problem_lists, wrong_questions, stats, mock_exams):
    app.include_router(module.router, prefix=settings.api_prefix)

@app.get("/api/health", tags=["系统"])
def health(request: Request):
    return {
        "status": "ok",
        "app": settings.app_name,
        "database": dialect_name_for_request(request),
        "mock_exam_minutes": settings.mock_exam_minutes,
    }

try:
    from workers import asgi
except ModuleNotFoundError:
    asgi = None

if asgi is not None:
    Default = asgi.entrypoint(app)
