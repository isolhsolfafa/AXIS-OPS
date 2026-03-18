-- Migration 025: DUAL 모델 L/R QR 지원
-- qr_registry.serial_number UNIQUE 제거 → 같은 S/N으로 L/R QR 2행 허용
-- completion_status FK를 plan.product_info.serial_number로 재지정

BEGIN;

-- 1. completion_status FK 제거 (qr_registry.serial_number UNIQUE에 의존)
ALTER TABLE completion_status DROP CONSTRAINT IF EXISTS completion_status_serial_number_fkey;

-- 2. qr_registry serial_number UNIQUE 제거
ALTER TABLE qr_registry DROP CONSTRAINT IF EXISTS qr_registry_serial_number_key;

-- 3. completion_status FK → plan.product_info.serial_number로 변경
ALTER TABLE completion_status ADD CONSTRAINT completion_status_serial_number_fkey
    FOREIGN KEY (serial_number) REFERENCES plan.product_info(serial_number) ON DELETE RESTRICT;

COMMIT;
