-- 제품 정보 + QR 매핑 테이블 생성
-- Schema: plan.product_info (생산 메타데이터) + public.qr_registry (QR ↔ 제품 매핑)
-- Timezone: Asia/Seoul (KST)

-- plan 스키마 생성
CREATE SCHEMA IF NOT EXISTS plan;

-- plan.product_info — 생산 메타데이터 (ETL로 Teams Excel에서 적재)
CREATE TABLE IF NOT EXISTS plan.product_info (
    id SERIAL PRIMARY KEY,
    serial_number VARCHAR(255) UNIQUE NOT NULL,
    model VARCHAR(255) NOT NULL,
    title_number VARCHAR(255),
    product_code VARCHAR(255),
    sales_order VARCHAR(255),
    customer VARCHAR(255),
    line VARCHAR(255),
    quantity VARCHAR(50) DEFAULT '1',
    mech_partner VARCHAR(255),
    elec_partner VARCHAR(255),
    module_outsourcing VARCHAR(255),
    prod_date DATE,                     -- 생산일 (= mech_start)
    mech_start DATE,                    -- MM 기구 시작
    mech_end DATE,                      -- MM 기구 종료
    elec_start DATE,                    -- EE 전장 시작
    elec_end DATE,                      -- EE 전장 종료
    module_start DATE,                  -- TM 모듈 시작
    pi_start DATE,                      -- PI 가압검사 시작
    qi_start DATE,                      -- QI 공정검사 시작
    si_start DATE,                      -- SI 마무리검사 시작
    ship_plan_date DATE,                -- 출하계획일
    location_qr_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- public.qr_registry — QR ↔ 제품 매핑 (ETL step2에서 qr_doc_id 발행)
CREATE TABLE IF NOT EXISTS public.qr_registry (
    id SERIAL PRIMARY KEY,
    qr_doc_id VARCHAR(255) UNIQUE NOT NULL,
    serial_number VARCHAR(255) UNIQUE NOT NULL
        REFERENCES plan.product_info(serial_number) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'active',
    issued_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- updated_at 자동 갱신 트리거
CREATE TRIGGER update_plan_product_info_updated_at
    BEFORE UPDATE ON plan.product_info
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_qr_registry_updated_at
    BEFORE UPDATE ON public.qr_registry
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_plan_pi_sn ON plan.product_info(serial_number);
CREATE INDEX IF NOT EXISTS idx_plan_pi_model ON plan.product_info(model);
CREATE INDEX IF NOT EXISTS idx_qr_reg_doc_id ON public.qr_registry(qr_doc_id);
CREATE INDEX IF NOT EXISTS idx_qr_reg_sn ON public.qr_registry(serial_number);
CREATE INDEX IF NOT EXISTS idx_qr_reg_status ON public.qr_registry(status);
