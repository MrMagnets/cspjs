-- 用户头像与审核状态
-- psql "$DATABASE_URL" -f backend/sql/migrations/2026_11_avatar.sql

BEGIN;
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url varchar(512) NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_status varchar(16) NOT NULL DEFAULT 'approved';
COMMIT;
