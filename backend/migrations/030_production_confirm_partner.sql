-- Migration 030: 혼재 O/N 실적확인 partner별 분리 (#37)
BEGIN;

ALTER TABLE plan.production_confirm
    ADD COLUMN IF NOT EXISTS partner VARCHAR(50) DEFAULT NULL;

DROP INDEX IF EXISTS plan.production_confirm_active_unique;

CREATE UNIQUE INDEX production_confirm_active_unique
    ON plan.production_confirm(sales_order, process_type, confirmed_week, COALESCE(partner, ''))
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_production_confirm_partner
    ON plan.production_confirm(partner)
    WHERE deleted_at IS NULL;

COMMIT;
