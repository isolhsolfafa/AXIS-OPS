-- Sprint 52: TM 체크리스트 스키마 확장
-- 043

-- ────────────────────────────────────────────────────────────────
-- 1. checklist_master에 item_group 컬럼 추가
--    용도: 15항목을 BURNER/REACTOR/EXHAUST/TANK 그룹으로 분류
-- ────────────────────────────────────────────────────────────────
ALTER TABLE checklist.checklist_master
    ADD COLUMN IF NOT EXISTS item_group VARCHAR(50);

COMMENT ON COLUMN checklist.checklist_master.item_group
    IS '항목 그룹 (TM: BURNER, REACTOR, EXHAUST, TANK)';


-- ────────────────────────────────────────────────────────────────
-- 2. checklist_record 변경: is_checked(bool) → check_result(varchar)
--    값: PASS, NA, NULL(미체크)
--    기존 데이터 마이그레이션: true→PASS, false→NULL
-- ────────────────────────────────────────────────────────────────
ALTER TABLE checklist.checklist_record
    ADD COLUMN IF NOT EXISTS check_result VARCHAR(10);

-- 기존 is_checked 데이터 마이그레이션
UPDATE checklist.checklist_record
SET check_result = CASE
    WHEN is_checked = TRUE THEN 'PASS'
    ELSE NULL
END
WHERE check_result IS NULL AND is_checked IS NOT NULL;

COMMENT ON COLUMN checklist.checklist_record.check_result
    IS '검사 결과: PASS=통과, NA=해당없음, NULL=미체크';


-- ────────────────────────────────────────────────────────────────
-- 3. checklist_record에 judgment_phase 컬럼 추가
--    Phase 1에서는 항상 1, Phase 2에서 2차 체크 시 2 사용
--    UNIQUE 제약 변경: (serial_number, master_id) → (serial_number, master_id, judgment_phase)
-- ────────────────────────────────────────────────────────────────
ALTER TABLE checklist.checklist_record
    ADD COLUMN IF NOT EXISTS judgment_phase INTEGER DEFAULT 1;

COMMENT ON COLUMN checklist.checklist_record.judgment_phase
    IS '판정 단계: 1=1차(TM종료 시점), 2=2차(가압검사 시점, 추후)';

-- 기존 UNIQUE 제약 제거 후 새 제약 추가
ALTER TABLE checklist.checklist_record
    DROP CONSTRAINT IF EXISTS checklist_record_serial_number_master_id_key;

ALTER TABLE checklist.checklist_record
    ADD CONSTRAINT checklist_record_sn_master_phase_key
    UNIQUE (serial_number, master_id, judgment_phase);


-- ────────────────────────────────────────────────────────────────
-- 4. alert_type_enum 확장: TM 체크리스트 알림 타입
-- ────────────────────────────────────────────────────────────────
ALTER TYPE alert_type_enum ADD VALUE IF NOT EXISTS 'CHECKLIST_TM_READY';
ALTER TYPE alert_type_enum ADD VALUE IF NOT EXISTS 'CHECKLIST_ISSUE';


-- ────────────────────────────────────────────────────────────────
-- 5. admin_settings에 TM 체크리스트 옵션 추가
--    tm_checklist_1st_checker: "is_manager" (기본값, 추후 "user" 가능)
--    tm_checklist_issue_alert: true (ISSUE 알림 on/off, 추후용 기능)
--    tm_checklist_scope: "product_code" (기본값, "all" 가능)
-- ────────────────────────────────────────────────────────────────
INSERT INTO admin_settings (setting_key, setting_value, description)
VALUES
    ('tm_checklist_1st_checker', '"is_manager"', 'TM 체크리스트 1차 체크 권한 (is_manager|user)'),
    ('tm_checklist_issue_alert', 'true', 'TM 체크리스트 ISSUE 알림 on/off'),
    ('tm_checklist_scope', '"product_code"', 'TM 체크리스트 항목 범위 (product_code|all)')
ON CONFLICT (setting_key) DO NOTHING;
