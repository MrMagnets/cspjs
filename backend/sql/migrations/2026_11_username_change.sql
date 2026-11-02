-- 用户名修改冷却
-- psql "$DATABASE_URL" -f backend/sql/migrations/2026_11_username_change.sql

BEGIN;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_username_change timestamptz NULL;
COMMIT;
