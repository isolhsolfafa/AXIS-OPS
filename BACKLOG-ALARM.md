# AXIS-OPS 알람(Alert) 로직 정리

> 마지막 업데이트: 2026-03-01
> 알람 시스템 전체 현황 — 트리거, 수신자, 메시지, 전달 방식

---

## 현재 구현된 알람 (13종)

### A. 작업 완료 연쇄 알림

| 알람 타입 | 트리거 | 수신자 | 메시지 |
|-----------|--------|--------|--------|
| TMS_TANK_COMPLETE | TMS `PRESSURE_TEST` 완료 | MECH 관리자 | `[시리얼] TMS 가압검사 완료: 작업명 작업이 완료되었습니다.` |
| TANK_DOCKING_COMPLETE | MECH `TANK_DOCKING` 완료 | ELEC 관리자 | `[시리얼] Tank Docking 완료: 작업명 작업이 완료되었습니다.` |

**흐름**:
- TMS_TANK_COMPLETE: `complete_work()` → `_trigger_completion_alerts()` → `create_and_broadcast_alert()`
- TANK_DOCKING_COMPLETE: `complete_single_action_route()` → `_trigger_completion_alerts()` → `create_alert()` (Sprint 27: SINGLE_ACTION)

---

### B. 공정 선행 검증 알림

| 알람 타입 | 트리거 | 수신자 | 메시지 |
|-----------|--------|--------|--------|
| PROCESS_READY | PI/QI/SI 작업 시작 시 MECH 미완료 | MECH 관리자 | `[시리얼] PI 공정 대기 중 - MECH 공정 미완료` |
| PROCESS_READY | PI/QI/SI 작업 시작 시 ELEC 미완료 | ELEC 관리자 | `[시리얼] PI 공정 대기 중 - ELEC 공정 미완료` |

**흐름**: `start_work()` → `validate_process_start()` → `create_alert()`

---

### C. 시간 이상 알림

| 알람 타입 | 트리거 | 수신자 | 메시지 |
|-----------|--------|--------|--------|
| DURATION_EXCEEDED | task 완료 시 작업시간 > 14시간(840분) | 해당 role 관리자 | `[시리얼] MECH - 작업명: 작업 시간 850분 (14시간 초과)` |
| REVERSE_COMPLETION | task 완료 시 `completed_at < started_at` | 해당 role 관리자 | `[시리얼] MECH - 작업명: 완료 시간이 시작 시간보다 이릅니다.` |

**흐름**: `complete_work()` → `validate_duration()` → `create_alert()`

---

### D. 스케줄러 자동 알림 (Cron)

| 알람 타입 | 스케줄 | 수신자 | 메시지 |
|-----------|--------|--------|--------|
| TASK_REMINDER | 매시 정각 (:00) | 진행 중 task 작업자 본인 | `[시리얼] 작업명: 작업 시작 후 3시간 경과, 아직 완료 전입니다.` |
| SHIFT_END_REMINDER | 17:00, 20:00 KST | 미완료 task 작업자 (1인 1회) | `퇴근 전 미완료 작업이 있습니다. [시리얼] 작업명. 작업을 완료하거나 관리자에게 보고해주세요.` |
| UNFINISHED_AT_CLOSING | 18:00 KST | 해당 role 관리자 | `[시리얼] 작업명: 작업 시작 후 15시간 경과, 미완료 상태` |
| TASK_ESCALATION | 09:00 KST (익일) | 작업자 소속 회사 관리자 (없으면 Admin) | `[에스컬레이션] [시리얼] 작업명: 전일(2026-02-28) 시작 후 미완료. 작업자: 홍길동 (FNI)` |

**조건**:
- TASK_REMINDER: `started_at IS NOT NULL AND completed_at IS NULL`
- TASK_ESCALATION: `started_at < 오늘 00:00 KST AND completed_at IS NULL`

---

### E. 휴게시간 자동 일시정지

| 알람 타입 | 트리거 | 수신자 | 메시지 |
|-----------|--------|--------|--------|
| BREAK_TIME_PAUSE | 휴게시간 시작 (오전/점심/오후/저녁) | 진행 중 task 작업자 본인 | `[시리얼] 작업명: 점심시간이 시작되었습니다. 작업이 자동으로 일시정지됩니다.` |
| BREAK_TIME_END | 휴게시간 종료 | Pause 상태 작업자 (1인 1회) | `점심시간이 종료되었습니다. 작업을 재개해주세요.` |

**조건**: `admin_settings.auto_pause_enabled = TRUE` 필수
**휴게 구간**: `break_morning`, `lunch`, `break_afternoon`, `dinner` (admin_settings 기반)

---

### F. 가입 승인/거부

| 알람 타입 | 트리거 | 수신자 | 메시지 |
|-----------|--------|--------|--------|
| WORKER_APPROVED | Admin이 가입 승인 | 해당 작업자 | `가입 신청이 승인되었습니다.` |
| WORKER_REJECTED | Admin이 가입 거부 | 해당 작업자 | `가입 신청이 거부되었습니다.` |

---

## 알람 수신자 결정 방식

