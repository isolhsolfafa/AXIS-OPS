# G-axis App — Agent Teams 프로젝트

## 프로젝트 개요
GST 제조 현장 작업 관리 시스템. 스프레드시트 수동 입력 → 모바일 App 실시간 Push 전환.
Clean Cut 전략: 기존 PDA는 그대로 유지, App MVP를 별도 개발 후 테스트 완료 시 일괄 전환.

## 팀 구성 & 모델 설정

### 리드 에이전트 (Lead — 설계 조율)
- **모델**: Opus (claude-opus-4-6)
- **역할**: 전체 아키텍처 설계, 에이전트 간 조율, 코드 리뷰, 의사결정
- **모드**: Delegate 모드 (Shift+Tab) — 리드는 직접 코드 작성하지 않고 조율만 수행
- **권한**: 모든 파일 읽기 가능, 직접 수정은 하지 않음

### 워커 에이전트 (Workers — 구현/테스트)
- **모델**: Sonnet (claude-sonnet-4-5)
- **역할**: FE, BE, TEST 각각 담당 영역의 코드 구현
- **모드**: 사용자 승인 후 코드 수정 가능 (위임 모드)

### 위임 모드 규칙
1. 리드가 작업을 분배하고 워커에게 위임
2. 워커는 코드 변경 전 **반드시 사용자 승인** 필요
3. 파일 소유권 위반 시 즉시 중단
4. 스프린트 단위로 작업 진행 (현재 Sprint 1부터 시작)

## 참조 문서
- `APP_PLAN_v4(26.02.16).md` — **주 참조 문서**. App 설계/로직/API/DB 스키마 전체 정의
- `PROJECT_COMPREHENSIVE_ANALYSIS_2026(02.16).md` — ⚠️ **부분 참조만 허용** (아래 규칙 준수)
  - ✅ 참조 가능: 섹션 1.1(비즈니스 목표), 섹션 6(기술 스택), 섹션 14(브랜드/로고)
  - ❌ 절대 참조 금지: 섹션 8.4(시간 계산 로직 — calculate_working_hours 사용 금지), 섹션 13(하이브리드 전환 분석 — Clean Cut으로 폐기), 섹션 2/4/5/9/11(구 전략/일정 — 전부 구버전)
  - ❌ 이 문서의 `info` 테이블, `google_doc_id`, `worksheet` 참조 금지 → 반드시 `product_info`, `qr_doc_id` 사용

## 기술 스택
- **Frontend**: Flutter 3.x (Web Build + PWA) + Riverpod + SQLite (오프라인) + dio (HTTP)
- **Backend**: Flask 3.x + PostgreSQL 15 + Flask-SocketIO (WebSocket) + psycopg2
- **Test**: pytest (BE) + flutter_test (FE) + integration tests

## 배포 전략: PWA 우선 (Web-First)
- **1단계 (현재)**: Flutter Web Build → PWA로 배포 (앱스토어 심사 없이 즉시 배포)
- **2단계 (안정화 후)**: 동일 코드로 iOS/Android 네이티브 빌드 → 앱스토어 정식 심사

### PWA 구현 필수사항
- `web/manifest.json` — 앱 이름, 아이콘, 테마 색상 설정
- `web/index.html` — Service Worker 등록 (오프라인 캐싱)
- 앱 아이콘: 192x192, 512x512 PNG 필요
- HTTPS 필수 (PWA 설치 조건)
- 카메라(QR 스캔): `html5-qrcode` JS interop 사용 (web/index.html에 스크립트 추가 + dart:js_interop 래핑)

### FE 에이전트 주의사항
- `flutter build web` 기준으로 개발
- 네이티브 전용 플러그인 사용 금지 (웹 미지원 플러그인 X)
- QR 스캔: `mobile_scanner` 사용 금지 → `html5-qrcode` JS interop만 사용 (iOS Safari PWA 호환성 보장)
- 로컬 저장소: SQLite 대신 `shared_preferences` 또는 `hive` (웹 호환)
- 반응형 UI: 모바일 브라우저 기준 설계 (375px ~ 428px 너비)

## 핵심 규칙 (모든 에이전트 공통)

### DB 규칙
- `qr_doc_id` 사용 (`google_doc_id` 사용 금지)
- `plan.product_info` 테이블 사용 — plan 스키마 (`info` 테이블 사용 금지)
- `qr_registry` 테이블로 QR ↔ 제품 매핑 (qr_doc_id는 product_info가 아닌 qr_registry에 존재)
- 제품 조회 시: `qr_registry JOIN plan.product_info ON serial_number`
- `duration = completed_at - started_at` (calculate_working_hours 함수 사용 금지)
- Staging DB 기준 개발 (PDA Production DB 절대 건드리지 않음)
- DB 타임존: `Asia/Seoul` (KST)
- **운영 데이터 보존 규칙**: 테스트 실행 시 아래 테이블 데이터는 반드시 백업/복원 (DELETE/TRUNCATE 금지)
  - `workers` — 실서비스 계정 (conftest.py 백업/복원 ✅)
  - `hr.worker_auth_settings` — PIN 설정 (conftest.py 백업/복원 ✅)
  - `hr.partner_attendance` — 출퇴근 기록 (conftest.py 백업/복원 ✅)
  - `qr_registry` — QR↔제품 매핑 (conftest.py 백업/복원 ✅)
  - `plan.product_info` — 생산 메타데이터 (conftest.py 백업/복원 ✅)
  - 테스트 cleanup fixture는 `WHERE created_at >= test_start` 조건으로 테스트 생성 데이터만 삭제
  - **최종 목표**: 사내 WAS DB로 마이그레이션 → production/test DB 분리 운영

### DB 스키마 구조 (Staging DB — 3-Tier)
```
plan 스키마 (생산관리 — ETL 적재):
  product_info — 생산 메타데이터 (S/N, model, 일정, 협력사)

public 스키마 (App 운영 — 14개 테이블):
  qr_registry          — QR ↔ 제품 매핑 브릿지 (qr_doc_id, serial_number, status)
  workers              — 작업자/관리자 계정
  email_verification   — 이메일 인증 코드
  app_task_details     — 작업 상세 (FK→qr_registry.qr_doc_id)
  completion_status    — 공정 완료 상태 (FK→qr_registry.serial_number)
  app_alert_logs       — 알림 로그
  work_start_log       — 작업 시작 이력
  work_completion_log  — 작업 완료 이력
  location_history     — 위치 이력
  offline_sync_queue   — 오프라인 동기화 큐
  product_bom          — BOM 목록 (Phase 2)
  bom_checklist_log    — BOM 검증 (Phase 2)
  documents            — PDA 기준 참조용 유지

defect 스키마 (추후 — 불량 분석, 추적, 리포트)
```

**FK 체인:**
```
app_task_details.qr_doc_id      → qr_registry.qr_doc_id
completion_status.serial_number → qr_registry.serial_number
qr_registry.serial_number      → plan.product_info.serial_number
```

**조회 흐름:**
```
QR 스캔 → qr_registry(qr_doc_id) → serial_number 획득
  → plan.product_info JOIN (제품 상세)
  → app_task_details 조회 (Task 목록)
```

- PDA 전용 테이블 11개 삭제 완료 (worksheet, task_summary, stats 등)
- DB 타임존: `Asia/Seoul` (KST)

### ⚠️ DB 테이블 정확한 컬럼 명세 (Staging DB 기준 — 반드시 준수)
> **주의**: 아래 컬럼명은 Staging DB에 실제 존재하는 이름입니다.
> migration SQL, Python model, Flask route 모두 이 컬럼명을 정확히 사용해야 합니다.

#### 1. workers (11컬럼) ✅ 코드 일치
```sql
id SERIAL PK, name VARCHAR(255) NOT NULL, email VARCHAR(255) UNIQUE NOT NULL,
password_hash VARCHAR(255) NOT NULL, role role_enum NOT NULL (MM/EE/TM/PI/QI/SI),
approval_status approval_status_enum DEFAULT 'pending' (pending/approved/rejected),
email_verified BOOLEAN DEFAULT FALSE, is_manager BOOLEAN DEFAULT FALSE,
is_admin BOOLEAN DEFAULT FALSE,
created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
```
- 트리거: update_workers_updated_at ✅
- Python model: Worker dataclass ✅

