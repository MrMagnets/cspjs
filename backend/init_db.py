"""一键同步数据库结构：创建缺失的表、补齐缺失的字段。

为什么需要它：
- Cloudflare Workers 上不会执行 `Base.metadata.create_all()`；
- Neon 旧库新增字段时，`create_all` 不会 ALTER 已有表；
- 这个脚本读取 models.py，对比真实库，自动 CREATE TABLE / ADD COLUMN。

用法（在 backend/ 下）：
    export DATABASE_URL='postgresql://user:pass@ep-xxx.neon.tech/db?sslmode=require'
    python init_db.py --dry-run     # 只看将执行的 SQL
    python init_db.py               # 交互确认后执行
    python init_db.py --yes         # 跳过确认（CI）

说明：
- 只创建缺失的表/字段，不删除、不改类型、不收缩约束；
- 新增 NOT NULL 字段会尽量带 DEFAULT，避免旧数据阻塞；
- 生产环境执行前请备份 Neon，建议先在分支库验证。
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent / "app"
sys.path.insert(0, str(APP_DIR))

from sqlalchemy import create_engine, inspect, text  # noqa: E402
from sqlalchemy.schema import CreateIndex, CreateTable  # noqa: E402

from database import create_engine_from_url, normalize_database_url  # noqa: E402
from models import Base  # noqa: E402


def _quote(engine, name: str) -> str:
    return engine.dialect.identifier_preparer.quote(name)


def _default_sql(column) -> str | None:
    """为新增 NOT NULL 列生成安全默认值。"""
    if column.server_default is not None:
        arg = column.server_default.arg
        return str(arg)

    if column.nullable:
        return None

    default = column.default
    if default is not None and getattr(default, "is_scalar", False):
        value = default.arg
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str):
            return "'" + value.replace("'", "''") + "'"

    # Python 侧没有默认值时，按类型给一个保守默认值
    type_name = column.type.__class__.__name__.lower()
    if "boolean" in type_name:
        return "false"
    if "integer" in type_name or "numeric" in type_name or "float" in type_name:
        return "0"
    if "string" in type_name or "text" in type_name:
        return "''"
    return None


def _column_sql(engine, column) -> str:
    col = f"{_quote(engine, column.name)} {column.type.compile(dialect=engine.dialect)}"
    default = _default_sql(column)
    if default is not None:
        col += f" DEFAULT {default}"
    if not column.nullable:
        # 没有可用默认值时只能先允许 NULL，避免 ALTER 直接失败
        if default is not None:
            col += " NOT NULL"
        else:
            print(f"  ! {column.table.name}.{column.name} 非空但无默认值，先按 NULL 添加")
    return col


def build_plan(engine) -> list[str]:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    planned_tables: set[str] = set()
    plan: list[str] = []

    # 1) 缺失表：直接使用 metadata 的 DDL
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            plan.append(str(CreateTable(table, if_not_exists=True).compile(dialect=engine.dialect)).strip() + ";")
            for index in table.indexes:
                plan.append(str(CreateIndex(index, if_not_exists=True).compile(dialect=engine.dialect)).strip() + ";")
            planned_tables.add(table.name)

    # 2) 已有表：补齐缺失列
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables or table.name in planned_tables:
            continue
        existing_cols = {c["name"] for c in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing_cols:
                continue
            sql = (
                f"ALTER TABLE {_quote(engine, table.name)} "
                f"ADD COLUMN {_column_sql(engine, column)};"
            )
            plan.append(sql)

    # 3) 已有表缺失的普通索引（唯一约束交给 init 的模型/迁移）
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables or table.name in planned_tables:
            continue
        existing_indexes = {idx["name"] for idx in inspector.get_indexes(table.name)}
        for index in table.indexes:
            if index.name and index.name not in existing_indexes:
                plan.append(str(CreateIndex(index, if_not_exists=True).compile(dialect=engine.dialect)).strip() + ";")

    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description="读取 models.py，自动创建缺失的表和字段")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", ""))
    parser.add_argument("--yes", action="store_true", help="跳过确认")
    parser.add_argument("--dry-run", action="store_true", help="只打印 SQL，不执行")
    args = parser.parse_args()

    if not args.database_url:
        print("错误：请设置 DATABASE_URL 或传 --database-url。", file=sys.stderr)
        return 2

    url = normalize_database_url(args.database_url)
    engine = create_engine_from_url(url)
    print(f"目标数据库：{engine.url.render_as_string(hide_password=True)}")

    # 先建缺失表（幂等）
    if not args.dry_run:
        Base.metadata.create_all(engine)

    plan = build_plan(engine)
    if not plan:
        print("数据库结构已是最新，无需修改。")
        return 0

    print("\n将执行以下 SQL：")
    for sql in plan:
        print(sql)

    if args.dry_run:
        print("\ndry-run：未执行。")
        return 0
    if not args.yes:
        answer = input("\n确认执行？输入 y 确认，其他取消：").strip().lower()
        if answer not in ("y", "yes"):
            print("已取消。")
            return 0

    with engine.begin() as conn:
        for sql in plan:
            conn.execute(text(sql))
    print(f"\n完成：执行 {len(plan)} 条 DDL。")


if __name__ == "__main__":
    raise SystemExit(main())
