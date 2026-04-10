-- Sprint 57-C: ELEC 체크리스트 seed 전체 교체 + 스키마 확장
BEGIN;

-- 0. 스키마 확장
ALTER TABLE checklist.checklist_master
    ADD COLUMN IF NOT EXISTS select_options JSONB DEFAULT NULL;

ALTER TABLE checklist.checklist_record
    ADD COLUMN IF NOT EXISTS selected_value VARCHAR(255) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS input_value    TEXT         DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS qr_doc_id      VARCHAR(100) NOT NULL DEFAULT '';

-- UNIQUE 제약 변경: qr_doc_id 추가 (DUAL L/R 분리)
ALTER TABLE checklist.checklist_record
    DROP CONSTRAINT IF EXISTS checklist_record_sn_master_phase_key;
ALTER TABLE checklist.checklist_record
    ADD CONSTRAINT checklist_record_sn_master_phase_qr_key
    UNIQUE (serial_number, master_id, judgment_phase, qr_doc_id);

-- 1. 기존 ELEC master 삭제
DELETE FROM checklist.checklist_master
WHERE category = 'ELEC' AND product_code = 'COMMON';

-- 2. 올바른 31항목 재삽입
INSERT INTO checklist.checklist_master
    (product_code, category, item_group, item_name, item_order, description, is_active, checker_role, phase1_na)
