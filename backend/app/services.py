"""审题 / 判分 / 错题复习调度等纯业务逻辑。"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

# 错题重做间隔（天）：首次做错 1 天，之后答对 3 天 / 7 天
REVIEW_INTERVALS = [1, 3, 7]
MASTER_AFTER_CONSECUTIVE_PASS = 2  # 连续答对两次 → 已掌握，移出复习队列

# 模拟考试结构：15 单选(30 分) + 3 阅读(40 分) + 2 完善(30 分)
MOCK_STRUCTURE = {"single": 15, "reading": 3, "completion": 2}
MOCK_POINTS = {"single": 2.0}          # single 每题 2 分
MOCK_SECTION_POINTS = {"reading": 40.0, "completion": 30.0}
# 阅读程序 3 题分摊 40 分（13/13/14），完善程序 2 题各 15 分
READING_SPLIT = [13.0, 13.0, 14.0]
COMPLETION_SPLIT = [15.0, 15.0]

ERROR_TYPE_LABELS = {1: "概念不清", 2: "方法不会", 3: "粗心", 4: "审题错误"}


def normalize_answer(value: str | None) -> str:
    """把 'a b' / 'BA' 统一成 'AB'，用于忽略顺序与大小写的比较。"""
    if not value:
        return ""
    return "".join(sorted(ch for ch in re.sub(r"[\s,，、;；]", "", str(value)).upper()))


def is_correct(user_answer: str | None, correct_answer: str | None) -> bool:
    user = normalize_answer(user_answer)
    return bool(user) and user == normalize_answer(correct_answer)


def next_review_after_wrong(now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    return now + timedelta(days=REVIEW_INTERVALS[0])


def apply_review_result(
    *, review_result: int, consecutive_pass: int, now: datetime | None = None
) -> tuple[int, int, datetime | None, bool]:
    """根据一次重做结果推进错题状态。

    返回 (redo_status, consecutive_pass, next_review_at, mastered)。
    """
    now = now or datetime.now(timezone.utc)
    if review_result == 1:
        consecutive_pass += 1
        if consecutive_pass >= MASTER_AFTER_CONSECUTIVE_PASS:
            return 1, consecutive_pass, None, True
        interval = REVIEW_INTERVALS[min(consecutive_pass, len(REVIEW_INTERVALS) - 1)]
        return 1, consecutive_pass, now + timedelta(days=interval), False
    return 2, 0, now + timedelta(days=REVIEW_INTERVALS[0]), False


def mock_exam_plan(counts: dict[str, int] | None = None) -> list[tuple[str, float]]:
    """返回 [(题型, 该题分值)]，按真实试卷的题序：单选 → 阅读程序 → 完善程序。"""
    plan: list[tuple[str, float]] = []
    for _ in range(MOCK_STRUCTURE["single"]):
        plan.append(("single", MOCK_POINTS["single"]))
    for idx in range(MOCK_STRUCTURE["reading"]):
        plan.append(("reading", READING_SPLIT[idx]))
    for idx in range(MOCK_STRUCTURE["completion"]):
        plan.append(("completion", COMPLETION_SPLIT[idx]))
    return plan


def problem_point_value(problem_type: str, index_in_type: int) -> float:
    if problem_type == "single":
        return MOCK_POINTS["single"]
    if problem_type == "reading":
        return READING_SPLIT[min(index_in_type, len(READING_SPLIT) - 1)]
    return COMPLETION_SPLIT[min(index_in_type, len(COMPLETION_SPLIT) - 1)]
