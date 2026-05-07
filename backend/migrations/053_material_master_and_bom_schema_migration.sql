-- =============================================================
-- Migration 053 — FEAT-MATERIAL-MASTER-AND-BOM-INTEGRATION-20260507
-- =============================================================
-- 등록일: 2026-05-07
-- 트리거: Twin파파 운영 catch (5-07) — Sprint 63 51a seed 의 placeholder 영구 차단
-- 선행 Sprint: Sprint 63-BE (MECH 체크리스트) ✅ / Sprint 65-BE (성적서 분기) ✅
-- 변경 내용:
--   (1) public.product_bom + bom_checklist_log + bom_csv_import DROP (데이터 0 검증 5-07)
--   (2) checklist.material_master CREATE (자재 마스터 — 정규화)
--   (3) checklist.product_bom CREATE (영문 컬럼 표준 + product_code soft FK)
--   (4) checklist.bom_checklist_log CREATE (17 컬럼, AI 검증 영역 보존)
--   (5) checklist.checklist_record.selected_material_id ADD COLUMN (NEW-M-01 정정)
-- Codex 라운드 1~5 합의 반영:
--   D1-01: google_doc_id → qr_doc_id (CLAUDE.md L72 표준)
--   D1-02: NOT NULL 제약 (boolean / timestamp)
--   D1-03: DROP 순서 자식→부모 (bom_checklist_log → product_bom)
--   NEW-M-01: selected_material_id INTEGER 컬럼 (FE 직접 전달 + BE 검증)
-- 사전 검증 SQL 11건 GREEN (5-07):
--   - public 3 테이블 데이터 0 / 외부 의존성 0
--   - update_updated_at_column public schema / search_path "$user", public
--   - select_options content_shape = 8 SELECT 항목 모두 legacy_string_array
--   - selected_material_id 컬럼 부재 (ADD COLUMN 안전)
-- =============================================================

BEGIN;

