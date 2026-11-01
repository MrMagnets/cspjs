"""全局配置：全部通过环境变量覆盖（见 .env.example）。

安全约定：
- 本文件不保存任何真实凭据；默认值只是**占位符**，生产环境必须用环境变量覆盖。
- 生产环境（ENVIRONMENT=production 或检测到 VERCEL）会拒绝使用占位符 JWT_SECRET 启动。
"""
import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# 占位符常量：代码里只出现这些无意义字符串，真实密钥一律来自环境变量
PLACEHOLDER_JWT_SECRET = "your-secret-here"
PLACEHOLDER_ADMIN_PASSWORD = "change-me-admin-password"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "CSP 初赛训练系统"
    api_prefix: str = "/api"
    environment: str = "development"

    # 不提供任何带账号密码的默认连接串：本地未设置时自动降级 SQLite，生产必须通过环境变量注入
    database_url: str = ""
    allow_sqlite_fallback: bool = True
    sqlite_path: str = "./cspjs.db"

    jwt_secret: str = PLACEHOLDER_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173"

    admin_username: str = "admin"
    admin_password: str = PLACEHOLDER_ADMIN_PASSWORD

    auto_seed: bool = True           # 启动时建表并写入管理员/演示数据
    seed_demo_student: bool = False  # 演示学生账号默认关闭，生产环境不要开启
    demo_student_password: str = ""  # 开启时必填，避免在代码里硬编码密码
    mock_exam_minutes: int = 120

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in ("production", "prod") or bool(os.environ.get("VERCEL"))

    @property
    def uses_placeholder_jwt_secret(self) -> bool:
        return self.jwt_secret == PLACEHOLDER_JWT_SECRET

    @property
    def uses_placeholder_admin_password(self) -> bool:
        return self.admin_password == PLACEHOLDER_ADMIN_PASSWORD


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
