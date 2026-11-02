"""清理测试 / 演示题目（可安全重复执行）。

用法：
    cd backend
    export DATABASE_URL='postgresql://user:pass@ep-xxx.neon.tech/db?sslmode=require'
    python cleanup_test_data.py                 # 交互确认
    python cleanup_test_data.py --yes           # 跳过确认（CI/脚本）
    python cleanup_test_data.py --ids 1,2,3     # 额外按题目 ID 删除
    python cleanup_test_data.py --dry-run       # 只列出，不删除

删除范围：
1. title 包含“演示”或“测试”的题目；
2. 通过 --ids 指定的题目；
3. 这些题目的 submissions / problem_tags / wrong_questions / contest_problems /
   problem_list_items 以及小题（外键 + 显式删除双保险）。
不会删除用户、比赛、讨论或真实手工录入的题目。
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent / "app"
sys.path.insert(0, str(APP_DIR))

from sqlalchemy import delete, or_, select  # noqa: E402
from sqlalchemy.exc import SQLAlchemyError  # noqa: E402

from database import create_engine_from_url, normalize_database_url  # noqa: E402
from models import (  # noqa: E402
    ContestProblem,
    Problem,
    ProblemListItem,
    ProblemTag,
    SubQuestion,
    Submission,
    WrongQuestion,
)


def parse_ids(raw: str) -> list[int]:
    ids: list[int] = []
    for part in (raw or "").split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return ids


def main() -> int:
    parser = argparse.ArgumentParser(description="删除演示/测试题目及其关联数据")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", ""))
    parser.add_argument("--ids", default="", help="额外删除的题目 ID，逗号分隔")
    parser.add_argument("--yes", action="store_true", help="跳过 y/n 确认")
    parser.add_argument("--dry-run", action="store_true", help="只显示，不删除")
    args = parser.parse_args()

    if not args.database_url:
        print("错误：请通过 DATABASE_URL 环境变量或 --database-url 提供 Neon 连接串。", file=sys.stderr)
        return 2

    ids = parse_ids(args.ids)
    engine = create_engine_from_url(normalize_database_url(args.database_url))

    with engine.begin() as conn:
        stmt = select(Problem.id, Problem.title, Problem.pool_type, Problem.status).where(
            or_(Problem.title.like("%演示%"), Problem.title.like("%测试%"), Problem.id.in_(ids) if ids else False)
        )
        try:
            rows = conn.execute(stmt).all()
        except SQLAlchemyError as exc:
            print(f"查询失败，请先执行数据库迁移：{exc}", file=sys.stderr)
            return 1
        if not rows:
            print("没有找到标题包含“演示/测试”或指定 ID 的题目，无需清理。")
            return 0

        print(f"将清理 {len(rows)} 道题目：")
        for pid, title, pool, status in rows:
            print(f"  - #{pid} [{pool}/{status}] {title}")

        if args.dry_run:
            print("dry-run：未执行删除。")
            return 0
        if not args.yes:
            answer = input("确认删除以上题目及其提交/错题/标签关联？输入 y 确认，其他取消：").strip().lower()
            if answer not in ("y", "yes"):
                print("已取消。")
                return 0

        problem_ids = [r[0] for r in rows]
        sub_ids = [
            sid
            for (sid,) in conn.execute(
                select(SubQuestion.id).where(SubQuestion.problem_id.in_(problem_ids))
            ).all()
        ]

        # 先删关联，再删题目，兼容未开启外键级联的旧库
        conn.execute(delete(Submission).where(Submission.problem_id.in_(problem_ids)))
        if sub_ids:
            conn.execute(delete(Submission).where(Submission.sub_question_id.in_(sub_ids)))
        conn.execute(delete(WrongQuestion).where(WrongQuestion.problem_id.in_(problem_ids)))
        if sub_ids:
            conn.execute(delete(WrongQuestion).where(WrongQuestion.sub_question_id.in_(sub_ids)))
        conn.execute(delete(ProblemTag).where(ProblemTag.problem_id.in_(problem_ids)))
        conn.execute(delete(ContestProblem).where(ContestProblem.problem_id.in_(problem_ids)))
        conn.execute(delete(ProblemListItem).where(ProblemListItem.problem_id.in_(problem_ids)))
        if sub_ids:
            conn.execute(delete(SubQuestion).where(SubQuestion.id.in_(sub_ids)))
        conn.execute(delete(Problem).where(Problem.id.in_(problem_ids)))

    print(f"完成：已删除 {len(rows)} 道题目及其关联数据；用户和真实题目未受影响。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
