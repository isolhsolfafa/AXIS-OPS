-- ============================================================
-- AXIS-OPS DB Schema 정리 (Sprint 5 사전 작업)
-- 실행 대상: Staging DB (PostgreSQL 15)
-- Timezone: Asia/Seoul (KST)
-- 실행 순서: 1 → 2 → 3 → 4 순서대로 실행
-- ============================================================

-- ============================================================
-- STEP 1: PDA 전용 테이블 삭제 (12개)
-- 스프레드시트 기반 PDA 시스템에서만 사용되었고
-- App 전환으로 불필요해진 테이블
-- ============================================================

BEGIN;

-- PDA 전용 — App 대체 완료 (3개)
DROP TABLE IF EXISTS info CASCADE;              -- → plan.product_info로 대체
DROP TABLE IF EXISTS worksheet CASCADE;         -- → app_task_details로 대체
DROP TABLE IF EXISTS task_summary CASCADE;      -- → work_completion_log로 대체

-- PDA 전용 — App에서 불필요 (9개)
DROP TABLE IF EXISTS progress_summary CASCADE;  -- → completion_status로 대체
DROP TABLE IF EXISTS progress_snapshots CASCADE;-- App 실시간 추적으로 대체
DROP TABLE IF EXISTS stats CASCADE;             -- App 실시간 쿼리로 대체
DROP TABLE IF EXISTS partner_stats CASCADE;     -- App 실시간 쿼리로 대체
DROP TABLE IF EXISTS additional_info CASCADE;   -- plan.product_info에 통합
DROP TABLE IF EXISTS ot_details CASCADE;        -- duration_minutes로 대체
DROP TABLE IF EXISTS treemap_data CASCADE;      -- App에서 실시간 생성
DROP TABLE IF EXISTS processing_log CASCADE;    -- 배치 처리 없어짐
DROP TABLE IF EXISTS processed_files CASCADE;   -- 파일 기반 처리 없어짐

COMMIT;

-- ============================================================
-- STEP 2: documents 테이블 유지 (기준 참조용)
-- PDA 13개 중 유일하게 유지 — 제품 메타데이터 참조
-- ============================================================

-- ============================================================
-- STEP 3: 스키마 구조 (3-tier)
-- ============================================================

-- DB 타임존 설정
ALTER DATABASE railway SET timezone = 'Asia/Seoul';

-- plan 스키마 — 생산 계획/일정 관리
CREATE SCHEMA IF NOT EXISTS plan;
COMMENT ON SCHEMA plan IS '생산 계획 스키마 - product_info, 일정 관리';

-- defect 스키마 — 불량 관리 (추후)
CREATE SCHEMA IF NOT EXISTS defect;
COMMENT ON SCHEMA defect IS '불량 관리 스키마 - 불량 분석, 추적, 리포트';

-- ============================================================
-- STEP 4: 현재 테이블 구조 요약
-- ============================================================

-- [plan 스키마]
--   plan.product_info          — 생산 메타데이터 (ETL 적재)
--     컬럼: id, serial_number, model, title_number, product_code,
--           sales_order, customer, line, quantity,
--           mech_partner, elec_partner, module_outsourcing,
--           prod_date, mech_start, mech_end,
--           elec_start, elec_end, module_start,
--           pi_start, qi_start, si_start, ship_plan_date,
--           location_qr_id, created_at, updated_at

-- [public 스키마]
--   qr_registry                — QR ↔ 제품 매핑
--     컬럼: id, qr_doc_id(UNIQUE), serial_number(UNIQUE→plan.product_info),
--           status(active/revoked/reissued), issued_at, revoked_at,
--           created_at, updated_at
--
--   workers                    — 작업자/관리자 계정
--   email_verification         — 이메일 인증 코드
--   app_task_details           — 작업 상세 (qr_doc_id FK→qr_registry)
--   completion_status          — 공정 완료 상태 (serial_number FK→qr_registry)
--   app_alert_logs             — 알림 로그
--   work_start_log             — 작업 시작 이력
--   work_completion_log        — 작업 완료 이력
--   location_history           — 위치 이력
--   offline_sync_queue         — 오프라인 동기화 큐
--   documents                  — PDA 기준 참조 (유지)

-- [defect 스키마]
--   (추후 추가 예정)

-- ============================================================
-- FK 체인:
--   app_task_details.qr_doc_id      → qr_registry.qr_doc_id
--   completion_status.serial_number → qr_registry.serial_number
--   qr_registry.serial_number       → plan.product_info.serial_number
--
-- 조회 흐름:
--   QR 스캔 → qr_registry(qr_doc_id)
--     → serial_number 획득
--     → plan.product_info JOIN (제품 상세)
--     → app_task_details 조회 (Task 목록)
-- ============================================================

-- 확인 쿼리
-- SELECT schemaname, tablename FROM pg_tables
-- WHERE schemaname IN ('public', 'plan', 'defect')
-- ORDER BY schemaname, tablename;

-- SELECT schema_name FROM information_schema.schemata
-- WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast');
