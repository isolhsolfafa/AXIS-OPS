-- BUG-24: task_type 컬럼 보장 + CASCADE → RESTRICT 변경
-- 이미 적용된 경우 IF NOT EXISTS / IF EXISTS로 안전하게 처리
BEGIN;

-- 1. task_type 컬럼 (migration 022가 누락될 경우 대비)
ALTER TABLE app_task_details
    ADD COLUMN IF NOT EXISTS task_type VARCHAR(20) DEFAULT 'NORMAL';

-- 2. FK: CASCADE → RESTRICT
ALTER TABLE app_task_details
    DROP CONSTRAINT IF EXISTS app_task_details_qr_doc_id_fkey;
ALTER TABLE app_task_details
    ADD CONSTRAINT app_task_details_qr_doc_id_fkey
    FOREIGN KEY (qr_doc_id) REFERENCES qr_registry(qr_doc_id) ON DELETE RESTRICT;

ALTER TABLE completion_status
    DROP CONSTRAINT IF EXISTS completion_status_serial_number_fkey;
ALTER TABLE completion_status
    ADD CONSTRAINT completion_status_serial_number_fkey
    FOREIGN KEY (serial_number) REFERENCES qr_registry(serial_number) ON DELETE RESTRICT;

COMMIT;
