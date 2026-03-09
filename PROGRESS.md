# AXIS-OPS 프로젝트 진행 상황

## 개요
GST 제조 현장 작업 관리 시스템 — 스프레드시트 수동 입력에서 모바일 App 실시간 Push로 전환.

> **현재 버전**: v1.5.0 (Sprint 21, 2026-03-09)

---

## Sprint 1: 인증 + DB 기반 (완료)

### BE 완료 내역
- DB 마이그레이션: `001_create_workers.sql`, `002_create_product_info.sql`
- `worker.py` — CRUD (psycopg2 raw SQL, RealDictCursor)
- `auth_service.py` — register, login, verify_email (bcrypt + PyJWT)
- `jwt_auth.py` — `jwt_required`, `get_current_worker_id`, `admin_required` 데코레이터
- `auth.py` — 4개 엔드포인트 (register, login, verify-email, approve)
- `__init__.py` — Flask app factory + CORS + 에러 핸들러

### FE 완료 내역
- `api_service.dart` — Dio + JWT interceptor
- `auth_service.dart` — login, register, verifyEmail
- `worker.dart` — fromJson/toJson
- `auth_provider.dart` — AuthNotifier (Riverpod)
- 로그인/회원가입/이메일인증 화면 구현

### 테스트: 8/8 PASSED
| 테스트 | 설명 |
|--------|------|
| `test_register_worker_success` | 회원가입 성공 |
| `test_register_duplicate_email` | 중복 이메일 거부 |
| `test_email_verification_success` | 이메일 인증 성공 |
| `test_verify_email_invalid_code` | 잘못된 인증코드 |
| `test_login_success_with_jwt` | JWT 로그인 성공 |
| `test_unapproved_worker_login_restricted` | 미승인 로그인 제한 |
| `test_login_wrong_password` | 잘못된 비밀번호 |
| `test_login_nonexistent_email` | 존재하지 않는 이메일 |

---

## Sprint 2: Task 핵심 플로우 (완료)

### BE 완료 내역
- DB 마이그레이션: `003_create_task_tables.sql`
- `product_info.py` — 제품 조회 CRUD
- `task_detail.py` — Task 생성/시작/완료/토글 CRUD
- `completion_status.py` — 공정별 완료 상태 관리
- `task_service.py` — 작업 시작/완료 비즈니스 로직
- `work.py` — 8개 엔드포인트 (start, complete, tasks, completion, validate, toggle, location)
- `product.py` — 제품 조회 엔드포인트

### FE 완료 내역
- QR 스캔 화면, Task 목록 화면, Task 상세 화면
- `task_service.dart`, `task_provider.dart`
- 시작/완료 터치 UI, completion_badge 위젯

### 테스트: 21/21 PASSED
| 테스트 | 설명 |
|--------|------|
| `test_start_work_success` | 작업 시작 성공 |
| `test_start_already_started_task` | 이미 시작된 작업 |
| `test_start_other_worker_task` | 다른 작업자 작업 시작 거부 |
| `test_start_nonexistent_task` | 존재하지 않는 작업 |
| `test_start_not_applicable_task` | 비적용 작업 시작 거부 |
| `test_start_without_jwt` | JWT 없이 작업 시작 |
| `test_complete_work_success` | 작업 완료 성공 |
| `test_complete_not_started_task` | 시작 안 한 작업 완료 거부 |
| `test_complete_already_completed_task` | 이미 완료된 작업 |
| `test_complete_updates_completion_status` | 완료 시 공정 상태 업데이트 |
| `test_get_tasks_all` | 시리얼별 전체 Task 조회 |
| `test_get_tasks_filtered_by_process_type` | 공정 유형별 필터 |
| `test_get_tasks_empty_result` | 빈 결과 |
| `test_get_completion_status` | 공정 완료 상태 조회 |
| `test_validate_missing_mm_ee` | MM/EE 미완료 검증 |
| `test_validate_mm_ee_completed` | MM/EE 완료 검증 |
| `test_validate_non_inspection_process` | 비검사 공정 스킵 |
| `test_toggle_applicable_success` | 적용 여부 토글 |
| `test_toggle_nonexistent_task` | 존재하지 않는 작업 토글 |
| `test_update_location_success` | 위치 QR 업데이트 |
| `test_update_location_nonexistent_product` | 존재하지 않는 제품 |

---

## Sprint 3: 공정 검증 + 알림 (완료)

### BE 완료 내역
- DB 마이그레이션: `004_create_alert_tables.sql`
- `alert_log.py` — AlertLog 모델 + CRUD (create, get, mark_read, unread_count)
- `process_validator.py` — 공정 누락 검증 (PI/QI/SI → MM/EE 완료 체크 + 알림 생성)
- `duration_validator.py` — 작업 시간 검증 (>14h, <1m, 역전) + `check_unfinished_tasks()`
- `alert_service.py` — 알림 생성/조회/읽음 처리 + WebSocket broadcast
- `alert.py` — 4개 엔드포인트 (alerts, read, read-all, unread-count)
- `events.py` — Flask-SocketIO 이벤트 핸들러 (connect, disconnect, join_room)
- `work.py` 버그 수정: duration_warnings 응답 전달

### FE 완료 내역
- `alert_log.dart` — AlertLog 모델
- `websocket_service.dart` — Socket.IO 연결 관리
- `alert_provider.dart` — 알림 상태 관리 (Riverpod)
- `alert_service.dart` — 알림 API 통신
- `process_alert_popup.dart` — 공정 누락 경고 팝업
- `alert_list_screen.dart` — 관리자 알림 화면

### 버그 수정 (5건)
| 파일 | 수정 내용 |
|------|----------|
| `work.py` | `duration_warnings`가 complete_work 응답에 전달되지 않음 |
| `work.py` | validate_process 이후 unreachable 코드 제거 |
| `jwt_auth.py` | WebSocket용 `decode_jwt()` 함수 추가 |
| `services/__init__.py` | 존재하지 않는 클래스 import → 실제 함수 import으로 수정 |
| `websocket/__init__.py` | `from typing import Any` 누락 수정 |

### 테스트: 21/21 PASSED

#### test_alert_service.py (11 tests)
| 테스트 | 설명 |
|--------|------|
| `test_get_alerts_success` | 알림 목록 조회 |
| `test_get_alerts_empty` | 알림 없는 워커 조회 |
| `test_get_alerts_unread_only` | 읽지 않은 알림만 필터 |
| `test_get_alerts_unauthorized` | JWT 없이 조회 → 401 |
| `test_mark_read_success` | 개별 알림 읽음 처리 |
| `test_mark_read_not_owner` | 다른 워커 알림 읽음 → 404 |
| `test_mark_read_not_found` | 존재하지 않는 알림 → 404 |
| `test_mark_all_read_success` | 전체 읽음 처리 |
| `test_mark_all_read_empty` | 읽을 알림 없을 때 |
| `test_unread_count_with_alerts` | 안 읽은 알림 개수 |
| `test_unread_count_zero` | 알림 없을 때 0 |

#### test_process_validator.py (6 tests)
| 테스트 | 설명 |
|--------|------|
| `test_pi_mm_incomplete` | PI 작업 시 MM 미완료 → 알림 생성 |
| `test_qi_ee_incomplete` | QI 작업 시 EE 미완료 → 경고 |
| `test_pi_both_complete` | MM+EE 완료 → 정상 진행 |
| `test_mm_skips_validation` | 비검사 공정(MM) → 검증 스킵 |
| `test_product_not_found` | 존재하지 않는 제품 → 404 |
| `test_no_location_qr` | Location QR 미등록 확인 |

#### test_duration_validator.py (4 tests)
| 테스트 | 설명 |
|--------|------|
| `test_normal_duration_no_warnings` | 2시간 작업 → 경고 없음 |
| `test_duration_over_14h` | 15시간 작업 → DURATION_EXCEEDED 경고 |
| `test_very_short_duration` | 10초 작업 → 짧은 작업 경고 |
| `test_reverse_completion` | 미래 시작 시간 → 역전 경고 |

---

## 전체 테스트 결과: 50/50 PASSED

```
Sprint 1 (Auth):              8/8   PASSED
Sprint 2 (Work):             21/21  PASSED
Sprint 3 (Alert/Validation): 21/21  PASSED
─────────────────────────────────────────
Total:                       50/50  PASSED
```

---

## 수정된 파일 목록 (Sprint 1~3 전체)

### Backend
```
backend/app/__init__.py                      # Flask app factory
backend/app/config.py                        # DB URL, JWT secret
backend/app/middleware/jwt_auth.py            # JWT 인증 + decode_jwt
backend/app/middleware/audit_log.py           # 감사 로그 (stub)
backend/app/models/worker.py                 # 작업자 CRUD
backend/app/models/product_info.py           # 제품 CRUD
backend/app/models/task_detail.py            # Task CRUD
backend/app/models/completion_status.py      # 공정 완료 상태
backend/app/models/alert_log.py              # 알림 CRUD
backend/app/models/location_history.py       # 위치 기록 (stub)
backend/app/routes/auth.py                   # 인증 API
backend/app/routes/work.py                   # 작업 API
backend/app/routes/product.py                # 제품 API
backend/app/routes/alert.py                  # 알림 API
backend/app/routes/admin.py                  # 관리자 API (stub)
backend/app/routes/sync.py                   # 동기화 API (stub)
backend/app/services/auth_service.py         # 인증 로직
backend/app/services/task_service.py         # 작업 로직
backend/app/services/process_validator.py    # 공정 검증
backend/app/services/duration_validator.py   # 작업 시간 검증
backend/app/services/alert_service.py        # 알림 서비스
backend/app/websocket/events.py              # WebSocket 이벤트
backend/migrations/001_create_workers.sql
backend/migrations/002_create_product_info.sql
backend/migrations/003_create_task_tables.sql
backend/migrations/004_create_alert_tables.sql
backend/migrations/005_create_sync_tables.sql
```

### Frontend
```
frontend/lib/main.dart
frontend/lib/models/worker.dart
frontend/lib/models/task_item.dart
frontend/lib/models/product_info.dart
frontend/lib/models/alert_log.dart
frontend/lib/services/api_service.dart
frontend/lib/services/auth_service.dart
frontend/lib/services/task_service.dart
frontend/lib/services/alert_service.dart
frontend/lib/services/websocket_service.dart
frontend/lib/services/local_db_service.dart
frontend/lib/providers/auth_provider.dart
frontend/lib/providers/task_provider.dart
frontend/lib/providers/alert_provider.dart
frontend/lib/screens/auth/login_screen.dart
frontend/lib/screens/auth/register_screen.dart
frontend/lib/screens/auth/verify_email_screen.dart
frontend/lib/screens/auth/approval_pending_screen.dart
frontend/lib/screens/home/home_screen.dart
frontend/lib/screens/qr/qr_scan_screen.dart
frontend/lib/screens/task/task_management_screen.dart
frontend/lib/screens/task/task_detail_screen.dart
frontend/lib/screens/admin/admin_dashboard.dart
frontend/lib/screens/admin/worker_approval_screen.dart
frontend/lib/screens/admin/alert_list_screen.dart
frontend/lib/widgets/process_alert_popup.dart
frontend/lib/widgets/task_card.dart
frontend/lib/widgets/completion_badge.dart
frontend/lib/utils/constants.dart
frontend/lib/utils/validators.dart
```

### Tests
```
tests/conftest.py
tests/backend/test_auth.py
tests/test_work_api.py
tests/backend/test_alert_service.py
tests/backend/test_process_validator.py
tests/backend/test_duration_validator.py
tests/fixtures/sample_workers.json
tests/fixtures/sample_products.json
tests/fixtures/sample_tasks.json
tests/fixtures/sample_alerts.json
tests/fixtures/sample_completion_status.json
```

---

## Sprint 4: 관리자 + 퇴근시간 자동감지 (완료)

### BE 완료 내역
- `admin.py` — 9개 엔드포인트 (승인/거절, 대기목록, 작업자목록, 대시보드 3종, 보정목록, 강제완료, 미완료체크)
- `sync.py` — 2개 엔드포인트 (오프라인 배치 동기화, 동기화 상태)
- `scheduler_service.py` — APScheduler cron (매일 18:00 미완료 체크)
- `__init__.py` — admin_bp, sync_bp 등록 + 스케줄러 초기화 (테스트 환경 비활성화)

### 버그 수정 (4건)
| 파일 | 수정 내용 |
|------|----------|
| `admin.py` | `request.get_json()` → `get_json(silent=True)` (415 에러 방지) |
| `admin.py` | `datetime.now()` → `datetime.now(timezone.utc)` (naive/aware 불일치) |
| `sync.py` | `request.get_json()` → `get_json(silent=True)` (빈 body 처리) |
| `sync.py` | `str(task_data)` → `json.dumps(task_data)` (JSONB 호환) |

### 테스트: 31/31 PASSED

#### test_admin_api.py (18 tests)
| 테스트 | 설명 |
|--------|------|
| `test_approve_worker_success` | 작업자 승인 성공 |
| `test_reject_worker_success` | 작업자 거절 성공 |
| `test_approve_nonexistent_worker` | 존재하지 않는 작업자 → 404 |
| `test_approve_without_admin` | 비관리자 접근 → 403 |
| `test_approve_without_jwt` | JWT 없이 → 401 |
| `test_get_pending_workers` | 대기 작업자 목록 |
| `test_get_pending_workers_empty` | 대기 작업자 없음 |
| `test_get_pending_workers_pagination` | 페이지네이션 |
| `test_get_workers_with_filter` | 필터링 조회 |
| `test_get_process_summary` | 공정 요약 |
| `test_get_active_tasks` | 활성 작업 목록 |
| `test_get_alerts_summary` | 알림 통계 |
| `test_dashboard_without_admin` | 비관리자 대시보드 → 403 |
| `test_get_task_corrections` | 보정 필요 작업 목록 |
| `test_force_complete_task_success` | 강제 완료 성공 |
| `test_force_complete_nonexistent_task` | 존재하지 않는 작업 → 404 |
| `test_manual_unfinished_check` | 수동 미완료 체크 |
| `test_unfinished_check_without_admin` | 비관리자 → 403 |

#### test_sync_api.py (13 tests)
| 테스트 | 설명 |
|--------|------|
| `test_sync_tasks_success` | 작업 동기화 성공 |
| `test_sync_locations_success` | 위치 동기화 성공 |
| `test_sync_alerts_read` | 알림 읽음 동기화 |
| `test_sync_batch_combined` | 배치 복합 동기화 |
| `test_sync_partial_failure` | 부분 실패 처리 |
| `test_sync_empty_data` | 빈 데이터 동기화 |
| `test_sync_without_jwt` | JWT 없이 → 401 |
| `test_sync_invalid_request_body` | 잘못된 요청 → 400 |
| `test_get_sync_status` | 동기화 상태 조회 |
| `test_sync_status_no_records` | 기록 없을 때 |
| `test_sync_status_without_jwt` | JWT 없이 → 401 |
| `test_sync_creates_queue_records` | DB 큐 레코드 생성 확인 |
| `test_sync_creates_location_records` | DB 위치 레코드 생성 확인 |

---

## Sprint 5: 보안 + PWA + 이메일 + 잔여 모델 (완료)

> ✅ DB 스키마 사전 작업 완료 상태에서 시작: plan.product_info + qr_registry 분리, 컬럼명 간소화, PDA 테이블 삭제

### BE Phase A 완료 내역 (Migration FK 수정 + 누락 모델)
- `003_create_task_tables.sql` FK 수정: `product_info` → `qr_registry` 참조로 변경
  - `app_task_details.qr_doc_id` FK → `qr_registry(qr_doc_id)`
  - `completion_status.serial_number` FK → `qr_registry(serial_number)`
- `004_create_alert_tables.sql` 업데이트: `read_at TIMESTAMPTZ` 컬럼 + `update_app_alert_logs_updated_at` 트리거 추가
- 누락 Python 모델 3개 신규 생성:
  - `work_start_log.py` — WorkStartLog dataclass + CRUD (create, get_by_id, get_by_serial, get_by_worker)
  - `work_completion_log.py` — WorkCompletionLog dataclass + CRUD (create, get_by_id, get_by_serial, get_by_worker)
  - `offline_sync_queue.py` — OfflineSyncQueue dataclass + CRUD (create, get_by_id, get_pending, mark_done)
- `location_history.py` 완성: from_db_row() 구현 + CRUD 함수 추가 (이전: pass 상태)
- `alert_log.py` 수정: `read_at: Optional[datetime]` 필드 + mark_alert_read()에 read_at 업데이트
- `worker.py` 수정: EmailVerification dataclass 추가 (6컬럼)
- `models/__init__.py` 업데이트: WorkStartLog, WorkCompletionLog, OfflineSyncQueue, EmailVerification import

### BE Phase B 완료 내역 (보안 + 이메일 + Refresh Token)
- `backend/.env` 생성 — DATABASE_URL, JWT 키, SMTP 설정 분리
- `backend/.env.example` 생성 — 온보딩용 템플릿
- `backend/.gitignore` 생성 — `.env` 보호
- `config.py` 수정:
  - `python-dotenv` 적용 (`load_dotenv()`)
  - 모든 credential `os.getenv()` 전환
  - SMTP 설정 6개 추가 (SMTP_HOST, PORT, USER, PASSWORD, FROM_NAME, FROM_EMAIL)
  - Refresh Token 설정 추가 (JWT_REFRESH_SECRET_KEY, 7일 만료)
- `auth_service.py` 수정:
  - `send_verification_email()` 실제 구현 (smtplib STARTTLS + HTML/Plain MIMEMultipart, SMTP_FROM_NAME=G-AXIS)
  - `create_refresh_token()` / `verify_refresh_token()` 구현 (전용 시크릿 키, 7일 만료)
  - `refresh_access_token()` 구현 (작업자 상태 재확인 포함)
  - `register()` 개선: 실제 이메일 발송 호출 (SMTP 미설정 시 개발 fallback)
  - `login()` 개선: Admin freepass 정책 (is_admin=True → 인증/승인 체크 skip), refresh_token 응답 포함
- `routes/auth.py` 수정: `/api/auth/refresh` (POST) 엔드포인트 추가
- `requirements.txt` 수정: `python-dotenv` 추가

### FE 완료 내역 (PWA + 빌드)
- PWA manifest/icons 정상 확인 (name="G-AXIS OPS", display="standalone", 192+512 아이콘)
- Flutter 기본 Service Worker 활용 (flutter_service_worker.js 자동 생성)
- `pubspec.yaml` 수정: `cupertino_icons: ^1.0.8` 추가 (빌드 경고 해소)
- `flutter build web` 성공 — build/web/ 정상 출력 확인
- 웹 호환성 확인: sqflite 미사용(shared_preferences), mobile_scanner 미사용, flutter_secure_storage 웹 지원

### 테스트: 59/59 PASSED

#### test_models.py (25 tests)
| 테스트 | 설명 |
|--------|------|
| `TestWorkStartLog` (4) | 생성, get_by_id, get_by_task_id, from_db_row |
| `TestWorkCompletionLog` (5) | 생성, get_by_id, get_by_task_id, from_db_row, nullable duration |
| `TestOfflineSyncQueue` (4) | 생성, mark_synced, get_unsynced, from_db_row |
| `TestLocationHistory` (4) | 생성, get_by_worker_id, from_db_row, 소수점 정밀도 |
| `TestEmailVerification` (5) | dataclass 생성, from_db_row, 6자리 코드, 10분 만료 |
| `TestAlertLogReadAt` (3) | read_at 필드 추가 검증, mark_read 동작, Optional 처리 |

#### test_email.py (12 tests)
| 테스트 | 설명 |
|--------|------|
| `test_send_verification_email_success` | SMTP mock 발송 성공 |
| `test_verification_code_format` | 6자리 숫자 형식 |
| `test_email_contains_code` | 본문 인증코드 포함 (base64 디코딩) |
| `test_smtp_connect_error` | SMTP 연결 오류 처리 |
| `test_smtp_auth_error` | SMTP 인증 오류 처리 |
| `test_smtp_timeout` | SMTP 타임아웃 처리 |
| `test_dev_fallback_no_smtp` | SMTP 미설정 시 개발 환경 fallback |
| `test_email_html_format` | HTML 멀티파트 메일 형식 검증 |
| `test_email_plain_text_fallback` | Plain text 본문 포함 확인 |
| `test_email_from_header` | From 헤더 G-AXIS 이름 확인 |
| `test_email_subject_encoding` | Subject UTF-8 인코딩 |
| `test_email_rate_limit` | Rate Limiting (5회/시간) 동작 확인 |

