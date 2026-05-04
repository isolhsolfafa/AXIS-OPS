-- Sprint 63-BE: MECH 체크리스트 항목 seed
-- 등록일: 2026-04-29 / 수정일: 2026-05-01 (사용자 결정: INLET S/N L/R 8개 master 분리)
-- 양식: Excel '현황판_260108_MFC Maker추가 260223.xlsm' '공정진행현황-2행' 시트
-- 추출 CSV: AXIS-OPS/docs/mech_checklist_seed_extracted.csv
-- 선행 migration: 051_mech_checklist_extension.sql
--
-- 변경 이력:
--   v1 (2026-04-29): 69 항목 (INLET S/N master 4개 + sub_label spec)
--   v2 (2026-05-01): 73 항목 (INLET S/N master 8개로 분리 — 사용자 결정 옵션 A 변형)
--                     이유: tank_in_mech=TRUE 모델은 L/R default 8개 record per S/N 보장
--                           VIEW(대시보드) 에서 명확히 8개 구분 react 가능
--                           N/A 처리는 record 의 check_result='NA' 로 자동

INSERT INTO checklist.checklist_master
    (product_code, category, item_group, item_name, item_order, description,
     item_type, checker_role, scope_rule, trigger_task_id, phase1_applicable,
     qi_check_required, select_options, is_active, remarks)
