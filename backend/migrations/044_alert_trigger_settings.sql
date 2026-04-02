-- Sprint 54: 공정 흐름 알림 트리거 on/off 설정
-- 기존 admin_settings 테이블에 INSERT (컬럼: setting_key, setting_value, description)

INSERT INTO admin_settings (setting_key, setting_value, description)
VALUES
    ('alert_tm_to_mech_enabled', 'true', 'TMS 가압검사 완료 → MECH 매니저 알림 활성화'),
    ('alert_mech_to_elec_enabled', 'true', 'MECH Tank Docking 완료 → ELEC 매니저 알림 활성화'),
    ('alert_elec_to_pi_enabled', 'false', 'ELEC 자주검사 완료 → PI 매니저 알림 활성화'),
    ('alert_mech_pressure_to_qi_enabled', 'false', 'DRAGON MECH 가압검사 완료 → QI 매니저 알림 활성화'),
    ('alert_tm_tank_module_to_elec_enabled', 'false', 'TMS TANK_MODULE 완료(가압제외) → ELEC 매니저 알림 활성화')
ON CONFLICT (setting_key) DO NOTHING;

-- ※ ELEC_COMPLETE를 alert_type_enum에 추가
ALTER TYPE alert_type_enum ADD VALUE IF NOT EXISTS 'ELEC_COMPLETE';
