-- Migration 027: 생산실적 확인 이력 (Sprint 33)
BEGIN;

CREATE TABLE IF NOT EXISTS plan.production_confirm (
    id SERIAL PRIMARY KEY,
    sales_order VARCHAR(255) NOT NULL,
    process_type VARCHAR(20) NOT NULL,
    confirmed_week VARCHAR(10) NOT NULL,
    confirmed_month VARCHAR(7) NOT NULL,
    sn_count INTEGER NOT NULL DEFAULT 0,
    confirmed_by INTEGER REFERENCES workers(id) ON DELETE SET NULL,
    confirmed_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ DEFAULT NULL,
    deleted_by INTEGER REFERENCES workers(id) ON DELETE SET NULL
);

-- partial unique index (soft delete된 행 제외)
CREATE UNIQUE INDEX IF NOT EXISTS production_confirm_active_unique
    ON plan.production_confirm(sales_order, process_type, confirmed_week)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_production_confirm_month ON plan.production_confirm(confirmed_month);
CREATE INDEX IF NOT EXISTS idx_production_confirm_order ON plan.production_confirm(sales_order);

-- 실적확인 공정별 on/off 설정
INSERT INTO admin_settings (setting_key, setting_value, description)
VALUES
    ('confirm_mech_enabled', 'true', '기구 실적확인 활성화'),
    ('confirm_elec_enabled', 'true', '전장 실적확인 활성화'),
    ('confirm_tm_enabled', 'true', 'Tank Module 실적확인 활성화'),
    ('confirm_pi_enabled', 'false', 'PI 실적확인 활성화'),
    ('confirm_qi_enabled', 'false', 'QI 실적확인 활성화'),
    ('confirm_si_enabled', 'false', 'SI 실적확인 활성화'),
    ('confirm_checklist_required', 'false', '실적확인 시 체크리스트 완료 필수 여부')
ON CONFLICT (setting_key) DO NOTHING;

COMMIT;
