# AXIS-OPS 프로젝트 진행 상황

## 개요
GST 제조 현장 작업 관리 시스템 — 스프레드시트 수동 입력에서 모바일 App 실시간 Push로 전환.

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

## Sprint 4: 관리자 + 퇴근시간 자동감지 (예정)

### BE 작업 목록
1. **관리자 승인 API** — `POST /api/admin/approve/{worker_id}` 구현 (현재 stub)
   - `jwt_required` + `admin_required` 적용
   - workers.approval_status 업데이트 (approved/rejected)
   - WebSocket으로 승인 결과 알림

2. **승인 대기 작업자 목록** — `GET /api/admin/pending-workers` 구현
   - approval_status='pending' 작업자 조회
   - 페이지네이션 지원

3. **관리자 대시보드 API** — `GET /api/admin/dashboard` 구현
   - 공정별 완료 현황 집계
   - 미완료 작업 수, 알림 현황

4. **미완료 Task 수동 보정** — `PUT /api/admin/task/close` 구현
   - 관리자가 completed_at 직접 입력
   - 감사 로그 기록

5. **퇴근시간 자동감지 cron** — `check_unfinished_tasks()` 연동
   - APScheduler 또는 cron으로 매일 20:00(평일)/17:00(주말) 실행
   - 14시간 초과 미완료 작업 → UNFINISHED_AT_CLOSING 알림

6. **오프라인 동기화 API** — `POST /api/app/sync/offline-data` 구현
   - offline_sync_queue 테이블 활용
   - 배치 INSERT/UPDATE 처리

7. **admin_bp, sync_bp Blueprint 등록** — `__init__.py`에서 활성화

### FE 작업 목록
1. 관리자 대시보드 UI 구현 (admin_dashboard.dart)
2. 작업자 승인 화면 완성 (worker_approval_screen.dart)
3. 오프라인 동기화 로직 (local_db_service.dart + sync queue)
4. 미완료 Task 알림 처리 UI

### TEST 작업 목록
1. BE 코드 리뷰 (Sprint 4 BE 코드 검증)
2. 관리자 승인 API 테스트
3. 퇴근시간 자동감지 테스트
4. 오프라인 동기화 테스트
5. 관리자 대시보드 테스트