#### 2. email_verification (6컬럼) ⚠️ Python dataclass 없음
```sql
id SERIAL PK, worker_id INTEGER FK→workers(id) NOT NULL,
verification_code VARCHAR(6) UNIQUE NOT NULL, expires_at TIMESTAMPTZ NOT NULL,
verified_at TIMESTAMPTZ, created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
```
- Python model: ❌ dataclass 없음 (Dict 반환) → Sprint 5에서 생성 필요

#### 3. plan.product_info (plan 스키마) ✅ 코드 일치
```sql
-- plan 스키마에 위치 (public 아님!)
id SERIAL PK,
serial_number VARCHAR(255) UNIQUE NOT NULL,
model VARCHAR(255) NOT NULL,
title_number VARCHAR(255),
product_code VARCHAR(255),
sales_order VARCHAR(255),
customer VARCHAR(255),
line VARCHAR(255),
quantity VARCHAR(255) DEFAULT '1',
mech_partner VARCHAR(255),
elec_partner VARCHAR(255),
module_outsourcing VARCHAR(255),
prod_date DATE,                  -- 생산일 (= mech_start)
mech_start DATE,                 -- 기구 시작일
mech_end DATE,                   -- 기구 종료일
elec_start DATE,                 -- 전장 시작일
elec_end DATE,                   -- 전장 종료일
module_start DATE,               -- 모듈(TM) 시작일
pi_start DATE,                   -- PI 가압검사 시작일
qi_start DATE,                   -- QI 공정검사 시작일
si_start DATE,                   -- SI 마무리검사 시작일
ship_plan_date DATE,             -- 출하계획일
location_qr_id VARCHAR(255),
created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
```
- ⚠️ `qr_doc_id`는 이 테이블에 없음 → `qr_registry` 테이블에서 관리
- 트리거: update_product_info_updated_at ✅
- Python model: ProductInfo dataclass ✅ (qr_registry JOIN으로 조회)
- BE model: `_BASE_JOIN_QUERY`로 qr_registry + plan.product_info JOIN

#### 4. qr_registry (public 스키마) ✅ 코드 일치
```sql
id SERIAL PK,
qr_doc_id VARCHAR(255) UNIQUE NOT NULL,     -- DOC_{serial_number}
serial_number VARCHAR(255) UNIQUE NOT NULL,  -- FK→plan.product_info
status VARCHAR(20) DEFAULT 'active',         -- active / revoked / reissued
issued_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
revoked_at TIMESTAMPTZ,
created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
```
- ETL에서 `plan.product_info` INSERT 후 `qr_registry` INSERT
- App 진입점: QR 스캔 → qr_doc_id로 조회

#### 5. app_task_details (14컬럼) ✅ 코드 일치
```sql
id SERIAL PK, worker_id INTEGER FK→workers(id) NOT NULL,
serial_number VARCHAR(255) NOT NULL,
qr_doc_id VARCHAR(255) FK→qr_registry(qr_doc_id) NOT NULL,
task_category VARCHAR(50) NOT NULL, task_id VARCHAR(100) NOT NULL,
task_name VARCHAR(255) NOT NULL, started_at TIMESTAMPTZ, completed_at TIMESTAMPTZ,
duration_minutes INTEGER, is_applicable BOOLEAN DEFAULT TRUE,
location_qr_verified BOOLEAN DEFAULT FALSE,
created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
UNIQUE (serial_number, task_category, task_id)
```
- 트리거: update_app_task_details_updated_at ✅
- Python model: TaskDetail dataclass ✅

#### 6. completion_status (11컬럼) ✅ 코드 일치
```sql
serial_number VARCHAR(255) PK FK→qr_registry(serial_number),
mm_completed BOOLEAN DEFAULT FALSE, ee_completed BOOLEAN DEFAULT FALSE,
tm_completed BOOLEAN DEFAULT FALSE, pi_completed BOOLEAN DEFAULT FALSE,
qi_completed BOOLEAN DEFAULT FALSE, si_completed BOOLEAN DEFAULT FALSE,
all_completed BOOLEAN DEFAULT FALSE, all_completed_at TIMESTAMPTZ,
created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
```
- Python model: CompletionStatus dataclass ✅

#### 7. app_alert_logs (11컬럼) ⚠️ read_at 누락
```sql
id SERIAL PK, alert_type alert_type_enum NOT NULL,
serial_number VARCHAR(255), qr_doc_id VARCHAR(255),
triggered_by_worker_id INTEGER FK→workers(id), target_worker_id INTEGER FK→workers(id),
target_role VARCHAR(50), message TEXT NOT NULL, is_read BOOLEAN DEFAULT FALSE,
created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
-- ❌ read_at TIMESTAMPTZ 추가 필요 (APP_PLAN 스펙: is_read + read_at)
```
- 트리거: ❌ update_app_alert_logs_updated_at 없음 → 추가 필요
- Python model: AlertLog dataclass ⚠️ read_at 필드 추가 필요

#### 8. work_start_log (9컬럼) ⚠️ Python 모델 없음
```sql
id SERIAL PK, task_id INTEGER FK→app_task_details(id) NOT NULL,
worker_id INTEGER FK→workers(id) NOT NULL, serial_number VARCHAR(255) NOT NULL,
qr_doc_id VARCHAR(255) NOT NULL, task_category VARCHAR(50) NOT NULL,
task_id_ref VARCHAR(100) NOT NULL, task_name VARCHAR(255) NOT NULL,
started_at TIMESTAMPTZ NOT NULL, created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
```
- Python model: ❌ 없음 → Sprint 5에서 생성 필요

#### 9. work_completion_log (10컬럼) ⚠️ Python 모델 없음
```sql
id SERIAL PK, task_id INTEGER FK→app_task_details(id) NOT NULL,
worker_id INTEGER FK→workers(id) NOT NULL, serial_number VARCHAR(255) NOT NULL,
qr_doc_id VARCHAR(255) NOT NULL, task_category VARCHAR(50) NOT NULL,
task_id_ref VARCHAR(100) NOT NULL, task_name VARCHAR(255) NOT NULL,
completed_at TIMESTAMPTZ NOT NULL, duration_minutes INTEGER,
created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
```
- Python model: ❌ 없음 → Sprint 5에서 생성 필요

#### 10. location_history (6컬럼) 🔴 모델 빈 껍데기
```sql
id SERIAL PK, worker_id INTEGER FK→workers(id) NOT NULL,
latitude DECIMAL(10,8) NOT NULL, longitude DECIMAL(11,8) NOT NULL,
recorded_at TIMESTAMPTZ NOT NULL, created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
```
- Python model: ❌ from_db_row()가 `pass` → Sprint 5에서 완성 필요

#### 11. offline_sync_queue (9컬럼) ⚠️ Python 모델 없음
```sql
id SERIAL PK, worker_id INTEGER FK→workers(id) NOT NULL,
operation VARCHAR(50) NOT NULL, table_name VARCHAR(100) NOT NULL,
record_id VARCHAR(255), data JSONB,
synced BOOLEAN DEFAULT FALSE, synced_at TIMESTAMPTZ,
created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
```
- Python model: ❌ 없음 → Sprint 5에서 생성 필요

#### 12-13. product_bom, bom_checklist_log — Phase 2 (미구현)

