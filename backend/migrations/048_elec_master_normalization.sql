-- Sprint 60-BE: ELEC 체크리스트 마스터 데이터 모델 정규화
-- 신규 컬럼 3개: phase1_applicable, qi_check_required, remarks

-- Step 1: 컬럼 추가 (기본값으로 무중단 배포)
ALTER TABLE checklist.checklist_master
    ADD COLUMN IF NOT EXISTS phase1_applicable BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE checklist.checklist_master
    ADD COLUMN IF NOT EXISTS qi_check_required BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE checklist.checklist_master
    ADD COLUMN IF NOT EXISTS remarks TEXT;

COMMENT ON COLUMN checklist.checklist_master.phase1_applicable IS
    'Phase 1(1차 배선)에 적용되는 항목 여부. FALSE=1차 자동 N.A';
COMMENT ON COLUMN checklist.checklist_master.qi_check_required IS
    'GST 검수원(QI) 확인 필요 항목 여부. 성적서/UI 대기 표시용. check_elec_completion 판정 미반영';
COMMENT ON COLUMN checklist.checklist_master.remarks IS
    '개정일자/사유 등 이력 (엑셀 성적서 양식 반영)';

-- Step 2: ELEC 기존 데이터 분류 전환
-- 2a) JIG 그룹 전체 (WORKER 7 + QI 7 = 14 row)
UPDATE checklist.checklist_master
   SET phase1_applicable = FALSE,
       qi_check_required = TRUE
 WHERE category = 'ELEC'
   AND item_group = 'JIG 검사 및 특별관리 POINT';

-- 2b) 조립 검사 "버너 위 배선상태"
UPDATE checklist.checklist_master
   SET phase1_applicable = FALSE
 WHERE category = 'ELEC'
   AND item_group = '조립 검사'
   AND item_name = '버너 위 배선상태';

-- 2c) 기존 phase1_na=TRUE 항목 일괄 보정 (누락 방지)
UPDATE checklist.checklist_master
   SET phase1_applicable = FALSE
 WHERE category = 'ELEC' AND phase1_na = TRUE;
