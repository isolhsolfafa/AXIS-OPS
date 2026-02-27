-- Sprint 7+: defect 스키마 생성 (PDA_ML ETL 연동)
-- 불량 데이터 수집, ML 분석 결과, 통계 집계
-- Timezone: Asia/Seoul (KST)

BEGIN;

-- ============================================================
-- 1. defect 스키마 생성
-- ============================================================
CREATE SCHEMA IF NOT EXISTS defect;

-- ============================================================
-- 2. defect.defect_record — 불량 기록 원본 (Teams Excel → ETL)
-- ============================================================
CREATE TABLE IF NOT EXISTS defect.defect_record (
    id SERIAL PRIMARY KEY,
    serial_number VARCHAR(255) REFERENCES plan.product_info(serial_number) ON DELETE SET NULL,
    qr_doc_id VARCHAR(255) REFERENCES public.qr_registry(qr_doc_id) ON DELETE SET NULL,

    -- Teams Excel 원본 필드
    model_name VARCHAR(255) NOT NULL,              -- 제품명 (GAIA-I, DRAGON 등)
    component_name VARCHAR(255) NOT NULL,          -- 부품명
    defect_detail TEXT NOT NULL,                   -- 상세불량내용
    defect_category_major VARCHAR(100),            -- 대분류 (부품불량, 기구작업불량, 전장작업불량)
    defect_category_minor VARCHAR(100),            -- 중분류
    detection_stage VARCHAR(100),                  -- 검출단계 (가압검사, 제조품질검사)
    occurrence_date DATE NOT NULL,                 -- 발생일
    remarks TEXT,                                  -- 비고

    -- 메타데이터
    source_worksheet VARCHAR(100),                 -- 소스 워크시트 (가압 불량내역 / 제조품질 불량내역)
    source_file_name VARCHAR(255),                 -- Teams Excel 파일명
    etl_loaded_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- 중복 방지 (같은 S/N + 부품 + 날짜 + 상세내용)
    CONSTRAINT unique_defect_record UNIQUE(serial_number, component_name, occurrence_date, defect_detail)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_defect_record_sn ON defect.defect_record(serial_number);
CREATE INDEX IF NOT EXISTS idx_defect_record_model ON defect.defect_record(model_name);
CREATE INDEX IF NOT EXISTS idx_defect_record_component ON defect.defect_record(component_name);
CREATE INDEX IF NOT EXISTS idx_defect_record_date ON defect.defect_record(occurrence_date DESC);
CREATE INDEX IF NOT EXISTS idx_defect_record_category ON defect.defect_record(defect_category_major, defect_category_minor);
CREATE INDEX IF NOT EXISTS idx_defect_record_stage ON defect.defect_record(detection_stage);
CREATE INDEX IF NOT EXISTS idx_defect_record_etl ON defect.defect_record(etl_loaded_at DESC);

-- updated_at 트리거
CREATE TRIGGER update_defect_record_updated_at
    BEFORE UPDATE ON defect.defect_record
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- 3. defect.defect_keyword — 불량 키워드 분석 (ML 전처리)
-- ============================================================
CREATE TABLE IF NOT EXISTS defect.defect_keyword (
    id SERIAL PRIMARY KEY,
    defect_record_id INTEGER NOT NULL REFERENCES defect.defect_record(id) ON DELETE CASCADE,
    keyword VARCHAR(100) NOT NULL,                 -- 추출된 키워드 (MeCab 형태소)
    keyword_type VARCHAR(20),                      -- korean / english / mixed
    tfidf_score DECIMAL(10,6),                     -- TF-IDF 점수
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_defect_keyword_record ON defect.defect_keyword(defect_record_id);
CREATE INDEX IF NOT EXISTS idx_defect_keyword_word ON defect.defect_keyword(keyword);
CREATE INDEX IF NOT EXISTS idx_defect_keyword_score ON defect.defect_keyword(tfidf_score DESC);

-- ============================================================
-- 4. defect.ml_prediction — ML 예측 결과
-- ============================================================
CREATE TABLE IF NOT EXISTS defect.ml_prediction (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(255) NOT NULL,              -- 제품 모델명
    component_name VARCHAR(255) NOT NULL,          -- 부품명

    -- 예측 결과
    defect_probability DECIMAL(5,2) NOT NULL,      -- 예상 불량률 (%)
    production_weight DECIMAL(5,3),                -- 생산 가중치
    priority VARCHAR(20),                          -- CRITICAL / HIGH / MEDIUM / LOW / IMMEDIATE

    -- ML 메타데이터
    ml_model_version VARCHAR(50),                  -- 모델 버전 (v2.4.0)
    ml_accuracy DECIMAL(5,2),                      -- 모델 정확도 (%)
    prediction_date DATE NOT NULL,                 -- 예측 기준일

    -- 개선 제안
    suggestion TEXT,                               -- Pin Point 개선 제안
    top_keywords JSONB,                            -- 주요 키워드 배열 ["누수", "체결불량"]

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- 같은 날짜에 같은 모델+부품 조합은 1건만 (재예측 시 UPDATE)
    CONSTRAINT unique_ml_prediction UNIQUE(model_name, component_name, prediction_date)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_ml_prediction_model ON defect.ml_prediction(model_name);
CREATE INDEX IF NOT EXISTS idx_ml_prediction_component ON defect.ml_prediction(component_name);
CREATE INDEX IF NOT EXISTS idx_ml_prediction_prob ON defect.ml_prediction(defect_probability DESC);
CREATE INDEX IF NOT EXISTS idx_ml_prediction_priority ON defect.ml_prediction(priority);
CREATE INDEX IF NOT EXISTS idx_ml_prediction_date ON defect.ml_prediction(prediction_date DESC);

-- updated_at 트리거
CREATE TRIGGER update_ml_prediction_updated_at
    BEFORE UPDATE ON defect.ml_prediction
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- 5. defect.defect_statistics — 불량 통계 집계 (일별/월별)
-- ============================================================
CREATE TABLE IF NOT EXISTS defect.defect_statistics (
    id SERIAL PRIMARY KEY,
    aggregation_period VARCHAR(20) NOT NULL,       -- daily / weekly / monthly / yearly
    period_start_date DATE NOT NULL,               -- 집계 시작일
    period_end_date DATE NOT NULL,                 -- 집계 종료일

    -- 집계 필터 (NULL = 전체)
    model_name VARCHAR(255),                       -- 제품 모델명
    component_name VARCHAR(255),                   -- 부품명
    defect_category_major VARCHAR(100),            -- 대분류

    -- 통계 수치
    defect_count INTEGER NOT NULL DEFAULT 0,       -- 불량 건수
    inspection_count INTEGER,                      -- 검사 대수
    defect_rate DECIMAL(5,2),                      -- 불량률 (%)

    -- 메타데이터
    calculated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- 같은 기간 + 조건으로 1건만 (재집계 시 UPDATE)
    CONSTRAINT unique_defect_statistics UNIQUE(
        aggregation_period,
        period_start_date,
        COALESCE(model_name, ''),
        COALESCE(component_name, ''),
        COALESCE(defect_category_major, '')
    )
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_defect_stats_period ON defect.defect_statistics(aggregation_period, period_start_date DESC);
CREATE INDEX IF NOT EXISTS idx_defect_stats_model ON defect.defect_statistics(model_name);
CREATE INDEX IF NOT EXISTS idx_defect_stats_component ON defect.defect_statistics(component_name);
CREATE INDEX IF NOT EXISTS idx_defect_stats_rate ON defect.defect_statistics(defect_rate DESC);

-- ============================================================
-- 6. defect.component_priority — 부품별 우선순위 관리
-- ============================================================
CREATE TABLE IF NOT EXISTS defect.component_priority (
    id SERIAL PRIMARY KEY,
    component_name VARCHAR(255) UNIQUE NOT NULL,   -- 부품명

    -- 우선순위 설정
    priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM', -- CRITICAL / HIGH / MEDIUM / LOW / IMMEDIATE
    priority_reason TEXT,                          -- 우선순위 사유

    -- 개선 제안 (관리자 수정 가능)
    improvement_suggestion TEXT,                   -- 개선 방안
    action_items JSONB,                            -- 조치 사항 배열

    -- 실제 데이터 기반 메트릭
    total_defect_count INTEGER DEFAULT 0,          -- 전체 누적 불량 건수
    last_defect_date DATE,                         -- 최근 불량 발생일

    -- 메타데이터
    updated_by INTEGER REFERENCES public.workers(id) ON DELETE SET NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_component_priority_name ON defect.component_priority(component_name);
CREATE INDEX IF NOT EXISTS idx_component_priority_level ON defect.component_priority(priority);
CREATE INDEX IF NOT EXISTS idx_component_priority_count ON defect.component_priority(total_defect_count DESC);

-- updated_at 트리거
CREATE TRIGGER update_component_priority_updated_at
    BEFORE UPDATE ON defect.component_priority
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- 7. defect.dashboard_snapshot — 대시보드 스냅샷 (HTML CI/CD)
-- ============================================================
CREATE TABLE IF NOT EXISTS defect.dashboard_snapshot (
    id SERIAL PRIMARY KEY,
    dashboard_type VARCHAR(50) NOT NULL,           -- internal / pie_defect
    year INTEGER NOT NULL,                         -- 연도 (2025, 2026)

    -- 스냅샷 메타데이터
    html_file_url VARCHAR(500),                    -- GitHub Pages URL
    data_json JSONB,                               -- 대시보드 데이터 스냅샷

    -- 통계 요약
    total_defect_count INTEGER,                    -- 전체 불량 건수
    total_inspection_count INTEGER,                -- 전체 검사 대수
    overall_defect_rate DECIMAL(5,2),              -- 전체 불량률 (%)

    -- CI/CD 정보
    git_commit_hash VARCHAR(40),                   -- GitHub commit hash
    deployed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_dashboard_snapshot_type ON defect.dashboard_snapshot(dashboard_type, year);
CREATE INDEX IF NOT EXISTS idx_dashboard_snapshot_date ON defect.dashboard_snapshot(deployed_at DESC);

COMMIT;
