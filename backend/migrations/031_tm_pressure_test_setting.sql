-- Migration 031: TM 가압검사 옵션 (#36-C)
BEGIN;

INSERT INTO admin_settings (setting_key, setting_value, description)
VALUES ('tm_pressure_test_required', 'true', 'TM 가압검사 progress/알람 포함 여부 (true=포함, false=탱크모듈만)')
ON CONFLICT (setting_key) DO NOTHING;

COMMIT;
