-- 用户管理后台依赖的 users 字段汇总（Neon / PostgreSQL）
-- 可重复执行；对应 backend/init_db.py 会做同样的事。

BEGIN;

ALTER TABLE users ADD COLUMN IF NOT EXISTS title varchar(64) NOT NULL DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS monkey_score integer NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS credit_score integer NOT NULL DEFAULT 100;
ALTER TABLE users ADD COLUMN IF NOT EXISTS status varchar(16) NOT NULL DEFAULT 'normal';
ALTER TABLE users ADD COLUMN IF NOT EXISTS ban_until timestamptz NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS can_create_problem boolean NOT NULL DEFAULT true;
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url varchar(512) NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_status varchar(16) NOT NULL DEFAULT 'approved';
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_username_change timestamptz NULL;

COMMIT;
