-- 작업자 및 이메일 검증 테이블 생성
-- Sprint 1: 인증 + 관리자 승인 2단계 시스템

-- ENUM 타입 정의
CREATE TYPE role_enum AS ENUM ('MM', 'EE', 'TM', 'PI', 'QI', 'SI');
CREATE TYPE approval_status_enum AS ENUM ('pending', 'approved', 'rejected');

-- 작업자 테이블
CREATE TABLE IF NOT EXISTS workers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role role_enum NOT NULL,
    approval_status approval_status_enum DEFAULT 'pending' NOT NULL,
    email_verified BOOLEAN DEFAULT FALSE NOT NULL,
    is_manager BOOLEAN DEFAULT FALSE NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 이메일 검증 테이블 (6자리 코드, 10분 만료)
CREATE TABLE IF NOT EXISTS email_verification (
    id SERIAL PRIMARY KEY,
    worker_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    verification_code VARCHAR(6) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    verified_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- updated_at 자동 갱신 함수 (범용)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- workers 테이블 updated_at 트리거
CREATE TRIGGER update_workers_updated_at
    BEFORE UPDATE ON workers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_workers_email ON workers(email);
CREATE INDEX IF NOT EXISTS idx_workers_approval_status ON workers(approval_status);
CREATE INDEX IF NOT EXISTS idx_workers_role ON workers(role);
CREATE INDEX IF NOT EXISTS idx_email_verification_code ON email_verification(verification_code);
CREATE INDEX IF NOT EXISTS idx_email_verification_worker_id ON email_verification(worker_id);
