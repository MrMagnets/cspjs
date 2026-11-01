"""端到端冒烟测试（仅用标准库，直接打真实 HTTP 接口）。

先启动后端：uvicorn app.main:app --port 8000
再运行：python smoke_test.py [base_url]
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
passed = 0


def call(method: str, path: str, body=None, token: str | None = None, expect: int = 200):
    global passed
    url = BASE + urllib.parse.quote(path, safe="/?=&")
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            code, raw = resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        code, raw = exc.code, exc.read().decode("utf-8")
    payload = json.loads(raw) if raw else None
    assert code == expect, f"{method} {path} -> {code} {raw[:400]} (期望 {expect})"
    passed += 1
    print(f"  ok  {method:5s} {path}  [{code}]")
    return payload


def main() -> None:
    print("1) 健康检查")
    call("GET", "/api/health")

    print("2) 管理员登录 + 注册普通用户")
    admin = call("POST", "/api/auth/login", {"username": "admin", "password": "adminmagnet"})
    admin_tok = admin["access_token"]
    username = "tester_smoke"
    reg = call(
        "POST", "/api/auth/register", {"username": username, "password": "test123456"},
        expect=201,
    ) if not _login_ok(username) else call(
        "POST", "/api/auth/login", {"username": username, "password": "test123456"}
    )
    user_tok = reg["access_token"]
    call("GET", "/api/auth/me", token=user_tok)

    print("3) 标签列表")
    tags = call("GET", "/api/tags")
    assert any(t["name"] == "排序" for t in tags)
    tag_id = next(t["id"] for t in tags if t["name"] == "排序")

    print("4) 普通用户投稿 → 仅自己可见 → 管理员审核通过")
    new_problem = call(
        "POST", "/api/problems",
        {
            "title": "冒烟测试题：循环次数",
            "type": "single",
            "source_tag": "original",
            "source_year": 2024,
            "source_exam": "CSP-J",
            "content_md": "下面循环体执行几次？\n\n```cpp\nfor (int i = 0; i < 5; i++) {}\n```",
            "answer_md": "共 5 次。",
            "tag_ids": [tag_id],
            "sub_questions": [
                {
                    "content_md": "",
                    "options": [{"key": "A", "text": "4"}, {"key": "B", "text": "5"}],
                    "correct_answer": "B",
                    "analysis_md": "i 取 0..4。",
                }
            ],
        },
        token=user_tok, expect=201,
    )
    pid = new_problem["id"]
    assert new_problem["status"] == "pending"
    mine = call("GET", "/api/problems?status=mine", token=user_tok)
    assert any(p["id"] == pid for p in mine["items"])
    public = call("GET", "/api/problems?keyword=冒烟测试题")
    assert not any(p["id"] == pid for p in public["items"]), "待审题目不应出现在公共题库"
    pending = call("GET", "/api/admin/pending", token=admin_tok)
    assert any(p["id"] == pid for p in pending["items"])
    call("POST", f"/api/problems/{pid}/review", {"action": "reject"}, token=admin_tok, expect=422)
    call("POST", f"/api/problems/{pid}/review", {"action": "reject", "reason": "题干不清晰"}, token=admin_tok)
    call("POST", f"/api/problems/{pid}/review", {"action": "approve"}, token=admin_tok, expect=400)

    print("5) 驳回后作者可修改并重新提交")
    rejected = call("GET", f"/api/problems/{pid}", token=user_tok)
    assert rejected["status"] == "rejected" and rejected["reject_reason"] == "题干不清晰"
    detail = call(
        "PUT", f"/api/problems/{pid}",
        {
            "title": "冒烟测试题：循环次数（已修订）",
            "type": "single",
            "source_tag": "original",
            "source_year": 2024,
            "source_exam": "CSP-J",
            "content_md": "下面循环体执行几次？\n\n```cpp\nfor (int i = 0; i < 5; i++) {}\n```",
            "answer_md": "共 5 次。",
            "tag_ids": [tag_id],
            "sub_questions": [
                {
                    "content_md": "",
                    "options": [{"key": "A", "text": "4"}, {"key": "B", "text": "5"}],
                    "correct_answer": "B",
                    "analysis_md": "i 取 0..4。",
                }
            ],
        },
        token=user_tok,
    )
    assert detail["status"] == "pending", "修改被驳回的题目应回到 pending"
    call("POST", f"/api/problems/{pid}/review", {"action": "approve"}, token=admin_tok)

    print("6) 公共题库筛选 + 详情 + 作答判分")
    filtered = call("GET", "/api/problems?type=single&tag=排序&status=approved")
    assert filtered["total"] >= 1
    detail = call("GET", f"/api/problems/{pid}")
    sub_id = detail["sub_questions"][0]["id"]
    result = call("POST", f"/api/problems/{pid}/answer", {"answers": {str(sub_id): "A"}}, token=user_tok)
    assert result["correct_count"] == 0 and result["items"][0]["is_correct"] is False
    assert result["items"][0]["analysis_md"]
    right = call("POST", f"/api/problems/{pid}/answer", {"answers": {str(sub_id): "B"}}, token=user_tok)
    assert right["correct_count"] == 1

    print("7) 错题本：自动入库 / 错因 / 复习调度")
    count = call("GET", "/api/wrong-questions/today-count", token=user_tok)
    assert count["total"] >= 1
    wrongs = call("GET", "/api/wrong-questions?scope=all", token=user_tok)
    wid = wrongs[0]["id"]
    call("PATCH", f"/api/wrong-questions/{wid}", {"error_type": 3}, token=user_tok)
    call("GET", f"/api/wrong-questions/{wid}/detail", token=user_tok)
    first = call("POST", f"/api/wrong-questions/{wid}/review", {"review_result": 1}, token=user_tok)
    assert first["consecutive_pass"] == 1 and first["next_review_at"] and first["redo_status"] == 1
    second = call("POST", f"/api/wrong-questions/{wid}/review", {"review_result": 1}, token=user_tok)
    assert second["consecutive_pass"] == 2 and second["next_review_at"] is None, "连续两次答对应已掌握"

    print("8) 做题统计")
    stats = call("GET", "/api/stats/me", token=user_tok)
    assert stats["total_answers"] >= 2 and stats["by_type"]

    print("9) 题单：创建 / 收录 / 排序 / 移除")
    plist = call(
        "POST", "/api/problem-lists",
        {"title": "冒烟测试题单", "description": "自动化测试", "is_public": True}, token=user_tok, expect=201,
    )
    lid = plist["id"]
    assert plist["problem_count"] == 0
    call("POST", f"/api/problem-lists/{lid}/items", {"problem_id": pid}, token=user_tok)
    call("POST", f"/api/problem-lists/{lid}/items", {"problem_id": pid}, token=user_tok, expect=409)
    call("PUT", f"/api/problem-lists/{lid}/reorder", {"problem_ids": [pid]}, token=user_tok)
    listed = call("GET", f"/api/problem-lists/{lid}")
    assert listed["problem_count"] == 1
    call("DELETE", f"/api/problem-lists/{lid}/items/{pid}", token=user_tok)

    print("10) 模拟考试：组卷 / 交卷判分 / 结果")
    exam = call("POST", "/api/mock-exams", {"exam_type": "J"}, token=user_tok, expect=201)
    assert exam["problem_count"] == 20, exam["problem_count"]
    assert exam["remaining_seconds"] and exam["remaining_seconds"] <= 7200
    assert not any("correct_answer" in sq for p in exam["problems"] for sq in p["sub_questions"])
    eid = exam["id"]
    answers = {}
    for problem in exam["problems"]:
        for sq in problem["sub_questions"]:
            answers[str(sq["id"])] = "A"
    submitted = call("POST", f"/api/mock-exams/{eid}/submit", {"answers": answers}, token=user_tok)
    assert submitted["status"] == "submitted" and isinstance(submitted["score"], int)
    assert submitted["by_type"] and submitted["by_tag"]
    again = call("GET", f"/api/mock-exams/{eid}/result", token=user_tok)
    assert again["score"] == submitted["score"]
    call("POST", f"/api/mock-exams/{eid}/submit", {"answers": answers}, token=user_tok, expect=400)

    print("11) 权限校验：普通用户不可审核 / 不可看他人待审题目")
    call("GET", "/api/admin/pending", token=user_tok, expect=403)
    call("POST", f"/api/problems/{pid}/review", {"action": "approve"}, token=user_tok, expect=403)
    call("GET", "/api/stats/me", expect=401)

    print(f"\n全部通过：{passed} 个接口断言 ✅")


def _login_ok(username: str) -> bool:
    try:
        call_silent("POST", "/api/auth/login", {"username": username, "password": "test123456"})
        return True
    except Exception:  # noqa: BLE001 - 账号不存在即可注册
        return False


def call_silent(method: str, path: str, body=None):
    url = BASE + path
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


if __name__ == "__main__":
    main()
