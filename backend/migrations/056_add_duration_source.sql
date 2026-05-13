-- Migration 056: Sprint 41-D — duration_source 컬럼 추가 (additive, NULLABLE)
--
-- Sprint: SPRINT-41-D-RELAY-FIRST-FINAL-LOGIC-20260513
-- 도입 시점: 2026-05-14 (Codex 라운드 1+2 GREEN 후)
--
-- 4종 enum (DURATION_SOURCE_ENUM):
--   - NORMAL_COMPLETION       : worker 정상 complete_work() 호출 (기본)
--   - ATTENDANCE_OUT          : hr.partner_attendance check_out 기준 (First/Second Close 자동)
--   - FALLBACK_TRIGGER_DATE_17: attendance 미체크 시 17:00 KST fallback (auto close)
--   - INVALID_WARNING         : duration_validator 비정상 검출 (운영 이상치)
--
-- 호환성:
--   - additive only (NULLABLE) — 기존 row forward-only NULL 유지
--   - CHECK constraint 도 NULL 허용
--   - Sprint 41-B 기존 auto_close_relay_task() 호출 시 default 'NORMAL_COMPLETION' 자동 적용

BEGIN;

-- 1. duration_source 컬럼 추가 (NULLABLE)
ALTER TABLE app_task_details
ADD COLUMN IF NOT EXISTS duration_source VARCHAR(40) DEFAULT NULL;

-- 2. CHECK constraint (4 enum + NULL 허용)
DO $$
BEGIN
    -- 기존 constraint 가 있으면 DROP (idempotent 재적용 안전)
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'app_task_details_duration_source_check'
          AND table_name = 'app_task_details'
    ) THEN
        ALTER TABLE app_task_details
        DROP CONSTRAINT app_task_details_duration_source_check;
    END IF;
END $$;

ALTER TABLE app_task_details
ADD CONSTRAINT app_task_details_duration_source_check
CHECK (
    duration_source IS NULL
    OR duration_source IN (
        'NORMAL_COMPLETION',
        'ATTENDANCE_OUT',
        'FALLBACK_TRIGGER_DATE_17',
        'INVALID_WARNING'
    )
);

-- 3. 검증 DO block (실패 시 자동 ROLLBACK)
DO $$
DECLARE
    col_exists BOOLEAN;
    constraint_exists BOOLEAN;
BEGIN
    -- 컬럼 존재 검증
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'app_task_details'
          AND column_name = 'duration_source'
    ) INTO col_exists;

    IF NOT col_exists THEN
        RAISE EXCEPTION 'Migration 056 FAIL: duration_source 컬럼 추가 실패';
    END IF;

    -- CHECK constraint 존재 검증
    SELECT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'app_task_details_duration_source_check'
          AND table_name = 'app_task_details'
    ) INTO constraint_exists;

    IF NOT constraint_exists THEN
        RAISE EXCEPTION 'Migration 056 FAIL: CHECK constraint 생성 실패';
    END IF;

    RAISE NOTICE 'Migration 056 GREEN: duration_source NULLABLE + CHECK constraint (4 enum)';
END $$;

COMMIT;