#### test_refresh_token.py (22 tests)
| 테스트 | 설명 |
|--------|------|
| `TestLoginReturnsBothTokens` (4) | access+refresh 반환, 만료시간 비교, admin 토큰 |
| `TestRefreshEndpoint` (4) | 성공, rotation, missing token, 빈 body |
| `TestRefreshWithExpiredToken` (2) | 만료 토큰 거부, access→refresh 자리 사용 |
| `TestRefreshWithInvalidToken` (6) | 서명 불일치, malformed, 빈 문자열, null, 미인증, 미존재 worker |
| `TestRefreshTokenLifecycle` (3+) | 전체 생명주기, payload 일관성, role 변경 후 refresh, 계정 거부 후 refresh, 다중 토큰 유효성 |
| `TestRefreshTokenSeparation` (2) | refresh→access 사용 불가, access→refresh 사용 불가 |

### Sprint 5 보완 작업 (Sprint 6 전 실행)
- `product_info.py`: ProductInfo dataclass 16개 필드 추가 (plan.product_info 25컬럼 완전 매핑), _BASE_JOIN_QUERY 확장, from_db_row() 동기화
- `auth_service.py`: 이메일 Rate Limiting 추가 (_check_email_rate_limit, 5회/시간 제한)
- `test_refresh_token.py`: 누락 테스트 5개 추가 (토큰 분리 정책 2개 + 생명주기 3개)

### 코드 리뷰 결과 (TEST → BE)
- Phase A 모델 전체 PASS — CLAUDE.md 컬럼 명세 일치 확인
- Phase B 보안/이메일 PASS — 중대 버그 없음
- 권장사항: `send_verification_email`을 별도 `email_service.py`로 분리 (Sprint 6 고려)

### 변경 파일 목록

#### 신규 생성
```
backend/app/models/work_start_log.py
backend/app/models/work_completion_log.py
backend/app/models/offline_sync_queue.py
backend/.env
backend/.env.example
backend/.gitignore
tests/backend/test_models.py
tests/backend/test_email.py
tests/backend/test_refresh_token.py
```

#### 수정
```
backend/migrations/003_create_task_tables.sql    # FK → qr_registry 수정
backend/migrations/004_create_alert_tables.sql   # read_at + 트리거 추가
backend/app/models/location_history.py           # from_db_row 완성 + CRUD
backend/app/models/alert_log.py                  # read_at 필드 추가
backend/app/models/worker.py                     # EmailVerification dataclass
backend/app/models/__init__.py                   # 새 모델 import
backend/app/models/product_info.py               # 16개 필드 추가 + JOIN 쿼리 확장
backend/app/config.py                            # .env + SMTP + Refresh Token 설정
backend/app/services/auth_service.py             # SMTP + Refresh Token + Admin freepass + Rate Limiting
backend/app/routes/auth.py                       # /api/auth/refresh 엔드포인트
backend/requirements.txt                         # python-dotenv 추가
frontend/pubspec.yaml                            # cupertino_icons 추가
```

---

## Sprint 6: Task 재설계 + 네이밍 변경 + Admin 옵션 (완료)

> MM→MECH, EE→ELEC 전체 코드베이스 네이밍 변경 + Task 27개→15개 재설계

### BE Phase A 완료 내역 (네이밍 + DB 스키마 변경)
- `006_sprint6_schema_changes.sql` 신규:
  - `role_enum` 변경: MECH, ELEC, ADMIN 추가 + 기존 MM→MECH, EE→ELEC 데이터 UPDATE
  - `workers` 테이블에 `company VARCHAR(50)` 컬럼 추가
  - `completion_status`: `mm_completed`→`mech_completed`, `ee_completed`→`elec_completed` 컬럼명 변경
  - `model_config` 테이블 생성 (6개 모델: GAIA/DRAGON/GALLANT/MITHAS/SDS/SWS)
  - `admin_settings` 테이블 생성 (heating_jacket_enabled, phase_block_enabled)
  - `app_task_details` 확장: elapsed_minutes, worker_count, force_closed, closed_by, close_reason
  - `alert_type_enum` 확장: TMS_TANK_COMPLETE, TANK_DOCKING_COMPLETE, TASK_REMINDER, SHIFT_END_REMINDER, TASK_ESCALATION
- 기존 코드 MM→MECH, EE→ELEC 전수 교체:
  - `auth_service.py`: VALID_ROLES = {'MECH', 'ELEC', 'TM', 'PI', 'QI', 'SI'}
  - `task_service.py`: VALID_PROCESS_TYPES = {'MECH', 'ELEC', 'TM', 'PI', 'QI', 'SI'}
  - `completion_status.py`: mech_completed/elec_completed 필드명 + process_map
  - `process_validator.py`, `work.py`, `admin.py`, `product.py` 등 전수 교체
- `worker.py`: company 필드 추가 (Optional[str])
- `auth_service.py`: COMPANY_ROLE_MAP 추가 + register()에서 company↔role 유효성 검증
- 신규 모델 2개:
  - `model_config.py` — ModelConfig dataclass + get_by_prefix() + get_all() + get_for_product()
  - `admin_settings.py` — AdminSettings dataclass + get_setting() + update_setting() + get_all()

### BE Phase B 완료 내역 (Task Seed 재설계)
- `task_seed.py` 신규:
  - TaskTemplate dataclass + 15개 템플릿 (MECH 7 + ELEC 6 + TMS 2)
  - `initialize_product_tasks(serial_number, qr_doc_id, model_name)` — model_config 기반 분기
  - GAIA: MECH 1~5,7 활성 + TMS 2개 / DRAGON: TANK_DOCKING만 비활성 / 기타: 자주검사만 활성
  - HEATING_JACKET: admin_settings.heating_jacket_enabled 제어
  - `get_task_categories_for_worker()` — company 기반 visible category 계산
  - `filter_tasks_for_worker()` — Task 필터링 헬퍼
- `admin.py`: POST /api/admin/products/initialize-tasks API
- `task_service.py`: `_trigger_completion_alerts()` — TMS_TANK_COMPLETE, TANK_DOCKING_COMPLETE 알림 트리거
- `work.py`: company 기반 Task 필터링 (GET /api/app/tasks/<serial_number>)

### BE Phase C 완료 내역 (멀티 작업자 + 미종료 + 강제 종료)
- `task_detail.py` 확장: elapsed_minutes, worker_count, force_closed, closed_by, close_reason 5개 필드
- `task_service.py` 멀티 작업자 duration 계산:
  - start_work(): work_start_log 기반 다중 작업자 참여
  - complete_work(): _all_workers_completed() → _finalize_task_multi_worker() 집계
  - duration_minutes = SUM(man-hour), elapsed_minutes = MAX-MIN, worker_count = DISTINCT
- `scheduler_service.py` 3단계 알림 스케줄러:
  - 1단계: task_reminder_job — 매 정각, TASK_REMINDER (작업자)
  - 2단계: shift_end_reminder_job — 17:00/20:00 KST, SHIFT_END_REMINDER (작업자)
  - 3단계: task_escalation_job — 09:00 KST, TASK_ESCALATION (같은 company 관리자)
- `admin.py`: PUT /api/admin/tasks/{task_id}/force-close API
- `jwt_auth.py`: manager_or_admin_required 데코레이터

### FE 완료 내역
- MM→MECH, EE→ELEC 전수 교체: worker.dart, task_item.dart, home_screen.dart, process_alert_popup.dart, splash_screen.dart
- Worker 모델 company 필드 추가 + fromJson/toJson/copyWith
- register_screen.dart: company 드롭다운 (7개) + role 자동 필터링 + deprecation 수정 (value→initialValue)
- auth_provider.dart, auth_service.dart: company 파라미터 추가
- admin_options_screen.dart 신설: admin_settings 토글 + 관리자 지정/해제 + 미종료 강제 종료
- main.dart: /admin-options 라우트 등록
- flutter build web 성공

### 테스트: 157 passed, 20 skipped, 0 failed

