-- Sprint 61-BE: 에스컬레이션 알람 확장

ALTER TYPE alert_type_enum ADD VALUE IF NOT EXISTS 'TASK_NOT_STARTED';
ALTER TYPE alert_type_enum ADD VALUE IF NOT EXISTS 'CHECKLIST_DONE_TASK_OPEN';
ALTER TYPE alert_type_enum ADD VALUE IF NOT EXISTS 'ORPHAN_ON_FINAL';

-- app_alert_logs 중복방지용 task_detail_id 컬럼 추가
ALTER TABLE app_alert_logs ADD COLUMN IF NOT EXISTS task_detail_id INTEGER NULL;
CREATE INDEX IF NOT EXISTS idx_alert_logs_dedupe
    ON app_alert_logs (alert_type, serial_number, task_detail_id)
    WHERE task_detail_id IS NOT NULL;

-- 신규 admin_settings 기본값
INSERT INTO admin_settings (setting_key, setting_value) VALUES
  ('alert_task_not_started_enabled', 'true'),
  ('alert_checklist_done_task_open_enabled', 'true'),
  ('alert_orphan_on_final_enabled', 'true'),
  ('task_not_started_threshold_days', '2')
ON CONFLICT (setting_key) DO NOTHING;