### Admin 계정 정책
관리자 계정은 **Migration Seed 방식**으로 사전 등록 (회원가입/이메일인증/승인 절차 우회):
```sql
-- 006_sprint6_schema_changes.sql 내 포함 (ON CONFLICT DO NOTHING → Sprint 간 초기화 방지)
INSERT INTO workers (name, email, password_hash, role, company,
                     approval_status, email_verified, is_manager, is_admin)
VALUES ('관리자', 'dkkim1@gst-in.com', '<pbkdf2_hash>',
        'ADMIN', 'GST', 'approved', TRUE, TRUE, TRUE)
ON CONFLICT (email) DO NOTHING;
```
- **⚠️ Admin Seed는 반드시 migration SQL 내에 존재해야 함** (Sprint 간 초기화 방지)
- Admin은 일반 회원가입 플로우 불필요 (DB 직접 등록)
- Admin 로그인 시 이메일 인증/승인 체크 건너뜀 (`is_admin = TRUE`면 freepass)
- 비밀번호: `Gst@dmin2026!` (werkzeug pbkdf2:sha256 해시)
- BE auth_service.py의 login 함수에서 admin 분기 처리:
  ```python
  if not worker.is_admin:
      # 일반 사용자만 이메일 인증/승인 체크
      if not worker.email_verified: return 403 (EMAIL_NOT_VERIFIED)
      if worker.approval_status == 'pending': return 403 (APPROVAL_PENDING)
      if worker.approval_status == 'rejected': return 403 (APPROVAL_REJECTED)
  ```

### 로그인 에러 코드 → 화면 분기 정책
| BE 에러 코드 | HTTP | FE 동작 |
|---|---|---|
| `INVALID_CREDENTIALS` | 401 | 로그인 화면에 에러 메시지 표시 |
| `EMAIL_NOT_VERIFIED` | 403 | 로그인 화면에 에러 메시지 표시 |
| `APPROVAL_PENDING` | 403 | **ApprovalPendingScreen으로 네비게이션** |
| `APPROVAL_REJECTED` | 403 | 로그인 화면에 에러 메시지 표시 |

- api_service.dart의 403 처리에서 서버 에러 코드를 `[ERROR_CODE] message` 형식으로 보존
- login_screen.dart에서 에러 메시지에 `APPROVAL_PENDING` 포함 시 ApprovalPendingScreen으로 이동

### 이메일 인증 설정
- 인증 메일 발송 대상 도메인: `@gst-in.com`, `@naver.com`, `@gmail.com`
- SMTP 설정 (.env 파일) — KT Biz Office SSL(465) 사용:
  ```
  SMTP_HOST=jmp.ktbizoffice.com
  SMTP_PORT=465
  SMTP_USER=dkkim1@gst-in.com
  SMTP_PASSWORD=<그룹웨어 비밀번호>
  SMTP_FROM_NAME=G-AXIS
  SMTP_FROM_EMAIL=dkkim1@gst-in.com
  ```
- SMTP 포트 분기: 465=SMTP_SSL 직접 연결, 587=STARTTLS (auth_service.py에서 자동 분기)
- 인증 코드: 6자리 숫자, 유효기간 10분
- 이메일 도메인 제한 없음 (사용자가 직접 입력)
- ⚠️ Rate Limiting: 동일 이메일 시간당 5회 발송 제한 (DoS 방지, `_check_email_rate_limit()`)
- ⚠️ Subject 인코딩: `email.header.Header`로 UTF-8 명시 (한글 깨짐 방지)

### 환경변수 운영 가이드
- **로컬 개발**: `backend/.env` 파일 사용 (`.gitignore`에 포함 — git에 올리지 않음)
- **배포 (Staging/Prod)**: Railway Variables에 동일 키-값 설정 → 배포 시 자동 주입
- **CI/CD (추후)**: GitHub Secrets → GitHub Actions에서 사용
- 테스트 시 Railway에 배포된 Flask API로 테스트 (Railway Variables 환경)
- 필수 환경변수 목록:
  ```
  DATABASE_URL          — PostgreSQL 연결 문자열
  JWT_SECRET_KEY        — Access Token 서명 키
  JWT_REFRESH_SECRET_KEY — Refresh Token 서명 키 (Access와 반드시 분리)
  SMTP_HOST             — smtp.gmail.com
  SMTP_PORT             — 587
  SMTP_USER             — 발송용 Gmail 계정
  SMTP_PASSWORD         — Gmail 앱 비밀번호
  SMTP_FROM_NAME        — G-AXIS
  SMTP_FROM_EMAIL       — noreply@gst-in.com
  ```

### API 규칙
- JWT 인증 필수
- 에러 응답: `{"error": "ERROR_CODE", "message": "설명"}`
- 응답시간 목표: < 500ms

### 코드 스타일
- Python: type hints 사용, docstring 필수
- Dart: Riverpod 패턴, null safety
- 한국어 주석 허용
- 커밋 메시지: 영어 (conventional commits)

---

## 에이전트 팀 구성

### Agent 1: FE (Frontend — Flutter App)
**담당**: Flutter 앱 전체 (UI, 상태관리, 로컬DB, API 통신)

**소유 파일**:
```
frontend/**
```

**주요 업무**:
- 회원가입/로그인 화면 (이메일 인증 포함)
- QR 스캔 → 제품 조회 화면
- Task 시작/완료 터치 UI
- 공정 누락 검증 팝업 (PI/QI/SI)
- 관리자 알림 수신 화면
- WebSocket 연결 (실시간 동기화)
- 오프라인 동기화 (SQLite + offline_sync_queue)

**절대 수정 금지**: `backend/**`, `tests/backend/**`

---

### Agent 2: BE (Backend — Flask API)
**담당**: Flask API 서버 전체 (인증, 작업관리, 알림, WebSocket)

**소유 파일**:
```
backend/**
```

**주요 업무**:
- JWT 인증 미들웨어
- 회원가입/로그인 API (workers + email_verification)
- 작업 시작/완료 API (app_task_details + completion_status)
- 공정 검증 로직 (MECH/ELEC 완료 체크)
- 관리자 알림 API (app_alert_logs)
- WebSocket 이벤트 (Flask-SocketIO)
- DB 마이그레이션 스크립트

**인증/권한 데코레이터** (`backend/app/middleware/jwt_auth.py`):
| 데코레이터 | 용도 | 선행 조건 | 추가 시점 |
|---|---|---|---|
| `@jwt_required` | JWT Bearer 토큰 검증 → g.worker_id, g.worker_email, g.worker_role 설정 | 없음 | Sprint 1 |
| `@admin_required` | is_admin=True 검증 (관리자 전용 API) | @jwt_required 선행 필수 | Sprint 1 |
| `@manager_or_admin_required` | is_admin=True OR is_manager=True 검증 (관리자/협력사 매니저 공용 API) | @jwt_required 선행 필수 | Sprint 6 |

사용 예시:
```python
@app.route('/api/admin/tasks/<int:task_id>/force-close', methods=['PUT'])
@jwt_required
@manager_or_admin_required
def force_close_task(task_id: int):
    ...
```

**절대 수정 금지**: `frontend/**`, `tests/frontend/**`

---

### Agent 3: TEST (테스트 담당)
**담당**: 전체 테스트 코드 작성 및 실행

**소유 파일**:
```
tests/**
```

**주요 업무**:
- Backend API 단위 테스트 (pytest)
- Frontend 위젯 테스트 (flutter_test)
- 통합 테스트 (API → DB 플로우)
- 공정 검증 로직 테스트 (누락 감지, 알림)
- 비정상 duration 검증 테스트
- 테스트 데이터 fixtures

**절대 수정 금지**: `backend/app/**` (소스코드), `frontend/lib/**` (소스코드)
**읽기 가능**: 모든 파일 (테스트 작성을 위해)

---

## 프로젝트 디렉토리 구조

