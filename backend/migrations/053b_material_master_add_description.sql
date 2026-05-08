-- =====================================================================
-- Migration 053b — checklist.material_master.description 컬럼 추가 + MFC backfill
-- =====================================================================
-- Sprint: FEAT-MATERIAL-MASTER-AND-BOM-INTEGRATION-20260507 Step 2 보완
-- Created: 2026-05-08
-- Version: v2.12.1 (target)
--
-- 목적:
--   - MFC 자재 13개 가스 종류 (LNG/CDA/O2/N2) 보존 → admin AXIS-VIEW 측 매핑 시
--     `description ILIKE '%LNG%'` 등으로 검색 보조
--   - 1110299900 (MKP | 150 SLM): LNG + O2 dual-use → description='LNG,O2'
--
-- 영향 범위:
--   - checklist.material_master: ADD COLUMN description TEXT (NULL 허용, 빈 값 OK)
--   - 13 MFC row UPDATE (item_code 기준)
--   - non-MFC row: description = NULL (의도된 상태, 회귀 0)
--
-- idempotent:
--   - ADD COLUMN IF NOT EXISTS — 재실행 안전
--   - UPDATE WHERE item_code = ... — item_code UNIQUE 보장
--
-- 관련:
--   - 053 (schema migration): public → checklist 이전, material_master 신설
--   - 053a (seed): 185 자재 + 1626 BOM INSERT (이미 적용)
--   - generate_migration_053a.py: CSV_COLUMN_MAP 에 '비고':'description' 추가됨 (이번 Step 2 보완)
-- =====================================================================

BEGIN;

-- 1. ALTER TABLE — description 컬럼 추가
ALTER TABLE checklist.material_master
    ADD COLUMN IF NOT EXISTS description TEXT;

COMMENT ON COLUMN checklist.material_master.description IS
    '자재 비고 — 가스 종류 (LNG/CDA/O2/N2) 등 검색 보조 정보. ILIKE 검색 대상.';

-- 2. Backfill — 13 MFC 자재 (item_code 기준 UNIQUE)
-- MFC LNG (5건)
UPDATE checklist.material_master SET description = 'LNG' WHERE item_code = '1110006700';
UPDATE checklist.material_master SET description = 'LNG' WHERE item_code = '1120094300';
UPDATE checklist.material_master SET description = 'LNG' WHERE item_code = '1110298800';
UPDATE checklist.material_master SET description = 'LNG' WHERE item_code = '1110020400';
UPDATE checklist.material_master SET description = 'LNG' WHERE item_code = '1110299800';

-- MFC LNG+O2 dual-use (1건) — 1110299900 합쳐진 단일 row
UPDATE checklist.material_master SET description = 'LNG,O2' WHERE item_code = '1110299900';

-- MFC CDA (2건)
UPDATE checklist.material_master SET description = 'CDA' WHERE item_code = '1110049600';
UPDATE checklist.material_master SET description = 'CDA' WHERE item_code = '1100479300';

-- MFC O2 (4건)
UPDATE checklist.material_master SET description = 'O2' WHERE item_code = '1110006800';
UPDATE checklist.material_master SET description = 'O2' WHERE item_code = '1120099400';
UPDATE checklist.material_master SET description = 'O2' WHERE item_code = '1100519700';
UPDATE checklist.material_master SET description = 'O2' WHERE item_code = '1110005900';

-- MFC N2 (1건)
UPDATE checklist.material_master SET description = 'N2' WHERE item_code = '1100887400';

-- 3. 검증 SELECT (commit 전 row 수 확인)
DO $$
DECLARE
    described_count INTEGER;
    expected_count INTEGER := 13;
BEGIN
    SELECT COUNT(*) INTO described_count
    FROM checklist.material_master
    WHERE description IS NOT NULL;

    IF described_count != expected_count THEN
        RAISE EXCEPTION '[053b] description backfill 실패: 예상 % 건, 실제 % 건', expected_count, described_count;
    END IF;

    RAISE NOTICE '[053b] description backfill 성공: % 건 (MFC 13개 자재)', described_count;
END $$;

COMMIT;
