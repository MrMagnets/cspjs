-- 在 Neon SQL Editor 中直接执行：清理所有“测试/演示”题目及其关联数据
-- 建议先 BEGIN 后检查 SELECT 结果，再 COMMIT。

BEGIN;

CREATE TEMP TABLE cleanup_problem_ids ON COMMIT DROP AS
SELECT id
FROM problems
WHERE title ILIKE '%测试%'
   OR title ILIKE '%演示%';

-- 关联提交（按题目 + 按小题双保险）
DELETE FROM submissions
WHERE problem_id IN (SELECT id FROM cleanup_problem_ids)
   OR sub_question_id IN (
       SELECT id FROM sub_questions
       WHERE problem_id IN (SELECT id FROM cleanup_problem_ids)
   );

-- 错题记录（wrong_reviews 通过 FK CASCADE 删除）
DELETE FROM wrong_questions
WHERE problem_id IN (SELECT id FROM cleanup_problem_ids)
   OR sub_question_id IN (
       SELECT id FROM sub_questions
       WHERE problem_id IN (SELECT id FROM cleanup_problem_ids)
   );

-- 标签 / 题单 / 比赛关联
DELETE FROM problem_tags
WHERE problem_id IN (SELECT id FROM cleanup_problem_ids);

DELETE FROM problem_list_items
WHERE problem_id IN (SELECT id FROM cleanup_problem_ids);

DELETE FROM contest_problems
WHERE problem_id IN (SELECT id FROM cleanup_problem_ids);

-- 小题与题目
DELETE FROM sub_questions
WHERE problem_id IN (SELECT id FROM cleanup_problem_ids);

DELETE FROM problems
WHERE id IN (SELECT id FROM cleanup_problem_ids);

COMMIT;

-- 删除后确认（应返回 0）
-- SELECT count(*) FROM problems WHERE title ILIKE '%测试%' OR title ILIKE '%演示%';