| 방식 | 설명 | 사용처 |
|------|------|--------|
| 개인 지정 | `target_worker_id` 직접 설정 | TASK_REMINDER, SHIFT_END, BREAK_TIME, 가입승인 |
| Role 기반 | `role = target_role AND is_manager = TRUE` | PROCESS_READY, DURATION, 완료 연쇄 |
| 회사 기반 | `company = 작업자.company AND is_manager = TRUE` | TASK_ESCALATION |
| Admin 폴백 | `is_admin = TRUE` (회사 없을 때) | TASK_ESCALATION 폴백 |

---

## 알람 전달 경로

```
트리거 발생
  ├─ DB 저장: app_alert_logs 테이블 INSERT
  └─ WebSocket 실시간 전달: emit_new_alert(worker_id, alert_data)
       ├─ new_alert 이벤트 (개인 대상)
       ├─ process_alert 이벤트 (Role 대상)
       └─ duration_alert 이벤트 (시간 이상)
```

---

## 알람 API

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/app/alerts` | 알람 목록 (페이징, unread_only 필터) |
| GET | `/api/app/alerts/unread-count` | 미읽은 알람 수 |
| PUT | `/api/app/alerts/{id}/read` | 단건 읽음 처리 |
| PUT | `/api/app/alerts/read-all` | 전체 읽음 처리 |

---

## FE 알람 우선순위

| 우선순위 | 알람 타입 | 아이콘 |
|----------|-----------|--------|
| 3 (높음) | DURATION_EXCEEDED, REVERSE_COMPLETION | timer_off, error_outline |
| 2 (중간) | PROCESS_READY, UNFINISHED_AT_CLOSING | notifications_active, warning |
| 1 (낮음) | TASK_REMINDER, BREAK_TIME_*, WORKER_* | 기본 |

---

## DB 스키마 (app_alert_logs)

| 컬럼 | 타입 | 설명 |
|-------|------|------|
| id | int (PK) | |
| alert_type | string (enum) | 13종 알람 타입 |
| serial_number | string (nullable) | 제품 시리얼 |
| qr_doc_id | string (nullable) | QR 문서 ID |
| triggered_by_worker_id | int (nullable) | 트리거한 작업자 |
| target_worker_id | int (nullable) | 수신 작업자 (개인 대상) |
| target_role | string (nullable) | 수신 Role (Role 대상) |
| message | string | 알람 메시지 |
| is_read | boolean (default: FALSE) | 읽음 여부 |
| read_at | timestamp (nullable) | 읽은 시각 |
| created_at | timestamp | 생성 시각 |
| updated_at | timestamp | 수정 시각 |

---

## 공정 흐름과 알람 매핑

```
TMS 가압검사(PRESSURE_TEST) 완료
  └─→ [TMS_TANK_COMPLETE] → MECH 관리자 알림
        │
        ▼
MECH Tank Docking(TANK_DOCKING) 완료
  └─→ [TANK_DOCKING_COMPLETE] → ELEC 관리자 알림
        │
        ▼
ELEC 작업 완료
  └─→ (현재 알람 없음)
        │
        ▼
PI/QI/SI 시작 시도 (선행 미완료 시)
  └─→ [PROCESS_READY] → MECH/ELEC 관리자 알림
```

---

## 추가 검토 필요 알람

| 제안 | 트리거 | 수신자 | 상태 |
|------|--------|--------|------|
| ELEC 완료 → 검사 시작 가능 | ELEC 전체 공정 완료 | PI/QI/SI 관리자 | 미구현 |
| QI 완료 → 출하 준비 가능 | QI 품질검사 통과 | SI 관리자 | 미구현 |
| 전체 공정 완료 → 출하 가능 | 모든 공정 완료 | Admin/GST 관리자 | 미구현 |
| 작업 시작 알림 | 작업자가 task 시작 | 해당 팀 관리자 | 미구현 |
| QR 스캔 실패 | QR 코드 DB 미존재 | Admin | 미구현 |

---

## 관련 소스 파일

| 파일 | 역할 |
|------|------|
| `backend/app/services/scheduler_service.py` | Cron 스케줄러 (TASK_REMINDER, SHIFT_END, ESCALATION, BREAK_TIME) |
| `backend/app/services/duration_validator.py` | 시간 검증 (DURATION_EXCEEDED, REVERSE_COMPLETION, UNFINISHED) |
| `backend/app/services/process_validator.py` | 공정 선행 검증 (PROCESS_READY) |
| `backend/app/services/task_service.py` | 완료 연쇄 알림 (_trigger_completion_alerts) |
| `backend/app/models/alert.py` | Alert 모델 + create_alert, create_and_broadcast_alert |
| `backend/app/routes/alert.py` | Alert API 엔드포인트 |
| `backend/app/routes/admin.py` | 가입 승인/거부 알림 |
| `frontend/lib/models/alert_log.dart` | AlertLog 모델 (우선순위, 아이콘) |
| `frontend/lib/services/alert_service.dart` | Alert API 호출 |
| `frontend/lib/providers/alert_provider.dart` | Riverpod 상태 관리 |
