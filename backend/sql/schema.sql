-- ============================================================
-- CCF CSP 第一轮认证刷题平台 —— PostgreSQL 建表 SQL
-- 与 backend/app/models.py 完全对应；应用启动时会自动 create_all，
-- 此脚本用于手工初始化 / DBA 审阅。
--   psql -U postgres -d cspjs -f backend/sql/schema.sql
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    password_hash CHAR(64)     NOT NULL,               -- SHA-256 十六进制
    role          VARCHAR(16)  NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    created_at    TIMESTAMP    NOT NULL DEFAULT (now() AT TIME ZONE 'UTC')
);

CREATE TABLE IF NOT EXISTS tags (
    id       SERIAL PRIMARY KEY,
    name     VARCHAR(64) NOT NULL UNIQUE,
    category VARCHAR(32) NOT NULL DEFAULT '知识点'
);

CREATE TABLE IF NOT EXISTS problems (
    id             SERIAL PRIMARY KEY,
    title          VARCHAR(200) NOT NULL,
    type           VARCHAR(16)  NOT NULL CHECK (type IN ('single', 'reading', 'completion')),
    source_tag     VARCHAR(16)  NOT NULL DEFAULT 'original' CHECK (source_tag IN ('original', 'real', 'adapted')),
    source_year    INTEGER,
    source_exam    VARCHAR(16)  CHECK (source_exam IN ('CSP-J', 'CSP-S')),
    content_md     TEXT         NOT NULL DEFAULT '',
    answer_md      TEXT         NOT NULL DEFAULT '',
    status         VARCHAR(16)  NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    contributor_id INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reviewer_id    INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    reject_reason  TEXT,
    created_at     TIMESTAMP    NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
    reviewed_at    TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_problems_status_type ON problems (status, type);
CREATE INDEX IF NOT EXISTS ix_problems_created_at ON problems (created_at);
CREATE INDEX IF NOT EXISTS ix_problems_contributor ON problems (contributor_id);

CREATE TABLE IF NOT EXISTS problem_tags (
    problem_id INTEGER NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    tag_id     INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (problem_id, tag_id)
);

CREATE TABLE IF NOT EXISTS sub_questions (
    id             SERIAL PRIMARY KEY,
    problem_id     INTEGER NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    order_no       INTEGER NOT NULL,
    content_md     TEXT    NOT NULL DEFAULT '',
    options_json   JSONB   NOT NULL DEFAULT '[]'::jsonb,   -- [{"key":"A","text":"..."}]
    correct_answer VARCHAR(8) NOT NULL DEFAULT 'A',        -- "A" 或 "AB"
    analysis_md    TEXT    NOT NULL DEFAULT '',
    CONSTRAINT uq_sub_problem_order UNIQUE (problem_id, order_no)
);

CREATE TABLE IF NOT EXISTS problem_lists (
    id          SERIAL PRIMARY KEY,
    title       VARCHAR(200) NOT NULL,
    description TEXT         NOT NULL DEFAULT '',
    creator_id  INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_public   BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP    NOT NULL DEFAULT (now() AT TIME ZONE 'UTC')
);

CREATE TABLE IF NOT EXISTS problem_list_items (
    list_id    INTEGER NOT NULL REFERENCES problem_lists(id) ON DELETE CASCADE,
    problem_id INTEGER NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    order_no   INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (list_id, problem_id)
);

CREATE TABLE IF NOT EXISTS wrong_questions (
    id               SERIAL PRIMARY KEY,
    user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    problem_id       INTEGER NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    sub_question_id  INTEGER NOT NULL REFERENCES sub_questions(id) ON DELETE CASCADE,
    error_type       INTEGER CHECK (error_type BETWEEN 1 AND 4),  -- 1概念不清 2方法不会 3粗心 4审题错误
    redo_status      INTEGER NOT NULL DEFAULT 0,                  -- 0待重做 1重做对 2重做错
    consecutive_pass INTEGER NOT NULL DEFAULT 0,
    next_review_at   TIMESTAMP,
    created_at       TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
    CONSTRAINT uq_wrong_user_problem_sub UNIQUE (user_id, problem_id, sub_question_id)
);
CREATE INDEX IF NOT EXISTS ix_wrong_user_next_review ON wrong_questions (user_id, next_review_at);

CREATE TABLE IF NOT EXISTS wrong_reviews (
    id            SERIAL PRIMARY KEY,
    wrong_id      INTEGER NOT NULL REFERENCES wrong_questions(id) ON DELETE CASCADE,
    review_result INTEGER NOT NULL CHECK (review_result IN (0, 1)),
    reviewed_at   TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'UTC')
);

CREATE TABLE IF NOT EXISTS mock_exams (
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    exam_type    VARCHAR(8) NOT NULL DEFAULT 'J' CHECK (exam_type IN ('J', 'S')),
    problem_ids  JSONB NOT NULL DEFAULT '[]'::jsonb,   -- 按题序
    answers_json JSONB NOT NULL DEFAULT '{}'::jsonb,   -- 扩展：考生作答 {sub_question_id: "AB"}
    status       VARCHAR(16) NOT NULL DEFAULT 'ongoing' CHECK (status IN ('ongoing', 'submitted')),
    started_at   TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
    submitted_at TIMESTAMP,
    score        INTEGER
);

CREATE TABLE IF NOT EXISTS submissions (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    problem_id      INTEGER NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    sub_question_id INTEGER NOT NULL REFERENCES sub_questions(id) ON DELETE CASCADE,
    user_answer     VARCHAR(16) NOT NULL DEFAULT '',
    is_correct      BOOLEAN NOT NULL DEFAULT FALSE,
    mock_exam_id    INTEGER REFERENCES mock_exams(id) ON DELETE SET NULL,  -- 扩展：非空则属于模拟考试
    submitted_at    TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'UTC')
);
CREATE INDEX IF NOT EXISTS ix_submissions_user_time ON submissions (user_id, submitted_at);
CREATE INDEX IF NOT EXISTS ix_submissions_mock_exam ON submissions (mock_exam_id);

-- 管理员账号（密码 adminmagnet 的 SHA-256），由 app/seed.py 自动写入，
-- 也可手动执行：
INSERT INTO users (username, password_hash, role)
SELECT 'admin', '<SHA256(adminmagnet)>', 'admin'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'admin');
