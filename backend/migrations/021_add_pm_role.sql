-- Sprint 24: PM (Production Manager) role 추가
-- GST 소속 생산관리자 역할
ALTER TYPE role_enum ADD VALUE IF NOT EXISTS 'PM';
