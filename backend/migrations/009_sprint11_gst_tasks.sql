-- Sprint 11: GST 검사 공정 (PI/QI/SI) + checklist 스키마 + active_role
-- 마이그레이션 번호: 009

-- ────────────────────────────────────────────────────────────────
-- 1. checklist 스키마 생성
-- ────────────────────────────────────────────────────────────────

CREATE SCHEMA IF NOT EXISTS checklist;

-- checklist_master: 체크리스트 항목 마스터 데이터
CREATE TABLE IF NOT EXISTS checklist.checklist_master (
    id SERIAL PRIMARY KEY,
    product_code VARCHAR(100) NOT NULL,
    category VARCHAR(20) NOT NULL,            -- 'HOOKUP', 'MECH', 'ELEC', 'PI', 'QI'
    item_name VARCHAR(255) NOT NULL,
    item_order INTEGER DEFAULT 0,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(product_code, category, item_name)
);
CREATE INDEX IF NOT EXISTS idx_checklist_master_product
    ON checklist.checklist_master(product_code, category);

-- checklist_record: 실제 체크리스트 기록
CREATE TABLE IF NOT EXISTS checklist.checklist_record (
    id SERIAL PRIMARY KEY,
    serial_number VARCHAR(100) NOT NULL,
    master_id INTEGER NOT NULL REFERENCES checklist.checklist_master(id),
    is_checked BOOLEAN DEFAULT FALSE,
    checked_by INTEGER REFERENCES public.workers(id),
    checked_at TIMESTAMPTZ,
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(serial_number, master_id)
);
CREATE INDEX IF NOT EXISTS idx_checklist_record_sn
    ON checklist.checklist_record(serial_number);
CREATE INDEX IF NOT EXISTS idx_checklist_record_master
    ON checklist.checklist_record(master_id);


-- ────────────────────────────────────────────────────────────────
-- 2. workers 테이블에 active_role 컬럼 추가
-- ────────────────────────────────────────────────────────────────

ALTER TABLE workers ADD COLUMN IF NOT EXISTS active_role VARCHAR(10);

-- GST 소속 작업자는 기본 role로 active_role 초기화
UPDATE workers
SET active_role = role
WHERE company = 'GST'
  AND active_role IS NULL;
