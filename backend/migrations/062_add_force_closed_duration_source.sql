-- Migration 062: FIX-FORCE-CLOSE-DURATION-SOURCE — duration_source enum 'FORCE_CLOSED' 추가 + backfill
--
-- Sprint: FIX-FORCE-CLOSE-DURATION-SOURCE-20260613
-- 도입 시점: 2026-06-13 (Codex 라운드 1 M-Q1 반영 — 트랜잭션 블록 + DO block 검증 보강)
--
-- 배경:
--   force_close_task 가 duration_source 미설정(NULL) → 입력정합(get_data_quality)에서
--   NULL=clean 으로 과대 집계 (force-close 199건 섞임, 81.8% → 정직값 72.7%).
--   클린 코어 데이터 원칙(2026-04-20): 강제종료 = "버리는 데이터" → 비-clean 표시 필요.
--   force-close 가 'FORCE_CLOSED' 기록 → 입력정합·CT 표본 가드 없이 자동 정합 (Fable/Codex 권고).
--
-- 신규 enum 'FORCE_CLOSED':
--   - force_close_task UPDATE 가 기록 (admin.py)
--   - 측정값 컬럼(active_time/ct_time/duration)은 audit·표시용 유지, source 로만 비-clean 표시
--
-- 호환성:
--   - additive only (기존 5 enum + 신규 1 = 총 6 enum), NULL 허용 유지
--   - backfill = clean(NULL/NORMAL)으로 잘못 집계된 기존 force-close 만 정정 (멱등)
--   - 약불변식: force_closed=TRUE 중 NULL/NORMAL → FORCE_CLOSED. FALLBACK/PREV_DAY_CAP force-close
--     (이미 비-clean)는 미변경 — cap source 정보 보존, 입력정합 집계 불오염 (Codex Q5 A 합의).

BEGIN;

-- 1. 기존 CHECK constraint DROP (idempotent, 057 패턴)
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

-- 2. 신규 CHECK constraint (6 enum + NULL 허용)
ALTER TABLE app_task_details
ADD CONSTRAINT app_task_details_duration_source_check
CHECK (
    duration_source IS NULL
    OR duration_source IN (
        'NORMAL_COMPLETION',
        'ATTENDANCE_OUT',
        'FALLBACK_TRIGGER_DATE_17',
        'INVALID_WARNING',
        'PREV_DAY_CAP',
        'FORCE_CLOSED'
    )
);

-- 3. backfill — clean 으로 잘못 집계된 기존 force-close(NULL/NORMAL)만 'FORCE_CLOSED' 정정.
--    멱등: 이미 FORCE_CLOSED/FALLBACK 등은 조건 불일치 → 무영향.
UPDATE app_task_details
SET duration_source = 'FORCE_CLOSED'
WHERE force_closed = TRUE
  AND (duration_source IS NULL OR duration_source = 'NORMAL_COMPLETION');

-- 4. 검증 DO block — CHECK 재생성 + FORCE_CLOSED enum 포함 + backfill clean 잔존 0
DO $$
DECLARE
    constraint_def TEXT;
    leaked INT;
BEGIN
    SELECT pg_get_constraintdef(oid) INTO constraint_def
    FROM pg_constraint
    WHERE conname = 'app_task_details_duration_source_check'
      AND conrelid = 'app_task_details'::regclass;

    IF constraint_def IS NULL THEN
        RAISE EXCEPTION 'Migration 062 FAIL: CHECK constraint 재생성 실패';
    END IF;
    IF constraint_def NOT LIKE '%FORCE_CLOSED%' THEN
        RAISE EXCEPTION 'Migration 062 FAIL: FORCE_CLOSED enum 미포함 (%)', constraint_def;
    END IF;

    SELECT COUNT(*) INTO leaked
    FROM app_task_details
    WHERE force_closed = TRUE
      AND (duration_source IS NULL OR duration_source = 'NORMAL_COMPLETION');
    IF leaked > 0 THEN
        RAISE EXCEPTION 'Migration 062 FAIL: force-close clean 잔존 % 건', leaked;
    END IF;

    RAISE NOTICE 'Migration 062 GREEN: FORCE_CLOSED enum 추가 (6 total) + backfill 완료 (clean 잔존 0)';
END $$;

COMMIT;
