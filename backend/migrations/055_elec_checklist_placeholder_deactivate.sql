-- Migration 055: ELEC 체크리스트 placeholder 31건 soft delete (046a 사고 정정)
--
-- Sprint: HOTFIX-ELEC-CHECKLIST-PLACEHOLDER-DEACTIVATE-20260513
-- Trigger: 2026-05-13 사용자 catch — 운영 DB id 111~124 영역에서 'Jig 검사 항목 1~7' placeholder 표시
--
-- 사고 trail:
--   1. 2026-04-09 22:55:08 — migration 046_elec_checklist.sql 적용 (스키마 생성)
--   2. 2026-04-10 11:26:40 — migration 047_elec_checklist_seed_fix.sql 적용 (DELETE + 정상 31항목 INSERT, id 62-92)
--   3. 2026-04-15 23:06:52 — migration 048_elec_master_normalization.sql 적용 (phase1_applicable + qi_check_required)
--   4. 2026-04-27 21:36:04 — HOTFIX-08 (v2.10.10) db_pool transaction 정리 fix 부수 효과
--                            → migration 046a_elec_checklist_seed.sql 자동 재적용 (placeholder seed)
--                            → 047 의 DELETE 이후 적용되어 placeholder 31건 신규 INSERT (id 94-124)
--                            → UNIQUE (product_code, category, item_group, item_name) 충돌 안 함 (item_name 다름)
--                            → ON CONFLICT DO NOTHING 우회되어 신규 row 31건 추가됨
--
-- 운영 DB 현황 (2026-05-13 기준):
--   - 정식 31건: id 62-92 (created_at 2026-04-10 11:26:40, is_active=TRUE) — 047 결과
--   - placeholder 31건: id 94-124 (created_at 2026-04-27 21:36:04, is_active=TRUE) — 046a 재적용 사고
--   - placeholder record 50건: id 111-117 (WORKER 영역, 운영자가 PASS/NA 입력)
--
-- 사용자 결정 (2026-05-13):
--   - Soft delete (is_active=FALSE) — DELETE 영역 위험 회피 + 운영 데이터 보존 원칙
--   - record 50건 보존 (FK 보존, 작업자 입력 trail 감사용)
--
-- Logic 변경: 0 (모든 ELEC 로직이 is_active=TRUE 필터 사용 — placeholder deactivate 후 정식 31건만 노출)
--   - check_elec_completion() Phase 1+2 (checklist_service.py L1170/L1192/L1209)
--   - get_elec_checklist() Phase 1/2 조회 (checklist_service.py L230)
--   - get_checklist_report() 성적서 (checklist_service.py L553)

BEGIN;

-- 1. placeholder 31건 deactivate
UPDATE checklist.checklist_master
SET is_active = FALSE,
    updated_at = NOW()
WHERE category = 'ELEC'
  AND product_code = 'COMMON'
  AND id BETWEEN 94 AND 124
  AND created_at::date = '2026-04-27';

-- 2. 검증 DO block (실패 시 자동 ROLLBACK)
DO $$
DECLARE
    placeholder_active_cnt INTEGER;
    legacy_active_cnt INTEGER;
    placeholder_deactivated_cnt INTEGER;
BEGIN
    -- placeholder 31건이 모두 is_active=FALSE 인지
    SELECT COUNT(*) INTO placeholder_active_cnt
    FROM checklist.checklist_master
    WHERE category = 'ELEC' AND product_code = 'COMMON'
      AND id BETWEEN 94 AND 124
      AND is_active = TRUE;

    -- 정식 31건이 그대로 is_active=TRUE 인지
    SELECT COUNT(*) INTO legacy_active_cnt
    FROM checklist.checklist_master
    WHERE category = 'ELEC' AND product_code = 'COMMON'
      AND id BETWEEN 62 AND 92
      AND is_active = TRUE;

    -- deactivate 된 row 수 (예상: 31)
    SELECT COUNT(*) INTO placeholder_deactivated_cnt
    FROM checklist.checklist_master
    WHERE category = 'ELEC' AND product_code = 'COMMON'
      AND id BETWEEN 94 AND 124
      AND is_active = FALSE;

    IF placeholder_active_cnt <> 0 THEN
        RAISE EXCEPTION 'Migration 055 FAIL: placeholder row deactivate 안 됨 (still active: %)', placeholder_active_cnt;
    END IF;

    IF legacy_active_cnt <> 31 THEN
        RAISE EXCEPTION 'Migration 055 FAIL: 정식 31건 active 유지 X (expected 31, got %)', legacy_active_cnt;
    END IF;

    IF placeholder_deactivated_cnt <> 31 THEN
        RAISE EXCEPTION 'Migration 055 FAIL: placeholder 31건 deactivate 안 됨 (expected 31, got %)', placeholder_deactivated_cnt;
    END IF;

    RAISE NOTICE 'Migration 055 GREEN: placeholder 31 deactivated / legacy 31 active 유지';
END $$;

COMMIT;
