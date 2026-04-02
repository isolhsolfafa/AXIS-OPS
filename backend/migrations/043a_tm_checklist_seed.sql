-- Sprint 52-A: TM 체크리스트 COMMON seed + scope 기본값 수정
-- 043a

-- ────────────────────────────────────────────────────────────────
-- 1. tm_checklist_scope 기본값 'all'로 변경
--    product_code별 관리는 표준화 완료 후 전환 (현재 100개+ → 목표 50개)
-- ────────────────────────────────────────────────────────────────
UPDATE admin_settings
SET setting_value = '"all"'
WHERE setting_key = 'tm_checklist_scope';

-- ────────────────────────────────────────────────────────────────
-- 2. UNIQUE 제약 변경: item_group 추가
--    기존: (product_code, category, item_name) → 동일 item_name이 다른 그룹에 존재 시 충돌
--    예: BURNER '클램프 체결' vs REACTOR '클램프 체결', BURNER 'SUS Fitting 조임 상태' vs EXHAUST 'SUS Fitting 조임 상태'
--    변경: (product_code, category, item_group, item_name)
-- ────────────────────────────────────────────────────────────────
ALTER TABLE checklist.checklist_master
    DROP CONSTRAINT IF EXISTS checklist_master_product_code_category_item_name_key;

ALTER TABLE checklist.checklist_master
    ADD CONSTRAINT checklist_master_product_category_group_name_key
    UNIQUE (product_code, category, item_group, item_name);

-- ────────────────────────────────────────────────────────────────
-- 3. item_type 컬럼 추가
--    CHECK = 체크 항목 (Pass/NA), INPUT = 입력 항목 (값 입력, MECH 전용)
--    기본값 'CHECK' → 기존 데이터(HOOKUP/PI/QI) 영향 없음
-- ────────────────────────────────────────────────────────────────
ALTER TABLE checklist.checklist_master
    ADD COLUMN IF NOT EXISTS item_type VARCHAR(10) DEFAULT 'CHECK';

COMMENT ON COLUMN checklist.checklist_master.item_type
    IS '항목 타입: CHECK=체크(Pass/NA), INPUT=입력(MECH 전용)';

-- ────────────────────────────────────────────────────────────────
-- 4. TM 체크리스트 15항목 공통 seed (기구 조립 검사 성적서 기준)
--    product_code = 'COMMON' → scope='all' 시 이 항목 사용
--    추후 MECH/ELEC도 동일 패턴: ('COMMON', 'MECH', ...), ('COMMON', 'ELEC', ...)
--    description: 기준/SPEC + 검사방법 통합 (Phase 1). 추후 컬럼 분리 가능.
-- ────────────────────────────────────────────────────────────────
INSERT INTO checklist.checklist_master
    (product_code, category, item_group, item_name, item_order, description, is_active)
VALUES
    -- BURNER (3항목)
    ('COMMON', 'TM', 'BURNER', 'SUS Fitting 조임 상태',       1, 'GAP GAUGE / 측수 검사', TRUE),
    ('COMMON', 'TM', 'BURNER', 'Gas Nozzle Cover 휨 여부',    2, 'Jig 활용 Center 확인 / 육안 검사', TRUE),
    ('COMMON', 'TM', 'BURNER', '클램프 체결',                  3, '조립 유동 여부 / 측수 검사', TRUE),
    -- REACTOR (4항목)
    ('COMMON', 'TM', 'REACTOR', 'Fitting 조임 상태',           1, '조립 유동 여부 / 측수 검사', TRUE),
    ('COMMON', 'TM', 'REACTOR', 'Tube 조립 상태',              2, '조립 유동 여부 / 측수 검사', TRUE),
    ('COMMON', 'TM', 'REACTOR', '클램프 체결',                  3, '조립 유동 여부 / 측수 검사', TRUE),
    ('COMMON', 'TM', 'REACTOR', 'Cir Line Tubing',            4, '조립 유동 여부 / 측수 검사', TRUE),
    -- EXHAUST (4항목)
    ('COMMON', 'TM', 'EXHAUST', 'Packing 조립 확인',           1, '적용 여부 / 육안 검사', TRUE),
    ('COMMON', 'TM', 'EXHAUST', 'Packing Guide 고정 확인',     2, '유동 여부 / 육안 검사', TRUE),
    ('COMMON', 'TM', 'EXHAUST', 'SUS Fitting 조임 상태',       3, 'GAP GAUGE / 측수 검사', TRUE),
    ('COMMON', 'TM', 'EXHAUST', 'BCW Nozzle Spray 방향',      4, '아래 방향 / 육안 검사', TRUE),
    -- TANK (4항목)
    ('COMMON', 'TM', 'TANK', 'Cir Pump Spec 확인',            1, '조립 도면과 현물 1:1 확인 / 육안 검사', TRUE),
    ('COMMON', 'TM', 'TANK', 'Flow Sensor Swirl Orifice',     2, 'Swirl Orifice 적용 조립 / 육안 검사', TRUE),
    ('COMMON', 'TM', 'TANK', 'Tank 내부 이물질 확인',          3, 'Tank 투시창 이용 확인 / 육안 검사', TRUE),
    ('COMMON', 'TM', 'TANK', '열교환기 Spec 확인',             4, '조립 도면과 현물 1:1 확인 / 육안 검사', TRUE)
ON CONFLICT (product_code, category, item_group, item_name) DO NOTHING;
