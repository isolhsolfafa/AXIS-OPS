-- Migration 032: S/N별 실적확인 (#38)
BEGIN;

ALTER TABLE plan.production_confirm
    ADD COLUMN IF NOT EXISTS serial_number VARCHAR(20) DEFAULT NULL;

ALTER TABLE plan.production_confirm
    DROP COLUMN IF EXISTS sn_count;

DROP INDEX IF EXISTS plan.production_confirm_active_unique;

CREATE UNIQUE INDEX production_confirm_active_unique
    ON plan.production_confirm(sales_order, process_type, COALESCE(partner, ''), serial_number)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_production_confirm_serial_number
    ON plan.production_confirm(serial_number)
    WHERE deleted_at IS NULL;

COMMIT;
