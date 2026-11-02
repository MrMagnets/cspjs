"""请求 / 响应 Pydantic 模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------- 认证 ----------------
class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_\u4e00-\u9fa5-]+$")
    password: str = Field(min_length=6, max_length=64)


class LoginIn(BaseModel):
    username: str
    password: str


class UserOut(ORMModel):
    id: int
    username: str
    role: str
    monkey_score: int = 0
    credit_score: int = 100
    status: str = "normal"
    ban_until: datetime | None = None
    title: str = ""
    can_create_problem: bool = True
    last_username_change: datetime | None = None
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------------- 标签 ----------------
class TagIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    category: str = Field(default="知识点", max_length=32)


class TagOut(ORMModel):
    id: int
    name: str
    category: str


# ---------------- 小题 ----------------
class SubQuestionIn(BaseModel):
    content_md: str = ""
    options: list[dict[str, str]] = Field(default_factory=list)
    correct_answer: str = "A"
    analysis_md: str = ""

    @field_validator("options")
    @classmethod
    def _check_options(cls, v: list[dict[str, str]]) -> list[dict[str, str]]:
        cleaned = []
        for opt in v:
            key = str(opt.get("key", "")).strip().upper()
            if not key:
                continue
            cleaned.append({"key": key, "text": str(opt.get("text", ""))})
        return cleaned


class SubQuestionOut(BaseModel):
    id: int
    order_no: int
    content_md: str
    options: list[dict[str, Any]]
    correct_answer: str
    analysis_md: str


class SubQuestionPublic(BaseModel):
    """考试进行中：隐藏答案与解析。"""
    id: int
    order_no: int
    content_md: str
    options: list[dict[str, Any]]


# ---------------- 题目 ----------------
class ProblemIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    type: Literal["single", "reading", "completion"]
    source_tag: Literal["original", "real", "adapted"] = "original"
    source_year: int | None = None
    source_exam: Literal["CSP-J", "CSP-S"] | None = None
    pool_type: Literal["P", "T", "S"] = "P"
    problem_number: str | None = None
    content_md: str = ""
    answer_md: str = ""
    tag_ids: list[int] = Field(default_factory=list)
    sub_questions: list[SubQuestionIn] = Field(min_length=1)

    @field_validator("content_md")
    @classmethod
    def _content_required(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("题干不能为空")
        return v

    @field_validator("sub_questions")
    @classmethod
    def _check_subs(cls, v: list[SubQuestionIn], info):
        ptype = info.data.get("type")
        if ptype == "single" and len(v) != 1:
            raise ValueError("单选题必须且只能包含 1 个小题")
        if ptype in ("reading", "completion") and len(v) < 2:
            raise ValueError("阅读程序 / 完善程序题至少需要 2 个小题")
        for sq in v:
            if not sq.options:
                raise ValueError("每个小题至少需要一个选项")
            if not sq.correct_answer.strip():
                raise ValueError("每个小题都需要正确答案")
        return v


class ProblemSummary(BaseModel):
    id: int
    title: str
    type: str
    source_tag: str
    source_year: int | None
    source_exam: str | None
    pool_type: str = "P"
    problem_number: str | None = None
    status: str
    contributor_id: int
    contributor_name: str | None = None
    tags: list[TagOut] = Field(default_factory=list)
    sub_question_count: int = 0
    created_at: datetime
    reviewed_at: datetime | None = None
    reject_reason: str | None = None


class ProblemDetail(ProblemSummary):
    content_md: str
    answer_md: str
    sub_questions: list[SubQuestionOut]


class ProblemPage(BaseModel):
    items: list[ProblemSummary]
    total: int
    page: int
    page_size: int


class ReviewIn(BaseModel):
    action: Literal["approve", "reject"]
    reason: str | None = None

    @model_validator(mode="after")
    def _reason_for_reject(self):
        if self.action == "reject" and not (self.reason or "").strip():
            raise ValueError("驳回必须填写原因")
        return self


# ---------------- 作答 ----------------
class AnswerIn(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict, description="{sub_question_id: 'A'}")


class AnswerItemResult(BaseModel):
    sub_question_id: int
    order_no: int
    user_answer: str
    correct_answer: str
    is_correct: bool
    analysis_md: str


class AnswerResult(BaseModel):
    problem_id: int
    correct_count: int
    total_count: int
    score_rate: float
    items: list[AnswerItemResult]
    wrong_question_ids: list[int] = Field(default_factory=list)
    answer_md: str = ""


# ---------------- 题单 ----------------
class ProblemListIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    is_public: bool = True
    problem_ids: list[int] = Field(default_factory=list)


class ProblemListSummary(BaseModel):
    id: int
    title: str
    description: str
    creator_id: int
    creator_name: str | None = None
    is_public: bool
    problem_count: int
    created_at: datetime


class ProblemListDetail(ProblemListSummary):
    problems: list[ProblemSummary] = Field(default_factory=list)


class ListItemsIn(BaseModel):
    problem_id: int


class ListReorderIn(BaseModel):
    problem_ids: list[int]


# ---------------- 错题本 ----------------
class WrongQuestionOut(BaseModel):
    id: int
    problem_id: int
    problem_title: str
    problem_type: str
    sub_question_id: int
    sub_question_order: int
    sub_question_content: str
    error_type: int | None
    redo_status: int
    consecutive_pass: int
    next_review_at: datetime | None
    created_at: datetime
    review_count: int = 0


class WrongReviewIn(BaseModel):
    review_result: Literal[0, 1]


class WrongErrorTypeIn(BaseModel):
    error_type: Literal[1, 2, 3, 4]


# ---------------- 统计 ----------------
class TagStat(BaseModel):
    name: str
    total: int
    correct: int
    accuracy: float


class TypeStat(BaseModel):
    type: str
    total: int
    correct: int
    accuracy: float


class StatsOut(BaseModel):
    total_answers: int
    correct_answers: int
    accuracy: float
    today_answers: int
    solved_problems: int
    by_tag: list[TagStat]
    by_type: list[TypeStat]
    wrong_pending: int


# ---------------- 模拟考试 ----------------
class MockExamCreate(BaseModel):
    exam_type: Literal["J", "S"] = "J"


class MockExamSummary(BaseModel):
    id: int
    exam_type: str
    status: str
    score: int | None
    started_at: datetime
    submitted_at: datetime | None
    problem_count: int
    deadline_at: datetime | None = None
    remaining_seconds: int | None = None


class MockExamProblem(BaseModel):
    id: int
    title: str
    type: str
    content_md: str
    sub_questions: list[SubQuestionPublic]


class MockExamDetail(MockExamSummary):
    problems: list[MockExamProblem] = Field(default_factory=list)
    answers: dict[str, str] = Field(default_factory=dict)


class MockExamSubmitIn(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)


class MockExamResult(MockExamSummary):
    problems: list[ProblemDetail] = Field(default_factory=list)
    answers: dict[str, str] = Field(default_factory=dict)
    items: list[AnswerItemResult] = Field(default_factory=list)
    by_type: list[TypeStat] = Field(default_factory=list)
    by_tag: list[TagStat] = Field(default_factory=list)
    duration_seconds: int | None = None

# ---------------- 用户 / 排行榜 ----------------
class UserPage(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    page_size: int


class CreatePermissionIn(BaseModel):
    can_create_problem: bool


class ChangeUsernameIn(BaseModel):
    new_username: str


class ChangeUsernameOut(BaseModel):
    message: str
    user: UserOut


class RankingEntry(BaseModel):
    rank: int
    user_id: int
    username: str
    title: str = ""
    monkey_score: int = 0
    credit_score: int = 100
    status: str = "normal"
    solved_count: int = 0


# ---------------- 比赛 ----------------
class ContestProblemIn(BaseModel):
    problem_id: int
    order_no: int = 1
    score: int = 10


class ContestIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = ""
    contest_type: Literal["personal", "official"] = "official"
    start_at: datetime
    end_at: datetime
    duration_minutes: int = 120
    problems: list[ContestProblemIn] = Field(default_factory=list)


class ContestProblemOut(BaseModel):
    problem_id: int
    title: str
    type: str
    order_no: int
    score: int
    content_md: str = ""
    sub_questions: list[SubQuestionPublic] = Field(default_factory=list)


class ContestSummary(BaseModel):
    id: int
    title: str
    contest_type: str
    status: str
    start_at: datetime
    end_at: datetime
    duration_minutes: int
    problem_count: int = 0
    participant_count: int = 0


class ContestResultOut(BaseModel):
    user_id: int
    username: str
    score: int
    cheat_count: int
    status: str
    submitted_at: datetime | None = None


class ContestDetail(ContestSummary):
    description: str = ""
    problems: list[ContestProblemOut] = Field(default_factory=list)
    my_result: ContestResultOut | None = None
    results: list[ContestResultOut] = Field(default_factory=list)


class AntiCheatIn(BaseModel):
    event: str = "visibilitychange"
    detail: str = ""


class ContestAnswersIn(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)
    time_spent: int = 0


class ContestJudgeIn(BaseModel):
    user_id: int
    cheat: bool = True
    reason: str = ""


# ---------------- 讨论 / 评论 / 举报 ----------------
class DiscussionIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    content_md: str = Field(min_length=1)
    category: Literal["站务", "学术", "题目"] = "学术"
    problem_id: int | None = None


class CommentIn(BaseModel):
    content_md: str = Field(min_length=1, max_length=20000)


class DiscussionSummary(BaseModel):
    id: int
    title: str
    category: str
    author_id: int
    author_name: str = ""
    is_pinned: bool = False
    is_locked: bool = False
    comment_count: int = 0
    created_at: datetime
    updated_at: datetime


class CommentOut(BaseModel):
    id: int
    author_id: int
    author_name: str = ""
    content_md: str
    created_at: datetime


class DiscussionDetail(DiscussionSummary):
    content_md: str
    problem_id: int | None = None
    comments: list[CommentOut] = Field(default_factory=list)


class ReportIn(BaseModel):
    target_type: Literal["problem", "discussion", "comment"]
    target_id: int
    reason: str = Field(min_length=2, max_length=500)


class ReportOut(BaseModel):
    id: int
    reporter_id: int
    reporter_name: str = ""
    target_type: str
    target_id: int
    reason: str
    status: str
    created_at: datetime


# ---------------- 申诉 ----------------
class AppealIn(BaseModel):
    contest_id: int | None = None
    reason: str = Field(min_length=2, max_length=2000)
    video_url: str = Field(min_length=5, max_length=512)


class AppealReviewIn(BaseModel):
    action: Literal["approve", "reject"]
    note: str = ""


class AppealOut(BaseModel):
    id: int
    user_id: int
    username: str = ""
    contest_id: int | None = None
    reason: str
    video_url: str
    status: str
    admin_note: str = ""
    created_at: datetime
    reviewed_at: datetime | None = None
