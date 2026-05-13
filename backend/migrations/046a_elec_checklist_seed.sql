-- Sprint 57: ELEC 체크리스트 31항목 seed
--
-- ⚠️ 2026-05-13 본 파일 내용 교체 (HOTFIX-ELEC-CHECKLIST-PLACEHOLDER-DEACTIVATE-20260513)
--    이전: placeholder 31항목 (PANEL/조립/JIG 검사 항목 1~7 등) — 실제 양식과 불일치
--    교체: 047_elec_checklist_seed_fix.sql 의 정식 31항목 (전장외주검사성적서.xlsx 기준)
--
-- 사고 trail (재발 방지 목적):
--   - 2026-04-10 047 적용 → 정식 31항목 운영 적용 (id 62-92)
--   - 2026-04-27 21:36 HOTFIX-08 (v2.10.10) 부수 효과 → 본 파일(구 placeholder seed) 자동 재실행
--   - 결과: 046a 의 placeholder 31항목이 운영 DB 에 신규 INSERT (id 94-124)
--           — item_name 이 047 와 달라 UNIQUE 제약(product_code,category,item_group,item_name) 충돌 회피
--   - 정정: migration 055 가 운영 DB id 94-124 deactivate
--   - 본 파일 교체로 향후 재실행되더라도 ON CONFLICT DO NOTHING 으로 신규 row 0 보장

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
    ('COMMON', 'ELEC', 'JIG 검사 및 특별관리 POINT', 'DC SOL VALVE 다이오드 (GST)', 14, '체결 방법 및 CABLE 간섭 — GST 검증', TRUE, 'QI', FALSE)
ON CONFLICT (product_code, category, item_group, item_name) DO NOTHING;
