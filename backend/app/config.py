"""全局配置：全部通过环境变量覆盖（见 .env.example）。"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "CCF CSP 第一轮认证刷题平台"
    api_prefix: str = "/api"

    # PostgreSQL 为生产/默认真实数据库；本地无 PG 时可通过 ALLOW_SQLITE_FALLBACK 自动降级
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/cspjs"
    allow_sqlite_fallback: bool = True
    sqlite_path: str = "./cspjs.db"

    jwt_secret: str = "change-me-in-production-please"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173"

    admin_username: str = "admin"
    admin_password: str = "adminmagnet"

    auto_seed: bool = True          # 启动时建表并写入管理员/演示数据
    seed_demo_student: bool = True  # 是否创建演示学生账号与示例题单（云托管建议 false）
    mock_exam_minutes: int = 120

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