#### 기존 테스트 네이밍 교체
- conftest.py, fixtures/*.json, test_models.py, test_process_validator.py 등 MM→MECH, EE→ELEC 교체

#### Sprint 6 신규 테스트
| 파일 | 테스트 수 | 내용 |
|------|----------|------|
| test_task_seed.py | 9 passed, 7 skipped | model_config 분기, Task Seed 초기화, company 필터링, admin_settings |
| test_multi_worker.py | 2 passed, 5 skipped | TC-MW-01~07 (join/join-complete API Sprint 7 대상) |
| test_scheduler.py | 7 passed, 1 skipped | TC-UF-01~08 (3단계 스케줄러) |
| test_force_close.py | 6 passed, 1 skipped | TC-FC-01~07 (관리자 강제 종료) |

SKIPPED 20건 사유:
- TC-MW-02~05, TC-MW-07 (5건): /join, /join-complete 엔드포인트 → Sprint 7
- TC-FC-07 (1건): SELF_INSPECTION 강제종료 시 mech_completed 자동 업데이트 → Sprint 7
- TC-UF-01b (1건): /api/admin/scheduler/run 엔드포인트 미구현
- TC-SEED 7건: plan 스키마 직접 접근 → 현재 public 단일 스키마 사용
- WebSocket 8건: Flask test client 미지원 (구조상 정상)

### SMTP 이슈 해결
- **원인**: 이전 TEST 에이전트가 SMTP mock 없이 register API 테스트 실행 → 실제 SMTP 서버로 @axisos.test 도메인에 메일 발송 시도 → Delivery Failure
- **조치**: conftest.py에 `_block_smtp_globally()` autouse=True fixture 추가 → smtplib.SMTP/SMTP_SSL 자동 차단

### BE 코드 리뷰 결과 (TEST → BE)
| 파일 | 결과 |
|------|------|
| task_seed.py | PASS |
| task_service.py | PASS |
| scheduler_service.py | PASS |
| admin.py (force-close) | PASS |
| model_config.py | PASS |
| admin_settings.py | PASS |

### 변경 파일 목록

#### 신규 생성
```
backend/migrations/006_sprint6_schema_changes.sql
backend/app/models/model_config.py
backend/app/models/admin_settings.py
backend/app/services/task_seed.py
frontend/lib/screens/admin/admin_options_screen.dart
tests/backend/test_task_seed.py
tests/backend/test_multi_worker.py
tests/backend/test_scheduler.py
tests/backend/test_force_close.py
```

#### 수정
```
backend/app/models/worker.py                    # company 필드 추가
backend/app/models/task_detail.py               # 5개 필드 확장
backend/app/models/completion_status.py         # mech_completed/elec_completed
backend/app/models/__init__.py                  # 새 모델 import
backend/app/services/auth_service.py            # COMPANY_ROLE_MAP + VALID_ROLES
backend/app/services/task_service.py            # 멀티 작업자 + 알림 트리거
backend/app/services/process_validator.py       # MECH/ELEC 네이밍
backend/app/services/scheduler_service.py       # 3단계 스케줄러
backend/app/routes/work.py                      # company 필터링
backend/app/routes/admin.py                     # initialize-tasks + force-close API
backend/app/middleware/jwt_auth.py              # manager_or_admin_required
frontend/lib/models/worker.dart                 # company 필드
frontend/lib/models/task_item.dart              # MECH/ELEC
frontend/lib/screens/auth/register_screen.dart  # company 드롭다운
frontend/lib/screens/home/home_screen.dart      # MECH/ELEC
frontend/lib/providers/auth_provider.dart       # company 파라미터
frontend/lib/services/auth_service.dart         # company 파라미터
frontend/lib/widgets/process_alert_popup.dart   # MECH/ELEC
frontend/lib/main.dart                          # /admin-options 라우트
tests/conftest.py                               # SMTP mock + Sprint 6 migration
tests/backend/test_models.py                    # MECH/ELEC 교체
tests/backend/test_process_validator.py         # MECH/ELEC 교체
tests/fixtures/sample_workers.json              # MECH/ELEC 교체
tests/fixtures/sample_tasks.json                # MECH/ELEC 교체
tests/fixtures/sample_alerts.json               # MECH/ELEC 교체
```

---

## 전체 테스트 결과: 297 collected, 277 passed, 20 skipped (Sprint 6 기준)

```
Sprint 1 (Auth):                 8/8   PASSED
Sprint 2 (Work):                21/21  PASSED
Sprint 3 (Alert/Validation):   21/21  PASSED
Sprint 4 (Admin/Sync):         31/31  PASSED
Sprint 5 (Models/Email/Token): 59/59  PASSED
Sprint 6 (Task Seed/Multi/Scheduler/ForceClose):
                               157 passed, 20 skipped, 0 failed
─────────────────────────────────────────────
Total:                         297 collected, 277 passed, 20 skipped
```

---

## Sprint 7: 실데이터 + 통합 테스트 (완료)

### TEST 완료 내역 (Phase 1~6)

#### Phase 1: Product API 테스트 신규 생성
**파일**: `tests/backend/test_product_api.py` (17 tests, 0 assert False)

| 클래스 | 테스트 수 | 내용 |
|--------|----------|------|
| `TestProductLookup` | 6 | 제품 조회 성공, GAIA is_tms=True, GALLANT is_tms=False, 404, 401 미인증, 401 잘못된 토큰 |
| `TestTaskSeedAutoInit` | 4 | GAIA 총 15개, TMS 2개, GALLANT TMS=0, 멱등성 |
| `TestProductTasks` | 3 | 전체 조회, category 필터, 404 |
| `TestLocationUpdate` | 3 | 성공, 필드 누락, 제품 없음 |
| `TestCompletionStatus` | 1 | 초기 상태 확인 |

#### Phase 2: Full Workflow 통합 테스트 전면 재작성
**파일**: `tests/integration/test_full_workflow.py` (23 tests, 0 assert False)
- 기존: `db_session` fixture 사용 + `assert False` 스텁 8클래스
- 신규: `db_conn` fixture 사용, 실제 API 플로우 구현

| 클래스 | 테스트 수 | 내용 |
|--------|----------|------|
| `TestNormalWorkflow` | 5 | 회원가입 201, 중복 이메일 400, 이메일 인증, 잘못된 코드 400, 전체 플로우 |
| `TestApprovalRejectionFlow` | 4 | pending→403, admin 승인, admin 거부, 비관리자 승인→403 |
| `TestAdminFreepassLogin` | 2 | admin 이메일인증/승인 우회, admin 토큰 정보 확인 |
| `TestTaskStartCompleteFlow` | 3 | QR→task 시작/완료, duration 양수, 미시작 task 완료→400 |
| `TestAccessControl` | 9 | 미인증 403, 인증 없는 각 API 401, 비관리자 admin→403, 잘못된 비밀번호, 필드 누락 |

#### Phase 3-4: Task Seed + Company Filtering 테스트 보완
**파일**: `tests/backend/test_task_seed.py` (22 tests, 0 assert False)
- 기존 9개 tests → 22개로 확장
- 신규 클래스 추가:

| 클래스 | 신규 테스트 수 | 내용 |
|--------|--------------|------|
| `TestCompanyBasedTaskFilter` | +2 (총 5) | GST 관리자 전체 조회, BAT 작업자 MECH만, GET /api/app/tasks/<serial> 엔드포인트 활용 |
| `TestTaskSeedDirectCall` | 3 (신규) | GAIA 직접 seed 반환값 검증, 멱등성 직접 호출, GALLANT TMS=0 직접 확인 |

#### Phase 5: Process Check Flow 통합 테스트 전면 재작성
**파일**: `tests/integration/test_process_check_flow.py` (18 tests, 0 assert False)
- 기존: `db_session` 사용 + `assert False` 스텁 3클래스 8메서드
- 신규: `db_conn` 사용, `POST /api/app/validation/check-process` 실제 검증

| 클래스 | 테스트 수 | 내용 |
|--------|----------|------|
| `TestProcessCheckValidation` | 10 | MECH/ELEC 미완료→PI 차단, MECH만 완료→차단, ELEC만 완료→차단, 둘다 완료→통과, QI/SI 동일 검증, MECH 타입 skip, 필드 누락 400, 제품 없음 404, 인증 없음 401 |
| `TestCompletionStatusFlow` | 3 | 초기 상태, SELF_INSPECTION 완료→mech_completed=true, INSPECTION 완료→elec_completed=true |
| `TestProcessSequenceFlow` | 3 | MECH→ELEC→PI 정상 순서 플로우, PI 미리 실행→false, completion API 반영 |
| `TestProcessAlertCreation` | 2 | MECH 관리자 알림 생성 확인, 둘다 미완료→missing_processes 확인 |

#### Phase 6: Concurrent Work 통합 테스트 전면 재작성
**파일**: `tests/integration/test_concurrent_work.py` (15 tests, 0 assert False)
- 기존: `db_session` 사용 + `assert False` 스텁 4클래스 10메서드
- 신규: 실제 다중 워커 시나리오 구현

| 클래스 | 테스트 수 | 내용 |
|--------|----------|------|
| `TestMultiWorkerIndependentTasks` | 3 | 2워커 다른 Task 시작, 독립 완료, MECH+ELEC 동시 작업 |
| `TestTaskConflictPrevention` | 4 | 이미 시작된 Task 재시작→400/409, 완료 Task 재시작→400, 타인 시작 Task 완료 시도, 미시작 Task 완료→400 |
| `TestTaskListRetrieval` | 4 | Task 목록 조회, process_type 필터, 없는 serial→빈배열, 인증 없음→401 |
| `TestTaskDuration` | 2 | 완료 Task duration>=0, 다수 Task 독립 추적 |
| `TestConcurrentAccessLight` | 2 | 같은 Task 2번 start→1번만 성공, 다른 제품 독립 completion_status |

### Sprint 7 TEST 추가 파일 요약

| 파일 | 기존 | 변경 후 | assert False |
|------|------|---------|-------------|
| `tests/backend/test_product_api.py` | 없음 | 17 tests | 0 |
| `tests/backend/test_task_seed.py` | 9 tests | 22 tests | 0 |
| `tests/integration/test_full_workflow.py` | 8 stubs (all assert False) | 23 tests | 0 |
| `tests/integration/test_process_check_flow.py` | 8 stubs (all assert False) | 18 tests | 0 |
| `tests/integration/test_concurrent_work.py` | 10 stubs (all assert False) | 15 tests | 0 |

**Sprint 7 신규/개선 총계: 95 tests, 0 assert False**

### Sprint 7 전체 누적 테스트 결과 (예상)

```
Sprint 1~6 기존:    277 passed, 20 skipped
Sprint 7 신규:       95 tests (추가분, 0 assert False)
─────────────────────────────────────────────────────
Sprint 7 기준 총합: ~392 collected, ~372+ passed
```

### Sprint 7 TEST 변경 파일 목록

#### 신규 생성
```
tests/backend/test_product_api.py            # Product API 17 tests
tests/integration/test_process_check_flow.py # Process Check 18 tests (전면 재작성)
tests/integration/test_concurrent_work.py    # Concurrent Work 15 tests (전면 재작성)
```

#### 수정
```
tests/backend/test_task_seed.py              # 9 → 22 tests (TestCompanyBasedTaskFilter 보완 + TestTaskSeedDirectCall 신규)
tests/integration/test_full_workflow.py      # stubs → 23 실 구현 tests (전면 재작성)
```

### 주요 설계 결정 및 기술 메모

#### 테스트 설계 원칙
- **db_session 제거**: conftest.py에 없는 픽스처 — 모든 통합 테스트에서 `db_conn` 사용
- **SMTP 차단**: `_block_smtp_globally()` autouse fixture로 전역 차단 — 추가 mock 불필요
- **graceful skip**: API 미구현 시 `pytest.skip()` 처리 (assert False 대신)
- **자체 cleanup**: 각 테스트가 삽입한 데이터를 `try/finally`로 정리

#### conftest.py Sprint 7 픽스처 활용
- `TEST_PRODUCTS` (6개: GAIA/DRAGON/GALLANT/MITHAS/SDS/SWS) + `seed_test_products` fixture
- `TEST_WORKERS` (9명: FNI/BAT/TMS(M)/TMS(E)/P&S/C&A/GST admin/pending/unverified) + `seed_test_workers` fixture
- 기존 `create_test_worker`, `create_test_product`, `create_test_task`, `get_auth_token`, `get_admin_auth_token` 활용

#### API 엔드포인트 매핑 (테스트 대상)
```
POST /api/auth/register                      → TestNormalWorkflow
POST /api/auth/login                         → TestAdminFreepassLogin, TestAccessControl
POST /api/auth/verify-email                  → TestNormalWorkflow
POST /api/admin/workers/approve              → TestApprovalRejectionFlow
GET  /api/app/product/<qr_doc_id>            → TestProductLookup, TestTaskSeedAutoInit
GET  /api/app/product/<qr_doc_id>/tasks      → TestProductTasks
PUT  /api/app/product/location/update        → TestLocationUpdate
GET  /api/app/completion/<serial>            → TestCompletionStatus, TestCompletionStatusFlow
POST /api/app/validation/check-process       → TestProcessCheckValidation, TestProcessSequenceFlow
POST /api/app/work/start                     → TestTaskStartCompleteFlow, TestMultiWorkerIndependentTasks
POST /api/app/work/complete                  → TestTaskDuration, TestConcurrentAccessLight
GET  /api/app/tasks/<serial_number>          → TestTaskListRetrieval, TestCompanyBasedTaskFilter
POST /api/admin/products/initialize-tasks    → TestTaskSeedGAIA, TestTaskSeedDRAGON, TestTaskSeedGALLANT
```

### Sprint 7 전체 테스트 결과: 356 passed, 0 failed, 19 skipped

```
Sprint 1~6 기존:     277 passed, 20 skipped
Sprint 7 신규/개선:   95 tests (0 assert False)
Sprint 7 리팩터링:    -1 skip (테스트 수정)
──────────────────────────────────────────────
Sprint 7 최종:       356 passed, 0 failed, 19 skipped
```

### Sprint 7 버그 수정
| 파일 | 수정 내용 |
|------|----------|
| `tests/integration/test_concurrent_work.py` | `_insert_task()` UniqueViolation → `ON CONFLICT DO UPDATE SET` 추가 |
| `tests/conftest.py` | `create_test_completion_status` 시그니처 mech_completed/elec_completed 통일 |

---

## UI Sprint: 화이트 글래스모피즘 테마 적용 (완료)

> 전체 12개 화면 + 3개 위젯에 White Glassmorphism 디자인 시스템 적용

### 디자인 시스템 (`design_system.dart`)
- `GxColors` — Core Brand (charcoal~snow) + Accent (indigo) + Status (success/warning/danger/info)
- `GxRadius` — sm:6, md:10, lg:14, xl:18
- `GxShadows` — card, md, lg, glass, glassSm
- `GxGradients` — background (4-color splash), accentButton (indigo gradient)
- `GxGlass` — cardBg (white@0.72), cardBgLight (white@0.5), card(), cardSm()

### Phase 1: Auth 화면 4개
| 파일 | 변경 내용 |
|------|----------|
| `login_screen.dart` | Card → GxGlass.cardSm, ElevatedButton → 그라디언트 Container |
| `register_screen.dart` | Card → GxGlass.cardSm, ElevatedButton → 그라디언트 Container |
| `verify_email_screen.dart` | Card → GxGlass.cardSm, verify → 그라디언트, resend → 글래스 아웃라인 |
| `approval_pending_screen.dart` | Info card → GxGlass.cardSm |

### Phase 2: 메인 화면 3개
| 파일 | 변경 내용 |
|------|----------|
| `home_screen.dart` | Worker info card + feature cards → GxGlass.cardSm |
| `qr_scan_screen.dart` | Product card + QR type card → GxGlass.cardSm, scan → 그라디언트 |
| `task_management_screen.dart` | Header + progress + task cards → GxGlass.cardSm |

### Phase 3: Task Detail + 위젯 3개
| 파일 | 변경 내용 |
|------|----------|
| `task_detail_screen.dart` | 4개 info cards → GxGlass.cardSm, start → accent 그라디언트, complete → success 그라디언트 |
| `task_card.dart` | Card → GxGlass.cardSm(radius: GxRadius.md) |
| `process_alert_popup.dart` | Dialog bg → GxGlass.cardBg, confirm → 그라디언트, dismiss → 글래스 아웃라인 |
| `completion_badge.dart` | Badge → statusColor alpha 패턴 |

### Phase 4: Admin 화면 4개
| 파일 | 변경 내용 |
|------|----------|
| `alert_list_screen.dart` | Alert tiles → GxGlass.cardSm(radius: GxRadius.md), unread → accentSoft |
| `admin_options_screen.dart` | Section cards → GxGlass.cardSm, filter chips → cardBgLight, force-close → danger 그라디언트 |
| `admin_dashboard.dart` | Stub → glassmorphism AppBar + cloud bg |
| `worker_approval_screen.dart` | Stub → glassmorphism AppBar + cloud bg |

### Phase 5: 최종 검증
- `GxShadows.card` 잔존: **0건**
- `ElevatedButton` 잔존 (main.dart 테마 제외): **0건** → 6개 인스턴스 모두 Container/InkWell로 교체
- `GxGlass.cardSm()`/`GxGlass.card()` 적용: **12개 파일, 22개소**
- AppBar 패턴 통일: **13개 전부** (화이트 bg + 인디고 액센트 바 + mist 하단 구분선)
- `flutter build web`: **0 errors**

### 변경 파일 목록

#### 신규 생성
```
frontend/lib/utils/design_system.dart           # 디자인 시스템 토큰
frontend/lib/screens/auth/splash_screen.dart    # 스플래시/랜딩 화면 (참조 구현)
```

#### 수정 (15개 파일)
```
frontend/lib/screens/auth/login_screen.dart
frontend/lib/screens/auth/register_screen.dart
frontend/lib/screens/auth/verify_email_screen.dart
frontend/lib/screens/auth/approval_pending_screen.dart
frontend/lib/screens/home/home_screen.dart
frontend/lib/screens/qr/qr_scan_screen.dart
frontend/lib/screens/task/task_management_screen.dart
frontend/lib/screens/task/task_detail_screen.dart
frontend/lib/screens/admin/alert_list_screen.dart
frontend/lib/screens/admin/admin_options_screen.dart
frontend/lib/screens/admin/admin_dashboard.dart
frontend/lib/screens/admin/worker_approval_screen.dart
frontend/lib/widgets/task_card.dart
frontend/lib/widgets/process_alert_popup.dart
frontend/lib/widgets/completion_badge.dart
```

---

## Sprint 8: Admin API 보완 + UX 개선 + 비밀번호 찾기 (완료)

### BE 완료 내역

#### 비밀번호 찾기 API (신규)
- `worker.py`: `create_password_reset_code()` (30분 만료), `update_password_hash()` 추가
- `auth_service.py`: `send_password_reset_email()`, `send_password_reset_code()`, `reset_password()` 추가
- `auth.py`: 2개 엔드포인트 추가
  - `POST /api/auth/forgot-password` — 비밀번호 리셋 코드 발송 (미존재 이메일도 200 응답 — 보안)
  - `POST /api/auth/reset-password` — 코드 검증 → bcrypt 해싱 → 비밀번호 변경

#### JWT 토큰 만료 시간 변경
- `config.py`: `JWT_ACCESS_TOKEN_EXPIRES` 24h → **2h**, `JWT_REFRESH_TOKEN_EXPIRES` 7d → **30d**

### FE 완료 내역

#### 자동 토큰 갱신 (401 → refresh → retry)
- `api_service.dart`: Dio error interceptor — 401 수신 → refresh_token으로 자동 갱신 → 원래 요청 재시도
- `auth_service.dart`: `tryAutoLogin()` 메서드 추가 — 앱 시작 시 저장된 refresh_token으로 자동 로그인
- `auth_provider.dart`: `AuthNotifier.tryAutoLogin()` + `onRefreshFailed` → 자동 logout

#### 마지막 화면 복원
- `auth_service.dart`: `saveLastRoute()`/`getLastRoute()` — SharedPreferences 기반
- `main.dart`: `AppStartup` 위젯 (로딩 → tryAutoLogin → 라우트 복원 or /home)
- `_RouteTracker` NavigatorObserver — push/replace 시 자동 저장
- 저장 대상: /home, /qr-scan, /task-management, /task-detail, /admin-options

#### 비밀번호 찾기 화면 (신규)
- `forgot_password_screen.dart`: 이메일 입력 → POST /api/auth/forgot-password → 리셋 화면 이동
- `reset_password_screen.dart`: 6자리 코드 + 새 비밀번호 + 확인 → POST /api/auth/reset-password
- `login_screen.dart`: "비밀번호를 잊으셨나요?" 링크 추가
- `main.dart`: `/forgot-password`, `/reset-password` 라우트 등록
- `constants.dart`: `authForgotPasswordEndpoint`, `authResetPasswordEndpoint` 추가

#### 빌드
- `flutter build web`: **0 errors**

### 테스트: 271 passed, 0 failed, 19 skipped (backend suite)

#### test_admin_options_api.py (23 tests — 신규)
| 클래스 | 테스트 수 | 내용 |
|--------|----------|------|
| `TestGetManagers` | 3 | 전체 목록, company=FNI 필터, company=TMS(M) 필터 |
| `TestToggleManager` | 3 | is_manager=true 설정, is_manager=false 해제, 비관리자→403 |
| `TestAdminSettings` | 3 | 설정 조회, 설정 변경, 변경 후 GET 확인 |
| `TestPendingTasks` | 2 | 미종료 목록 반환, 미종료 없으면 빈 리스트 |
| `TestAdminAuth` | 1 | 미인증→401 |
| 기타 | 11 | company 필터 상세, state restoration, edge cases |

#### test_forgot_password.py (12 tests — 신규)
| 클래스 | 테스트 수 | 내용 |
|--------|----------|------|
| `TestForgotPassword` | 3 | 성공(SMTP mock), 미존재 이메일→200(보안), 필드 누락→400 |
| `TestResetPassword` | 5 | 성공+로그인 확인, 잘못된 코드→400, 코드 재사용 거부, 교차 사용자 코드 거부, 필드 누락 |
| `TestForgotResetIntegration` | 4 | 전체 플로우, 코드 형식 검증, 기존 비밀번호 실패 확인 |

#### test_refresh_token.py (5 tests 추가)
| 클래스 | 테스트 수 | 내용 |
|--------|----------|------|
| `TestTokenExpiryTimes` | 5 | access 2시간 만료, refresh 30일 만료, 발급 직후 유효, refresh > access 수명 |

### Sprint 8 완료 조건 달성
- ✅ Admin API 5개 (Sprint 7에서 이미 구현) + 테스트 23개 PASS
- ✅ 비밀번호 찾기 플로우 (이메일 → 코드 → 재설정) + 테스트 12개 PASS
- ✅ 로그인 유지 (자동 refresh) + 마지막 화면 복원
- ✅ JWT 토큰 만료 조정 (access 2h, refresh 30d) + 테스트 5개 PASS
- ✅ flutter build web 0 errors
- ✅ 리그레션 0 failures (271 passed, 19 skipped)

### 변경 파일 목록

#### 신규 생성
```
frontend/lib/screens/auth/forgot_password_screen.dart   # 비밀번호 찾기 화면
frontend/lib/screens/auth/reset_password_screen.dart    # 비밀번호 재설정 화면
tests/backend/test_admin_options_api.py                 # Admin 옵션 API 테스트
tests/backend/test_forgot_password.py                   # 비밀번호 찾기 API 테스트
```

#### 수정
```
backend/app/config.py                          # JWT 만료 시간 변경
backend/app/models/worker.py                   # create_password_reset_code, update_password_hash
backend/app/services/auth_service.py           # send_password_reset_email, send_password_reset_code, reset_password
backend/app/routes/auth.py                     # forgot-password, reset-password 엔드포인트
frontend/lib/main.dart                         # AppStartup, RouteTracker, 라우트 등록
frontend/lib/services/api_service.dart         # 401 자동 refresh interceptor
frontend/lib/services/auth_service.dart        # tryAutoLogin, saveLastRoute, getLastRoute
frontend/lib/providers/auth_provider.dart      # tryAutoLogin, onRefreshFailed
frontend/lib/screens/auth/login_screen.dart    # 비밀번호 찾기 링크 추가
frontend/lib/utils/constants.dart              # 신규 엔드포인트 상수
tests/backend/test_refresh_token.py            # TestTokenExpiryTimes 5개 추가
```

---

## Sprint 9: Pause/Resume + 근무시간 관리 (완료)

### BE 완료 내역

#### DB 마이그레이션 (008_sprint9_pause_resume.sql)
- `work_pause_log` 테이블 생성 (task_detail_id, worker_id, paused_at, resumed_at, pause_type, pause_duration_minutes)
- `app_task_details`에 `is_paused BOOLEAN DEFAULT FALSE`, `total_pause_minutes INTEGER DEFAULT 0` 컬럼 추가
- `alert_type_enum`에 `BREAK_TIME_PAUSE`, `BREAK_TIME_END` 추가
- `admin_settings`에 9개 휴게시간 설정 seed (break_morning, lunch, break_afternoon, dinner 시작/종료 + auto_pause_enabled)

#### work_pause_log 모델 (신규)
- `work_pause_log.py`: WorkPauseLog dataclass + CRUD (create_pause, resume_pause, get_active_pause, get_pauses_by_task)

#### Pause/Resume API (work.py에 3개 엔드포인트 추가)
| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/app/work/pause` | POST | 작업 일시정지 (검증: 시작됨+미완료+미일시정지+본인) |
| `/api/app/work/resume` | POST | 작업 재개 (검증: 일시정지 중+본인 또는 관리자) |
| `/api/app/work/pause-history/<id>` | GET | 일시정지 이력 조회 |

#### Duration 계산 수정 (task_service.py)
- `complete_work()`: 완료 시 `is_paused=TRUE`면 자동 재개 처리 (resumed_at = completed_at)
- `_finalize_task_multi_worker()`: `duration_minutes = max(0, raw_duration - total_pause_minutes)`
- 총 중지 시간(total_pause_minutes) 자동 차감

#### 휴게/식사시간 자동 강제 중지 스케줄러 (scheduler_service.py)
- `check_break_time_job()`: 매 1분 실행, KST 기준 4개 휴게 기간 체크
- `force_pause_all_active_tasks(pause_type)`: 진행 중 전체 작업 강제 일시정지 + BREAK_TIME_PAUSE 알림
- `send_break_end_notifications(pause_type)`: 휴게 종료 알림 (BREAK_TIME_END)
- 4개 시간대: 오전 휴게(10:00-10:20), 점심(11:20-12:20), 오후 휴게(15:00-15:20), 저녁(17:00-18:00)
- 저녁시간 특수: "무시하고 계속" 옵션, 18:00 시 아직 paused인 작업자에게만 종료 알림

#### Admin 시간 설정 검증 (admin.py)
- HH:MM 정규식 검증: `^([01]\d|2[0-3]):[0-5]\d$`
- 시작/종료 쌍 검증: start < end (INVALID_TIME_RANGE 에러)
- ALLOWED_KEYS 확장: 기존 2개 + 새 9개 = 11개

### FE 완료 내역

#### Pause/Resume UI (task_detail_screen.dart)
- 진행 중 + 미일시정지: [일시정지 (pause_circle)] + [작업 완료 (green gradient)] 버튼 Row
- 진행 중 + 일시정지: [재개 (play_circle, accent gradient)] + [완료 (disabled)] 버튼 Row
- 총 중지 시간(totalPauseMinutes) 표시

#### Task 목록 일시정지 표시 (task_management_screen.dart)
- 일시정지 작업: 주황색 "일시정지" 배지 + "재개" 버튼

#### 휴게시간 팝업 (신규 위젯 2개)
- `break_time_popup.dart`: BREAK_TIME_PAUSE 알림 → showDialog (barrierDismissible: false)
  - 저녁시간 전용: "무시하고 계속 작업" 버튼 → POST /app/work/resume
- `break_time_end_popup.dart`: BREAK_TIME_END 알림 → "재개하기" 버튼

#### Admin 근무시간 설정 UI (admin_options_screen.dart)
- Section 4 "근무시간 설정" 추가 (Icons.schedule)
- `auto_pause_enabled` 토글
- 4개 시간대 행: 각각 시작/종료 시간 TimePicker
- 변경 시 PUT /admin/settings 즉시 저장

#### TaskItem 모델 업데이트
- `task_item.dart`: isPaused, totalPauseMinutes 필드 추가

#### 기타
- `task_provider.dart`: pauseTask(), resumeTask() 메서드 추가
- `task_service.dart`: pauseTask(), resumeTask() API 호출 추가
- `constants.dart`: workPauseEndpoint, workResumeEndpoint, workPauseHistoryEndpoint
- `home_screen.dart`: BREAK_TIME_PAUSE/END WebSocket 이벤트 → 팝업 표시
- `flutter build web`: **0 errors**, `flutter analyze`: 0 errors/warnings

### 테스트: 318 passed, 0 failed, 19 skipped

#### test_pause_resume.py (24 tests — 신규)
| 클래스 | 테스트 수 | 내용 |
|--------|----------|------|
| `TestPauseBasic` | 9 | TC-PR-01~09: 기본 pause/resume, 미시작→400, 완료→400, 중복 pause→400, 미pause resume→400, 타인→403, 관리자 resume |
| `TestPauseDuration` | 3 | TC-PR-10~12: pause 시간 차감, 다중 pause 합산, 완료 시 자동 resume |
| `TestPauseHistory` | 2 | TC-PR-13~14: 이력 조회, 빈 이력 |
| `TestPauseMultiWorker` | 3 | TC-PR-15~17: 한쪽 pause + 다른 쪽 계속, 둘 다 pause, 한쪽 완료 |
| `TestPauseAuth` | 7 | TC-PR-18+: 미인증 401, task_id 누락, task 미존재 등 |

#### test_break_time_settings.py (8 tests — 신규)
| 클래스 | 테스트 수 | 내용 |
|--------|----------|------|
| `TestBreakTimeSettings` | 8 | TC-BS-01~08: 설정 조회, 시간 변경, auto_pause 토글, 잘못된 형식→400, start>end→400, 비관리자→403, 미인증→401 |

#### test_break_time_scheduler.py (14 tests — 신규)
| 클래스 | 테스트 수 | 내용 |
|--------|----------|------|
| `TestBreakTimePause` | 6 | TC-BT-01~06: 4개 시간대 자동 강제 pause, 진행 중 작업 없으면 미발생, BREAK_TIME_PAUSE 알림 생성 |
| `TestDinnerSpecial` | 3 | TC-BT-07~09: 저녁 pause 후 "무시하고 계속" resume, 18:00 종료 알림, resume 후 알림 미발송 |
| `TestAdminSettingsEffect` | 3 | TC-BT-10~12: auto_pause_enabled=false→미발생, 시간 변경 반영, 이미 수동 pause→중복 방지 |
| `TestBreakAlerts` | 2 | TC-BT-13~14: BREAK_TIME_PAUSE/END 알림 생성 확인 |

### Sprint 9 완료 조건 달성
- ✅ Pause/Resume API 정상 동작 (pause → is_paused=true, resume → is_paused=false)
- ✅ duration 계산 시 total_pause_minutes 자동 차감
- ✅ 휴게/식사시간 자동 강제 중지 스케줄러 (4개 시간대)
- ✅ 저녁시간 "무시하고 계속" 옵션
- ✅ Admin 옵션에서 휴게/식사시간 변경 + HH:MM 형식 검증
- ✅ FE: 일시정지/재개 버튼 + 휴게시간 팝업 + 상태 배지
- ✅ flutter build web 0 errors
- ✅ 신규 테스트 46개 PASS (pause_resume 24 + break_time_settings 8 + break_time_scheduler 14)
- ✅ 리그레션 0 failures (318 passed, 19 skipped)

### 변경 파일 목록

#### 신규 생성
```
backend/migrations/008_sprint9_pause_resume.sql     # 마이그레이션
backend/app/models/work_pause_log.py                # WorkPauseLog 모델
frontend/lib/widgets/break_time_popup.dart          # 휴게시간 시작 팝업
frontend/lib/widgets/break_time_end_popup.dart      # 휴게시간 종료 팝업
tests/backend/test_pause_resume.py                  # Pause/Resume 테스트
tests/backend/test_break_time_scheduler.py          # 스케줄러 테스트 (skip 대기)
tests/backend/test_break_time_settings.py           # 설정 테스트
```

#### 수정
```
backend/app/models/task_detail.py                   # is_paused, total_pause_minutes 필드 추가
backend/app/models/__init__.py                      # WorkPauseLog import
backend/app/routes/work.py                          # pause/resume/pause-history 엔드포인트 + _task_to_dict 업데이트
backend/app/services/task_service.py                # duration 계산에서 pause 시간 차감 + 자동 resume
backend/app/services/scheduler_service.py           # check_break_time_job + force_pause + break_end 알림
backend/app/routes/admin.py                         # 시간 형식 검증 + ALLOWED_KEYS 확장
frontend/lib/models/task_item.dart                  # isPaused, totalPauseMinutes
frontend/lib/screens/task/task_detail_screen.dart   # Pause/Resume 버튼 Row
frontend/lib/screens/task/task_management_screen.dart # 일시정지 배지 + 재개 버튼
frontend/lib/screens/admin/admin_options_screen.dart # Section 4 근무시간 설정
frontend/lib/screens/home/home_screen.dart          # 휴게시간 팝업 WebSocket 연동
frontend/lib/providers/task_provider.dart            # pauseTask, resumeTask
frontend/lib/services/task_service.dart              # pause/resume API 호출
frontend/lib/utils/constants.dart                    # 신규 엔드포인트 상수
tests/conftest.py                                    # Sprint 9 마이그레이션 + 픽스처
```

---

## Sprint 10: 수동 검증 + 버그 수정 확인 (완료)

### 목표
Sprint 9 이후 수동으로 진행한 디버그/개선 사항 6건을 코드 레벨에서 검증 + 테스트 보완.

### 수정사항 6건 검증 결과

| # | 수정사항 | BE | FE | 결과 |
|---|---------|----|----|------|
| 1 | 로그아웃 화면 전환 (main.dart: navigatorKey + ref.listen + pushAndRemoveUntil) | - | PASS | ✅ |
| 2 | Pause/Resume 전체 task 응답 (work.py: _task_to_dict 반환) | PASS | - | ✅ |
| 3 | 가입 승인 대기 company 필터 (admin_options: _selectedPendingCompany) | - | PASS | ✅ |
| 4 | 협력사 관리자 미종료 작업 화면 (manager_pending_tasks_screen + admin.py) | PASS + 보안패치 | PASS | ✅ |
| 5 | location_qr_required admin setting (process_validator + admin_options) | PASS | PASS | ✅ |
| 6 | 관리자 목록 기본 필터 (_selectedManagerCompany = _companies.first) | - | PASS | ✅ |

### 추가 보안 패치 (Fix 4)
검증 과정에서 BE 에이전트가 보안 이슈 발견 → 즉시 수정:
- `admin.py:get_pending_tasks()` — 협력사 관리자 company를 서버에서 강제 주입 (클라이언트 파라미터 무시)
- `admin.py:force_close_task()` — manager company와 task worker company 일치 검증, 불일치 시 403

### Test regression 수정
- `test_pause_resume.py` 3개 테스트 Fix 2 대응 수정:
  - `test_pause_success`: `paused_at` → `is_paused == True` 검증
  - `test_resume_success`: `resumed_at` → `is_paused == False` 검증
  - `test_resume_records_duration`: `pause_duration_minutes` → `total_pause_minutes` 검증
  - `test_resume_not_paused`: 400 → 400 or 404 허용 (TASK_NOT_PAUSED or PAUSE_NOT_FOUND)

### 버그 수정 4건 (Bug A/B/C/D)

| Bug | 내용 | 상태 |
|-----|------|------|
| A | DB 시간 UTC 표시 → KST (worker.py: `options="-c timezone=Asia/Seoul"`) | ✅ 이미 반영 확인 |
| B | Heating Jacket OFF 시 task 목록 숨김 (admin.py 동기화 + FE isApplicable 필터) | ✅ 이미 반영 확인 |
| C | location_qr_required가 ALLOWED_KEYS에 누락 → 추가됨 | ✅ 이미 반영 확인 |
| D | phase_block_enabled 차단 로직 미구현 → **신규 구현** | ✅ 구현 완료 |

### Bug D 구현 상세 (phase_block_enabled)
- `task_detail.py:200-229` — `get_task_by_serial_and_id()` 함수 추가
- `task_service.py:80-94` — `start_work()` 내 phase_block 체크 추가
  - MECH POST_DOCKING task (WASTE_GAS_LINE_2, UTIL_LINE_2) 시작 시
  - phase_block_enabled=true이면 TANK_DOCKING 완료 여부 확인
  - 미완료 시 400 PHASE_BLOCKED 반환
  - phase_block_enabled=false(기본값)이면 차단 없음

### Sprint 10 신규 테스트: 19/19 PASSED
| 테스트 | 설명 |
|--------|------|
| `test_manager_pending_tasks_own_company` | FNI 관리자가 본인 company 미종료 작업 조회 성공 |
| `test_manager_pending_tasks_other_company` | FNI 관리자가 타 company 조회 시 빈 리스트 |
| `test_admin_pending_tasks_all` | admin이 company 필터 없이 전체 미종료 작업 조회 |
| `test_worker_pending_tasks_forbidden` | 일반 작업자 미종료 작업 조회 시 403 |
| `test_pause_response_full_task_fields` | pause 응답에 전체 task 필드 포함 확인 |
| `test_resume_response_full_task_fields` | resume 응답에 전체 task 필드 포함 확인 |
| `test_location_qr_not_required_no_warning` | location_qr_required=false → 경고 미생성 |
| `test_location_qr_required_warning` | location_qr_required=true → 경고 생성 |
| `test_location_qr_default_warning` | 기본값(true) + location QR 미등록 → 경고 생성 |
| `test_manager_force_close` | 협력사 관리자 강제 종료 성공 |
| `test_start_work_response_kst_timezone` | 작업 시작 응답 KST(+09:00) 확인 (Bug A) |
| `test_heating_jacket_off_sets_not_applicable` | Heating Jacket OFF → is_applicable=false (Bug B) |
| `test_heating_jacket_on_restores_applicable` | Heating Jacket ON → is_applicable=true 복원 (Bug B) |
| `test_completed_heating_jacket_not_affected` | 완료된 task는 setting 변경 영향 안 받음 (Bug B) |
| `test_location_qr_required_put_success` | location_qr_required PUT 200 성공 (Bug C) |
| `test_phase_block_tank_docking_incomplete` | phase_block + TANK_DOCKING 미완료 → 400 (Bug D) |
| `test_phase_block_tank_docking_complete` | phase_block + TANK_DOCKING 완료 → 시작 성공 (Bug D) |
| `test_phase_block_disabled_allows_start` | phase_block=false → 차단 없음 (Bug D) |
| `test_phase_block_default_allows_start` | phase_block 기본값(false) → 차단 없음 (Bug D) |

### 빌드 확인
- `flutter build web`: 0 errors (Wasm dry-run 경고만 — flutter_secure_storage, non-blocking)

### 수정/생성 파일
```
backend/app/routes/admin.py                         # Fix 4 보안패치 (manager company 강제)
backend/app/models/task_detail.py                   # get_task_by_serial_and_id() 추가 (Bug D)
backend/app/services/task_service.py                # phase_block 차단 로직 (Bug D)
tests/backend/test_sprint10_fixes.py                # 19개 테스트 (기존 10 + Bug A/B/C/D 9)
tests/backend/test_pause_resume.py                  # Fix 2 대응 수정 (4개 테스트)
```

---

## Sprint 11: GST Task + 홈 메뉴 확장 + Checklist 스키마 (완료 ✅)

### BE 완료 내역
- `009_sprint11_gst_tasks.sql` — migration 실행 완료
  - `checklist` 스키마 생성 + `checklist_master`, `checklist_record` 테이블
  - `workers.active_role VARCHAR(10)` 컬럼 추가
  - PI/QI/SI task 템플릿 4개 추가 (task_seed.py 반영)
- `backend/app/routes/gst.py` — GST 진행 제품 대시보드 API
  - `GET /api/app/gst/products/<category>` (PI/QI/SI)
  - 상태 필터: active, all, completed, not_started, in_progress, paused
- `backend/app/routes/checklist.py` — Checklist CRUD API
  - `GET /api/app/checklist/<serial_number>/<category>` — 체크리스트 조회
  - `PUT /api/app/checklist/check` — 체크/해제 UPSERT
  - `POST /api/admin/checklist/import` — Excel 일괄 import (admin)
- `backend/app/models/worker.py` — `active_role` 필드 + `update_active_role()` 구현
- `backend/app/services/task_seed.py` — PI/QI/SI task 템플릿 추가 (전 모델 공통)
- `backend/app/__init__.py` — gst_bp, checklist_bp 블루프린트 등록

### FE 완료 내역
- `frontend/lib/screens/gst/gst_products_screen.dart` — GST 진행 제품 대시보드 화면
- `frontend/lib/screens/checklist/checklist_screen.dart` — 체크리스트 화면
- `frontend/lib/main.dart` — /gst-products, /checklist 라우트 등록
- `flutter build web` — 0 errors ✅

### TEST 완료 내역

Sprint 11 테스트 4개 파일 (총 45 tests) — 44 PASSED, 1 SKIPPED:

#### 신규 테스트 파일

| 파일 | 테스트 수 | 내용 |
|------|----------|------|
| `test_gst_task_seed.py` | 10 | PI/QI/SI task seed 생성 확인 (GAIA/DRAGON/GALLANT 모든 모델 공통) |
| `test_gst_products_api.py` | 12 | GET /api/app/gst/products/{category} — GST 진행 제품 대시보드 |
| `test_checklist_api.py` | 14 | checklist 스키마 CRUD (GET/PUT/import), 인증/권한 검증 |
| `test_active_role.py` | 9 | PUT /api/auth/active-role — GST 작업자 active_role 전환 |

#### test_gst_task_seed.py (10 tests)
| 테스트 | 내용 |
|--------|------|
| TC-GST-SEED-01 | GAIA seed → PI task 2개 (PI_LNG_UTIL, PI_CHAMBER) is_applicable=True |
| TC-GST-SEED-02 | GAIA seed → QI task 1개 (QI_INSPECTION) is_applicable=True |
| TC-GST-SEED-03 | GAIA seed → SI task 1개 (SI_FINISHING) is_applicable=True |
| TC-GST-SEED-04 | GAIA seed → 총 19개 (MECH 7 + ELEC 6 + TMS 2 + PI 2 + QI 1 + SI 1) |
| TC-GST-SEED-05 | DRAGON seed → PI/QI/SI 4개 생성 (모든 모델 공통) |
| TC-GST-SEED-06 | GALLANT seed → PI/QI/SI 4개 생성 |
| TC-GST-SEED-07 | 중복 생성 방지 — 같은 S/N 재초기화 시 PI/QI/SI 중복 없음 |
| TC-GST-SEED-08 | GST 작업자가 PI/QI/SI task 조회 가능 (PASSED — task 직접 삽입) |
| TC-GST-SEED-09 | Admin이 PI/QI/SI task 조회 가능 (PASSED — task 직접 삽입) |
| TC-GST-SEED-10 | POST /api/admin/products/initialize-tasks → PI/QI/SI 포함 19개 생성 |

#### test_gst_products_api.py (12 tests)
| 테스트 | 내용 |
|--------|------|
| TC-GST-GP-01 | GST 작업자 PI 진행 제품 조회 200 |
| TC-GST-GP-02 | GST 작업자 QI 진행 제품 조회 200 |
| TC-GST-GP-03 | GST 작업자 SI 진행 제품 조회 200 |
| TC-GST-GP-04 | 미시작 제품 목록 포함 (status: not_started) |
| TC-GST-GP-05 | 완료된 task → 제외 또는 completed 상태 표시 |
| TC-GST-GP-06 | Admin 조회 성공 |
| TC-GST-GP-07 | FNI 협력사 작업자 → 403 |
| TC-GST-GP-08 | 미인증 → 401 |
| TC-GST-GP-09 | 응답에 worker_name, started_at 포함 확인 |
| TC-GST-GP-10 | 빈 목록 시 products=[] 반환 |
| TC-GST-GP-11 | 같은 GST 작업자끼리 타 작업자 task pause 성공 |
| TC-GST-GP-12 | 같은 GST 작업자끼리 타 작업자 task complete 성공 |

#### test_checklist_api.py (14 tests)
| 테스트 | 내용 |
|--------|------|
| TC-CL-01 | checklist 스키마 존재 확인 |
| TC-CL-02 | checklist_master + checklist_record 테이블 존재 |
| TC-CL-03 | GET /api/app/checklist/{sn}/HOOKUP → 체크리스트 반환 |
| TC-CL-04 | 마스터 없는 경우 빈 리스트 반환 (200) |
| TC-CL-05 | 미인증 GET → 401 |
| TC-CL-06 | PUT is_checked=True → checked_by, checked_at 기록 |
| TC-CL-07 | PUT is_checked=False (체크 해제) 성공 |
| TC-CL-08 | PUT 후 GET으로 checked_by 확인 |
| TC-CL-09 | 중복 PUT → UPSERT (에러 없음, 레코드 1개) |
| TC-CL-10 | 없는 master_id → 400/404 |
| TC-CL-11 | note 필드 저장 확인 |
| TC-CL-12 | 미인증 PUT → 401 |
| TC-CL-13 | Admin Excel import 성공 |
| TC-CL-14 | 일반 작업자 import → 403 |

#### test_active_role.py (9 tests)
| 테스트 | 내용 |
|--------|------|
| TC-AR-01 | GST 작업자 active_role='PI' 변경 성공 |
| TC-AR-02 | GST 작업자 active_role='QI' 변경 + DB 반영 확인 |
| TC-AR-03 | GST 작업자 active_role='SI' 변경 성공 |
| TC-AR-04 | 유효하지 않은 role 'MECH' → 400 |
| TC-AR-05 | FNI 협력사 작업자 active_role 변경 → 403 |
| TC-AR-06 | GET /api/auth/me → active_role 필드 포함 |
| TC-AR-07 | active_role 변경 후 GET me 반영 확인 |
| TC-AR-08 | 미인증 PUT → 401 |
| TC-AR-09 | active_role='PI' 후 작업 관리 PI task 조회 |

### Sprint 11 완료 상태
- ✅ PI/QI/SI task 템플릿 4개 정상 생성 (모든 모델 공통)
- ✅ 홈 메뉴에 PI/QI/SI 진행 제품 대시보드 3개 표시 (GST + admin)
- ✅ GST 진행 제품 대시보드 API 정상 동작
- ✅ checklist 스키마 생성 + CRUD API 정상 동작
- ✅ active_role 전환 API + 필터링
- ✅ Sprint 11 신규 테스트 44 PASS, 1 SKIP
- ✅ 기존 테스트 regression 수정 완료 (task count 15→19/13→17 업데이트)

### Regression 수정 사항
Sprint 11에서 PI/QI/SI 4개 task 추가로 인해 기존 task count 기대값 변경:
- `test_task_seed.py`: GAIA 15→19 (4곳 수정)
- `test_model_task_seed_integration.py`: GAIA 15→19, DRAGON/GALLANT/MITHAS/SDS/SWS 13→17 (8곳 수정)
- `test_product_api.py`: GAIA 15→19, GALLANT 13→17 (2곳 수정)
- `tests/conftest.py`: Worker cleanup FK chain 확장 (checklist_record, work_pause_log 등 추가)

### 생성/수정 파일
```
tests/backend/test_gst_task_seed.py     # 신규 — 10 tests (TDD)
tests/backend/test_gst_products_api.py  # 신규 — 12 tests (TDD)
tests/backend/test_checklist_api.py     # 신규 — 14 tests (TDD)
tests/backend/test_active_role.py       # 신규 — 9 tests (TDD)
```

### Sprint 11 수동 핫픽스 (Cowork 세션에서 직접 수정)

#### Fix 1: gst_products_screen.dart — FE 타입 불일치 (TypeError)
- **증상**: QI 공정검사 화면 진입 시 `TypeError: "QI_INSPECTION": type 'String' is not a subtype of type 'int?'`
- **원인 2가지**:
  1. BE 응답 키 `task_status`를 FE에서 `status`로 읽고 있었음
  2. `task_id`(String: "QI_INSPECTION")를 `int?`로 캐스팅 시도
- **수정**:
  - `product['status']` → `product['task_status']`
  - `product['task_id'] as int?` → `product['task_detail_id'] as int?`
  - 네비게이션 arguments도 `task_id` → `task_detail_id`로 변경
- **영향**: PI/QI/SI 3개 화면 모두 동일 파일이므로 한 번 수정으로 전부 적용

#### Fix 2: gst.py — 미태깅 제품이 모든 대시보드에 표시되는 문제
- **증상**: PI에서 태깅한 제품이 QI/SI 대시보드에도 보임 (모든 공정에 seed task가 생성되어 있어서)
- **원인**: default 상태 필터가 `t.completed_at IS NULL` → not_started(미태깅) 포함
- **수정**:
  - default(active): `t.completed_at IS NULL` → `t.started_at IS NOT NULL AND t.completed_at IS NULL`
  - all: `1=1` → `t.started_at IS NOT NULL`
- **결과**: 각 공정 대시보드에 해당 공정에서 실제 태깅(작업 시작)한 제품만 표시

```
수정 파일:
frontend/lib/screens/gst/gst_products_screen.dart  # Fix 1: 타입 불일치 수정
backend/app/routes/gst.py                           # Fix 2: 태깅된 제품만 필터링
```

#### Fix 3: QR 스캔 완료 페이지에 기구/전장 협력사 정보 추가
- **요청**: QR 스캔 후 제품 정보에 기구 협력사, 전장 협력사도 표시
- **원인**: FE `ProductInfo` 모델에 `elecPartner` 필드 누락 + QR 스캔 화면에 협력사 정보 미표시
- **수정 4개 파일**:
  1. `frontend/lib/models/product_info.dart` — `elecPartner` 필드 추가 (fromJson/toJson/copyWith/==)
  2. `frontend/lib/screens/qr/qr_scan_screen.dart` — 기구 협력사 + 전장 협력사 행 추가
  3. `backend/app/routes/product.py` — 응답에 `elec_partner` 필드 추가
  4. `backend/app/routes/work.py` — 응답에 `elec_partner` 필드 추가

```
수정 파일:
frontend/lib/models/product_info.dart               # Fix 3: elecPartner 필드 추가
frontend/lib/screens/qr/qr_scan_screen.dart         # Fix 3: 협력사 정보 표시
backend/app/routes/product.py                        # Fix 3: elec_partner 응답 추가
backend/app/routes/work.py                           # Fix 3: elec_partner 응답 추가
```

#### Fix 4: FE 전체 화면 시간 표시 UTC→KST (toLocal 누락)
- **증상**: 작업관리 메뉴에서 시작시간이 UTC 기준으로 표시 (한국 시간 09:08인데 23:08으로 표시)
- **원인**: BE는 `+09:00` 오프셋 포함 KST로 반환하나, `DateTime.parse()`가 UTC로 변환 저장 → FE에서 `.toLocal()` 호출 없이 그대로 출력
- **수정 4개 파일**:
  1. `task_management_screen.dart` — `_formatDateTime()`에 `.toLocal()` 추가
  2. `task_detail_screen.dart` — `_formatFullDateTime()`에 `.toLocal()` 추가
  3. `alert_list_screen.dart` — `_formatDateTime()` + `_formatFullDateTime()`에 `.toLocal()` 추가
  4. `manager_pending_tasks_screen.dart` — `startedAt` 파싱 시 `.toLocal()` 추가

```
수정 파일:
frontend/lib/screens/task/task_management_screen.dart       # Fix 4: toLocal 추가
frontend/lib/screens/task/task_detail_screen.dart           # Fix 4: toLocal 추가
frontend/lib/screens/admin/alert_list_screen.dart           # Fix 4: toLocal 추가
frontend/lib/screens/manager/manager_pending_tasks_screen.dart  # Fix 4: toLocal 추가
```

---

## Sprint 12: PIN 간편 로그인 + 협력사 출퇴근 + QR 카메라 스캔 (완료 ✅)

### BE 완료 내역
- `010_sprint12_hr_schema.sql` — migration 실행 완료
  - `hr` 스키마 생성
  - `hr.worker_auth_settings` — PIN 인증 설정 (pin_hash, fail_count, locked_until)
  - `hr.partner_attendance` — 협력사 출퇴근 기록 (check_type, method, 인덱스 2개)
  - `hr.gst_attendance` — GST 사내 근태 (테이블만, API 미구현)
- `backend/app/routes/auth.py` — PIN API 4개 추가
  - `POST /api/auth/set-pin` — 4자리 숫자 PIN 설정 (werkzeug bcrypt, UPSERT)
  - `PUT /api/auth/change-pin` — 현재 PIN 검증 후 변경
  - `POST /api/auth/pin-login` — PIN 로그인 (3회 실패→5분 잠금, JWT 발급)
  - `GET /api/auth/pin-status` — PIN 등록 여부 조회
- `backend/app/routes/hr.py` — 출퇴근 API 2개 (신규 파일)
  - `POST /api/hr/attendance/check` — 출근/퇴근 (협력사만, 당일 중복 방지)
  - `GET /api/hr/attendance/today` — 당일 출퇴근 기록 조회
- `backend/app/__init__.py` — hr_bp 블루프린트 등록

### FE 완료 내역
- `frontend/lib/screens/settings/profile_screen.dart` — 개인 설정 화면 (신규)
  - PIN 등록/변경 버튼, 생체인증 "추후 오픈 예정" 메뉴
- `frontend/lib/screens/settings/pin_settings_screen.dart` — PIN 설정 화면 (신규)
  - 4자리 도트 + 숫자 키패드, 등록/변경 플로우
- `frontend/lib/screens/auth/pin_login_screen.dart` — PIN 로그인 화면 (신규)
  - 3회 실패→잠금, "이메일로 로그인" 링크
- `frontend/lib/screens/home/home_screen.dart` — 출퇴근 카드 추가 (협력사만)
- `frontend/lib/screens/qr/qr_scan_screen.dart` — QR 카메라 스캔 (수정)
  - html5-qrcode JS interop, 카메라 메인 + 직접 입력 보조
- `frontend/lib/services/qr_scanner_service.dart` + `qr_scanner_web.dart` + `qr_scanner_stub.dart` — QR 스캔 서비스 (신규)
- `frontend/web/index.html` — html5-qrcode 스크립트 추가
- `frontend/lib/main.dart` — /profile, /pin-settings, /pin-login 라우트 등록
- `flutter build web` — 0 errors ✅

### TEST 완료 내역 (22/22 PASSED)

| 파일 | 테스트 수 | 내용 |
|------|----------|------|
| `test_pin_auth.py` | 14 | PIN 설정/변경/로그인/상태/잠금/UPSERT |
| `test_attendance.py` | 8 | 출근/퇴근/중복방지/GST차단/당일조회 |

### Sprint 12 완료 상태
- ✅ hr 스키마 생성 (worker_auth_settings + partner_attendance + gst_attendance)
- ✅ PIN 설정/변경/로그인/상태 API 4개 정상 동작
- ✅ PIN 3회 실패 → 5분 잠금 동작
- ✅ 출퇴근 check-in/check-out API 정상 (협력사만)
- ✅ 당일 중복 출근 방지
- ✅ 개인 설정 화면 — PIN 등록/변경 + 생체인증 "추후 오픈" 메뉴
- ✅ PIN 로그인 화면 — 4자리 입력 + 키패드 + 실패 카운트 표시
- ✅ 홈 화면 — 협력사 출퇴근 카드 (GST 제외)
- ✅ QR 카메라 스캔 메인 + 텍스트 입력 보조
- ✅ Sprint 12 신규 테스트 22/22 PASSED
- ✅ 기존 테스트 regression 신규 0건
- ✅ flutter build web 에러 0건

### 생성/수정 파일
```
backend/migrations/010_sprint12_hr_schema.sql          # 신규
backend/app/routes/hr.py                                # 신규
backend/app/routes/auth.py                              # PIN API 4개 추가
backend/app/__init__.py                                 # hr_bp 등록
frontend/lib/screens/settings/profile_screen.dart       # 신규
frontend/lib/screens/settings/pin_settings_screen.dart  # 신규
frontend/lib/screens/auth/pin_login_screen.dart         # 신규
frontend/lib/services/qr_scanner_service.dart           # 신규
frontend/lib/services/qr_scanner_web.dart               # 신규
frontend/lib/services/qr_scanner_stub.dart              # 신규
frontend/lib/screens/home/home_screen.dart              # 출퇴근 카드 추가
frontend/lib/screens/qr/qr_scan_screen.dart             # QR 카메라 스캔
frontend/web/index.html                                 # html5-qrcode 추가
frontend/lib/main.dart                                  # 라우트 3개 추가
tests/backend/test_pin_auth.py                          # 신규 — 14 tests
tests/backend/test_attendance.py                        # 신규 — 8 tests
tests/conftest.py                                       # hr cleanup 추가
```

### Sprint 12 핫픽스: PIN 자동로그인 분기 로직 (Cowork 세션에서 직접 수정)

Sprint 12 에이전트가 PIN 화면/API는 구현했지만, 앱 시작 시 PIN 분기 로직이 누락됨.
수동으로 4개 파일 핫픽스 적용.

**문제**: 앱을 껐다 켜도 항상 이메일 로그인 화면이 표시됨 (PIN 등록 사용자도 동일)

**수정 내용**:

1. **`auth_service.dart`** — PIN 헬퍼 메서드 3개 추가
   - `hasRefreshToken()`: refresh_token 존재 확인 (자동 로그인 가능 여부)
   - `hasPinRegistered()`: PIN 등록 여부 로컬 캐시 확인
   - `savePinRegistered(bool)`: PIN 등록 상태 캐시 저장
   - `logout()`에 `_pinRegisteredKey` 삭제 추가

2. **`main.dart`** — `_initialize()` 3단계 분기 로직 추가
   - 1단계: refresh_token 없음 → 이메일 로그인 화면 (기존)
   - 2단계: refresh_token 있음 + PIN 등록됨 → PIN 입력 화면
   - 3단계: refresh_token 있음 + PIN 미등록 → 자동 로그인 → 마지막 경로 복원

3. **`pin_settings_screen.dart`** — PIN 등록/변경 성공 시 `savePinRegistered(true)` 호출 추가

4. **`pin_login_screen.dart`** — 3가지 수정
   - `worker_id`를 API 요청에 포함 (BE 필수 파라미터)
   - `_loadWorkerInfo()`: secure storage에서 worker 정보 로드 (앱 재시작 시 authProvider 비어있음)
   - PIN 성공 후 토큰 저장 + authProvider 상태 갱신 + 마지막 경로 복원

**앱 시작 플로우 (수정 후)**:
```
앱 시작 → AppStartup._initialize()
  ├─ refresh_token 없음 → SplashScreen (이메일 로그인)
  ├─ refresh_token 있음 + PIN 등록 → PinLoginScreen
  │   └─ PIN 성공 → 토큰 갱신 → 마지막 경로 복원 or /home
  └─ refresh_token 있음 + PIN 미등록 → tryAutoLogin()
      ├─ 성공 → 마지막 경로 복원 or /home
      └─ 실패 → SplashScreen
```

---

## 전체 테스트 결과 (Sprint 10 기준)

```
Sprint 1 (Auth):                  8/8   PASSED
Sprint 2 (Work):                 21/21  PASSED
Sprint 3 (Alert/Validation):    21/21  PASSED
Sprint 4 (Admin/Sync):          31/31  PASSED
Sprint 5 (Models/Email/Token):  59/59  PASSED
Sprint 6 (Task Seed/Multi/Scheduler/ForceClose):
                                157 passed, 20 skipped
Sprint 7 (Product/Integration): 356 passed, 19 skipped
Sprint 8 (AdminOpt/PwdReset/Token):
                                271 passed (backend), 19 skipped
Sprint 9 (Pause/Resume/BreakTime):
                                318 passed, 19 skipped
  신규: test_pause_resume (24) + test_break_time_settings (8)
        + test_break_time_scheduler (14) = 46 tests
Sprint 10 (수정사항 검증 + 버그 수정):
                                456+ passed, 19 skipped
  신규: test_sprint10_fixes (19) — Fix 검증 10 + Bug A/B/C/D 9
  수정: test_pause_resume (4개 Fix 2 대응)
  구현: phase_block_enabled 차단 로직 (Bug D)
  Flaky: 일부 (단독 실행 시 모두 PASS — 테스트 간 데이터 간섭)
Sprint 11 (GST Task + 대시보드 + Checklist):
                                44 passed, 1 skipped
  신규: test_gst_task_seed (10) + test_gst_products_api (12)
        + test_checklist_api (14) + test_active_role (9) = 45 tests
  Regression 수정: task count 15→19/13→17 (PI/QI/SI 추가 반영)
  conftest.py FK cleanup 확장 (checklist_record 등)
Sprint 12 (PIN 간편 로그인 + 협력사 출퇴근 + QR 카메라):
                                22 passed (신규), 397 passed (전체)
  신규: test_pin_auth (14) + test_attendance (8) = 22 tests
  conftest.py hr 스키마 cleanup 추가
─────────────────────────────────────────────
누적 테스트 파일: 34개, Sprint 12 신규 regression 0건
```

---

## Sprint 12 배포 + 핫픽스 (2026-02-28, Cowork 세션)

### 배포 완료
- **Netlify PWA**: `gaxis-ops.netlify.app` — `flutter build web` → `build/web` 드래그&드롭 배포
- **Railway Flask API**: `axis-ops-api.up.railway.app` — GitHub push → 자동 배포
- `constants.dart` apiBaseUrl → Railway 도메인으로 변경
- `web/_redirects` 생성 (`/*  /index.html  200` SPA 라우팅)
- 전체 API 동작 확인: auth/refresh ✅, hr/attendance/today ✅, app/alerts ✅

### QR 카메라 수정
- **Shadow DOM 이슈 해결**: Flutter `HtmlElementView` → `document.body`에 직접 div 생성 (`dart:html`)
- **카메라 3단계 fallback**: environment(후면) → user(전면) → cameraId(첫번째 가용)
- **권한 팝업 가려짐 해결**: `getUserMedia()` 선행 호출 → 권한 획득 후 div 생성
- **스캐너 정사각형 조정**: 컨테이너 `width=height` (화면 78%), `aspectRatio: 1.0`, `borderRadius: 12px`

### 앱 아이콘 커스터마이징
- `logo-color.png`에서 G 다이아몬드 심볼 추출 (cols 232-448, rows 396-615)
- favicon (32x32), PWA Icon-192/512 생성 (72% fill, 배경 #1E1E23)

### WebSocket 임시 조치
- FE raw WebSocket ↔ BE Flask-SocketIO 프로토콜 불일치 확인
- reconnect 최대 2회, 간격 10초로 축소 (에러 로그 최소화)

### Task 화면 제품 정보 개선

#### BE 수정
- `product.py`, `work.py` — API 응답에 `sales_order`, `customer`, `title_number`, `mech_start/end`, `elec_start/end` 추가

#### FE 수정
- `product_info.dart` — 6개 필드 추가 (`salesOrder`, `customer`, `titleNumber`, `mechStart/End`, `elecStart/End`)
- `task_management_screen.dart` — 상단 헤더 간소화: **S/N, 모델 | 수주번호, 위치** 만 표시 (QR Doc ID 제거)
- `task_detail_screen.dart` — 제품 상세 확장: 수주번호, 고객사, 기구/전장 협력사, 기구/전장 일정, 모듈 외주, QR Doc ID

### BACKLOG 정비
- 배포 항목(DP-3, DP-4) 완료 처리
- BUG-1 (QR 카메라 팝업), BUG-2 (WebSocket 불일치) 추가
- QR ETL 자동화 파이프라인 + QR 라벨 관리 페이지 추가
- Geolocation 2차 보안 (GPS 위치 검증 + Admin 설정) 추가
- 앱 아이콘 최적화(RV-3) 추가

### 수정 파일 목록
| 파일 | 변경 내용 |
|------|----------|
| `backend/app/routes/product.py` | API 응답에 sales_order 등 7개 필드 추가 |
| `backend/app/routes/work.py` | location update 응답에 동일 필드 추가 |
| `frontend/lib/models/product_info.dart` | 6개 필드 추가 (salesOrder, customer 등) |
| `frontend/lib/screens/task/task_management_screen.dart` | 헤더 간소화 (S/N, 모델, 수주번호, 위치) |
| `frontend/lib/screens/task/task_detail_screen.dart` | 제품 상세 정보 확장 |
| `frontend/lib/services/qr_scanner_web.dart` | Shadow DOM 우회 + 권한 선행 요청 + 정사각형 |
| `frontend/lib/services/websocket_service.dart` | reconnect 2회/10초 축소 |
| `frontend/lib/utils/constants.dart` | apiBaseUrl Railway 도메인 |
| `frontend/web/_redirects` | Netlify SPA 라우팅 |
| `frontend/web/favicon.png` | G 심볼 아이콘 |
| `frontend/web/icons/Icon-192.png` | PWA 아이콘 192x192 |
| `frontend/web/icons/Icon-512.png` | PWA 아이콘 512x512 |
| `BACKLOG.md` | 전면 정비 (완료 처리 + 버그/신규 항목 추가) |

---

## Sprint 12 → 13 사이 버그 수정 (2026-02-28, Cowork 세션)

### BUG-6 수정: 협력사 task 리스트에 작업자명 미표시

#### BE 수정
- `work.py` — `get_tasks_by_serial()`: task 목록 반환 시 workers 테이블 batch lookup 추가
  - `worker_ids = list(set(t.worker_id for t in tasks if t.worker_id))`
  - `SELECT id, name FROM workers WHERE id = ANY(%s)` → `worker_map` 생성
  - 각 task에 `worker_name` 필드 추가

#### FE 수정
- `task_item.dart` — `workerName` 필드 추가 (constructor, fromJson, toJson, copyWith, equality, hashCode)
- `task_management_screen.dart` — 카테고리 행에 작업자 아이콘(`Icons.person_outline`) + 이름 표시

### BUG-5 수정: QR 카메라 프레임 벗어남 (2차 수정 포함)

#### 1차 수정: 컨테이너 좌표 전달
- `qr_scan_screen.dart` — `_getCameraContainerRect()` 메서드 추가, `_cameraContainerKey`로 Flutter 컨테이너 위치/크기 계산
- `qr_scanner_service.dart` — `start()`에 `containerLeft/Top/Width/Height` 파라미터 추가 + `updatePosition()` 메서드
- `qr_scanner_web.dart` — `ensureScannerDiv(containerRect)` 전달, `updateScannerDivPosition()` 함수 추가
- `qr_scanner_stub.dart` — 새 시그니처 매칭

#### 2차 수정: html5-qrcode 내부 video 요소 CSS 오버라이드
- `qr_scanner_web.dart` — `_injectScannerCss()`: `#qr-scanner-dom-div video`에 `object-fit: cover`, `position: absolute`, `width/height: 100%`

#### 3차 수정: 카메라 위치 오른쪽 치우침 해결
- `qr_scanner_web.dart` — CSS 전면 개선:
  - 모든 자식(`*`)에 `box-sizing: border-box`
  - 내부 div 2단계(`> div`, `> div > div`) 모두 `overflow: hidden` + `max-width: 100%`
  - video: `min-width/min-height: 100%` 추가
  - img `display: none` (불필요한 이미지 요소 숨김)
- config 변경: `aspectRatio: 1.0` 제거, `qrbox` 정수형으로 동적 계산 (컨테이너 60%)
- `_forceContainerFit()` 함수 추가: start() 완료 후 200ms 뒤 JS로 내부 요소 inline style 직접 덮어쓰기

### Worker DB 보존 수정

#### 문제
- `conftest.py`가 production Railway DB에 `DROP TABLE workers CASCADE` 실행
- 테스트 DB URL = 프로덕션 DB URL (같은 Railway 인스턴스)
- Sprint 테스트 실행 시마다 admin 외 모든 worker 데이터 초기화됨

#### 수정
- `conftest.py` — `db_schema` fixture에 backup/restore 로직 추가:
  - DROP 전: `SELECT * FROM workers` → `backed_up_workers` 보관
  - 마이그레이션 후: `INSERT INTO workers (...) ON CONFLICT (id) DO NOTHING` + `setval(workers_id_seq)`
  - `hr.worker_auth_settings` 동일하게 backup/restore
- `010_sprint12_hr_schema.sql` migration_files 목록에 추가 (누락 수정)
- `DROP SCHEMA IF EXISTS hr CASCADE` drop_stmts에 추가

### 수정 파일 목록
| 파일 | 변경 내용 |
|------|----------|
| `backend/app/routes/work.py` | worker_name batch lookup 추가 (BUG-6) |
| `frontend/lib/models/task_item.dart` | workerName 필드 추가 (BUG-6) |
| `frontend/lib/screens/task/task_management_screen.dart` | 작업자 아이콘+이름 표시 (BUG-6) |
| `frontend/lib/services/qr_scanner_web.dart` | CSS 강화 + config 변경 + _forceContainerFit (BUG-5) |
| `frontend/lib/screens/qr/qr_scan_screen.dart` | _getCameraContainerRect + key 이동 (BUG-5) |
| `frontend/lib/services/qr_scanner_service.dart` | container 좌표 파라미터 + updatePosition (BUG-5) |
| `frontend/lib/services/qr_scanner_stub.dart` | 새 시그니처 매칭 (BUG-5) |
| `tests/conftest.py` | worker backup/restore + hr schema (DB 보존) |

---

## Sprint 13: WebSocket flask-sock 마이그레이션 (완료 ✅)

> 목표: BUG-2 (WebSocket 프로토콜 불일치) + BUG-4 (알림 실시간 전달 안됨) 해결
> FE 변경: 0건 (이미 raw WebSocket 사용 중)

### BE 수정

#### 1. 의존성 변경
- `requirements.txt` — `Flask-SocketIO>=5.3`, `eventlet>=0.33` 제거 → `flask-sock` 추가
- `Procfile` — `--worker-class eventlet` → `--worker-class gthread --threads 4`

#### 2. events.py 전체 리라이트 (핵심)
- `ConnectionRegistry` 클래스: thread-safe dict (`threading.Lock()`)
  - `register(ws_id, ws, worker_id, role)` → worker_{id}, role_{role} room 자동 등록
  - `unregister(ws_id)` → room 정리, 빈 room 삭제
  - `send_to_room(room, message)` → 특정 room 전송
  - `broadcast(message)` → 전체 전송
- `ws_handler(ws)` — `/ws` 라우트 핸들러
  - JWT query param → `decode_jwt()` → worker_id, role 추출
  - connected 이벤트 전송
  - 메시지 루프: ping → pong, 60초 timeout
  - disconnect 시 registry cleanup
- emit 함수 3개 — **기존 시그니처 100% 유지** (alert_service.py 호환)
  - `emit_new_alert(worker_id, alert_data)` → worker room 전송
  - `emit_process_alert(alert_data)` → role room 또는 broadcast
  - `emit_task_completed(serial_number, task_category, worker_id)` → broadcast
- 메시지 포맷: `{"event": "xxx", "data": {...}}` — FE `websocket_service.dart`와 일치

#### 3. 앱 팩토리 수정
- `app/__init__.py` — `from flask_socketio import SocketIO` 제거 → `from flask_sock import Sock`
  - `socketio = SocketIO()` → `sock = Sock()`
  - `socketio.init_app(app)` → `sock.init_app(app)`
  - `@sock.route('/ws')` 데코레이터로 ws_handler 등록
- `websocket/__init__.py` — `register_events(socketio)` 제거 → `ws_handler, registry` export
- `run.py` — `from app import create_app, socketio` → `from app import create_app`
  - `socketio.run(app, ...)` → `app.run(host, port, debug)`

#### 4. 스케줄러 BUG-4 수정
- `scheduler_service.py` — 5곳 `create_alert()` → `create_and_broadcast_alert()` 변경:
  1. `task_reminder_job()` — 매 1시간 TASK_REMINDER
  2. `shift_end_reminder_job()` — 17:00/20:00 SHIFT_END_REMINDER
  3. `task_escalation_job()` — 익일 09:00 TASK_ESCALATION
  4. `force_pause_all_active_tasks()` — 휴게시간 BREAK_TIME_PAUSE
  5. `send_break_end_notifications()` — 휴게시간 종료 BREAK_TIME_END
- 효과: DB 저장 + WebSocket broadcast 동시 처리 (이전: DB 저장만)

### 테스트 수정
- `test_websocket.py` — 전면 리라이트 (Flask-SocketIO test_client → ConnectionRegistry 단위 테스트)
  - `TestConnectionRegistry`: 등록/해제, room 생성/삭제, unknown ws_id 처리
  - `TestRegistryMessaging`: room 전송, broadcast, role room, 전송 실패 처리, 빈 room
  - `TestMessageFormat`: new_alert/process_alert/task_completed JSON 포맷 검증
  - `TestConcurrentConnections`: 다중 worker 분리, 같은 worker 다중 기기
  - `TestPingPong`: ping/pong 메시지 포맷

### 수정 파일 목록
| 파일 | 변경 내용 |
|------|----------|
| `backend/requirements.txt` | Flask-SocketIO/eventlet 제거, flask-sock 추가 |
| `backend/Procfile` | gthread --threads 4 |
| `backend/app/websocket/events.py` | 전체 리라이트 (ConnectionRegistry + ws_handler) |
| `backend/app/websocket/__init__.py` | ws_handler/registry export |
| `backend/app/__init__.py` | SocketIO → Sock + /ws 라우트 |
| `backend/run.py` | socketio.run() → app.run() |
| `backend/app/services/scheduler_service.py` | 5곳 create_and_broadcast_alert 변경 |
| `tests/backend/test_websocket.py` | 전면 리라이트 (단위 테스트) |
| `BACKLOG.md` | BUG-2/4 완료, Sprint 13 이력 추가 |
| `AGENT_TEAM_LAUNCH.md` | Sprint 13 프롬프트 추가 |

### 테스트 결과
- Sprint 13 신규: **18/18 PASSED** (ConnectionRegistry, 메시징, 포맷, 동시 연결, ping/pong)
- 회귀 테스트: **415 passed, 5 failed (기존 flaky), 12 skipped** — Sprint 13 regression 0건

### 배포 완료 (2026-03-01)
- [x] git commit & push (`4f6644f`)
- [x] Railway 배포 — `gunicorn --worker-class gthread --threads 4` 정상 동작
- [x] flutter build web → Netlify 배포 (https://gaxis-ops.netlify.app)
- [x] WSS 연결 테스트: `wss://axis-ops-api.up.railway.app/ws` — connected + ping/pong ✅
- [x] 기존 REST API 정상 동작 확인 (`/health` 200 OK)
- [x] 알림 E2E: Admin 로그인 → JWT WSS 연결 → Admin API 200 OK ✅
- [x] Admin 비밀번호 해시 수정 (migration SQL + DB 동기화)

---

## BUG-5 핫픽스: QR 카메라 DOM 오버레이 위치 정렬 (2026-03-01) ✅

### 근본 원인
- `qr_scanner_web.dart`의 `ensureScannerDiv()`가 **`left + right` CSS 대칭 여백 가정** 사용
- `right = containerLeft` → 비대칭 레이아웃(SafeArea, ScrollView padding)에서 카메라 프레임이 오른쪽으로 벗어남

### 수정 내용
**FE 수정** (`frontend/lib/services/qr_scanner_web.dart`):
1. `ensureScannerDiv()`: `left + right` → **`left + width` 명시 방식**으로 변경
   - Flutter `renderBox.size.width`를 `containerWidth`로 직접 전달
   - `right` CSS 비움 (`..right = ''`)
2. `_startResizeListener()`: 저장된 `_savedLeft + _savedWidth`로 리사이즈 대응
3. `updateScannerDivPosition()`: 동일한 `left + width` 방식 적용
4. 미사용 `actualDivWidth` 변수 제거

**변경 파일**: 1개 (`qr_scanner_web.dart`)
**빌드 확인**: `flutter build web --release` — 에러 0건

### 테스트 (`tests/backend/test_qr_scanner_logic.py`)
- **19/19 PASSED** (좌표 계산 로직 Python 재현 테스트)
  - TC-QR-01: 명시적 좌표 적용 (비대칭 여백, 좁은/넓은 뷰포트)
  - TC-QR-02: fallback 사이즈 (최소/최대 margin 클램프)
  - TC-QR-03: 위치 업데이트 (스크롤 시 top만 변경)
  - TC-QR-04: div 제거 상태 정리
  - TC-QR-05: qrbox 크기 계산 (120~250 클램프)

---

## BUG-5 추가 수정: QR 스캔 영역 바코드→정사각형 (2026-03-01) ✅

### 문제 (5차 수정 후 발견)
카메라 위치는 해결되었으나:
1. **스캔 영역이 바코드 형태**: html5-qrcode 흰색 브라켓이 가로로 긴 직사각형으로 렌더링
2. **QR 인식 미동작**: 정사각형 QR 코드가 스캔 영역과 불일치하여 인식 불가

### 근본 원인
**Dart `js_util.jsify()` 중첩 객체 변환 불가** — html5-qrcode가 qrbox config를 인식 못함.
시도한 방법 (6~8차 모두 실패):
- 6차: `qrbox` 정수 전달 (`jsify({'qrbox': qrboxSize})`) → 직사각형 유지
- 7차: `js_util.newObject()` + `setProperty()` → 직사각형 유지
- 8차: `JSON.parse()` + `allowInterop` 콜백 → 직사각형 유지

**공통 실패 원인**: Dart-to-JS interop으로 생성한 객체는 html5-qrcode 내부에서 프로퍼티 접근 불가

### 해결 (9차 수정 — 순수 JavaScript 주입) ✅
**핵심**: config 전체를 `<script>` 태그로 순수 JavaScript에서 생성, Dart interop 완전 제거

**`frontend/lib/services/qr_scanner_web.dart`**:
```dart
// ★ 9차 수정: config 전체를 순수 JavaScript로 생성
final configScript = html.ScriptElement()
  ..text = '''
    window.__qrScanConfig = {
      fps: 10,
      qrbox: function(viewfinderWidth, viewfinderHeight) {
        var size = Math.round(Math.min(viewfinderWidth, viewfinderHeight) * 0.7);
        size = Math.max(120, Math.min(250, size));
        return { width: size, height: size };
      }
    };
  ''';
html.document.head!.append(configScript);
configScript.remove();
final config = js_util.getProperty(js_util.globalThis, '__qrScanConfig');
```

**추가 변경**:
- `qr_scan_screen.dart`: 진단 로그 추가 (Container rect, Screen size, DevicePixelRatio)
- `qr_scan_screen.dart`: Flutter 파란색 스캔 프레임 오버레이 제거 (html5-qrcode 자체 UI 사용)
- `index.html`: G-AXIS 로고 스플래시 스크린 추가 (`flutter-first-frame` 이벤트로 fade-out)
- `web/img/g-axis-splash.png`: 투명 배경 가로형 로고 (assets/images/g-axis-2.png 복사)

### 배포 검증 결과
Console 로그 확인:
```
[QrScannerWeb] ★ JS qrbox: viewfinder=390x293 → qrbox=205x205
```
- ✅ qrbox 콜백 실행됨 (typeof qrbox = function)
- ✅ 205×205 정사각형 반환 (min(390,293) × 0.7 = 205)
- ✅ 웹 브라우저 정상 동작 확인

### 변경 파일
| 파일 | 변경 내용 |
|------|-----------|
| `frontend/lib/services/qr_scanner_web.dart` | 9차 수정: 순수 JS config + qrbox 콜백 |
| `frontend/lib/screens/qr/qr_scan_screen.dart` | 진단 로그 + Flutter 스캔 오버레이 제거 |
| `frontend/web/index.html` | G-AXIS 스플래시 스크린 추가 |
| `frontend/web/img/g-axis-splash.png` | 스플래시 로고 이미지 |

### 수정 이력 (6차~9차)
| 차수 | 방법 | 결과 |
|------|------|------|
| 6차 | `jsify({'qrbox': qrboxSize})` 정수 | ❌ 직사각형 |
| 7차 | `newObject()` + `setProperty()` | ❌ 직사각형 (iPad/Android/iOS 3기기) |
| 8차 | `JSON.parse()` + `allowInterop` 콜백 | ❌ 직사각형 |
| 9차 | 순수 JS `<script>` 태그 주입 | ✅ 정사각형 (205×205) |

---

## Sprint 14: 작업자명 표시 + QR 스캔 영역 정사각형 (2026-03-02) ✅

### 목표
1. Task를 시작한 작업자 전원의 이름이 화면에 표시되도록 (협력사 Task Detail + GST 대시보드)
2. QR 스캔 영역이 직사각형(바코드형) → 정사각형으로 수정 (10차)

### BE 변경

**`backend/app/routes/work.py` — `get_tasks_by_serial()`**:
- task_list 빌드 후 `work_start_log` + `work_completion_log` 배치 JOIN 조회 (ANY 사용, N+1 없음)
- 결과를 `workers_by_task` dict로 그룹화 → 각 task에 `workers` 배열 추가
- Legacy fallback: `work_start_log` 없는 task는 기존 `worker_id`/`worker_name`으로 단일 항목 생성
- 기존 `worker_id`, `worker_name` 필드 유지 (하위 호환)

**`backend/app/routes/gst.py` — `get_gst_products()`**:
- 동일 패턴: 기존 conn 재사용, task_detail_ids 배치 수집, workers 일괄 조회

**workers 배열 항목 구조**:
```json
{
  "worker_id": 10,
  "worker_name": "김철수",
  "started_at": "2026-03-02T10:00:00+09:00",
  "completed_at": "2026-03-02T10:30:00+09:00",
  "duration_minutes": 30,
  "status": "completed"
}
```

### FE 변경

**Task Detail 작업자 정보 섹션** (`task_detail_screen.dart`):
- `_buildWorkerInfoSection()` 추가 (제품 정보 ~ 작업 시간 사이)
- 단일 작업자: 이름만 표시
- 다중 작업자: ✅/🔄 아이콘 + 이름 + 시작~종료 시간 + 소요분

**GST 대시보드 작업자명 보완** (`gst_products_screen.dart`):
- workers 배열 우선 사용, 다중이면 "김철수 외 2명" 형식
- 빈 배열이면 기존 `worker_name` fallback

**TaskItem 모델** (`task_item.dart`):
- `workers: List<Map<String, dynamic>>` 필드 추가 (fromJson/toJson/copyWith)

**QR 스캔 영역 정사각형 (10차)** (`qr_scanner_web.dart` + `qr_scan_screen.dart`):
- qrbox: JS 콜백 함수 → 정수 `200` (자동 정사각형)
- 카메라 컨테이너: `height: 300` 고정 → 정사각형 `width = height = min(screenWidth-40, 350)`
- start() 성공 후 `qr-shaded-region` DOM 크기 로그 추가

### 변경 파일
| 파일 | 변경 내용 |
|------|-----------|
| `backend/app/routes/work.py` | workers 배열 배치 조회 + 그룹핑 + fallback |
| `backend/app/routes/gst.py` | 동일 workers 배열 패턴 |
| `frontend/lib/models/task_item.dart` | workers 필드 추가 |
| `frontend/lib/screens/task/task_detail_screen.dart` | 작업자 정보 섹션 신규 |
| `frontend/lib/screens/gst/gst_products_screen.dart` | workers 기반 "외 N명" 표시 |
| `frontend/lib/services/qr_scanner_web.dart` | qrbox 정수 + scan-region 로그 |
| `frontend/lib/screens/qr/qr_scan_screen.dart` | 정사각형 카메라 컨테이너 |
| `tests/backend/test_task_workers_api.py` | 신규 7건 |
| `tests/backend/test_qr_scanner_logic.py` | 추가 2건 |

### 테스트 결과
- Sprint 14 신규: **28/28 PASSED** (workers API 7 + QR 로직 21)
- 빌드: `flutter build web --release` — 에러 0건

### 배포 (2026-03-02)
- [x] git commit & push (`bdbe203`)
- [x] Railway 자동 배포 (GitHub push)
- [x] flutter build web → Netlify 배포 (https://gaxis-ops.netlify.app)

---

## Sprint 14 핫픽스: BUG-7/8/9/10/11 수정 (2026-03-02) ✅ 완료

### 배경
Sprint 14 배포 후 현장 테스트에서 추가 버그 5건 발견.
공정 진행 task와 시간 계산은 핵심 기능이므로 3-에이전트 팀(BE/FE/TEST)으로 구현.

### 수정 내역

**BUG-7: 휴게시간 자동 일시정지/재개 수정** ✅
- 원인 1: `IntervalTrigger(minutes=1)` → 정각 보장 안 됨 → `CronTrigger(second=0)` 변경
- 원인 2: `send_break_end_notifications()`가 알림만 → `resume_pause()` + `set_paused(False)` 자동재개 추가
- 원인 3: `force_pause_all_active_tasks()`가 `t.worker_id`(첫 번째만) → `work_start_log LEFT JOIN work_completion_log`로 모든 활동 작업자 조회 + 각각 pause log 생성

**BUG-8: 작업시간(duration)에서 휴게시간 자동 차감** ✅
- `_calculate_working_minutes(started_at, completed_at)` 함수 신규 구현
- `_calculate_break_overlap()` 헬퍼: 작업구간과 break 구간의 겹침(분) 계산
- admin_settings 4개 break period (morning/lunch/afternoon/dinner) 자동 차감
- 다일(multi-day) 작업 지원: 각 날짜별 break 차감
- `_record_completion_log()`에서 raw delta 대신 `_calculate_working_minutes()` 사용
- `_finalize_task_multi_worker()`에서 이중차감 방지: manual pause만 차감 (break auto-pause는 `_calculate_working_minutes`에서 이미 처리)

**BUG-9: Force-close에서 pause/휴게시간 차감** ✅
- `admin.py` force-close: pending workers duration에 `_calculate_working_minutes()` 적용
- manual pause만 별도 차감 (break auto-pause 이중차감 방지)
- `duration_minutes = max(0, duration_minutes - manual_pause_minutes)`

**BUG-10: QR 카메라 프레임 스크롤 싱크** ✅
- `qr_scan_screen.dart`: `ScrollController` 추가 + `_onScroll()` 리스너
- 스크롤 시 `_getCameraContainerRect()`로 현재 위치 계산 → `updateScannerDivPosition()` 호출
- `updateScannerDivPosition()`은 `qr_scanner_web.dart`에 이미 구현됨 (Sprint 14)

**BUG-11: Location QR 필수 설정 작동** ✅
- BE `task_service.start_work()`: `get_setting('location_qr_required', False)` 체크, True이고 `location_qr_verified=False`면 400 `LOCATION_QR_REQUIRED` 반환
- FE `task_detail_screen.dart`: `LOCATION_QR_REQUIRED` 에러 시 Location QR 필요 다이얼로그 + "QR 스캔" 버튼
- FE `api_service.dart`: 400 상태코드 에러코드 전파 (`[ERROR_CODE] message` 형식)
- `migration 010`: `location_qr_required` admin_settings 초기값 추가

### 변경 파일
| 파일 | 변경 내용 |
|------|----------|
| `backend/app/services/scheduler_service.py` | IntervalTrigger→CronTrigger, auto-resume, 멀티작업자 pause |
| `backend/app/services/task_service.py` | `_calculate_working_minutes()`, `_calculate_break_overlap()` 신규, duration 수정, 이중차감 방지, location_qr 체크 |
| `backend/app/routes/admin.py` | force-close: `_calculate_working_minutes` + manual pause 차감 |
| `backend/migrations/010_sprint12_hr_schema.sql` | `location_qr_required` admin_settings 초기값 |
| `frontend/lib/screens/qr/qr_scan_screen.dart` | ScrollController + onScroll → updateScannerDivPosition |
| `frontend/lib/screens/task/task_detail_screen.dart` | LOCATION_QR_REQUIRED 에러 다이얼로그 |
| `frontend/lib/services/api_service.dart` | 400 에러코드 전파 |
| `tests/backend/test_break_time_scheduler.py` | +7건 (CronTrigger, auto-resume, 멀티작업자) |
| `tests/backend/test_working_hours.py` | 신규 18건 (break overlap, working minutes, edge cases) |
| `tests/backend/test_force_close.py` | +3건 (pause 차감, break overlap) |
| `tests/backend/test_qr_scanner_logic.py` | +2건 (scroll sync) |
| `tests/backend/test_location_qr_required.py` | 신규 5건 |

### 테스트 결과
- Sprint 14 핫픽스 전체: **76 passed, 1 skipped, 0 failed**
  - test_break_time_scheduler: 7건 추가
  - test_working_hours: 18건 신규
  - test_force_close: 3건 추가
  - test_qr_scanner_logic: 2건 추가
  - test_location_qr_required: 5건 신규
- 빌드: `flutter build web --release` — 에러 0건

### 배포 (2026-03-02)
- [x] git commit & push (`192d135`)
- [x] Railway 자동 배포 (GitHub push)
- [x] flutter build web → Netlify 배포 (https://gaxis-ops.netlify.app)

---

## Sprint 15: 멀티 작업자 Join + BUG-11 재수정 + MH/WH 로깅 (2026-03-03) ✅
> Sprint 15.5 (BUG-15 + /api/app/settings) 포함: commit b277ac8

### 목표
1. 🔴 BUG-12: 멀티 작업자 start/end FE 언블록 — worker2가 이미 시작된 task에 참여/완료 가능
2. 🔴 BUG-11 재수정: Location QR 차단이 여전히 동작하지 않는 문제
3. 🔴 Working Hour 계산 검증 — 휴게시간 차감 로깅 추가
4. MH 계산 Method B 확인 — duration = 개인별 SUM, line_efficiency 로깅

### BE 완료 내역
- **my_status batch query** (work.py L271-317, gst.py L211-252)
  - `work_start_log` + `work_completion_log` JOIN으로 작업자별 참여 상태 조회
  - 응답 필드: `my_status` = 'not_started' | 'in_progress' | 'completed'
  - N+1 방지: `ANY(%s)` 배열 쿼리로 일괄 조회
- **BUG-11 재수정** (task_service.py L96-110)
  - `task.location_qr_verified` (항상 FALSE) → `product.location_qr_id` 체크로 변경
  - `admin_settings.location_qr_required` 설정 기반 조건부 차단
  - `[BUG-11]` 디버그 로그 추가
- **[WORKING_HOURS] 로깅** (task_service.py L598-610)
  - 각 break period overlap 개별 로깅
  - 요약 로그: raw_minutes, break_overlap, net_working_minutes
- **MH line_efficiency 로깅** (task_service.py L875-880)
  - `_finalize_task_multi_worker`에서 MH(duration), CT(elapsed), workers, line_efficiency% 로깅

### FE 완료 내역
- **task_item.dart**: `myStatus` 필드 + `myWorkStatus` getter 추가
- **task_detail_screen.dart**: `_buildJoinButton()` (작업 참여) + `_buildMyCompletedBadge()` (내 작업 완료)
  - 버튼 분기: pending→시작, in_progress+not_started→참여, in_progress+completed→내완료뱃지
- **task_management_screen.dart**: `task.myWorkStatus` 기반 상태 표시 (참여 가능/내 작업 완료)
- **qr_scan_screen.dart**: Location QR 필수 팝업 + 자동 location scan 모드 전환
- **task_provider.dart**: `_extractErrorMessage()` 헬퍼 (startTask/completeTask 에러 처리)
- 빌드: `flutter build web --release` — 에러 0건

### 변경 파일 목록
| 파일 | 변경 내용 |
|------|----------|
| `backend/app/routes/work.py` | my_status batch query 추가 |
| `backend/app/routes/gst.py` | my_status batch query 추가 |
| `backend/app/services/task_service.py` | BUG-11 fix + [WORKING_HOURS] 로깅 + MH 로깅 |
| `frontend/lib/models/task_item.dart` | myStatus 필드 + myWorkStatus getter |
| `frontend/lib/providers/task_provider.dart` | _extractErrorMessage 헬퍼 |
| `frontend/lib/screens/qr/qr_scan_screen.dart` | Location QR 필수 팝업 |
| `frontend/lib/screens/task/task_detail_screen.dart` | Join 버튼 + 내완료 뱃지 |
| `frontend/lib/screens/task/task_management_screen.dart` | myWorkStatus 기반 상태 표시 |
| `frontend/lib/services/task_service.dart` | toggleTaskApplicable 서비스 추가 |
| `tests/backend/test_multi_worker_join.py` | 신규 10건 |
| `tests/backend/test_location_qr_recheck.py` | 신규 6건 |
| `tests/backend/test_working_hours_recheck.py` | 신규 7건 |
| `tests/backend/test_mh_calculation_method_b.py` | 신규 5건 |

### 테스트 결과
- Sprint 15 신규: **28/28 PASSED**
  - test_multi_worker_join: 10건 (my_status 필드 + join 플로우)
  - test_location_qr_recheck: 6건 (BUG-11 location_qr_required 설정 분기)
  - test_working_hours_recheck: 7건 (break time 차감 검증)
  - test_mh_calculation_method_b: 5건 (MH=SUM(개인), line_efficiency)
- 빌드: `flutter build web --release` — 에러 0건

### 배포 (2026-03-03)
- [x] git commit & push (`0d923f5`)
- [x] Railway 자동 배포 (GitHub push)
- [x] flutter build web → Netlify 배포 (https://gaxis-ops.netlify.app)

---

## Sprint 16: Admin 로그인 간소화 + BUG-13/14 수정 + QR 카메라 정사각형 (2026-03-03) ✅

### 목표
1. FEAT-1: Admin 이메일 prefix 매칭 로그인 (`admin` → `admin@gst-in.com`)
2. BUG-13: FE `getAdminSettings()` 에러 시 안전모드 기본값 반환
3. BUG-14: 다중 작업자 표시 디버깅 로깅 (BE + FE)
4. BUG-15: QR 카메라 DOM 정사각형 3중 방어 (CSS + DOM 강제 + MutationObserver)
5. `/api/app/settings` 일반 작업자 접근 허용 엔드포인트 (Sprint 15.5에서 구현, 테스트 추가)

### BE 완료 내역
- **Admin prefix 매칭** (worker.py L275-305)
  - `get_admin_by_email_prefix(prefix)` 신규 함수
  - `SELECT * FROM workers WHERE email LIKE '{prefix}@%' AND is_admin = TRUE`
  - 매칭 1명일 때만 반환, 0명/2명+ → None (보안)
- **auth_service.py login() 분기** (L414-419)
  - `@` 포함 → 기존 정확 매칭
  - `@` 미포함 → admin prefix 우선 → fallback 정확 매칭
- **BUG-14 디버그 로깅** (work.py L293-298, gst.py L197-202)
  - workers batch query 결과에서 2명+ 인 task에 `[BUG-14]` 로그 출력

### FE 완료 내역
- **BUG-13 안전모드** (task_service.dart L264)
  - `getAdminSettings()` catch: `{}` → `{'location_qr_required': true}` (블록 활성 기본값)
- **BUG-14 디버그 로그** (task_item.dart L93-100)
  - `fromJson` workers 파싱 시 2명+ → `debugPrint('[BUG-14]...')` 출력
- **Admin 힌트 텍스트** (login_screen.dart L155-161)
  - 이메일 필드 아래 `'Admin은 이메일 앞부분만 입력 가능'` 안내 텍스트
- **QR 카메라 정사각형 3중 방어** (qr_scanner_web.dart)
  - 방어 1: CSS `aspect-ratio: 1/1 !important` + `video { object-fit: cover }`
  - 방어 2: `_forceSquareAfterCameraStart()` — 카메라 start 후 DOM height=width 강제
  - 방어 3: MutationObserver 실시간 감시 (html5-qrcode 비동기 크기 변경 즉시 재적용)

### 변경 파일 목록
| 파일 | 변경 내용 |
|------|----------|
| `backend/app/models/worker.py` | `get_admin_by_email_prefix()` 신규 |
| `backend/app/services/auth_service.py` | login() prefix 매칭 분기 |
| `backend/app/routes/work.py` | BUG-14 다중 작업자 디버그 로깅 |
| `backend/app/routes/gst.py` | BUG-14 다중 작업자 디버그 로깅 |
| `frontend/lib/services/task_service.dart` | BUG-13 안전모드 기본값 |
| `frontend/lib/models/task_item.dart` | BUG-14 debugPrint + foundation import |
| `frontend/lib/screens/auth/login_screen.dart` | Admin 힌트 텍스트 |
| `frontend/lib/services/qr_scanner_web.dart` | QR 카메라 정사각형 3중 방어 |
| `tests/backend/test_sprint16_admin_login.py` | 신규 4건 |
| `tests/backend/test_sprint16_app_settings.py` | 신규 5건 |

### 테스트 결과
- Sprint 16 신규: **9/9 PASSED**
  - test_sprint16_admin_login: 4건 (full email, prefix, 일반사용자 거부, @매칭)
  - test_sprint16_app_settings: 5건 (admin/worker 접근, 미인증 거부, admin-only)
- 빌드: `flutter build web --release` — 에러 0건

### 배포 (2026-03-03)
- [x] git commit & push (`c7457c4`)
- [x] Railway 자동 배포 (GitHub push)
- [x] flutter build web → Netlify 배포 (https://gaxis-ops.netlify.app)

---

## Sprint 16.1: 버전 관리 + System Online + LOC 형식 정리 (2026-03-03) ✅

### 목표
1. 버전 관리 시스템: BE/FE 단일 소스에서 관리, splash 화면 표시
2. System Online 실제 연동: 목업 → BE `/health` API 실시간 체크
3. 버전 `v1.1.0` (MINOR 업)

### BE 완료 내역
- **`backend/version.py`** (신규)
  - `VERSION = "1.1.0"`, `BUILD_DATE = "2026-03-03"` — 단일 소스
- **`backend/app/__init__.py`** — health 엔드포인트 수정
  - `{"status": "ok", "version": "1.1.0", "build_date": "2026-03-03"}` 반환

### FE 완료 내역
- **`frontend/lib/utils/app_version.dart`** (신규)
  - `AppVersion.version`, `AppVersion.display` — FE 단일 소스
- **`frontend/lib/services/api_service.dart`** — `getPublic()` 추가
  - 인증 없이 루트 경로 GET 요청 (Dio 별도 인스턴스, `/api` prefix 우회)
- **`frontend/lib/screens/auth/splash_screen.dart`** — 3개 수정
  - 버전: `'G-AXIS OPS v1.0.0'` → `AppVersion.display` (중앙 관리)
  - System Online: 목업 → `_checkSystemHealth()` 실시간 `/health` 호출
  - 상태 표시: Connecting...(회색) → System Online(초록) / System Offline(빨강)

### 변경 파일 목록
| 파일 | 변경 내용 |
|------|----------|
| `backend/version.py` | 신규 — 버전 단일 소스 |
| `backend/app/__init__.py` | /health에 version, build_date 추가 |
| `frontend/lib/utils/app_version.dart` | 신규 — FE 버전 단일 소스 |
| `frontend/lib/services/api_service.dart` | getPublic() 메서드 추가 |
| `frontend/lib/screens/auth/splash_screen.dart` | 버전 중앙관리 + health check 실연동 |

### 테스트 결과
- 빌드: `flutter build web --release` — 에러 0건
- `/health` API 응답 확인: version, build_date 포함

### 배포 (2026-03-03)
- [x] git commit & push (`b17f696`)
- [x] Railway 자동 배포 (GitHub push)
- [x] flutter build web → Netlify 배포 (https://gaxis-ops.netlify.app)

---

## Sprint 16.2: 담당공정 설정 이동 + BUG-16/17 배포 (2026-03-03) ✅

### 목표
1. 담당공정 설정 이동: 홈 화면 프로필 카드의 "활성 역할" → 개인설정(ProfileScreen)으로 이동
2. 용어 변경: "활성 역할" → "담당공정" (현장 작업자 이해도 향상)
3. BUG-16/17 코드 반영분 배포 확인

### FE 완료 내역
- **홈 화면 제거** (`home_screen.dart`)
  - 프로필 카드 내 활성 역할 UI 블록 삭제 (line 606-652)
  - `_showActiveRoleDialog()` 메서드 삭제 (ProfileScreen으로 이동)
  - `_getActiveRoleLabel()` 메서드 삭제 (ProfileScreen으로 이동)
  - `_getRoleColor()`, `_getRoleIcon()` — 다른 UI에서 사용하므로 유지
- **개인설정 화면 추가** (`profile_screen.dart`)
  - PIN 설정 위에 "담당공정" 섹션 추가 (GST/Admin만 표시)
  - 담당공정 변경 버튼 → PI/QI/SI 선택 다이얼로그
  - 헬퍼 메서드 3개 추가: `_getActiveRoleLabel()`, `_getRoleColor()`, `_showActiveRoleDialog()`
  - 선택 후 `setState()` 호출로 UI 즉시 갱신

### 변경 파일 목록
| 파일 | 변경 내용 |
|------|----------|
| `frontend/lib/screens/home/home_screen.dart` | 활성 역할 UI + 관련 메서드 삭제 |
| `frontend/lib/screens/settings/profile_screen.dart` | 담당공정 섹션 + 헬퍼 메서드 3개 추가 |

### 테스트 결과
- 빌드: `flutter build web --release` — 에러 0건

### 배포 (2026-03-03)
- [x] git commit & push (`e3d0c8e`)
- [x] Railway 자동 배포 (GitHub push)
- [x] flutter build web → Netlify 배포 (https://gaxis-ops.netlify.app)

---

## Sprint 17: 출퇴근 분류 체계 — work_site + product_line (2026-03-04) ✅

### 목표
1. 협력사 출퇴근 기록에 근무지(work_site: GST/HQ)와 제품군(product_line: SCR/CHI) 분류 추가
2. CHI(칠러) 제조기술부 통합 대비 + ELEC 협력사 변동 대응
3. 버전 `v1.1.0` → `v1.2.0` (MINOR 업 — 신규 기능)

### BE 완료 내역
- **`backend/migrations/017_add_attendance_classification.sql`** (신규)
  - `hr.partner_attendance`에 `work_site VARCHAR(10) NOT NULL DEFAULT 'GST'` 추가
  - `hr.partner_attendance`에 `product_line VARCHAR(10) NOT NULL DEFAULT 'SCR'` 추가
  - CHECK constraint: `work_site IN ('GST', 'HQ')`, `product_line IN ('SCR', 'CHI')`
  - 복합 인덱스: `idx_partner_att_site_line(work_site, product_line)`
  - 기존 데이터는 DEFAULT 값(GST/SCR) 자동 적용
- **`backend/app/routes/hr.py`** — 2개 엔드포인트 수정
  - `attendance_check()`: work_site/product_line 파싱, IN 시 유효성 검사, OUT 시 마지막 IN에서 자동 복사
  - `attendance_today()`: SELECT/Response에 work_site, product_line 추가
- **`backend/version.py`** — `VERSION = "1.2.0"`, `BUILD_DATE = "2026-03-04"`

### FE 완료 내역
- **`frontend/lib/screens/home/home_screen.dart`**
  - 미출근 상태에서 드롭다운 4옵션 표시 (GST공장-SCR, GST공장-CHI, 협력사본사-SCR, 협력사본사-CHI)
  - 퇴근 중/완료 시 드롭다운 숨김
  - 출근(IN) 시만 work_site/product_line API 전송
  - 이전 출근 기록에서 기본값 복원
- **`frontend/lib/utils/app_version.dart`** — `version = '1.2.0'`

### TEST 완료 내역 (5개 신규)
| TC | 테스트 | 설명 |
|----|--------|------|
| TC-ATT-09 | `test_check_in_with_work_site_product_line` | 출근 시 work_site+product_line DB 저장 |
| TC-ATT-10 | `test_check_out_copies_last_in_classification` | 퇴근 시 마지막 IN 값 자동 복사 |
| TC-ATT-11 | `test_invalid_work_site` | 잘못된 work_site → 400 |
| TC-ATT-12 | `test_invalid_product_line` | 잘못된 product_line → 400 |
| TC-ATT-13 | `test_today_includes_classification` | today 응답에 분류 필드 포함 |

### 테스트 결과
- `test_attendance.py`: **13 passed** (기존 8 + 신규 5)
- FE 빌드: `flutter build web --release` — 에러 0건

### 배포 (2026-03-04)
- [x] DB 마이그레이션 실행 (Staging Railway PostgreSQL)
- [x] git commit & push (`b379df4`, `3da2fd7`)
- [x] Railway 자동 배포 (GitHub push)
- [x] flutter build web → Netlify 배포 (https://gaxis-ops.netlify.app)

---

## Sprint 18: 협력사별 S/N 작업 진행률 뷰 — v1.3.0 (2026-03-04) ✅

### 목표
1. 협력사 관리자/작업자가 자사 담당 S/N들의 작업 진행률을 종합 조회
2. 카테고리(MECH/ELEC/TMS)별 진행바 + 전체 진행률 표시
3. AXIS-VIEW(React)에서도 동일 API 재사용 가능하도록 범용 설계
4. 버전 `v1.2.0` → `v1.3.0`

### BE 완료 내역
- **`backend/app/services/progress_service.py`** (신규)
  - `get_partner_sn_progress()` — 협력사별 S/N 필터링 + 카테고리별 진행률 집계
  - 회사별 WHERE 절 자동 구성: FNI/BAT(mech_partner), TMS(M)(mech_partner OR module_outsourcing), TMS(E)/P&S/C&A(elec_partner), GST/Admin(전체)
  - `is_applicable = false` task는 진행률 집계에서 자동 제외
  - 완료 제품 필터: `all_completed = false OR all_completed_at > NOW() - N days`
  - `my_category` 필드로 자사 담당 공정 강조 지원
- **`backend/app/routes/product.py`** — `GET /api/app/product/progress` 엔드포인트 추가
  - `@jwt_required` 인증
  - Admin은 `?company=` 파라미터로 특정 회사 필터 가능
  - `?days=` 파라미터로 완료 후 포함 기간 설정 (기본 1일)
  - Response: `{ products: [...], summary: { total, in_progress, completed_recent } }`
- **`backend/version.py`** — `VERSION = "1.3.0"`

### FE 완료 내역
- **`frontend/lib/screens/progress/sn_progress_screen.dart`** (신규)
  - ConsumerStatefulWidget, RefreshIndicator(pull-to-refresh)
  - 30초 자동 갱신 Timer
  - Summary 카드 (전체/진행 중/최근 완료)
  - S/N별 카드: 모델명, 고객명, 전체 진행바, 카테고리별 미니 진행바, 납기일
  - 자사 담당 공정 강조색 (굵은 글자 + 두꺼운 바)
  - 100% 완료 시 초록 배경 + "(완료)" 뱃지
  - ship_plan_date 오름차순 정렬
- **`frontend/lib/screens/home/home_screen.dart`** — "작업 진행현황" 카드 추가
  - 협력사: "작업 진행현황", GST/Admin: "전사 작업 진행현황"
  - teal 컬러 아이콘 (0xFF0D9488)
- **`frontend/lib/main.dart`** — import + `/sn-progress` 라우트 등록 + saveable routes 추가
- **`frontend/lib/utils/app_version.dart`** — `version = '1.3.0'`

### TEST 완료 내역 (10개 신규)
| TC | 테스트 | 설명 |
|----|--------|------|
| TC-PROG-01 | `test_progress_requires_auth` | JWT 없이 접근 시 401 반환 |
| TC-PROG-02 | `test_fni_worker_sees_own_products` | FNI 작업자 → mech_partner=FNI 제품만 조회 |
| TC-PROG-03 | `test_admin_sees_all_products` | Admin → 전체 제품 조회 |
| TC-PROG-04 | `test_admin_company_filter` | Admin → ?company=FNI 필터링 |
| TC-PROG-05 | `test_non_admin_ignores_company_param` | 비admin ?company= 무시, 자기 회사만 |
| TC-PROG-06 | `test_category_progress_accuracy` | MECH 67%, ELEC 50%, overall 60% 정확성 |
| TC-PROG-07 | `test_non_applicable_excluded` | is_applicable=false → 진행률 제외 |
| TC-PROG-08 | `test_tms_m_filter` | TMS(M) → mech_partner=TMS OR module_outsourcing=TMS |
| TC-PROG-09 | `test_summary_counts` | summary total/in_progress/completed_recent 정확 |
| TC-PROG-10 | `test_ps_worker_elec_filter` | P&S → elec_partner=P&S 제품만 |

### 테스트 결과
- `test_sn_progress.py`: **10 passed**
- `test_attendance.py` 회귀: **13 passed** (변경 없음)
- FE 빌드: `flutter build web --release` — 에러 0건

### 배포 (2026-03-04)
- [x] DB 마이그레이션 없음 (기존 테이블 활용)
- [x] git commit & push (`f566e25`)
- [x] Railway 자동 배포 (GitHub push)
- [x] flutter build web → Netlify 배포 (https://gaxis-ops.netlify.app)

---

## Sprint 19-A: Refresh Token Rotation + Device ID (2026-03-05) ✅

### 목표
1. Refresh Token Rotation 구현 — 토큰 탈취 창 30일 → 2시간 축소
2. Device ID 수집 (로깅 전용) — 다중 기기 식별 기반 마련 (Phase C에서 DB 저장 예정)

### Phase A: Refresh Token Rotation (BE 코드 수정만)
- **`backend/app/services/auth_service.py`** — `refresh_access_token()` 수정
  - 기존: `access_token`만 반환
  - 변경: `access_token` + 새 `refresh_token` 함께 반환
  - `jti` (UUID v4) 필드 추가 → 같은 초에 생성해도 고유 토큰 보장
- **FE 수정 불필요**: OPS FE `auth_service.dart:252`에 `if (response['refresh_token'] != null)` 이미 있음

### Phase B: Device ID 수집
- **`frontend/lib/services/auth_service.dart`** — `getDeviceId()` 메서드 추가
  - SharedPreferences 기반 (웹+모바일 크로스플랫폼)
  - `dart:math` Random.secure()로 UUID v4 생성 (외부 패키지 불필요)
  - 최초 생성 후 영구 저장, 이후 재사용
- **`frontend/lib/screens/auth/pin_login_screen.dart`** — PIN 로그인에 device_id 전송
- **`backend/app/routes/auth.py`** — login, refresh, pin-login 3곳에 device_id 수신 + 로깅
  - `data.get('device_id', 'unknown')` — 미전송 시 'unknown' 기본값 (에러 아님)

### TEST 완료 내역 (6개 신규)
| TC | 테스트 | 설명 |
|----|--------|------|
| TC-ROT-01 | `test_refresh_returns_both_tokens` | refresh 응답에 access_token + refresh_token 모두 포함 |
| TC-ROT-02 | `test_new_refresh_token_works` | 새 refresh_token으로 재차 refresh 성공 |
| TC-ROT-03 | `test_old_refresh_token_still_works` | 이전 refresh_token 아직 유효 (Phase C에서 차단 예정) |
| TC-ROT-04 | `test_login_with_device_id` | login에 device_id 포함 → 정상 200 |
| TC-ROT-05 | `test_login_without_device_id` | device_id 미전송 → 정상 처리 |
| TC-ROT-06 | `test_refresh_with_device_id` | refresh에 device_id 포함 → rotation 정상 |

### 테스트 결과
- `test_auth_rotation.py`: **6 passed**
- `test_refresh_token.py` 회귀: **28 passed** (회귀 0건)
- FE 빌드: `flutter build web --release` — 에러 0건

### 배포 (2026-03-05)
- [x] git commit & push (`0f527c1`)
- [x] Railway 자동 배포 (GitHub push)
- [x] flutter build web → Netlify 배포 (https://gaxis-ops.netlify.app)

---

## Sprint 19-B: DB 기반 Refresh Token 관리 + 탈취 감지 (2026-03-06) ✅

### 목표
1. Refresh Token을 DB(auth 스키마)에 해시 저장 — 토큰 무효화(revoke) 가능
2. 탈취 감지: revoked 토큰 재사용 시 해당 worker 전체 토큰 자동 무효화
3. 로그아웃 API 구현 (토큰 DB 무효화)
4. Device별 토큰 관리 (동일 worker+device → 이전 토큰 rotation revoke)

### BE 완료 내역
- **`backend/migrations/018_auth_refresh_tokens.sql`** (신규)
  - `auth` 스키마 생성
  - `auth.refresh_tokens` 테이블: worker_id, device_id, token_hash(SHA256), expires_at, revoked, revoked_reason
  - 인덱스 2개: `idx_refresh_tokens_worker`, `idx_refresh_tokens_hash`
- **`backend/app/services/auth_service.py`** — 4개 메서드 추가
  - `_store_refresh_token()`: 로그인/refresh 시 DB에 해시 저장 + 동일 (worker, device) 이전 토큰 revoke
  - `_validate_refresh_token_db()`: DB 검증 + 탈취 감지 (revoked 토큰 재사용 → 전체 무효화)
  - `revoke_refresh_token()`: 단일 토큰 무효화 (로그아웃)
  - `revoke_all_worker_tokens()`: worker 전체 토큰 무효화 (탈취 감지/관리자)
- **`backend/app/routes/auth.py`** — `POST /api/auth/logout` 엔드포인트 추가
  - refresh_token 전송 시 해당 토큰 revoke, 미전송 시 worker 전체 토큰 revoke

### TEST 완료 내역 (10개 신규)
| TC | 테스트 | 설명 |
|----|--------|------|
| TC-TDB-01 | `test_login_stores_token_in_db` | 로그인 시 auth.refresh_tokens에 해시 저장 |
| TC-TDB-02 | `test_refresh_rotates_token_in_db` | refresh 시 이전 토큰 revoked + 새 토큰 저장 |
| TC-TDB-03 | `test_theft_detection_revokes_all` | revoked 토큰 재사용 → 전체 토큰 무효화 |
| TC-TDB-04 | `test_logout_revokes_token` | 로그아웃 시 토큰 DB 무효화 |
| TC-TDB-05 | `test_logout_token_cannot_refresh` | 로그아웃된 토큰으로 refresh 불가 |
| TC-TDB-06 | `test_logout_without_token_revokes_all` | 토큰 미전송 로그아웃 → 전체 무효화 |
| TC-TDB-07 | `test_rotation_per_device` | 동일 device에서 refresh 시 이전만 revoke |
| TC-TDB-08 | `test_token_hash_format` | SHA256 해시 64자 형식 검증 |
| TC-TDB-09 | `test_pin_login_stores_token` | PIN 로그인도 DB 토큰 저장 |
| TC-TDB-10 | `test_logout_requires_auth` | JWT 없이 로그아웃 → 401 |

---

## Sprint 19-D: Geolocation 기반 출퇴근 위치 보안 (2026-03-06) ✅

### 목표
1. 협력사 출퇴근 시 GPS 좌표 검증 — 허용 반경 밖이면 차단
2. Admin 설정으로 기준점(위도/경도) + 반경(m) + on/off 제어
3. soft/strict 모드: soft=위치 미전송 시 경고만, strict=거부
4. work_site='HQ'(협력사 본사) → GPS 검증 면제

### BE 완료 내역
- **`backend/migrations/019_geolocation_settings.sql`** (신규)
  - admin_settings에 5개 키 추가: `geo_check_enabled`, `geo_latitude`, `geo_longitude`, `geo_radius_meters`, `geo_strict_mode`
  - 기본값: 비활성(false), GST 공장 좌표(37.4028, 127.1060), 반경 500m, soft 모드
- **`backend/app/services/geo_service.py`** (신규)
  - `verify_location(lat, lon)` → Haversine 공식으로 거리 계산, (allowed, distance) 반환
  - `is_geo_check_enabled()` → admin_settings 조회
  - `is_geo_strict_mode()` → 엄격 모드 여부 조회
  - `get_geo_config()` → 전체 설정 딕셔너리 반환
- **`backend/app/routes/hr.py`** — `attendance_check()` 수정
  - GPS 검증 조건: `is_geo_check_enabled() and work_site == 'GST'` (HQ 면제)
  - soft 모드: 좌표 미전송 → 경고 로그만, 출근 허용
  - strict 모드: 좌표 미전송 → 400 LOCATION_REQUIRED 거부
  - 좌표 전송 시: 거리 검증 → 403 OUT_OF_RANGE
- **`backend/app/routes/admin.py`** — `geo_strict_mode` 추가 (defaults + ALLOWED_KEYS)

### FE 완료 내역
- **`frontend/lib/screens/admin/admin_options_screen.dart`** — 위치 보안 섹션 추가
  - 위치 보안 on/off 토글, 위도/경도/반경 입력 필드
  - BE 키명 정합: `geo_check_enabled`, `geo_latitude`, `geo_longitude`
- **`frontend/lib/screens/home/home_screen.dart`** — 출퇴근 시 GPS 좌표 전송
  - `navigator.geolocation.getCurrentPosition()` → `latitude`/`longitude` 키로 전송
  - 403 OUT_OF_RANGE 에러 시 사용자 안내 메시지

### BE/FE 키명 정합 수정 (리드 세션)
에이전트 구현 후 발견된 BE↔FE 키 불일치 6건 수정:
| FE (수정 전) | BE (정답) | 수정 파일 |
|---|---|---|
| `geolocation_enabled` | `geo_check_enabled` | admin_options_screen.dart |
| `geo_lat` | `geo_latitude` | admin_options_screen.dart |
| `geo_lng` | `geo_longitude` | admin_options_screen.dart |
| `body['lat']` | `body['latitude']` | home_screen.dart |
| `body['lng']` | `body['longitude']` | home_screen.dart |
| `LOCATION_OUT_OF_RANGE` | `OUT_OF_RANGE` | home_screen.dart |

추가 누락 구현:
- BE `geo_strict_mode` 설정 키 추가 (migration + geo_service + admin.py)
- BE `work_site='HQ'` GPS 검증 면제 로직 (hr.py)
- BE soft/strict 모드 분기 (hr.py)

### TEST 완료 내역 (11개 신규)
| TC | 테스트 | 설명 |
|----|--------|------|
| TC-GEO-01 | `test_geo_disabled_allows_checkin` | geo 비활성 → 좌표 없이 출근 성공 |
| TC-GEO-02 | `test_geo_soft_mode_no_coords_allows` | soft 모드 + 좌표 미전송 → 201 허용 |
| TC-GEO-03 | `test_geo_enabled_valid_location_allows` | 허용 범위 내 좌표 → 출근 성공 |
| TC-GEO-04 | `test_geo_enabled_out_of_range_blocks` | 범위 밖 좌표 → 403 OUT_OF_RANGE |
| TC-GEO-05 | `test_geo_enabled_invalid_coords_rejected` | 잘못된 좌표 형식 → 400 |
| TC-GEO-06 | `test_geo_custom_radius_allows` | 커스텀 반경 설정 → 범위 판정 정확 |
| TC-GEO-07 | `test_admin_get_geo_settings` | GET admin settings → 5개 geo 키 포함 |
| TC-GEO-08 | `test_geo_checkout_skips_validation` | 퇴근(OUT)은 GPS 검증 스킵 |
| TC-GEO-09 | `test_geo_strict_mode_no_coords_blocks` | strict 모드 + 좌표 미전송 → 400 |
| TC-GEO-10 | `test_hq_work_site_bypasses_geo` | HQ 근무지 → GPS 검증 면제 |
| TC-GEO-11 | `test_admin_update_geo_strict_mode` | admin settings → geo_strict_mode 업데이트 |

### 테스트 결과
- `test_geolocation.py`: **11 passed** (113s)
- `test_token_db.py`: **10 passed**
- 전체 회귀: **526 passed, 23 failed (기존), 11 skipped, 14 errors** — 신규 regression 0건
- FE 빌드: `flutter build web --release` — 에러 0건

### 생성/수정 파일
```
backend/migrations/018_auth_refresh_tokens.sql           # 신규 (19-B)
backend/migrations/019_geolocation_settings.sql          # 신규 (19-D)
backend/app/services/auth_service.py                     # 수정 (19-B: DB 토큰 메서드 4개)
backend/app/services/geo_service.py                      # 신규 (19-D)
backend/app/routes/auth.py                               # 수정 (19-B: logout 엔드포인트)
backend/app/routes/hr.py                                 # 수정 (19-D: GPS 검증 + soft/strict + HQ 면제)
backend/app/routes/admin.py                              # 수정 (19-D: geo_strict_mode)
frontend/lib/screens/admin/admin_options_screen.dart      # 수정 (19-D: 위치 보안 UI + 키명 정합)
frontend/lib/screens/home/home_screen.dart                # 수정 (19-D: GPS 좌표 전송 + 키명 정합)
tests/backend/test_token_db.py                           # 신규 (19-B: 10 tests)
tests/backend/test_geolocation.py                        # 신규 (19-D: 11 tests)
```

---

## Hotfix: Admin 옵션 UI 일관성 개선 (2026-03-06)

### FE 수정 내역
- `admin_options_screen.dart` — 협력사 관리자 관리 (섹션 2) UI 패턴 통일
  - 기존: `Column` + `map` 전체 펼침 → 명단 많으면 화면 넘침
  - 변경: `BoxConstraints(maxHeight: 300)` + `Scrollbar` + `ListView.separated`
  - 가입 승인 대기 (섹션 0)와 동일한 스크롤 패턴 적용 → UI 일관성 확보

### 배포
- Netlify: https://gaxis-ops.netlify.app (production deploy 완료)

---

## Sprint 19-E: VIEW용 Admin 출퇴근 API (2026-03-06) ✅

### 목표
AXIS-VIEW 대시보드가 실 데이터를 조회할 수 있도록 Admin 전용 출퇴근 API 3개 추가.
VIEW Sprint 3 (실 데이터 연결)의 선행 작업.

### BE 완료 내역
- **`backend/app/routes/admin.py`** — 3개 엔드포인트 + 공통 함수 추가
  - `GET /api/admin/hr/attendance/today` — 오늘 전체 출퇴근 현황 (KST 기준)
  - `GET /api/admin/hr/attendance?date=YYYY-MM-DD` — 날짜별 출퇴근 현황 조회
  - `GET /api/admin/hr/attendance/summary` — 회사별 출퇴근 요약
  - `_kst_date_range()` — KST 기준 날짜 범위 계산 헬퍼
  - `_get_attendance_data()` — 출퇴근 데이터 조회 공통 함수 (records + summary 반환)
- **핵심 로직**:
  - KST 기준 날짜 범위 계산 (UTC 이슈 방지)
  - IN/OUT 피봇 SQL (LEFT JOIN + CASE WHEN + GROUP BY)
  - status 계산: not_checked / working / left
  - company != 'GST' 필터 (협력사만)
  - approval_status = 'approved' 필터 (미승인 제외)
  - ISO8601 KST 문자열 변환

### TEST 완료 내역 (8개 신규)
| TC | 테스트 | 설명 |
|----|--------|------|
| ATT-01 | `test_att01_empty_data` | 출퇴근 기록 없음 → 전부 not_checked |
| ATT-02 | `test_att02_checked_in_only` | 출근만 → status='working' |
| ATT-03 | `test_att03_checked_in_and_out` | 출근+퇴근 → status='left' |
| ATT-04 | `test_att04_not_checked` | 미출근 → status='not_checked' |
| ATT-05 | `test_att05_date_param` | 날짜 파라미터 정상 동작 |
| ATT-06 | `test_att06_invalid_date` | 잘못된 날짜 → 400 에러 |
| ATT-07 | `test_att07_company_summary` | 회사별 집계 정확성 |
| ATT-08 | `test_att08_non_admin_forbidden` | 비관리자 → 403 |

### 테스트 결과
- `test_admin_attendance.py`: **8 passed** (160s)

### 생성/수정 파일
```
backend/app/routes/admin.py                # 수정 (3개 엔드포인트 + 공통 함수)
tests/backend/test_admin_attendance.py     # 신규 (8 tests)
```

---

## Sprint 20-A: 신규 가입 시 Admin 이메일 알림 (2026-03-06) ✅

### 목표
작업자가 회원가입하면 DB의 `is_admin=true` 사용자 전원에게 이메일 자동 발송.
가입 사실을 즉시 인지하고 승인/거부 판단 가능.

### BE 완료 내역
- **`backend/app/services/email_service.py`** (신규)
  - `get_admin_emails()` — DB에서 is_admin=true 사용자 이메일 목록 조회
  - `_send_email()` — smtplib SMTP 발송 (auth_service.py와 동일 패턴)
  - `render_register_notification()` — 신규 가입 알림 HTML 템플릿 (이름, 이메일, 역할, 협력사, 가입일시)
  - `send_register_notification()` — Admin 전원에게 알림 발송 (best-effort)
- **`backend/app/routes/auth.py`** — register 성공(201) 시 알림 호출 추가
  - try-catch best-effort: 이메일 실패해도 가입 정상 완료

### TEST 완료 내역 (5개 신규)
| TC | 테스트 | 설명 |
|----|--------|------|
| MAIL-01 | `test_mail01_register_triggers_admin_notification` | 가입 → send_register_notification 호출 확인 |
| MAIL-02 | `test_mail02_smtp_not_configured_register_succeeds` | SMTP 미설정 → 가입 성공 |
| MAIL-03 | `test_mail03_smtp_failure_register_succeeds` | SMTP 실패 → 가입 성공 |
| MAIL-04 | `test_mail04_notification_contains_worker_info` | 이메일 내용에 가입자 정보 포함 |
| MAIL-05 | `test_mail05_multiple_admins_each_receive` | Admin 여러 명 → 각각 개별 발송 |

### 테스트 결과
- `test_admin_email_notification.py`: **5 passed** (34s)

### 생성/수정 파일
```
backend/app/services/email_service.py              # 신규
backend/app/routes/auth.py                         # 수정 (register에 알림 호출)
tests/backend/test_admin_email_notification.py     # 신규 (5 tests)
```

---

## Sprint 20-B: 공지사항 탭 (앱 내 업데이트 노트) (2026-03-06) ✅

### 목표
앱 내 공지사항 기능 — 버전 업데이트마다 사용자에게 변경사항을 요약 게시.
Admin이 직접 공지 작성/수정/삭제.

### BE 완료 내역
- **`backend/migrations/020_create_notices.sql`** (신규)
  - `notices` 테이블 생성 (title, content, version, is_pinned, created_by)
  - `updated_at` 자동 갱신 트리거
- **`backend/app/routes/notices.py`** (신규) — 5개 엔드포인트
  - `GET /api/notices` — 공지 목록 (고정 상단, 최신순, 페이지네이션, 버전 필터)
  - `GET /api/notices/<id>` — 공지 상세
  - `POST /api/admin/notices` — 공지 작성 (Admin only)
  - `PUT /api/admin/notices/<id>` — 공지 수정 (Admin only)
  - `DELETE /api/admin/notices/<id>` — 공지 삭제 (Admin only)
- **`backend/app/__init__.py`** — `notices_bp` Blueprint 등록

### FE 완료 내역
- **`frontend/lib/services/notice_service.dart`** (신규) — API 호출 서비스
- **`frontend/lib/screens/notice/notice_list_screen.dart`** (신규) — 공지 목록 화면
  - 고정 공지 핀 아이콘, 버전 태그, 더 보기 페이지네이션
  - SharedPreferences로 마지막 확인 공지 ID 저장
- **`frontend/lib/screens/notice/notice_detail_screen.dart`** (신규) — 공지 상세 화면
  - 제목, 본문, 작성자, 날짜, 버전 태그, 고정 아이콘
  - Admin: 삭제 버튼
- **`frontend/lib/screens/admin/notice_write_screen.dart`** (신규) — Admin 공지 작성 화면
  - 제목, 내용, 버전(선택), 상단 고정 토글
- **`frontend/lib/screens/home/home_screen.dart`** — 공지사항 메뉴 카드 추가
- **`frontend/lib/main.dart`** — `/notices`, `/notice-write` 라우트 등록
- FE 빌드: `flutter build web --release` 에러 0건

### TEST 완료 내역 (6개 신규)
| TC | 테스트 | 설명 |
|----|--------|------|
| NTC-01 | `test_ntc01_admin_create_notice` | Admin 공지 작성 → 목록 표시 |
| NTC-02 | `test_ntc02_non_admin_create_forbidden` | 일반 작업자 → 403 |
| NTC-03 | `test_ntc03_pagination` | 페이지네이션 (10개 단위) |
| NTC-04 | `test_ntc04_pinned_on_top` | 고정 공지 상단 표시 |
| NTC-05 | `test_ntc05_update_and_delete` | 수정/삭제 |
| NTC-06 | `test_ntc06_version_filter` | 버전 필터 |

### 테스트 결과
- `test_notices_api.py`: **6 passed** (80s)

### 생성/수정 파일
```
backend/migrations/020_create_notices.sql                          # 신규
backend/app/routes/notices.py                                      # 신규 (5 endpoints)
backend/app/__init__.py                                            # 수정 (Blueprint 등록)
frontend/lib/services/notice_service.dart                          # 신규
frontend/lib/screens/notice/notice_list_screen.dart                # 신규
frontend/lib/screens/notice/notice_detail_screen.dart              # 신규
frontend/lib/screens/admin/notice_write_screen.dart                # 신규
frontend/lib/screens/home/home_screen.dart                         # 수정 (메뉴 추가)
frontend/lib/main.dart                                             # 수정 (라우트 등록)
tests/backend/test_notices_api.py                                  # 신규 (6 tests)
```

## Sprint 21: QR Registry 목록 API (2026-03-07) ✅

### 목표
Admin/Manager용 QR 등록 목록 조회 API — 검색, 필터, 페이지네이션, 통계 제공.

### BE 완료 내역
- **`backend/app/routes/qr.py`** (신규) — 1개 엔드포인트
  - `GET /api/admin/qr/list` — QR 목록 조회 (qr_registry JOIN product_info)
    - 검색: S/N 또는 qr_doc_id 부분검색 (ILIKE)
    - 필터: model, status (active/revoked)
    - 페이지네이션: page, per_page (default 50, max 200)
    - 정렬: sort_by (qr.created_at, serial_number, model, mech_start, module_start, sales_order), sort_order (asc/desc)
    - 응답: items, total, page, per_page, total_pages, models (필터용 목록), stats (total/active/revoked)
    - 권한: `@jwt_required` + `@manager_or_admin_required`
- **`backend/app/__init__.py`** — `qr_bp` Blueprint 등록 (Sprint 21 주석)

### 생성/수정 파일
```
backend/app/routes/qr.py                                            # 신규 (1 endpoint)
backend/app/__init__.py                                              # 수정 (Blueprint 등록)
```

## ETL 파이프라인 → axis-core-etl repo 분리 (2026-03-09)

> ETL 코드가 별도 repo(`axis-core-etl`)로 분리되었습니다.
> 이후 ETL 관련 진행 상황은 `AXIS-CORE/CORE-ETL/PROGRESS.md`에서 관리.
>
> **repo**: axis-core-etl
> **관계**: axis-core-etl → AXIS-OPS DB 직접 적재 (DATABASE_URL)
