-- 제품 정보 테이블 생성
-- Sprint 1: QR 기반 제품 조회 + Location 추적 + TMS 분기 지원

CREATE TABLE IF NOT EXISTS product_info (
    id SERIAL PRIMARY KEY,
    qr_doc_id VARCHAR(255) UNIQUE NOT NULL,
    serial_number VARCHAR(255) UNIQUE NOT NULL,
    model VARCHAR(255) NOT NULL,
    production_date DATE NOT NULL,
    location_qr_id VARCHAR(255),
    mech_partner VARCHAR(255),
    module_outsourcing VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- updated_at 자동 갱신 트리거
-- (update_updated_at_column 함수는 001_create_workers.sql에서 생성됨)
CREATE TRIGGER update_product_info_updated_at
    BEFORE UPDATE ON product_info
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_product_info_qr_doc_id ON product_info(qr_doc_id);
CREATE INDEX IF NOT EXISTS idx_product_info_serial_number ON product_info(serial_number);
CREATE INDEX IF NOT EXISTS idx_product_info_model ON product_info(model);
CREATE INDEX IF NOT EXISTS idx_product_info_location_qr_id ON product_info(location_qr_id);
