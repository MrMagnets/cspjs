"""路由包：统一导出，便于 main.py 挂载。"""
from  import auth, mock_exams, problem_lists, problems, stats, tags, wrong_questions

__all__ = ["auth", "tags", "problems", "problem_lists", "wrong_questions", "stats", "mock_exams"]
