# API 参考

- 基础地址：`http://127.0.0.1:8000/api`
- 认证方式：`Authorization: Bearer <access_token>`
- 请求 / 响应均为 `application/json`
- 交互式文档：`/docs`（Swagger UI）、`/redoc`

## 错误格式

```json
{ "detail": "已通过的题目不可直接修改，如需修改请联系管理员" }
```

参数校验失败（HTTP 422）时 `detail` 为数组：

```json
{ "detail": [{ "loc": ["body", "sub_questions"], "msg": "单选题必须且只能包含 1 个小题", "type": "value_error" }] }
```

前端 `src/api/client.js` 会把这两种形态统一转换成可直接展示的中文消息。

---

## 认证

### POST /auth/register

```json
{ "username": "alice", "password": "secret123" }
```

`201` 响应（注册后直接登录）：

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": { "id": 5, "username": "alice", "role": "user", "created_at": "2026-11-01T06:40:00Z" }
}
```

用户名规则：3–50 字符，允许中英文、数字、`_`、`-`；密码 6–64 字符。

### POST /auth/login

```json
{ "username": "admin", "password": "adminmagnet" }
```

### GET /auth/me

返回当前用户对象。

---

## 题库

### GET /problems

| 参数 | 说明 |
| --- | --- |
| `type` | `single` / `reading` / `completion` |
| `tag` | 标签名或标签 id |
| `source_tag` | `original` / `real` / `adapted` |
| `year` | 来源年份，如 `2024` |
| `exam` | `CSP-J` / `CSP-S` |
| `keyword` | 标题或题干模糊匹配 |
| `status` | `approved`（默认）/ `pending` / `rejected` / `mine` / `all`（管理员） |
| `mine` | `true` 时只看自己的投稿（可叠加 status） |
| `page` / `page_size` | 默认 1 / 12，最大 50 |

```json
{
  "items": [
    {
      "id": 12,
      "title": "循环时间复杂度",
      "type": "single",
      "source_tag": "original",
      "source_year": 2022,
      "source_exam": "CSP-J",
      "status": "approved",
      "contributor_id": 1,
      "contributor_name": "admin",
      "tags": [{ "id": 2, "name": "时间复杂度", "category": "知识点" }],
      "sub_question_count": 1,
      "created_at": "2026-11-01T06:30:00Z",
      "reviewed_at": "2026-11-01T06:30:00Z",
      "reject_reason": null
    }
  ],
  "total": 21,
  "page": 1,
  "page_size": 12
}
```

### GET /problems/{id}

返回 `content_md`、`answer_md` 以及带答案与解析的小题：

```json
{
  "id": 22,
  "title": "完善程序：0/1 背包",
  "type": "completion",
  "content_md": "下面程序用动态规划求解 0/1 背包……",
  "answer_md": "答案：……",
  "sub_questions": [
    {
      "id": 101,
      "order_no": 1,
      "content_md": "① 处容量循环必须从大到小的原因是（ ）。",
      "options": [{ "key": "A", "text": "保证每件物品只被选一次" }],
      "correct_answer": "A",
      "analysis_md": "逆序更新使 `dp[j-w[i]]` 仍是上一轮状态。"
    }
  ]
}
```

匿名只能读取 `approved`；`pending` / `rejected` 仅贡献者与管理员可读（否则 403）。

### POST /problems

```json
{
  "title": "字符溢出",
  "type": "single",
  "source_tag": "real",
  "source_year": 2021,
  "source_exam": "CSP-J",
  "content_md": "执行下面的 C++ 代码后，输出结果是（ ）。\n\n```cpp\nchar c = 127;\n```",
  "answer_md": "整体解析……",
  "tag_ids": [2, 5],
  "sub_questions": [
    {
      "content_md": "",
      "options": [{ "key": "A", "text": "127" }, { "key": "B", "text": "-128" }],
      "correct_answer": "B",
      "analysis_md": "补码回绕。"
    }
  ]
}
```

- 普通用户：`status=pending`；管理员：直接 `approved`
- `single` 必须且只能有 1 个小题；`reading` / `completion` 至少 2 个
- 每个小题至少 1 个选项、必须给出正确答案

### PUT /problems/{id}

字段同 POST。普通用户仅能改自己的 `pending` / `rejected` 题目；修改被驳回的题目会自动回到 `pending` 并清空驳回原因。

### POST /problems/{id}/review

```json
{ "action": "reject", "reason": "第 (2) 小题答案与解析矛盾" }
```

`action=reject` 时 `reason` 必填（缺失返回 422）。只有 `pending` 可审核。

### POST /problems/{id}/answer

```json
{ "answers": { "101": "A", "102": "BC" } }
```

响应：

```json
{
  "problem_id": 22,
  "correct_count": 1,
  "total_count": 2,
  "score_rate": 0.5,
  "items": [
    {
      "sub_question_id": 101,
      "order_no": 1,
      "user_answer": "A",
      "correct_answer": "A",
      "is_correct": true,
      "analysis_md": "……"
    }
  ],
  "wrong_question_ids": [7],
  "answer_md": "整体解析……"
}
```

答错的小题会自动写入 `wrong_questions`（首次间隔 1 天）；同一小题重复答错会重置进度。

---

## 标签

- `GET /tags` → `[{ "id": 1, "name": "排序", "category": "知识点" }]`
- `POST /tags`：`{ "name": "前缀和", "category": "知识点" }`（普通用户仅可建知识点标签，管理员可建任意分类）
- `DELETE /tags/{id}`：管理员，级联移除题目关联

## 题单

- `GET /problem-lists?scope=visible|public|mine`
- `POST /problem-lists`：`{ "title": "...", "description": "...", "is_public": true, "problem_ids": [1,2] }`
- `GET /problem-lists/{id}`：返回 `problems`（仅 approved）与顺序
- `PUT /problem-lists/{id}`：可整体替换 `problem_ids` 以调整顺序
- `POST /problem-lists/{id}/items`：`{ "problem_id": 12 }`（重复收录返回 409，非 approved 返回 400）
- `DELETE /problem-lists/{id}/items/{problem_id}`
- `PUT /problem-lists/{id}/reorder`：`{ "problem_ids": [3,1,2] }`

## 错题本

- `GET /wrong-questions?scope=due|all|mastered`：`due` 为 `next_review_at <= now` 且未掌握
- `GET /wrong-questions/today-count` → `{ "due": 3, "total": 12, "mastered": 4 }`
- `GET /wrong-questions/{id}/detail`：重做所需题干、选项、正确答案、解析
- `PATCH /wrong-questions/{id}`：`{ "error_type": 3 }`（1 概念不清 / 2 方法不会 / 3 粗心 / 4 审题错误）
- `POST /wrong-questions/{id}/review`：`{ "review_result": 1 }`，返回更新后的错题（含 `next_review_at`、`consecutive_pass`）

复习进度规则：首次做错 1 天 → 答对后 3 天 → 连续答对两次标记掌握并移出队列；答错重新从 1 天开始。

## 统计

`GET /stats/me`：

```json
{
  "total_answers": 42,
  "correct_answers": 31,
  "accuracy": 0.738,
  "today_answers": 6,
  "solved_problems": 18,
  "wrong_pending": 5,
  "by_tag": [{ "name": "排序", "total": 8, "correct": 5, "accuracy": 0.625 }],
  "by_type": [
    { "type": "single", "total": 12, "correct": 10, "accuracy": 0.833 },
    { "type": "reading", "total": 9, "correct": 6, "accuracy": 0.667 }
  ]
}
```

`by_tag` 只统计 `category = '知识点'` 的标签；所有统计均排除 `mock_exam_id` 非空的记录。

## 模拟考试

### POST /mock-exams

```json
{ "exam_type": "J" }
```

- 从 approved 池随机抽 15 单选 + 3 阅读 + 2 完善，同卷不重复
- 题量不足：`400 {"detail": "题库数量不足，无法组卷：阅读程序题 需要 3 道，题库仅有 2 道。请先通过审核补充题目。"}`

响应（`201`）：

```json
{
  "id": 3,
  "exam_type": "J",
  "status": "ongoing",
  "score": null,
  "started_at": "2026-11-01T06:52:00Z",
  "deadline_at": "2026-11-01T08:52:00Z",
  "remaining_seconds": 7200,
  "problem_count": 20,
  "problems": [
    {
      "id": 12,
      "title": "字符溢出",
      "type": "single",
      "content_md": "...",
      "sub_questions": [{ "id": 101, "order_no": 1, "content_md": "", "options": [...] }]
    }
  ]
}
```

进行中的试卷**不含** `correct_answer` / `analysis_md`。

### POST /mock-exams/{id}/submit

```json
{ "answers": { "101": "B", "115": "A" } }
```

响应 `MockExamResult`：`score`（0-100 整数）、`items`（逐小题对错）、`problems`（含答案与解析）、`by_type`、`by_tag`、`duration_seconds`。

### GET /mock-exams/{id}/result

仅已交卷可访问，返回与交卷相同的结构，用于刷新 / 历史回看。
