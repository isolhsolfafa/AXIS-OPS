-- Sprint 27: 단일 액션 Task 지원
-- task_type: 'NORMAL' (기본, 시작→완료) / 'SINGLE_ACTION' (완료 체크만)

ALTER TABLE app_task_details
ADD COLUMN IF NOT EXISTS task_type VARCHAR(20) NOT NULL DEFAULT 'NORMAL';

-- 기존 Tank Docking 행을 SINGLE_ACTION으로 업데이트
UPDATE app_task_details
SET task_type = 'SINGLE_ACTION'
WHERE task_id = 'TANK_DOCKING';

COMMENT ON COLUMN app_task_details.task_type IS 'NORMAL: 시작/완료 2단계, SINGLE_ACTION: 완료 체크만';