```
AXIS-OPS/
├── CLAUDE.md                              # 이 파일
├── APP_PLAN_v4(26.02.16).md              # App 설계 문서
├── PROJECT_COMPREHENSIVE_ANALYSIS_2026(02.16).md  # 종합 분석 문서
│
├── frontend/                              # [FE 소유]
│   ├── lib/
│   │   ├── main.dart
│   │   ├── models/                        # 데이터 모델
│   │   │   ├── worker.dart
│   │   │   ├── task_item.dart
│   │   │   ├── product_info.dart
│   │   │   └── alert_log.dart
│   │   ├── services/                      # API/DB 서비스
│   │   │   ├── api_service.dart
│   │   │   ├── auth_service.dart
│   │   │   ├── websocket_service.dart
│   │   │   └── local_db_service.dart
│   │   ├── providers/                     # Riverpod 상태관리
│   │   │   ├── auth_provider.dart
│   │   │   ├── task_provider.dart
│   │   │   └── alert_provider.dart
│   │   ├── screens/                       # UI 화면
│   │   │   ├── auth/
│   │   │   │   ├── login_screen.dart
│   │   │   │   ├── register_screen.dart
│   │   │   │   └── verify_email_screen.dart
│   │   │   ├── home/
│   │   │   │   └── home_screen.dart
│   │   │   ├── task/
│   │   │   │   ├── task_management_screen.dart
│   │   │   │   └── task_detail_screen.dart
│   │   │   ├── qr/
│   │   │   │   └── qr_scan_screen.dart
│   │   │   └── admin/
│   │   │       ├── admin_dashboard.dart
│   │   │       └── worker_approval_screen.dart
│   │   ├── widgets/                       # 재사용 위젯
│   │   │   ├── process_alert_popup.dart
│   │   │   ├── task_card.dart
│   │   │   └── completion_badge.dart
│   │   └── utils/
│   │       ├── constants.dart
│   │       └── validators.dart
│   ├── pubspec.yaml
│   └── README.md
│
├── backend/                               # [BE 소유]
│   ├── app/
│   │   ├── __init__.py                    # Flask app factory
│   │   ├── config.py                      # 설정 (DB URL, JWT secret 등)
│   │   ├── models/                        # SQLAlchemy 모델 (or raw SQL)
│   │   │   ├── __init__.py
│   │   │   ├── worker.py
│   │   │   ├── product_info.py
│   │   │   ├── task_detail.py
│   │   │   ├── completion_status.py
│   │   │   ├── alert_log.py
│   │   │   └── location_history.py
│   │   ├── routes/                        # API 엔드포인트
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                    # /api/auth/*
│   │   │   ├── work.py                    # /api/app/work/*
│   │   │   ├── product.py                 # /api/app/product/*
│   │   │   ├── alert.py                   # /api/app/alerts/*
│   │   │   ├── admin.py                   # /api/admin/*
│   │   │   └── sync.py                    # /api/app/sync
│   │   ├── services/                      # 비즈니스 로직
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py
│   │   │   ├── task_service.py
│   │   │   ├── process_validator.py       # 공정 누락 검증
│   │   │   ├── alert_service.py
│   │   │   └── duration_validator.py      # 비정상 duration 검증
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── jwt_auth.py
│   │   │   └── audit_log.py
│   │   └── websocket/
│   │       ├── __init__.py
│   │       └── events.py                  # SocketIO 이벤트 핸들러
│   ├── migrations/                        # DB 마이그레이션
│   │   ├── 001_create_workers.sql
│   │   ├── 002_create_product_info.sql
│   │   ├── 003_create_task_tables.sql
│   │   ├── 004_create_alert_tables.sql
│   │   └── 005_create_sync_tables.sql
│   ├── requirements.txt
│   ├── run.py                             # 서버 실행 진입점
│   └── README.md
│
└── tests/                                 # [TEST 소유]
    ├── conftest.py                        # 공통 fixtures
    ├── backend/
    │   ├── test_auth.py                   # 인증 API 테스트
    │   ├── test_work_api.py               # 작업 API 테스트
    │   ├── test_process_validator.py      # 공정 검증 테스트
    │   ├── test_duration_validator.py     # duration 검증 테스트
    │   ├── test_alert_service.py          # 알림 서비스 테스트
    │   └── test_websocket.py              # WebSocket 테스트
    ├── frontend/
    │   ├── test_task_management.dart       # Task UI 테스트
    │   ├── test_auth_flow.dart            # 인증 플로우 테스트
    │   └── test_offline_sync.dart         # 오프라인 동기화 테스트
    ├── integration/
    │   ├── test_full_workflow.py           # 전체 워크플로우 (가입→작업→완료)
    │   ├── test_process_check_flow.py     # 공정 검증 플로우
    │   └── test_concurrent_work.py        # 동시 작업 테스트
    └── fixtures/
        ├── sample_workers.json
        ├── sample_products.json
        └── sample_tasks.json
```

## 작업 우선순위

### Sprint 1: 인증 + DB 기반 (2주)
1. **BE**: DB 마이그레이션 스크립트 (5개 테이블) → JWT 인증 → 회원가입/로그인 API
2. **FE**: 회원가입/로그인/이메일인증 화면 → API 연동
3. **TEST**: 인증 API 테스트 → 이메일 인증 플로우 테스트

### Sprint 2: Task 핵심 플로우 (2주)
1. **BE**: 제품조회 API → 작업 시작/완료 API → completion_status 업데이트
2. **FE**: QR 스캔 화면 → Task 목록 → 시작/완료 터치 UI
3. **TEST**: 작업 API 테스트 → Task 플로우 통합 테스트

### Sprint 3: 공정 검증 + 알림 (2주)
1. **BE**: 공정 누락 검증 로직 → 알림 API → WebSocket 이벤트
2. **FE**: 공정 누락 팝업 → 관리자 알림 화면 → WebSocket 연결
3. **TEST**: 공정 검증 테스트 → 알림 테스트 → WebSocket 테스트

### Sprint 4: 관리자 + 오프라인 (2주) ✅ 완료

### Sprint 5: 보안 + PWA + 이메일 + 잔여 모델 (1주) ✅ 완료 (보완 필요)
> ✅ DB 스키마 사전 작업 완료: plan.product_info + qr_registry 분리, 컬럼명 간소화, ETL 동기화, PDA 테이블 삭제
1. **BE (migration SQL 동기화 + 누락 모델)**: ✅ 완료
   - `003_create_task_tables.sql` FK 수정: `qr_registry(qr_doc_id)`, `qr_registry(serial_number)` ✅
   - 누락 Python 모델 3개 생성 ✅ / location_history 완성 ✅ / alert_log read_at ✅ / worker EmailVerification ✅
2. **BE (보안 + 이메일)**: ✅ 완료
   - .env 분리 ✅ / SMTP 연동 ✅ / Refresh Token ✅
3. **FE**: PWA 빌드 성공 ✅
4. **TEST**: 54개 테스트 구현 (test_models 25 + test_email 12 + test_refresh_token 17)

#### ⚠️ Sprint 5 보완 필요 사항 (Sprint 6 전에 반드시 완료):
1. **product_info.py — ProductInfo dataclass 15개 컬럼 추가**: 현재 10개 필드만 있음. plan.product_info 25개 컬럼 중 title_number~ship_plan_date 15개 누락. `_BASE_JOIN_QUERY` SELECT절도 동기화 필요
2. **SMTP Subject UTF-8 인코딩**: `email.header.Header`로 한글 Subject 인코딩 명시 (일부 메일 클라이언트 깨짐 방지)
3. **이메일 Rate Limiting 추가**: 시간당 5회 제한 (DoS 방지). 메모리 기반 `_check_email_rate_limit()` 함수 추가
4. **test_refresh_token.py 5개 테스트 보충**: PROGRESS.md 22개 주장 vs 실제 17개. access↔refresh 혼용 방지 등 5개 추가 필요
5. **PROGRESS.md 테스트 카운트 정정**: test_email 8→12, test_refresh_token 22→17(보충 후 22), 합계 55→59

### Sprint 6: Task 재설계 + 네이밍 변경 + Admin 옵션 (1~2주)
> ⚠️ 네이밍 변경: MM→MECH, EE→ELEC (전체 코드베이스 22+ 파일 영향)
> ⚠️ Task 재설계: 기존 27개(MM19+EE8) → 15개(MECH7+ELEC6+TMS2)
1. **BE (Phase A — 네이밍 + DB 변경)**:
   - `role_enum` 변경: MM→MECH, EE→ELEC, ADMIN 추가 (migration SQL)
   - `workers` 테이블에 `company VARCHAR(50)` 컬럼 추가
   - `model_config` 테이블 신설 (model_prefix, has_docking, is_tms, tank_in_mech)
   - `admin_settings` 테이블 신설 (key-value 구조, heating_jacket_enabled, phase_block_enabled 등)
   - 기존 코드 MM→MECH, EE→ELEC 전수 교체 (auth_service, task_service, process_validator, completion_status, work.py)