VALUES
  ('COMMON', 'MECH', '3Way V/V', '3Way V/V Spec 확인', 1, '조립 도면과 현물 1:1 확인 / 육안 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', '3Way V/V', '볼트 체결', 2, '조립 유동 여부 / 촉수 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'WASTE GAS', '배관 도면 일치 여부', 1, '조립 도면과 현물 1:1 확인 / 육안 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'WASTE GAS', '클램프 체결', 2, '조립 유동 여부 / 촉수 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'INLET', '배관 도면 일치 여부', 1, '조립 도면과 현물 1:1 확인 / 육안 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'INLET', '배관 S/N 확인 - Left #1', 2, 'Left 측 #1 배관 (DRAGON 2중관 Bellows)', 'INPUT', 'WORKER', 'DRAGON', 'WASTE_GAS_LINE_2', TRUE, FALSE, NULL, TRUE, '※DRAGON 2중관 Bellows 적용 — 1대당 L/R 8개 S/N 입력 (사용자 결정 옵션 A 변형 2026-05-01). 후속 OCR 도입 예정.'),
  ('COMMON', 'MECH', 'INLET', '배관 S/N 확인 - Right #1', 3, 'Right 측 #1 배관 (DRAGON 2중관 Bellows)', 'INPUT', 'WORKER', 'DRAGON', 'WASTE_GAS_LINE_2', TRUE, FALSE, NULL, TRUE, '※DRAGON 2중관 Bellows 적용 — 1대당 L/R 8개 S/N 입력 (사용자 결정 옵션 A 변형 2026-05-01). 후속 OCR 도입 예정.'),
  ('COMMON', 'MECH', 'INLET', '배관 S/N 확인 - Left #2', 4, 'Left 측 #2 배관 (DRAGON 2중관 Bellows)', 'INPUT', 'WORKER', 'DRAGON', 'WASTE_GAS_LINE_2', TRUE, FALSE, NULL, TRUE, '※DRAGON 2중관 Bellows 적용 — 1대당 L/R 8개 S/N 입력 (사용자 결정 옵션 A 변형 2026-05-01). 후속 OCR 도입 예정.'),
  ('COMMON', 'MECH', 'INLET', '배관 S/N 확인 - Right #2', 5, 'Right 측 #2 배관 (DRAGON 2중관 Bellows)', 'INPUT', 'WORKER', 'DRAGON', 'WASTE_GAS_LINE_2', TRUE, FALSE, NULL, TRUE, '※DRAGON 2중관 Bellows 적용 — 1대당 L/R 8개 S/N 입력 (사용자 결정 옵션 A 변형 2026-05-01). 후속 OCR 도입 예정.'),
  ('COMMON', 'MECH', 'INLET', '배관 S/N 확인 - Left #3', 6, 'Left 측 #3 배관 (DRAGON 2중관 Bellows)', 'INPUT', 'WORKER', 'DRAGON', 'WASTE_GAS_LINE_2', TRUE, FALSE, NULL, TRUE, '※DRAGON 2중관 Bellows 적용 — 1대당 L/R 8개 S/N 입력 (사용자 결정 옵션 A 변형 2026-05-01). 후속 OCR 도입 예정.'),
  ('COMMON', 'MECH', 'INLET', '배관 S/N 확인 - Right #3', 7, 'Right 측 #3 배관 (DRAGON 2중관 Bellows)', 'INPUT', 'WORKER', 'DRAGON', 'WASTE_GAS_LINE_2', TRUE, FALSE, NULL, TRUE, '※DRAGON 2중관 Bellows 적용 — 1대당 L/R 8개 S/N 입력 (사용자 결정 옵션 A 변형 2026-05-01). 후속 OCR 도입 예정.'),
  ('COMMON', 'MECH', 'INLET', '배관 S/N 확인 - Left #4', 8, 'Left 측 #4 배관 (DRAGON 2중관 Bellows)', 'INPUT', 'WORKER', 'DRAGON', 'WASTE_GAS_LINE_2', TRUE, FALSE, NULL, TRUE, '※DRAGON 2중관 Bellows 적용 — 1대당 L/R 8개 S/N 입력 (사용자 결정 옵션 A 변형 2026-05-01). 후속 OCR 도입 예정.'),
  ('COMMON', 'MECH', 'INLET', '배관 S/N 확인 - Right #4', 9, 'Right 측 #4 배관 (DRAGON 2중관 Bellows)', 'INPUT', 'WORKER', 'DRAGON', 'WASTE_GAS_LINE_2', TRUE, FALSE, NULL, TRUE, '※DRAGON 2중관 Bellows 적용 — 1대당 L/R 8개 S/N 입력 (사용자 결정 옵션 A 변형 2026-05-01). 후속 OCR 도입 예정.'),
  ('COMMON', 'MECH', 'BURNER', 'SUS Fitting 조임 상태', 1, 'GAP GAUGE / 촉수 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'BURNER', 'Gas Nozzle Cover 휨 여부', 2, 'Jig 활용 Center 확인 / 육안 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'BURNER', '클램프 체결', 3, '조립 유동 여부 / 촉수 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'REACTOR', 'Fitting 조임 상태', 1, '조립 유동 여부 / 촉수 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'REACTOR', 'Tube 조립 상태', 2, '조립 유동 여부 / 촉수 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'REACTOR', '클램프 체결', 3, '조립 유동 여부 / 촉수 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'REACTOR', 'Cir Line Tubing', 4, '조립 유동 여부 / 촉수 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'GN2', 'Sol V/V Spec, Flow 방향', 1, '조립 도면과 현물 1:1 확인 / 육안 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'GN2', 'SUS Fitting 조임 상태', 2, 'GAP GAUGE / 촉수 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'GN2', 'Tube 조립 상태', 3, 'Tube In/Out, 넘버링 확인 / 육안, 촉수 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'GN2', 'Speed Controller 방향', 4, '조립 도면과 현물 1:1 확인 / 육안 검사', 'CHECK', 'WORKER', 'all', 'UTIL_LINE_1', TRUE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'GN2', 'Speed Controller 수량', 5, '조립 도면과 현물 1:1 확인 / 육안 검사', 'INPUT', 'WORKER', 'all', 'UTIL_LINE_1', TRUE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'GN2', 'MFC Spec :', 6, '', 'SELECT', 'WORKER', 'all', 'UTIL_LINE_2', TRUE, FALSE, '["MKS GE50A | 5 SLM | 0.5 MPa | 0.1-0.7 MPa", "Brooks 5850E | 10 SLM | 0.7 MPa | 0.2-0.9 MPa", "Horiba SEC-Z512 | 20 SLM | 1.0 MPa | 0.3-1.2 MPa"]', TRUE, NULL),
  ('COMMON', 'MECH', 'LNG', 'MFC Spec, Flow 방향', 1, '조립 도면과 현물 1:1 확인 / 육안 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'LNG', 'SUS Fitting 조임 상태', 2, 'GAP GAUGE / 촉수 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'LNG', 'Part 조립 상태', 3, 'Part In/Out, Flow 확인 / 육안 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'LNG', 'MFC Maker: ▶            MFC Spec: ▶Flow Rate            ▶Working Pressure            ▶Pressure Range', 4, '', 'SELECT', 'WORKER', 'all', 'UTIL_LINE_2', TRUE, FALSE, '["MKS GE50A | 5 SLM | 0.5 MPa | 0.1-0.7 MPa", "Brooks 5850E | 10 SLM | 0.7 MPa | 0.2-0.9 MPa", "Horiba SEC-Z512 | 20 SLM | 1.0 MPa | 0.3-1.2 MPa"]', TRUE, NULL),
  ('COMMON', 'MECH', 'O2', 'MFC Spec, Flow 방향', 1, '조립 도면과 현물 1:1 확인 / 육안 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'O2', 'SUS Fitting 조임 상태', 2, 'GAP GAUGE / 촉수 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'O2', 'Part 조립 상태', 3, 'Part In/Out, Flow 확인 / 육안 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'O2', 'MFC Maker: ▶            MFC Spec: ▶Flow Rate            ▶Working Pressure            ▶Pressure Range', 4, '', 'SELECT', 'WORKER', 'all', 'UTIL_LINE_2', TRUE, FALSE, '["MKS GE50A | 5 SLM | 0.5 MPa | 0.1-0.7 MPa", "Brooks 5850E | 10 SLM | 0.7 MPa | 0.2-0.9 MPa", "Horiba SEC-Z512 | 20 SLM | 1.0 MPa | 0.3-1.2 MPa"]', TRUE, NULL),
  ('COMMON', 'MECH', 'CDA', 'Sol V/V Spec, Flow 방향', 1, '조립 도면과 현물 1:1 확인 / 육안 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'CDA', 'SUS Fitting 조임 상태', 2, 'GAP GAUGE / 촉수 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'CDA', 'Part 조립 상태', 3, 'Part In/Out, Flow 확인 / 육안 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'CDA', 'Speed Controller 방향', 4, '조립 도면과 현물 1:1 확인 / 육안 검사', 'CHECK', 'WORKER', 'all', 'UTIL_LINE_1', TRUE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'CDA', 'Speed Controller 수량', 5, '조립 도면과 현물 1:1 확인 / 육안 검사', 'INPUT', 'WORKER', 'all', 'UTIL_LINE_1', TRUE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'CDA', 'MFC Maker: ▶            MFC Spec: ▶Flow Rate            ▶Working Pressure            ▶Pressure Range', 6, '', 'SELECT', 'WORKER', 'all', 'UTIL_LINE_2', TRUE, FALSE, '["MKS GE50A | 5 SLM | 0.5 MPa | 0.1-0.7 MPa", "Brooks 5850E | 10 SLM | 0.7 MPa | 0.2-0.9 MPa", "Horiba SEC-Z512 | 20 SLM | 1.0 MPa | 0.3-1.2 MPa"]', TRUE, NULL),
  ('COMMON', 'MECH', 'BCW', 'Flow Sensor Spec, 방향', 1, '조립 도면과 현물 1:1 확인 / 육안 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'BCW', 'Flow Sensor Spec :', 2, '', 'SELECT', 'WORKER', 'all', 'UTIL_LINE_2', TRUE, FALSE, '["KEYENCE FD-Q20C | 0.5-30 L/min | 0.5 MPa", "IFM SBY245 | 0.1-25 L/min | 1.0 MPa", "OMRON E8FC | 1-20 L/min | 0.7 MPa"]', TRUE, NULL),
  ('COMMON', 'MECH', 'BCW', '공압 밸브 Flow 방향', 3, 'A→IN B→OUT,넘버링 확인 / 육안 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'BCW', 'SUS Fitting 조임 상태', 4, 'GAP GAUGE / 촉수 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'BCW', 'Part 조립 상태', 5, 'Part In/Out, Flow 확인 / 육안 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'PCW-S', 'Flow Sensor Spec, 방향', 1, '조립 도면과 현물 1:1 확인 / 육안 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'PCW-S', 'Flow Sensor Spec :', 2, '', 'SELECT', 'WORKER', 'all', 'UTIL_LINE_2', TRUE, FALSE, '["KEYENCE FD-Q20C | 0.5-30 L/min | 0.5 MPa", "IFM SBY245 | 0.1-25 L/min | 1.0 MPa", "OMRON E8FC | 1-20 L/min | 0.7 MPa"]', TRUE, NULL),
  ('COMMON', 'MECH', 'PCW-S', '공압 밸브 Flow 방향', 3, 'A→IN B→OUT,넘버링 확인 / 육안 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'PCW-S', 'SUS Fitting 조임 상태', 4, 'GAP GAUGE / 촉수 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'PCW-S', 'Part 조립 상태', 5, 'Part In/Out, Flow 확인 / 육안 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'PCW-R', 'Flow Sensor Spec, 방향', 1, '조립 도면과 현물 1:1 확인 / 육안 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'PCW-R', 'Flow Sensor Spec :', 2, '', 'SELECT', 'WORKER', 'all', 'UTIL_LINE_2', TRUE, FALSE, '["KEYENCE FD-Q20C | 0.5-30 L/min | 0.5 MPa", "IFM SBY245 | 0.1-25 L/min | 1.0 MPa", "OMRON E8FC | 1-20 L/min | 0.7 MPa"]', TRUE, NULL),
  ('COMMON', 'MECH', 'PCW-R', '공압 밸브 Flow 방향', 3, 'A→IN B→OUT,넘버링 확인 / 육안 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'PCW-R', 'SUS Fitting 조임 상태', 4, 'GAP GAUGE / 촉수 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'PCW-R', 'Part 조립 상태', 5, 'Part In/Out, Flow 확인 / 육안 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'Exhaust', 'Packing 조립 확인', 1, '적용 여부 / 육안 검사', 'CHECK', 'WORKER', 'tank_in_mech', NULL, FALSE, FALSE, NULL, TRUE, 'Tank Ass''y 파트 — DRAGON/GALLANT/SWS 만 활성, 나머지 모델 disabled NA'),
  ('COMMON', 'MECH', 'Exhaust', 'Packing Guide 고정 확인', 2, '유동 여부 / 육안 검사', 'CHECK', 'WORKER', 'tank_in_mech', NULL, FALSE, FALSE, NULL, TRUE, 'Tank Ass''y 파트 — DRAGON/GALLANT/SWS 만 활성, 나머지 모델 disabled NA'),
  ('COMMON', 'MECH', 'Exhaust', 'SUS Fitting 조임 상태', 3, 'GAP GAUGE / 촉수 검사', 'CHECK', 'WORKER', 'tank_in_mech', NULL, FALSE, FALSE, NULL, TRUE, 'Tank Ass''y 파트 — DRAGON/GALLANT/SWS 만 활성, 나머지 모델 disabled NA'),
  ('COMMON', 'MECH', 'Exhaust', 'BCW Nozzle Spray 방향', 4, '아래 방향 / 육안 검사', 'CHECK', 'WORKER', 'tank_in_mech', NULL, FALSE, FALSE, NULL, TRUE, 'Tank Ass''y 파트 — DRAGON/GALLANT/SWS 만 활성, 나머지 모델 disabled NA'),
  ('COMMON', 'MECH', 'TANK', 'Cir Pump Spec 확인', 1, '조립 도면과 현물 1:1 확인 / 육안 검사', 'CHECK', 'WORKER', 'tank_in_mech', NULL, FALSE, FALSE, NULL, TRUE, 'Tank Ass''y 파트 — DRAGON/GALLANT/SWS 만 활성, 나머지 모델 disabled NA'),
  ('COMMON', 'MECH', 'TANK', 'Flow Sensor Swirl Orifice', 2, 'Swirl Orifice 적용 조립 / 육안 검사', 'CHECK', 'WORKER', 'tank_in_mech', NULL, FALSE, FALSE, NULL, TRUE, 'Tank Ass''y 파트 — DRAGON/GALLANT/SWS 만 활성, 나머지 모델 disabled NA'),
  ('COMMON', 'MECH', 'TANK', 'Tank 내부 이물질 확인', 3, 'Tank 투시창 이용 확인 / 육안 검사', 'CHECK', 'WORKER', 'tank_in_mech', NULL, FALSE, FALSE, NULL, TRUE, 'Tank Ass''y 파트 — DRAGON/GALLANT/SWS 만 활성, 나머지 모델 disabled NA'),
  ('COMMON', 'MECH', 'PU', '버너 및 이그저스트 위치', 1, '위치 별 방향, 넘버링 확인 / 육안, 촉수 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', '설비 상부', 'SUS Fitting 조임 상태', 1, 'GAP GAUGE / 촉수 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', '설비 상부', 'Drain Nut 조립 상태', 2, '조립 유동 여부 / 촉수 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', '설비 상부', '미사용 Hole 막음 처리', 3, '미사용 Hole 막음 확인 / 육안 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', '설비 전면부', 'Interface 스티커 부착', 1, 'LNG 가압 스티커 옆 부착 / 육안 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'H/J', '배관 H/J 완전체 조립', 1, 'Bypass, 3Way V/v, Inlet / 육안 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'H/J', '벨크로 체결 상태', 2, '벨크로 덜조임 및 이탈 확인 / 육안 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'H/J', '케이블 정리 및 체결', 3, '곡률 반경 및 체결 확인 / 육안 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL),
  ('COMMON', 'MECH', 'Quenching', 'Flow Sensor Spec, 방향', 1, '조립 도면과 현물 1:1 확인 / 육안 검사', 'CHECK', 'WORKER', 'tank_in_mech', NULL, FALSE, FALSE, NULL, TRUE, 'Tank Ass''y 파트 — DRAGON/GALLANT/SWS 만 활성, 나머지 모델 disabled NA'),
  ('COMMON', 'MECH', 'Quenching', 'Flow Sensor 위치 확인', 2, 'Quenching / Quenching T / 육안 검사', 'CHECK', 'WORKER', 'tank_in_mech', NULL, FALSE, FALSE, NULL, TRUE, 'Tank Ass''y 파트 — DRAGON/GALLANT/SWS 만 활성, 나머지 모델 disabled NA'),
  ('COMMON', 'MECH', '눈관리', '눈관리 스티커 위치', 1, '부착 상태 및 위치 확인 / 육안 검사', 'CHECK', 'WORKER', 'all', NULL, FALSE, FALSE, NULL, TRUE, NULL);


-- ────────────────────────────────────────────────────────────────
-- 검증 쿼리 (배포 후 실행)
-- ────────────────────────────────────────────────────────────────
-- SELECT COUNT(*) FROM checklist.checklist_master WHERE category='MECH';
-- 기대: 73 (v2: INLET S/N 8개로 분리)
--
-- SELECT scope_rule, COUNT(*) FROM checklist.checklist_master
-- WHERE category='MECH' GROUP BY scope_rule ORDER BY scope_rule;
-- 기대: all=56 / tank_in_mech=9 / DRAGON=8 (v2: INLET S/N 4→8)
--
-- SELECT trigger_task_id, COUNT(*) FROM checklist.checklist_master
-- WHERE category='MECH' GROUP BY trigger_task_id ORDER BY trigger_task_id;
-- 기대: NULL=54 / UTIL_LINE_1=4 / UTIL_LINE_2=7 / WASTE_GAS_LINE_2=8 (v2: INLET S/N 4→8)
--
-- SELECT phase1_applicable, COUNT(*) FROM checklist.checklist_master
-- WHERE category='MECH' GROUP BY phase1_applicable ORDER BY phase1_applicable;
-- 기대: TRUE=19 / FALSE=54 (v2: INLET S/N 4→8 추가로 phase1 TRUE 15→19)
--
-- SELECT item_type, COUNT(*) FROM checklist.checklist_master
-- WHERE category='MECH' GROUP BY item_type ORDER BY item_type;
-- 기대: CHECK=56 / INPUT=10 / SELECT=7 (v2: INPUT 6→10 — INLET S/N 4→8)
--
-- DRAGON L/R 정합 검증:
-- SELECT item_name, scope_rule, trigger_task_id FROM checklist.checklist_master
-- WHERE category='MECH' AND item_group='INLET' AND item_type='INPUT'
-- ORDER BY item_order;
-- 기대: Left #1, Right #1, Left #2, Right #2, ..., Left #4, Right #4 (8 row)
