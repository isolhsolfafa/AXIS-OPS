# Task #1: DB Migration 스크립트 보완 계획

## 목표
001_create_workers.sql과 002_create_product_info.sql을 APP_PLAN_v4 스키마 설계에 맞게 보완

## 변경 사항

### 001_create_workers.sql

#### 1. approval_status ENUM 타입 추가
```sql
CREATE TYPE approval_status_enum AS ENUM ('pending', 'approved', 'rejected');
```

#### 2. workers 테이블 컬럼 수정/추가
- **제거**: `is_approved BOOLEAN`
- **추가**:
  - `approval_status approval_status_enum DEFAULT 'pending' NOT NULL`
  - `is_manager BOOLEAN DEFAULT FALSE NOT NULL`
  - `email_verified BOOLEAN DEFAULT FALSE NOT NULL`

#### 3. updated_at 자동 갱신 트리거 함수 추가
```sql
-- 범용 updated_at 갱신 함수
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- workers 테이블 트리거
CREATE TRIGGER update_workers_updated_at
    BEFORE UPDATE ON workers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

#### 4. email_verification 테이블 개선
- `token` → `verification_code` (VARCHAR(6)) - 6자리 숫자 코드
- 10분 만료는 expires_at 컬럼으로 이미 구현됨 (INSERT 시 NOW() + INTERVAL '10 minutes')

#### 5. 인덱스 추가
- `idx_workers_approval_status` - approval_status 필터링용
- `idx_email_verification_worker_id` - worker_id FK 조회 최적화

### 002_create_product_info.sql

#### 1. 컬럼 추가
- `location_qr_id VARCHAR(255)` - Location QR 등록 추적 (nullable)
- `mech_partner VARCHAR(255)` - 기구 협력사 (TMS 분기용, nullable)
- `module_outsourcing VARCHAR(255)` - 모듈 아웃소싱 (TMS 분기용, nullable)

#### 2. updated_at 트리거 추가
```sql
CREATE TRIGGER update_product_info_updated_at
    BEFORE UPDATE ON product_info
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```
(함수는 001에서 이미 생성됨)

#### 3. 인덱스 추가
- `idx_product_info_location_qr_id` - Location QR 조회용

## 파일 수정 순서
1. 001_create_workers.sql 전체 재작성
2. 002_create_product_info.sql 전체 재작성

## 검증 포인트
- [ ] approval_status enum 3가지 값 정의 확인
- [ ] is_manager, email_verified DEFAULT FALSE 확인
- [ ] verification_code VARCHAR(6) 확인
- [ ] location_qr_id, mech_partner, module_outsourcing nullable 확인
- [ ] updated_at 트리거 두 테이블 모두 적용 확인
- [ ] 모든 인덱스 생성 확인
- [ ] FK 제약조건 ON DELETE CASCADE 확인

## 참조 문서
- APP_PLAN_v4(26.02.16).md - Section 3.1 (핵심 테이블)
- CLAUDE.md - DB 규칙