2. **BE (Phase B — Task Seed 재설계)**:
   - Task 템플릿 15개 정의 (MECH 7 + ELEC 6 + TMS 2)
   - `initialize_product_tasks(serial_number, qr_doc_id, model_name)` 구현
   - model_config 기반 분기: GAIA(docking), DRAGON(tank_in_mech), 기타
   - company 기반 Task 필터링 API 구현
   - 알림 트리거 2개: TMS_TANK_COMPLETE → MECH 관리자, TANK_DOCKING_COMPLETE → ELEC 관리자
3. **FE**:
   - 회원가입 화면: company 드롭다운 추가 → role 자동 필터링
   - MM→MECH, EE→ELEC 네이밍 전수 교체 (worker.dart, home_screen.dart, register_screen.dart 등)
   - Admin 옵션 화면 신설 (heating_jacket, phase_block 토글)
4. **TEST**: 기존 테스트 MM→MECH, EE→ELEC 교체 → Task Seed 테스트 → model_config 분기 테스트

### Sprint 7: 전체 플로우 검증 + 통합 테스트 (⚠️ 신규 기능 없음)
1. **BE**: 테스트용 모델별 제품 데이터 Seed fixture 추가 (GAIA/DRAGON/GALLANT/MITHAS/SDS/SWS 6종) + GET /api/app/product 엔드포인트 테스트 보완 + 발견 버그 수정
2. **FE**: flutter build web 에러 0건 확인 + 화면 플로우 코드 점검
3. **TEST**:
   - 빈 껍데기 통합 테스트 3개 파일 전부 실제 구현 (`assert False` 0건)
   - test_product_api.py 신규 (제품 조회 + Task Seed 자동 생성 검증)
   - test_model_task_seed_integration.py 신규 (6개 모델 혼합 Task Seed 검증)
   - test_company_task_filtering.py 신규 (모든 company-worker 조합 필터링 검증)
   - test_scheduler_integration.py 신규 (미종료 알림 시간 경과 시뮬레이션)
   - 기존 단위 테스트 regression 0건

### Sprint 8: Admin API 보완 + UX 개선 + 버그 수정
1. **BE**: Admin 누락 API 5개 구현 + 비밀번호 찾기 API (forgot-password, reset-password) + 토큰 만료 변경 (access 2시간, refresh 30일) + worker_id NULL 대응
2. **FE**: admin_options_screen API 연동 + 로그인 유지 (401→자동 refresh→retry) + 마지막 화면 복원 (shared_preferences route 저장) + 비밀번호 찾기 화면 + worker_id/created_at null 방어
3. **TEST**: Admin API 테스트 12개+ + 비밀번호 찾기 테스트 8개+ + 토큰 만료 확인 + regression 0건

### Sprint 9: Pause/Resume + 근무시간 관리 (예정)
1. **BE**:
   - `POST /api/app/work/pause` + `POST /api/app/work/resume` API
   - `work_pause_log` 테이블 (task_detail_id, worker_id, paused_at, resumed_at)
   - duration 계산 시 중지 시간 자동 차감
   - 휴게/식사시간 강제 중지 스케줄러 (admin_settings에서 시간 관리)
   - 기본값: 오전휴게 10:00-10:20, 점심 11:20-12:20, 오후휴게 15:00-15:20, 저녁 17:00-18:00
2. **FE**:
   - Task 상세: 일시정지/재개 버튼 + 상태 표시 (진행중/일시정지)
   - 휴게시간 시작 시 알림 팝업 + 자동 강제 pause
   - 휴게시간 종료 시 알림 → 수동 재개
   - 저녁시간: "무시하고 계속" 옵션 (작업시간에 포함)
   - Admin 옵션: 휴게/식사시간 변경 설정 UI
3. **TEST**: pause/resume 플로우 + 휴게시간 자동 중지 + duration 차감 검증

### Sprint 10+: Railway 배포 + PWA (production 준비)
- Railway 배포 설정 (Procfile, railway.toml, eventlet, CORS, DATABASE_URL 호환, PORT 대응)
- PWA 설치 가능 상태 (manifest.json, Service Worker, 아이콘)
- API_BASE_URL 환경 분기 (constants.dart)

---

## 고도화 로드맵

### Phase A: 로그인 ID + 생체인증
| 항목 | 설명 |
|------|------|
| **login_id 컬럼 추가** | `workers` 테이블에 `login_id VARCHAR UNIQUE` 추가. 회원가입 시 이메일(인증용) + 로그인 ID(간편 접속용) 입력. 로그인은 ID + 비밀번호만으로 처리 |
| **BE 로그인 분기** | `auth_service.login()` — email 또는 login_id로 조회: `get_worker_by_email(identifier) OR get_worker_by_login_id(identifier)` |
| **FE 로그인 화면** | 이미 `EMAIL / ID` 입력 가능 (validateLoginId 적용 완료). login_id 지원 시 BE만 수정하면 연동 가능 |
| **생체인증 (지문/FaceID)** | 네이티브 빌드 전환 후 `local_auth` 패키지 적용. 최초 1회 ID/PW 로그인 → 생체 등록 → 이후 생체만으로 JWT 발급. PWA에서는 WebAuthn API로 대체 가능 |

### Phase B: 협력사 근태 관리 (MECH, ELEC, TM 전용)

> **핵심**: 생산 추적(qr_doc_id, location_qr_id)과 **완전 분리**.
> **대상**: 협력사(MECH/ELEC/TM)만 해당. 사내직원(PI/QI/SI)은 회사 그룹웨어로 근태 관리 → App 근태 불필요.
> **스키마**: `hr` 스키마 신설 — `public`은 제조 운영 전용으로 유지.

#### 5-Tier 스키마 아키텍처 (고도화 후)
```
plan       → 생산 메타데이터 (ETL 적재: product_info)
app        → 제조 운영 (workers, tasks, alerts, qr_registry, work_logs...)
checklist  → 공정별 체크리스트 (Hook-Up, BOM 검수 등)
hr         → 인사/인증/근태 (PIN 인증: 전체, 출퇴근: 협력사, GST 확장 예약)
defect     → 불량 분석 (QMS 연동)
```

| 항목 | 설명 |
|------|------|
| **PIN 간편 로그인** | 전체 사용자(GST + 협력사) 대상. 앱 재진입 시 4자리 PIN으로 빠른 로그인 |
| **근태 입력 화면** | 협력사 계정 로그인 시 홈 화면에 출근/퇴근 버튼 표시. PIN 로그인 ≠ 출근 |
| **생체 인증 (추후)** | 지문 / FaceID — 메뉴만 표시, 추후 WebAuthn API로 구현 |
| **PIN/생체 등록 시점** | **최초 로그인 후 개인 설정 화면**에서 등록 (회원가입 시 X) |
| **Admin 대시보드** | 협력사 출퇴근 현황 실시간 조회, 지각/결근 집계, 월간 리포트 |

#### DB 설계 (`hr` 스키마)
```sql
CREATE SCHEMA IF NOT EXISTS hr;

-- ① 간편 인증 설정 (전체 사용자 — GST + 협력사)
CREATE TABLE hr.worker_auth_settings (
    worker_id INTEGER PRIMARY KEY REFERENCES public.workers(id),
    pin_hash VARCHAR(255),               -- 4자리 PIN bcrypt 해시
    biometric_enabled BOOLEAN DEFAULT FALSE,
    biometric_type VARCHAR(20),          -- 'fingerprint' / 'face_id' (추후)
    pin_fail_count INTEGER DEFAULT 0,    -- PIN 연속 실패 횟수
    pin_locked_until TIMESTAMPTZ,        -- 3회 실패 시 잠금 시각
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ② 협력사 출퇴근 기록 (company != 'GST')
CREATE TABLE hr.partner_attendance (
    id SERIAL PRIMARY KEY,
    worker_id INTEGER NOT NULL REFERENCES public.workers(id),
    check_type VARCHAR(3) NOT NULL,      -- 'in' / 'out'
    check_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    method VARCHAR(10) DEFAULT 'button', -- 'button' / 'pin' / 'fingerprint' / 'face_id'
    note TEXT,                           -- 비고 (지각 사유 등)
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_partner_att_worker ON hr.partner_attendance(worker_id, check_time DESC);

-- ③ GST 사내직원 근태 (추후 확장 예약 — 그룹웨어 연동 or RDB 동기화)
CREATE TABLE hr.gst_attendance (
    id SERIAL PRIMARY KEY,
    worker_id INTEGER NOT NULL REFERENCES public.workers(id),
    check_type VARCHAR(3) NOT NULL,      -- 'in' / 'out'
    check_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source VARCHAR(20) DEFAULT 'manual', -- 'manual' / 'groupware_sync' / 'api'
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_gst_att_worker ON hr.gst_attendance(worker_id, check_time DESC);
```

