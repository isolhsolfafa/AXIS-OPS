-- =====================================================================
-- Migration 054 — ELEC IF_1/IF_2 task_name 도킹 전/후 명시 (작업자 혼동 방지)
-- =====================================================================
-- Sprint: FIX-ELEC-IF-NAMING-DOCKING-CLARITY-20260510
-- Created: 2026-05-10
-- Version: v2.12.4 (target)
--
-- 트리거:
--   사용자 측 운영 catch — 작업자들이 IF_1 / IF_2 의 1/2 기준이 도킹 전/후 인지
--   혼동. 명시적 라벨 부여 ("(도킹 전)" / "(도킹 후)") 로 영구 해결.
--
-- 영향:
--   - app_task_details 의 task_name UPDATE only (식별자 task_id 변경 없음)
--   - 기존 데이터 정정: IF_1 185 row + IF_2 185 row = 370 row UPDATE 예정
--   - task_id 매칭 로직 영향 0 (코드/알림/체크리스트 trigger 전부 task_id 기반)
--   - FE 코드 변경 0 (task_name display only)
--
-- idempotent:
--   - WHERE task_name = 'I.F 1' 조건 — 재실행 시 매칭 0 row → no-op
--   - WHERE task_name = 'I.F 2' 동일
-- =====================================================================

BEGIN;

-- 1. IF_1 task_name UPDATE
UPDATE app_task_details
   SET task_name = 'I.F 1 (도킹 전)',
       updated_at = CURRENT_TIMESTAMP
 WHERE task_category = 'ELEC'
   AND task_id = 'IF_1'
   AND task_name = 'I.F 1';

-- 2. IF_2 task_name UPDATE
UPDATE app_task_details
   SET task_name = 'I.F 2 (도킹 후)',
       updated_at = CURRENT_TIMESTAMP
 WHERE task_category = 'ELEC'
   AND task_id = 'IF_2'
   AND task_name = 'I.F 2';

-- 3. 검증 (정합성 보장)
DO $$
DECLARE
    if1_remaining INTEGER;
    if2_remaining INTEGER;
    if1_updated INTEGER;
    if2_updated INTEGER;
BEGIN
    -- 옛 이름 잔존 0 검증
    SELECT COUNT(*) INTO if1_remaining
      FROM app_task_details
     WHERE task_category = 'ELEC' AND task_id = 'IF_1' AND task_name = 'I.F 1';
    SELECT COUNT(*) INTO if2_remaining
      FROM app_task_details
     WHERE task_category = 'ELEC' AND task_id = 'IF_2' AND task_name = 'I.F 2';

    -- 신규 이름 적용 카운트
    SELECT COUNT(*) INTO if1_updated
      FROM app_task_details
     WHERE task_category = 'ELEC' AND task_id = 'IF_1' AND task_name = 'I.F 1 (도킹 전)';
    SELECT COUNT(*) INTO if2_updated
      FROM app_task_details
     WHERE task_category = 'ELEC' AND task_id = 'IF_2' AND task_name = 'I.F 2 (도킹 후)';

    IF if1_remaining > 0 OR if2_remaining > 0 THEN
        RAISE EXCEPTION
            '[054] task_name 정정 잔존 영역 — IF_1 잔존:%, IF_2 잔존:%',
            if1_remaining, if2_remaining;
    END IF;

    RAISE NOTICE '[054] ELEC IF task_name 정합 완료: IF_1=% rows, IF_2=% rows', if1_updated, if2_updated;
END $$;

COMMIT;
