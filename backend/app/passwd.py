"""管理员密码重置工具（云托管场景下的运维脚本）。

Render 免费实例没有 shell，无法在控制台执行命令，因此在本机用平台提供的
「External Database URL」连库执行即可：

    # PowerShell
    $env:DATABASE_URL = "postgresql://user:pass@xxx.render.com/cspjs?sslmode=require"
    python -m app.passwd --username admin

    # bash
    DATABASE_URL="postgresql://..." python -m app.passwd --username admin

也支持非交互：
    python -m app.passwd --username admin --password '新的强密码'

注意：密码按项目约定以 SHA-256 存储（见 app/security.py）。
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys

from sqlalchemy import select

from .config import settings
from .database import SessionLocal, engine, normalize_database_url
from .models import User
from .security import hash_password


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="重置指定用户的密码（SHA-256 存储）")
    parser.add_argument("--username", default="admin", help="用户名，默认 admin")
    parser.add_argument("--password", default=None, help="新密码；省略则交互输入")
    args = parser.parse_args(argv)

    if args.password:
        password = args.password
    else:
        password = getpass.getpass("新密码：")
        confirm = getpass.getpass("再次输入：")
        if password != confirm:
            print("两次输入不一致，已取消", file=sys.stderr)
            return 1
    if len(password) < 6:
        print("密码至少 6 位", file=sys.stderr)
        return 1

    # 防止"以为在改云上数据库，实际改的是本地降级出来的 SQLite"
    target = normalize_database_url(settings.database_url)
    explicit_db = bool(os.environ.get("DATABASE_URL"))
    if target.startswith("postgresql") and engine.dialect.name != "postgresql":
        message = (
            "无法连接目标 PostgreSQL，已降级为本地 SQLite（%s）。\n"
            "请检查 DATABASE_URL 是否正确（云托管请用 External Database URL，并带 ?sslmode=require）。"
        ) % engine.url.render_as_string(hide_password=True)
        if explicit_db:
            print("错误：" + message + "\n操作已中止，未修改任何数据。", file=sys.stderr)
            return 2
        print("警告：" + message, file=sys.stderr)
        print("（未显式设置 DATABASE_URL，按本地开发模式继续）", file=sys.stderr)

    print("目标数据库：%s" % engine.url.render_as_string(hide_password=True))

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.username == args.username))
        if user is None:
            print(f"用户 {args.username!r} 不存在", file=sys.stderr)
            return 1
        user.password_hash = hash_password(password)
        db.commit()
        print(f"已重置 {user.username}（id={user.id}, role={user.role}）的密码")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