> **역할 분류**: MECH/ELEC/TM = 협력사 (작업) | PI/QI/SI = 사내직원 (인스펙션, 그룹웨어 근태)

### Phase C: BOM 검증 (기존 Phase 2)
| 항목 | 설명 |
|------|------|
| **product_bom** | 제품별 BOM(자재 목록) 관리 |
| **bom_checklist_log** | 자재 검수 체크리스트 기록 |

---

## Task Seed 데이터 (MECH 7 + ELEC 6 + TMS 2 = 15개)

> ⚠️ 기존 27개(MM19+EE8)에서 15개로 간소화 (2026-02-20 확정)

### model_config (모델별 분기 설정)
```
| model_prefix | has_docking | is_tms | tank_in_mech | 설명 |
|-------------|------------|--------|-------------|------|
| GAIA        | TRUE       | TRUE   | FALSE       | TMS(M) 탱크 별도 → MECH 도킹 |
| DRAGON      | FALSE      | FALSE  | TRUE        | 한 협력사가 탱크+MECH 일괄 |
| GALLANT     | FALSE      | FALSE  | FALSE       | 탱크/도킹 없음 |
| MITHAS      | FALSE      | FALSE  | FALSE       | 탱크/도킹 없음 |
| SDS         | FALSE      | FALSE  | FALSE       | 탱크/도킹 없음 |
| SWS         | FALSE      | FALSE  | FALSE       | 탱크/도킹 없음 |
```
- DRAGON: tank~mech 일괄 처리. 주로 TMS(M)이지만 **반드시 product_info.mech_partner 확인**
- product_info 단위 override 가능하도록 설계

### workers.company (7개 — product_info 실제 값과 동일)
```
| company  | role       | 매칭 컬럼              | 매칭 값 |
|----------|-----------|----------------------|--------|
| FNI      | MECH      | mech_partner         | FNI    |
| BAT      | MECH      | mech_partner         | BAT    |
| TMS(M)   | MECH      | module_outsourcing   | TMS    |
| TMS(E)   | ELEC      | elec_partner         | TMS    |
| P&S      | ELEC      | elec_partner         | P&S    |
| C&A      | ELEC      | elec_partner         | C&A    |
| GST      | PI,QI,SI,ADMIN | —              | —      |
```
- TMS(M): TMS task(Tank Module, 가압검사) + mech_partner 매칭 시 MECH task도 표시
- TMS(E): elec_partner = 'TMS'인 제품의 ELEC task만 표시

### MECH (기구) — 7개
```
| # | task_id          | task_name          | phase         | docking 모델 | non-docking | 비고 |
|---|------------------|--------------------|---------------|-------------|-------------|------|
| 1 | WASTE_GAS_LINE_1 | Waste Gas LINE 1   | PRE_DOCKING   | ✅          | ❌          |      |
| 2 | UTIL_LINE_1      | Util LINE 1        | PRE_DOCKING   | ✅          | ❌          |      |
| 3 | TANK_DOCKING     | Tank Docking       | DOCKING       | ✅          | ❌          |      |
| 4 | WASTE_GAS_LINE_2 | Waste Gas LINE 2   | POST_DOCKING  | ✅          | ❌          |      |
| 5 | UTIL_LINE_2      | Util LINE 2        | POST_DOCKING  | ✅          | ❌          |      |
| 6 | HEATING_JACKET   | Heating Jacket     | PRE_DOCKING   | ⚙️          | ⚙️          | admin 옵션 (default false) |
| 7 | SELF_INSPECTION  | 자주검사 ⭐         | FINAL         | ✅          | ✅          |      |
```
모델별 분기:
- **GAIA** (has_docking): 1~5, 7 활성 + phase 구분 적용
- **DRAGON** (tank_in_mech): 1~5 활성 + TANK_DOCKING만 비활성
- **기타**: 자주검사만 활성, 1~5 비활성
- **HEATING_JACKET**: `admin_settings.heating_jacket_enabled`로 제어 (default false)

### ELEC (전장) — 6개
```
| # | task_id       | task_name        | phase         |
|---|--------------|------------------|---------------|
| 1 | PANEL_WORK   | 판넬 작업         | PRE_DOCKING   |
| 2 | CABINET_PREP | 케비넷 준비 작업   | PRE_DOCKING   |
| 3 | WIRING       | 배선 포설         | PRE_DOCKING   |
| 4 | IF_1         | I.F 1            | PRE_DOCKING   |
| 5 | IF_2         | I.F 2            | POST_DOCKING  |
| 6 | INSPECTION   | 자주검사 (검수) ⭐ | FINAL         |
```
전 모델 공통: 6개 전부 활성
- GAIA: I.F 1 후 도킹 완료 대기 → I.F 2 (phase_block 옵션으로 제어, default false)
- 기타: I.F 1 → I.F 2 순차 (phase 무의미)

### TMS (모듈) — 2개 (GAIA 전용)
```
| # | task_id        | task_name    |
|---|---------------|-------------|
| 1 | TANK_MODULE    | Tank Module  |
| 2 | PRESSURE_TEST  | 가압검사 ⭐   |
```
GAIA만 생성 (is_tms = TRUE)

### admin_settings 테이블
```sql
CREATE TABLE admin_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value JSONB NOT NULL DEFAULT 'false',
    description TEXT,
    updated_by INTEGER REFERENCES workers(id),
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
-- 초기값
INSERT INTO admin_settings (setting_key, setting_value, description) VALUES
('heating_jacket_enabled', 'false', 'Heating Jacket task 활성화 여부'),
('phase_block_enabled', 'false', 'Tank Docking 완료 전 POST_DOCKING task 차단 여부');
```

### 알림 트리거 (MVP)
```
TMS 가압검사 완료 → alert_type: TMS_TANK_COMPLETE → 수신: 해당 제품 MECH 관리자 (GAIA만)
MECH Tank Docking 완료 → alert_type: TANK_DOCKING_COMPLETE → 수신: 해당 제품 ELEC 관리자 (GAIA만)
```

### Task Seed 자동 초기화 트리거
- **QR 스캔 시 자동 실행**: `GET /api/app/product/{qr_doc_id}` → 제품 조회 후 `initialize_product_tasks()` 자동 호출
- `ON CONFLICT DO NOTHING` — 이미 Task가 존재하면 무시 (멱등성 보장)
- 실패 시 non-blocking (제품 조회는 정상 반환, 로그만 기록)
- Admin 수동 초기화도 유지: `POST /api/admin/products/initialize-tasks`

### Task Seed 초기화 로직
```python
def initialize_product_tasks(serial_number: str, qr_doc_id: str, model_name: str):
    config = get_model_config(model_name)  # prefix 매칭

    # MECH Tasks (7개)
    for t in get_templates('MECH'):
        is_applicable = True
        if t.task_id == 'HEATING_JACKET':
            is_applicable = get_admin_setting('heating_jacket_enabled', False)
        elif t.is_docking_required:
            if config['has_docking']:
                is_applicable = True           # GAIA: 전부 활성
            elif config['tank_in_mech']:
                is_applicable = (t.task_id != 'TANK_DOCKING')  # DRAGON: DOCKING만 비활성
            else:
                is_applicable = False          # 기타: 비활성
        create_task(serial_number, qr_doc_id, 'MECH', t, is_applicable)

    # ELEC Tasks (6개) — 전 모델 공통
    for t in get_templates('ELEC'):
        create_task(serial_number, qr_doc_id, 'ELEC', t, True)

    # TMS Tasks (2개) — GAIA만
    if config['is_tms']:
        for t in get_templates('TMS'):
            create_task(serial_number, qr_doc_id, 'TMS', t, True)
```

