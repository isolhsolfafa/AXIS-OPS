-- Migration 057: v2.15.16 — duration_source enum 'PREV_DAY_CAP' 추가
--
-- Sprint: SPRINT-V2-15-16-MECH-FORCE-CLOSED-PREV-DAY-CAP-20260515
-- 도입 시점: 2026-05-15 (Codex 라운드 1 Q3 M 반영)
--
-- 배경:
--   v2.15.15 catch — 익일/주말 trigger 시 close_at = trigger_time 으로
--   18h+ 비정상 duration 저장됨 (시나리오 C). Codex Q3 권고 = duration_calculator.py
--   에 전일 경계 cap 추가 → trigger.date() > started.date() 시 started.date() 17:00 KST cap.
--
-- 신규 enum 'PREV_DAY_CAP':
--   - trigger 발동 날짜가 worker 시작 날짜 보다 다음 날 이상일 때 활성
--   - close_at = started.date() 17:00 KST (전일 정규 퇴근시간)
--   - 운영 영역: 사용자 catch (5-15) 시나리오 C 처리, audit trail 정확
--
-- 호환성:
--   - additive only (기존 4 enum + 신규 1 = 총 5 enum)
--   - NULL 허용 유지
--   - 기존 row 영향 0

BEGIN;

-- 1. 기존 CHECK constraint DROP (idempotent)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'app_task_details_duration_source_check'
          AND table_name = 'app_task_details'
    ) THEN
        ALTER TABLE app_task_details
        DROP CONSTRAINT app_task_details_duration_source_check;
    END IF;
END $$;

-- 2. 신규 CHECK constraint (5 enum + NULL 허용)
ALTER TABLE app_task_details
ADD CONSTRAINT app_task_details_duration_source_check
CHECK (
    duration_source IS NULL
    OR duration_source IN (
        'NORMAL_COMPLETION',
        'ATTENDANCE_OUT',
        'FALLBACK_TRIGGER_DATE_17',
        'INVALID_WARNING',
        'PREV_DAY_CAP'
    )
);

-- 3. 검증 DO block
DO $$
DECLARE
    constraint_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'app_task_details_duration_source_check'
          AND table_name = 'app_task_details'
    ) INTO constraint_exists;

    IF NOT constraint_exists THEN
        RAISE EXCEPTION 'Migration 057 FAIL: CHECK constraint 재생성 실패';
    END IF;

    -- 신규 enum 'PREV_DAY_CAP' 삽입 테스트 (rollback 됨, transaction 영역)
    BEGIN
        PERFORM 1 WHERE 'PREV_DAY_CAP' IN (
            'NORMAL_COMPLETION', 'ATTENDANCE_OUT', 'FALLBACK_TRIGGER_DATE_17',
            'INVALID_WARNING', 'PREV_DAY_CAP'
        );
    EXCEPTION WHEN OTHERS THEN
        RAISE EXCEPTION 'Migration 057 FAIL: PREV_DAY_CAP enum 검증 실패';
    END;

    RAISE NOTICE 'Migration 057 GREEN: PREV_DAY_CAP enum 추가 (5 total)';
END $$;

COMMIT;
