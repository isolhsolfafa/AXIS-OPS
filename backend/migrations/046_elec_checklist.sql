-- Sprint 57: ELEC 체크리스트 스키마 확장

-- 1. checker_role 컬럼 추가 (GST/QI 항목 구분)
ALTER TABLE checklist.checklist_master
    ADD COLUMN IF NOT EXISTS checker_role VARCHAR(20) DEFAULT 'WORKER';

COMMENT ON COLUMN checklist.checklist_master.checker_role IS
    'WORKER: 외주 작업자 체크, QI: GST QI인원 체크 (ELEC Group 3 GST 담당자)';

-- 2. phase별 N.A 기본값 관리
ALTER TABLE checklist.checklist_master
    ADD COLUMN IF NOT EXISTS phase1_na BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN checklist.checklist_master.phase1_na IS
    'TRUE이면 1차(judgment_phase=1)에서 자동 N.A 처리 (예: 버너 위 배선상태)';

-- 3. ELEC 체크리스트 ISSUE 알림 admin_settings
INSERT INTO admin_settings (setting_key, setting_value, description)
VALUES ('elec_checklist_issue_alert', 'true', 'ELEC 체크리스트 ISSUE 알림 on/off')
ON CONFLICT (setting_key) DO NOTHING;