### Task 필터링 로직 (작업자 화면)
```python
# TMS(M) 작업자가 보는 Task:
#   1. module_outsourcing = 'TMS' → TMS task (Tank Module, 가압검사)
#   2. mech_partner 매칭 → 해당 제품의 MECH task (DRAGON 등 일괄 처리 케이스)
#
# FNI/BAT 작업자: mech_partner = 'FNI'/'BAT' → MECH task만
# TMS(E)/P&S/C&A 작업자: elec_partner 매칭 → ELEC task만
# GST 작업자: PI/QI/SI role 기반 → 검사 task
```

### 멀티 작업자 동시 작업 로직
> 같은 Task에 여러 작업자(A, B, C)가 서로 다른 시간에 시작/종료 가능

`app_task_details` 확장 컬럼:
```sql
duration_minutes INTEGER,          -- man-hour (A+B+C 개별 duration 합산)
elapsed_minutes INTEGER,           -- 실경과시간 (최초 시작 ~ 마지막 종료)
worker_count INTEGER DEFAULT 1,    -- 투입 인원
force_closed BOOLEAN DEFAULT FALSE,-- 강제 종료 여부
closed_by INTEGER REFERENCES workers(id),  -- 강제 종료한 관리자
close_reason TEXT                  -- 강제 종료 사유
```

계산 로직:
```
app_task_details.started_at     = MIN(work_start_log.started_at)       ← 최초 시작
app_task_details.completed_at   = MAX(work_completion_log.completed_at) ← 마지막 종료
app_task_details.duration_minutes = SUM(각 worker 개별 duration)        ← man-hour 합산
app_task_details.elapsed_minutes  = completed_at - started_at           ← 실경과시간
app_task_details.worker_count     = COUNT(DISTINCT worker_id)           ← 투입 인원
```

### 작업 미종료 알림 체계 (3단계)
> scheduler_service.py (APScheduler) + alert_log + WebSocket 활용

```
[1단계] 작업자 리마인더 — 매 1시간
  - 트리거: 작업 시작 후 1시간 단위 경과, completed_at IS NULL
  - 수신: 해당 작업자
  - alert_type: TASK_REMINDER
  - 메시지: "{task_name} 작업이 {N}시간째 진행 중입니다. 완료 시 종료 버튼을 눌러주세요."

[2단계] 퇴근 시간 알림 — 17:00, 20:00 (KST)
  - 트리거: 17:00 정상퇴근, 20:00 잔업종료 시점에 미종료 작업 존재
  - 수신: 해당 작업자
  - alert_type: SHIFT_END_REMINDER
  - 메시지: "퇴근 전 미완료 작업 {N}건이 있습니다."

[3단계] 관리자 에스컬레이션 — 익일 09:00
  - 트리거: 전일 미종료 작업 (started_at < 오늘 00:00, completed_at IS NULL)
  - 수신: 해당 협력사 관리자 (is_manager=true + 같은 company)
  - alert_type: TASK_ESCALATION
  - 메시지: "작업자 {name}의 {task_name} 작업이 전일 미종료 상태입니다."
  - 관리자 액션: 강제 종료 (force_closed=true, closed_by, close_reason 입력)
```

관리자 강제 종료 API: `PUT /api/admin/tasks/{task_id}/force-close`
- body: `{ "completed_at": "2026-02-20T17:00:00+09:00", "close_reason": "작업자 미처리" }`
- force_closed=true, closed_by=관리자 worker_id 자동 설정

### Admin 옵션 화면 기능 목록 + 필수 API
```
1. admin_settings 관리 (heating_jacket, phase_block 등 토글)
2. 협력사 관리자 지정/해제 (workers.is_manager 토글, company 기준 필터)
3. 미종료 작업 목록 → 강제 종료 버튼
4. model_config 조회/수정 (추후)
```

**⚠️ Admin 옵션 화면 필수 API (FE가 호출 — BE 구현 필수)**:
| HTTP | 엔드포인트 | 설명 | 권한 |
|------|-----------|------|------|
| GET | `/api/admin/managers?company=` | 작업자 목록 (approved, company 필터) | admin_required |
| PUT | `/api/admin/workers/{id}/manager` | is_manager 토글 `{"is_manager": bool}` | admin_required |
| GET | `/api/admin/settings` | admin_settings 전체 조회 | admin_required |
| PUT | `/api/admin/settings` | admin_settings 업데이트 `{"setting_key", "setting_value"}` | admin_required |
| GET | `/api/admin/tasks/pending` | 미종료 작업 목록 (started_at NOT NULL, completed_at IS NULL) | admin_required |
| PUT | `/api/admin/tasks/{id}/force-close` | 강제 종료 (이미 구현됨) | manager_or_admin_required |

### 멀티 작업자 + 미종료 처리 테스트 케이스 (TEST 반드시 전수 구현)

**멀티 작업자 duration 계산:**
```
TC-MW-01: 1명 단독 작업 → duration = 개인 작업시간, worker_count = 1
TC-MW-02: 2명 동시 시작, 다른 시간에 종료 → started_at = 동일, completed_at = 마지막 종료, duration = 합산
TC-MW-03: 3명 모두 다른 시작/종료 → started_at = MIN, completed_at = MAX, duration = SUM, elapsed = MAX-MIN
TC-MW-04: 작업자 A 종료 + B 아직 진행 중 → Task.completed_at IS NULL (미완료 상태 유지)
TC-MW-05: 마지막 작업자 종료 → Task 자동 완료, duration/elapsed/worker_count 모두 정확한지 검증
TC-MW-06: duration_minutes(man-hour) ≠ elapsed_minutes(실경과) 값이 서로 다른지 확인 (3명 동시 작업 시)
TC-MW-07: worker_count = 실제 참여 작업자 수 (중복 제거 DISTINCT)
```

**미종료 알림 스케줄러:**
```
TC-UF-01: 작업 시작 1시간 경과 → TASK_REMINDER 알림 생성 확인
TC-UF-02: 작업 시작 3시간 경과 → TASK_REMINDER 3회 누적 확인
TC-UF-03: 작업 완료된 건 → 알림 미생성 확인 (false positive 방지)
TC-UF-04: 17:00 KST 도달 + 미종료 작업 → SHIFT_END_REMINDER 생성
TC-UF-05: 17:00 KST 도달 + 미종료 작업 없음 → 알림 미생성
TC-UF-06: 20:00 KST 도달 + 미종료 작업 → SHIFT_END_REMINDER 생성
TC-UF-07: 익일 09:00 + 전일 미종료 → TASK_ESCALATION 관리자 알림 (is_manager=true + 같은 company)
TC-UF-08: 다른 company 관리자에게는 알림 미전송 확인
```

**관리자 강제 종료:**
```
TC-FC-01: 관리자(is_manager=true) → force-close 성공, force_closed=true 확인
TC-FC-02: 일반 작업자 → force-close 시도 → 403 거부
TC-FC-03: 강제 종료 시 completed_at = 관리자 지정 시간, closed_by = 관리자 ID 확인
TC-FC-04: 강제 종료 후 duration_minutes, elapsed_minutes 정확 계산 확인
TC-FC-05: close_reason 필수 입력 검증 (빈값 → 400)
TC-FC-06: 이미 완료된 Task에 force-close → 400 거부
TC-FC-07: 강제 종료된 Task는 리포트에서 force_closed=true로 필터 가능 확인
```

---

## Sprint 1 상세 작업 지시

