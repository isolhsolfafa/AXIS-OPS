-- Sprint 62-BE v2.2: Factory KPI 날짜 컬럼 스키마 정합 + partial index 3종
-- 배경: Railway prod DB에는 actual_ship_date / finishing_plan_end 컬럼이 이미 존재 (ETL 생성)이나,
--       backend/migrations/*.sql 에는 정식 DDL이 없어 test DB / 신규 환경에서 빠짐.
--       본 migration 으로 BE 의존 컬럼을 명시적으로 DDL 화 + 인덱스 동시 생성.
-- 실측 (2026-04-23 Prod): actual_ship_date NULL 35.3% / ship_plan_date NULL 0.1% / finishing_plan_end NULL 0.1%
-- CONCURRENTLY → migration_runner.py autocommit 모드 사용 (ENUM 패턴과 동일).

-- 1) 컬럼 정합 (Prod 기존 존재 → IF NOT EXISTS no-op, Test/신규 DB → 신규 생성)
ALTER TABLE plan.product_info
    ADD COLUMN IF NOT EXISTS actual_ship_date DATE;

ALTER TABLE plan.product_info
    ADD COLUMN IF NOT EXISTS finishing_plan_end DATE;

-- 2) Partial index 3종 (NULL 제외 → 공간·쓰기 비용 절감)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_info_actual_ship_date
    ON plan.product_info (actual_ship_date)
    WHERE actual_ship_date IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_info_ship_plan_date
    ON plan.product_info (ship_plan_date)
    WHERE ship_plan_date IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_info_finishing_plan_end
    ON plan.product_info (finishing_plan_end)
    WHERE finishing_plan_end IS NOT NULL;