-- ────────────────────────────────────────────────────────────────
-- (1) 기존 public 테이블 DROP (데이터 0 검증 완료 — 5-07)
--     RESTRICT — 잔존 의존성 발견 시 에러 발생 (안전 차원)
--     bom_csv_import: 사용자 측 임시 임포트 테이블 (P1 #9 묶음 DROP)
--     순서: bom_checklist_log → product_bom (자식 → 부모, FK 직조)
-- ────────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS public.bom_csv_import RESTRICT;
DROP TABLE IF EXISTS public.bom_checklist_log RESTRICT;
DROP TABLE IF EXISTS public.product_bom RESTRICT;


-- ────────────────────────────────────────────────────────────────
-- (2) checklist.material_master CREATE (자재 마스터)
--     - item_code: 자재코드 (UNIQUE, csv 1310225400 / 1110006700 등)
--     - item_name: 자재내역 (CENTER O-RING, MFC LNG 등)
--     - category: 자재내역 분류 (csv 자재내역 그대로, MFC, ANCHOR BRACKET 등)
--     - spec_1, spec_2: 규격1, 규격2 (NULL 허용)
--     - unit: 단위 (EA 등)
--     - is_active: NOT NULL DEFAULT TRUE (D1-02)
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS checklist.material_master (
    id              SERIAL PRIMARY KEY,
    item_code       VARCHAR(50) UNIQUE NOT NULL,
    item_name       VARCHAR(200) NOT NULL,
    category        VARCHAR(50),
    spec_1          VARCHAR(200),
    spec_2          VARCHAR(200),
    unit            VARCHAR(20),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,                       -- D1-02
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,      -- D1-02
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP       -- D1-02
);

CREATE INDEX IF NOT EXISTS idx_material_master_category
    ON checklist.material_master(category) WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_material_master_item_name
    ON checklist.material_master(item_name);


-- ────────────────────────────────────────────────────────────────
-- (3) checklist.product_bom CREATE (product_code 별 BOM 매핑)
--     - product_code: plan.product_info.product_code 와 매칭 (soft FK)
--                     → csv 4100xxxx prefix 다수가 plan 미등록 영역이라 hard FK X
--     - material_id: checklist.material_master(id) hard FK + RESTRICT
--     - UNIQUE (product_code, material_id) — Step 2 ON CONFLICT 정합
--     - is_active: NOT NULL DEFAULT TRUE (D1-02)
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS checklist.product_bom (
    id              SERIAL PRIMARY KEY,
    product_code    VARCHAR(50) NOT NULL,
    customer        VARCHAR(100),
    model           VARCHAR(100),
    material_id     INTEGER NOT NULL REFERENCES checklist.material_master(id) ON DELETE RESTRICT,
    quantity        INTEGER,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,                       -- D1-02
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,      -- D1-02
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,      -- D1-02
    UNIQUE (product_code, material_id)
);

CREATE INDEX IF NOT EXISTS idx_product_bom_product_code
    ON checklist.product_bom(product_code) WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_product_bom_material_id
    ON checklist.product_bom(material_id);


-- ────────────────────────────────────────────────────────────────
-- (4) checklist.bom_checklist_log CREATE (SI hook-up 검사 결과, 17 컬럼)
--     - qr_doc_id: D1-01 (google_doc_id → qr_doc_id 표준 준수)
--     - bom_item_id: checklist.product_bom(id) hard FK + RESTRICT
--     - AI 검증 영역 (Phase 3 보존): ai_verified, ai_image_url, ai_response 등
--     - is_checked / mismatch_reported: NOT NULL DEFAULT FALSE (D1-02)
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS checklist.bom_checklist_log (
    id                  SERIAL PRIMARY KEY,
    serial_number       VARCHAR(128) NOT NULL,
    qr_doc_id           VARCHAR(100),                                    -- D1-01
    product_code        VARCHAR(50) NOT NULL,
    bom_item_id         INTEGER NOT NULL REFERENCES checklist.product_bom(id) ON DELETE RESTRICT,
    is_checked          BOOLEAN NOT NULL DEFAULT FALSE,                  -- D1-02
    checked_at          TIMESTAMPTZ,
    checked_by          VARCHAR(50),
    -- AI 검증 영역 (Phase 3 보존)
    ai_verified         BOOLEAN,
    ai_verified_at      TIMESTAMPTZ,
    ai_confidence       NUMERIC,
    ai_image_url        TEXT,
    ai_response         JSONB,
    -- 불일치 보고
    mismatch_reported   BOOLEAN NOT NULL DEFAULT FALSE,                  -- D1-02
    mismatch_notes      TEXT,
    -- 메타
    created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,  -- D1-02
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP   -- D1-02
);

CREATE INDEX IF NOT EXISTS idx_bom_checklist_log_serial
    ON checklist.bom_checklist_log(serial_number);

CREATE INDEX IF NOT EXISTS idx_bom_checklist_log_bom_item
    ON checklist.bom_checklist_log(bom_item_id);


-- ────────────────────────────────────────────────────────────────
-- (5) checklist.checklist_record.selected_material_id ADD COLUMN
--     - NEW-M-01 정정 영역: FE 가 dropdown 의 underlying value (material_id) 직접 전달
--     - selected_value (display string) + selected_material_id (FK) 양쪽 보유
--     - FK → checklist.material_master(id) RESTRICT (자재 삭제 시 record 보호)
--     - partial index — material_id 매핑된 record 만 (legacy placeholder 영역 제외)
-- ────────────────────────────────────────────────────────────────
ALTER TABLE checklist.checklist_record
    ADD COLUMN IF NOT EXISTS selected_material_id INTEGER
    REFERENCES checklist.material_master(id) ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS idx_checklist_record_selected_material_id
    ON checklist.checklist_record(selected_material_id)
 WHERE selected_material_id IS NOT NULL;


-- ────────────────────────────────────────────────────────────────
-- (6) updated_at 자동 갱신 트리거
--     update_updated_at_column() 함수 — public schema 에 위치
--     search_path "$user", public 으로 unqualified 호출 가능 (검증 5-07)
-- ────────────────────────────────────────────────────────────────
DROP TRIGGER IF EXISTS trg_material_master_updated_at ON checklist.material_master;
CREATE TRIGGER trg_material_master_updated_at
    BEFORE UPDATE ON checklist.material_master
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_product_bom_updated_at ON checklist.product_bom;
CREATE TRIGGER trg_product_bom_updated_at
    BEFORE UPDATE ON checklist.product_bom
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_bom_checklist_log_updated_at ON checklist.bom_checklist_log;
CREATE TRIGGER trg_bom_checklist_log_updated_at
    BEFORE UPDATE ON checklist.bom_checklist_log
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ────────────────────────────────────────────────────────────────
-- (7) 운영 코멘트
-- ────────────────────────────────────────────────────────────────
COMMENT ON TABLE checklist.material_master IS
    '자재 마스터 (Migration 053) — MFC / Flow Sensor / SI hook-up 자재 통합. 5-07 사용자 합의 (csv 173 + MFC 13 = 186 unique).';

COMMENT ON TABLE checklist.product_bom IS
    'product_code 별 BOM 매핑 (Migration 053) — csv 출하 어플용 1,640 row + admin UI 추가. soft FK (plan.product_info 미참조).';

COMMENT ON TABLE checklist.bom_checklist_log IS
    'SI hook-up 검사 결과 (Migration 053, 17 컬럼) — AI 검증 영역 보존 (Phase 3). qr_doc_id 표준 준수 (CLAUDE.md L72).';

COMMENT ON COLUMN checklist.checklist_record.selected_material_id IS
    'FE dropdown 의 material_id 직접 추적 (Migration 053, NEW-M-01 정정). selected_value display string + selected_material_id FK 양쪽 보유 — 자재 spec 변경 시 BE override 자동 반영.';

COMMIT;