### BE 워커 — Sprint 1 작업 순서
```
1. backend/migrations/001_create_workers.sql 검토 및 보완
2. backend/migrations/002_create_product_info.sql 검토 및 보완
3. backend/app/models/worker.py — CRUD 함수 구현 (psycopg2)
4. backend/app/services/auth_service.py — register, login, verify_email 구현
5. backend/app/middleware/jwt_auth.py — 인증/권한 데코레이터 구현
6. backend/app/routes/auth.py — 4개 엔드포인트 구현
7. backend/app/__init__.py — app factory에서 auth blueprint 등록 확인
8. backend/run.py — 서버 실행 테스트
```

### FE 워커 — Sprint 1 작업 순서
```
1. frontend/lib/services/api_service.dart — Dio + JWT interceptor 구현
2. frontend/lib/services/auth_service.dart — login, register, verifyEmail 구현
3. frontend/lib/models/worker.dart — fromJson/toJson 완성
4. frontend/lib/providers/auth_provider.dart — AuthNotifier 상태 관리 구현
5. frontend/lib/screens/auth/login_screen.dart — 로그인 UI 구현
6. frontend/lib/screens/auth/register_screen.dart — 회원가입 UI 구현 (역할 선택 포함)
7. frontend/lib/screens/auth/verify_email_screen.dart — 이메일 인증 화면
8. frontend/lib/main.dart — 라우팅 설정 (인증 상태에 따른 화면 분기)
```

### TEST 워커 — Sprint 1 작업 순서
```
1. tests/conftest.py — Flask test app fixture, test DB 연결 구현
2. tests/fixtures/sample_workers.json — 테스트 데이터 보완
3. tests/backend/test_auth.py — 6개 인증 테스트 케이스 구현
4. pytest 실행 확인 (backend 테스트만)
```

---

## 충돌 방지 규칙

| 에이전트 | 쓰기 가능 | 읽기 가능 | 절대 수정 금지 |
|---------|----------|----------|--------------|
| FE | `frontend/**` | 모든 파일 | `backend/**`, `tests/**` |
| BE | `backend/**` | 모든 파일 | `frontend/**`, `tests/**` |
| TEST | `tests/**` | 모든 파일 | `backend/app/**`, `frontend/lib/**` |

**공유 파일 (수정 전 리드 승인 필수)**:
- `CLAUDE.md` — 리드만 수정 가능
- API 인터페이스 변경 시 → 리드가 FE/BE 양쪽에 동기화 지시

---

## 버전 관리 기준 (Semantic Versioning)

### 버전 형식: `MAJOR.MINOR.PATCH`

| 구분 | 올리는 시점 | 예시 |
|------|-----------|------|
| **MAJOR** (X.0.0) | 기존 API 호환 깨지는 변경, DB 스키마 대규모 변경, 아키텍처 전환 | v1→v2: DB 전면 재설계, 인증 체계 교체 |
| **MINOR** (0.X.0) | 신규 기능 추가, 새 Sprint 기능 완료, 보안 강화 (하위 호환 유지) | v1.3→v1.4: Sprint 19 보안 기능 추가 |
| **PATCH** (0.0.X) | 버그 수정, UI 미세 조정, 기존 기능 개선 (기능 변경 없음) | v1.4.0→v1.4.1: 출근 버튼 오류 수정 |

### 버전 업데이트 파일 목록

스프린트 완료 후 반드시 아래 2개 파일을 **동시에** 업데이트:

1. `backend/version.py` — BE 버전 (VERSION, BUILD_DATE)
2. `frontend/lib/utils/app_version.dart` — FE 버전 (version, buildDate)

> health endpoint (`/api/health`)에서 VERSION 자동 반영됨, 앱 스플래시에서 `AppVersion.display` 자동 반영됨

### 버전 업데이트 절차

```
1. 스프린트 전체 완료 + 테스트 통과 확인
2. backend/version.py → VERSION, BUILD_DATE 업데이트
3. frontend/lib/utils/app_version.dart → version, buildDate 업데이트
4. 두 파일의 VERSION 값이 반드시 동일해야 함
5. CLAUDE.md 버전 이력에 기록
6. PROGRESS.md에 스프린트 완료 내역 추가 (BE/FE/TEST 완료 항목, 테스트 결과, 생성/수정 파일)
7. BACKLOG.md 업데이트 (완료 항목 체크, 다음 스프린트 계획 반영)
```

### FE 빌드 + 배포 절차 (Netlify)

```
1. cd frontend
2. flutter build web --release          # build/web 생성
3. npx netlify-cli deploy --prod --dir=build/web --site=ab8041c3-dc51-40c6-96e4-9966222aeda3
   # 사이트: https://gaxis-ops.netlify.app
4. git add → commit → push (빌드 결과물은 커밋하지 않음, 소스 변경만 커밋)
```

> **참고**: `state.json` 없이 `--site=<site_id>` 플래그로 직접 지정.
> Netlify CLI가 없으면 `npx netlify-cli`로 자동 설치 후 실행됨.

### 버전 이력

| 버전 | 날짜 | 스프린트 | 주요 변경 |
|------|------|---------|----------|
| v1.0.0 | 2026-02-16 | Sprint 1-10 | 초기 릴리스 (인증, 출퇴근, 작업관리, 관리자) |
| v1.1.0 | 2026-02-25 | Sprint 13 | QR 스캔 + 생산실적 입력 |
| v1.2.0 | 2026-02-28 | Sprint 14-15 | 일시정지/재개, 알림, 스케줄러 |
| v1.3.0 | 2026-03-04 | Sprint 16-17 | 버전 시스템 도입, 파트너 S/N 진행률 |
| v1.4.0 | 2026-03-06 | Sprint 19-A/B/D | 보안 강화 (Refresh Token Rotation, Device ID, DB 토큰 관리, Geolocation) |
| v1.5.0 | 2026-03-06 | Sprint 19-E/20-A/B | VIEW용 출퇴근 API, 가입 Admin 알림, 공지사항 탭 |
| v1.6.0 | 2026-03-10 | Sprint 21/22-A/B | QR 목록 API, 이메일 인증 개선, GPS 정확도 + DMS 변환 |
| v1.6.1 | 2026-03-10 | Sprint 22-A 보완 | 인증 3분 만료, 재전송 API 연동, 승인목록 인증필터, PM role |
| v1.6.2 | 2026-03-10 | Sprint 22-C | Manager 권한 위임 (같은 회사 is_manager 부여, Admin 보호) |
| v1.6.3 | 2026-03-11 | Sprint 22-D | 공지수정 UI, Admin 간편로그인, ETL 변경이력 API |
| v1.7.0 | 2026-03-11 | Sprint 23 | Manager 권한 위임 화면, 홈 메뉴 재구성, managers API 권한 완화 |
| v1.7.1 | 2026-03-11 | Sprint 24 | QR 목록 actual_ship_date 추가, Manager 자사 필터 (QR/출퇴근) |
| v1.7.2 | 2026-03-12 | Sprint 25 | BUG-22 Logout Storm 수정 (401 무한 루프 방지, jwt_optional) |
| v1.7.3 | 2026-03-12 | Sprint 26 | PWA 버전 업데이트 토스트 + 업데이트 내용 팝업, conftest 운영 데이터 보호 |
| v1.7.4 | 2026-03-13 | Sprint 27 | AXIS-VIEW 권한 데코레이터 재정비 (get_current_worker 캐싱, gst_or_admin_required, view_access_required) |
| v1.7.5 | 2026-03-15 | Sprint 27-fix | Task Seed silent fail 수정, SINGLE_ACTION UI 반영, BUG-23 QR viewfinder 코너 수정 |
| v1.7.6 | 2026-03-15 | Sprint 29 | 공장 API (monthly-detail, weekly-kpi) — BE only, factory.py 신규 |
| v1.7.7 | 2026-03-16 | Sprint 29 보완 | PM role 추가, 이름 로그인, ship_plan_date, per_page 500 |
| v1.7.8 | 2026-03-16 | Sprint 29-fix | BUG-24 재발 방지 — ensure_schema 앱 시작 시 DB 스키마 자동 검증 |
| v1.8.0 | 2026-03-17 | Sprint 30 | DB Connection Pool 도입 — 33파일 175건 conn.close→put_conn 변환 |