VALUES
    ('COMMON', 'ELEC', 'PANEL 검사', '파트 사양확인 (라벨 포함)', 1, 'Part 및 Duct Label 도면상의 사양 일치', TRUE, 'WORKER', FALSE),
    ('COMMON', 'ELEC', 'PANEL 검사', '파트 고정위치', 2, '도면상의 위치 일치', TRUE, 'WORKER', FALSE),
    ('COMMON', 'ELEC', 'PANEL 검사', '파트 고정상태', 3, '유동 없을것', TRUE, 'WORKER', FALSE),
    ('COMMON', 'ELEC', 'PANEL 검사', 'NUMBERING 상태', 4, '표기오류 및 누락 없을것', TRUE, 'WORKER', FALSE),
    ('COMMON', 'ELEC', 'PANEL 검사', 'LOADLOCK 와셔', 5, 'ELCB, NFB, N/F-비스프링, M/C, T/B등 AC Line', TRUE, 'WORKER', FALSE),
    ('COMMON', 'ELEC', 'PANEL 검사', 'TUBE 종류 / 색상 (R, S, T, PE)', 6, 'TUBE 색상 조합 선택 후 판정', TRUE, 'WORKER', FALSE),
    ('COMMON', 'ELEC', 'PANEL 검사', 'Connector (JST / MOLEX 외), Penhole 작업 상태 검사', 7, 'LUG 압착부 끝단 1±1mm 노출', TRUE, 'WORKER', FALSE),
    ('COMMON', 'ELEC', 'PANEL 검사', 'MFC CONNECTOR확인', 8, '아날로그 모듈부 넘버링 확인 (D-SUB 쪽은 제외)', TRUE, 'WORKER', FALSE),
    ('COMMON', 'ELEC', 'PANEL 검사', 'FLOW SENSOR확인', 9, 'PIN번호, 색상, 넘버링 작업 후 즉시 1차 육안 확인', TRUE, 'WORKER', FALSE),
    ('COMMON', 'ELEC', 'PANEL 검사', 'I-Marking 상태 확인', 10, 'I-Marking 기준에 따른 작업 확인', TRUE, 'WORKER', FALSE),
    ('COMMON', 'ELEC', 'PANEL 검사', 'CLEANING 상태', 11, '제품 內 이물질 없을것', TRUE, 'WORKER', FALSE),
    ('COMMON', 'ELEC', '조립 검사', 'Surge Protector 장착 상태', 1, '지정 위치 정상 장착', TRUE, 'WORKER', FALSE),
    ('COMMON', 'ELEC', '조립 검사', 'BOLT 체결상태', 2, '풀림 및 유동 없을것', TRUE, 'WORKER', FALSE),
    ('COMMON', 'ELEC', '조립 검사', '버너 위 배선상태', 3, '탄화방지 작업 확인', TRUE, 'WORKER', TRUE),
    ('COMMON', 'ELEC', '조립 검사', '3M CONECTOR 압착상태', 4, '압착이 덜 되어 있거나 PIN이 빠지지 않을 것', TRUE, 'WORKER', FALSE),
    ('COMMON', 'ELEC', '조립 검사', 'E CONECTOR 체결상태', 5, '케이블 두께 기준 체결 정상 확인 및 도면 확인', TRUE, 'WORKER', FALSE),
    ('COMMON', 'ELEC', '조립 검사', '당김 검사', 6, '커넥터, WIRE 빠짐 없을것', TRUE, 'WORKER', FALSE),
    ('COMMON', 'ELEC', 'JIG 검사 및 특별관리 POINT', 'PUMP 배선 상태 CHECK', 1, 'PUMP 배선 체결 순서 및 상태 1차 작업 시 육안 확인', TRUE, 'WORKER', FALSE),
    ('COMMON', 'ELEC', 'JIG 검사 및 특별관리 POINT', 'MFC 배선 상태 CHECK', 2, '아날로그모듈로 들어가는 배선만 체결 순서 및 상태 확인', TRUE, 'WORKER', FALSE),
    ('COMMON', 'ELEC', 'JIG 검사 및 특별관리 POINT', 'IGNITION 및 M/T스크래퍼 CONECTOR 배선 CHECK', 3, 'CONECTOR 배선만 순서 확인', TRUE, 'WORKER', FALSE),
    ('COMMON', 'ELEC', 'JIG 검사 및 특별관리 POINT', 'AC LINE SHORT 검사', 4, 'AC LINE SHORT 확인', TRUE, 'WORKER', FALSE),
    ('COMMON', 'ELEC', 'JIG 검사 및 특별관리 POINT', 'DC LINE SHORT 검사', 5, 'DC LINE SHORT 및 체결 상태 확인', TRUE, 'WORKER', FALSE),
    ('COMMON', 'ELEC', 'JIG 검사 및 특별관리 POINT', 'MUX (ANALOG MODULE) ↔ PLC 배선 CHECK', 6, 'PIN번호 육안 확인', TRUE, 'WORKER', FALSE),
    ('COMMON', 'ELEC', 'JIG 검사 및 특별관리 POINT', 'DC SOL VALVE 다이오드 체결 상태 확인', 7, '체결 방법 및 CABLE 간섭 유/무 확인', TRUE, 'WORKER', FALSE),
    ('COMMON', 'ELEC', 'JIG 검사 및 특별관리 POINT', 'PUMP 배선 상태 CHECK (GST)', 8, 'PUMP 배선 체결 순서 및 상태 — GST 검증', TRUE, 'QI', FALSE),
    ('COMMON', 'ELEC', 'JIG 검사 및 특별관리 POINT', 'MFC 배선 상태 CHECK (GST)', 9, '아날로그모듈 배선 체결 — GST 검증', TRUE, 'QI', FALSE),
    ('COMMON', 'ELEC', 'JIG 검사 및 특별관리 POINT', 'IGNITION 및 M/T스크래퍼 CONECTOR (GST)', 10, 'CONECTOR 배선 순서 — GST 검증', TRUE, 'QI', FALSE),
    ('COMMON', 'ELEC', 'JIG 검사 및 특별관리 POINT', 'AC LINE SHORT 검사 (GST)', 11, 'AC LINE SHORT — GST 검증', TRUE, 'QI', FALSE),
    ('COMMON', 'ELEC', 'JIG 검사 및 특별관리 POINT', 'DC LINE SHORT 검사 (GST)', 12, 'DC LINE SHORT — GST 검증', TRUE, 'QI', FALSE),
    ('COMMON', 'ELEC', 'JIG 검사 및 특별관리 POINT', 'MUX (ANALOG MODULE) ↔ PLC (GST)', 13, 'PIN번호 — GST 검증', TRUE, 'QI', FALSE),
    ('COMMON', 'ELEC', 'JIG 검사 및 특별관리 POINT', 'DC SOL VALVE 다이오드 (GST)', 14, '체결 방법 및 CABLE 간섭 — GST 검증', TRUE, 'QI', FALSE);

-- 3. TUBE 색상 항목 SELECT 타입 설정
UPDATE checklist.checklist_master
SET item_type = 'SELECT',
    select_options = '["비가역 EYE CAP(갈, 검, 회, 녹)", "비가역 EYE CAP(적, 황, 청, 녹)", "비가역 EYE CAP(황, 녹, 적, 흑)"]'::jsonb
WHERE category = 'ELEC' AND product_code = 'COMMON'
  AND item_name = 'TUBE 종류 / 색상 (R, S, T, PE)';

COMMIT;
