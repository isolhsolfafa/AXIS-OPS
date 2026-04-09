# AXIS-OPS 알람(Alert) 로직 정리

> 마지막 업데이트: 2026-04-08
> 알람 시스템 전체 현황 — 20종 트리거, 수신자, 메시지, 전달 방식
> DB enum: `alert_type_enum` (migration 004 → 006 → 008 → 041 → 042 → 043 → 044)

---

## 현재 구현된 알람 (20종)

### A. 작업 완료 연쇄 알림 (4종)

| # | 알람 타입 | 트리거 | 수신자 | 메시지 | admin_settings 옵션 |
|---|-----------|--------|--------|--------|---------------------|
| 1 | TMS_TANK_COMPLETE | TMS `PRESSURE_TEST` 완료 (양방향 가압 전부 완료) | MECH partner 관리자 | `[SN \| O/N: xxx] TMS 가압검사 완료: 작업명 작업이 완료되었습니다.` | `alert_tm_to_mech_enabled` |
| 2 | TMS_TANK_COMPLETE | MECH `PRESSURE_TEST` 완료 | QI 관리자 | `[SN \| O/N: xxx] MECH 가압검사 완료: 작업명 작업이 완료되었습니다.` | `alert_mech_pressure_to_qi_enabled` |
| 3 | TANK_DOCKING_COMPLETE | MECH `TANK_DOCKING` 완료 | ELEC partner 관리자 | `[SN \| O/N: xxx] Tank Docking 완료: 작업명 작업이 완료되었습니다.` | `alert_mech_to_elec_enabled` |
| 4 | ELEC_COMPLETE | ELEC 자주검사 전체 완료 | PI 관리자 | `[SN \| O/N: xxx] ELEC 자주검사 완료: 작업명 작업이 완료되었습니다.` | `alert_elec_to_pi_enabled` |

**흐름**: `complete_work()` → `_trigger_completion_alerts()` → `create_and_broadcast_alert()`
**코드**: `task_service.py` L475-542

**공정 연쇄**:
```
TMS 가압검사 완료 → [TMS_TANK_COMPLETE] → MECH 관리자
MECH 가압검사 완료 → [TMS_TANK_COMPLETE] → QI 관리자
MECH Tank Docking 완료 → [TANK_DOCKING_COMPLETE] → ELEC 관리자
ELEC 자주검사 완료 → [ELEC_COMPLETE] → PI 관리자
PI/QI/SI 시작 시 선행 미완료 → [PROCESS_READY] → MECH/ELEC 관리자
```

---

### B. 공정 선행 검증 알림 (1종)

| # | 알람 타입 | 트리거 | 수신자 | 메시지 |
|---|-----------|--------|--------|--------|
| 5 | PROCESS_READY | PI/QI/SI 작업 시작 시 MECH/ELEC 미완료 | 해당 MECH 또는 ELEC 관리자 | `[SN] PI 공정 대기 중 - MECH 공정 미완료` |

**흐름**: `start_work()` → `validate_process_start()` → `create_alert()`
**코드**: `process_validator.py` L94-125

---

### C. 시간 이상 알림 (2종)

| # | 알람 타입 | 트리거 | 수신자 | 메시지 |
|---|-----------|--------|--------|--------|
| 6 | DURATION_EXCEEDED | task 완료 시 작업시간 > 14시간(840분) | 해당 role 관리자 | `[SN] MECH - 작업명: 작업 시간 850분 (14시간 초과)` |
| 7 | REVERSE_COMPLETION | task 완료 시 `completed_at < started_at` | 해당 role 관리자 | `[SN] MECH - 작업명: 완료 시간이 시작 시간보다 이릅니다.` |

**흐름**: `complete_work()` → `validate_duration()` → `create_alert()`
**코드**: `duration_validator.py` L75-112

---

### D. 스케줄러 자동 알림 — Cron (5종)

| # | 알람 타입 | 스케줄 | 수신자 | 메시지 | 중복방지 |
|---|-----------|--------|--------|--------|---------|
| 8 | TASK_REMINDER | 매시 정각 | 진행 중 task 작업자 본인 | `[SN] 작업명: 작업 시작 후 N시간 경과, 아직 완료 전입니다.` | 없음 (매시간 반복) |
| 9 | SHIFT_END_REMINDER | 17:00, 20:00 KST | 미완료 task 작업자 (1인 1회) | `퇴근 전 미완료 작업이 있습니다. [SN] 작업명.` | 1인당 1회 |
| 10 | UNFINISHED_AT_CLOSING | 18:00 KST | 해당 role 관리자 | `[SN] 작업명: 작업 시작 후 N시간 경과, 미완료 상태` | 관리자당 1회 |
| 11 | TASK_ESCALATION | 09:00 KST (익일) | 작업자 소속 회사 관리자 (없으면 Admin) | `[에스컬레이션] [SN] 작업명: 전일 시작 후 미완료. 작업자: 홍길동 (FNI)` | 없음 |
| 12 | RELAY_ORPHAN | 매시 정각 | 해당 task_category 관리자 | `[릴레이 미완료] SN 작업명 — 작업자 N명 참여 후 4시간 이상 미완료 상태입니다.` | 24시간 task별 |

**조건**:
- TASK_REMINDER: `started_at IS NOT NULL AND completed_at IS NULL`
- TASK_ESCALATION: `started_at < 오늘 00:00 KST AND completed_at IS NULL`
- RELAY_ORPHAN: `마지막 completion_log > 4시간 전 AND task 미완료`
- UNFINISHED_AT_CLOSING: `duration > 14시간 AND completed_at IS NULL`

**코드**: `scheduler_service.py` L185-852

---

### E. 휴게시간 자동 일시정지 (2종)

| # | 알람 타입 | 트리거 | 수신자 | 메시지 | 중복방지 |
|---|-----------|--------|--------|--------|---------|
| 13 | BREAK_TIME_PAUSE | 휴게시간 시작 (오전/점심/오후/저녁) | 진행 중 task 작업자 본인 | `[SN] 작업명: 점심시간이 시작되었습니다. 작업이 자동으로 일시정지됩니다.` | worker당 1회 |
| 14 | BREAK_TIME_END | 휴게시간 종료 | Pause 상태 작업자 | `[SN] 작업명: 점심시간이 종료되었습니다. 작업을 재개해주세요.` | worker당 1회 |

**조건**: `admin_settings.auto_pause_enabled = TRUE` 필수
**휴게 구간**: `break_morning`, `lunch`, `break_afternoon`, `dinner` (admin_settings 기반)
**스케줄**: 매 분 체크 (CronTrigger second=0)
**코드**: `scheduler_service.py` L546-782

---

### F. 가입 승인/거부 (2종)

| # | 알람 타입 | 트리거 | 수신자 | 메시지 |
|---|-----------|--------|--------|--------|
| 15 | WORKER_APPROVED | Admin이 가입 승인 | 해당 작업자 | `가입 신청이 승인되었습니다.` |
| 16 | WORKER_REJECTED | Admin이 가입 거부 | 해당 작업자 | `가입 신청이 거부되었습니다.` |

**코드**: `admin.py` L186-194

---

### G. 체크리스트 알림 (2종) — Sprint 52 추가

| # | 알람 타입 | 트리거 | 수신자 | 메시지 | admin_settings 옵션 |
|---|-----------|--------|--------|--------|---------------------|
| 17 | CHECKLIST_TM_READY | TMS `TANK_MODULE` 완료 (비관리자) | TMS module_outsourcing 관리자 | `[SN \| O/N: xxx] Tank Module 작업 완료 — 체크리스트 검수가 필요합니다` | — |
| 18 | CHECKLIST_ISSUE | TM 체크리스트 완료 시 ISSUE 코멘트 있음 | MECH 관리자 | `[SN] TM 체크리스트 ISSUE: 항목명 - ISSUE 내용` | `tm_checklist_issue_alert` |

**코드**: `task_service.py` L649-665, `checklist_service.py` L557-564

---

### H. 작업자 관리 (1종) — Sprint 40-C 추가

| # | 알람 타입 | 트리거 | 수신자 | 메시지 |
|---|-----------|--------|--------|--------|
| 19 | WORKER_DEACTIVATION_REQUEST | 작업자 비활성화 요청 | Admin | 비활성화 요청 알림 |

**코드**: migration 041

---

### I. 미사용 enum (코드 미참조, DB에만 존재)

| # | 알람 타입 | 비고 |
|---|-----------|------|
| 20 | DUPLICATE_COMPLETION | 004 원본 enum. 코드에서 사용처 없음 |
| — | LOCATION_QR_FAILED | 004 원본 enum. 코드에서 사용처 없음 |

---

## 알람 수신자 결정 방식

| 방식 | 설명 | 사용처 |
|------|------|--------|
| 개인 지정 | `target_worker_id` 직접 설정 | TASK_REMINDER, SHIFT_END, BREAK_TIME, 가입승인 |
| Role 기반 | `role = target_role AND is_manager = TRUE` | PROCESS_READY, DURATION, 완료 연쇄, CHECKLIST_ISSUE |
| Partner 기반 | `company = admin_settings.partner AND is_manager = TRUE` | TMS_TANK_COMPLETE, TANK_DOCKING_COMPLETE |
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

## DB enum 이력 (alert_type_enum)

| Migration | 추가된 값 | Sprint |
|-----------|----------|--------|
| 004 | PROCESS_READY, UNFINISHED_AT_CLOSING, DURATION_EXCEEDED, REVERSE_COMPLETION, DUPLICATE_COMPLETION, LOCATION_QR_FAILED, WORKER_APPROVED, WORKER_REJECTED | 초기 |
| 006 | TMS_TANK_COMPLETE, TANK_DOCKING_COMPLETE, TASK_REMINDER, SHIFT_END_REMINDER, TASK_ESCALATION | Sprint 6 |
| 008 | BREAK_TIME_PAUSE, BREAK_TIME_END | Sprint 9 |
| 041 | WORKER_DEACTIVATION_REQUEST | Sprint 40-C |
| 042 | RELAY_ORPHAN | Sprint 41-B |
| 043 | CHECKLIST_TM_READY, CHECKLIST_ISSUE | Sprint 52 |
| 044 | ELEC_COMPLETE | Sprint 54 |

---

## FE 알람 우선순위

| 우선순위 | 알람 타입 | 아이콘 |
|----------|-----------|--------|
| 3 (높음) | DURATION_EXCEEDED, REVERSE_COMPLETION | timer_off, error_outline |
| 2 (중간) | PROCESS_READY, UNFINISHED_AT_CLOSING, RELAY_ORPHAN | notifications_active, warning |
| 1 (낮음) | TASK_REMINDER, BREAK_TIME_*, WORKER_*, CHECKLIST_* | 기본 |

---

## DB 스키마 (app_alert_logs)

| 컬럼 | 타입 | 설명 |
|-------|------|------|
| id | int (PK) | |
| alert_type | alert_type_enum | 20종 알람 타입 |
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

## 관련 소스 파일

| 파일 | 역할 | 알람 타입 |
|------|------|----------|
| `backend/app/services/scheduler_service.py` | Cron 스케줄러 | TASK_REMINDER, SHIFT_END, ESCALATION, BREAK_TIME, RELAY_ORPHAN, UNFINISHED |
| `backend/app/services/duration_validator.py` | 시간 검증 | DURATION_EXCEEDED, REVERSE_COMPLETION, UNFINISHED_AT_CLOSING |
| `backend/app/services/process_validator.py` | 공정 선행 검증 | PROCESS_READY |
| `backend/app/services/task_service.py` | 완료 연쇄 알림 | TMS_TANK_COMPLETE, TANK_DOCKING_COMPLETE, ELEC_COMPLETE, CHECKLIST_TM_READY |
| `backend/app/services/checklist_service.py` | 체크리스트 알림 | CHECKLIST_ISSUE |
| `backend/app/models/alert_log.py` | Alert 모델 + create_alert | 전체 |
| `backend/app/routes/alert.py` | Alert API 엔드포인트 | 전체 |
| `backend/app/routes/admin.py` | 가입 승인/거부 | WORKER_APPROVED, WORKER_REJECTED |

---

## 테스트 커버리지

| 알람 타입 | 테스트 파일 | 커버리지 |
|-----------|------------|---------|
| TMS_TANK_COMPLETE | `test_sprint54_alert_triggers.py` TC-54-11~15 | 완료 (API 통합) |
| TANK_DOCKING_COMPLETE | `test_sprint54_alert_triggers.py` TC-54-16~18 | 완료 (API 통합) |
| ELEC_COMPLETE | `test_sprint54_alert_triggers.py` TC-54-19~20 | 완료 (API 통합) |
| CHECKLIST_TM_READY | `test_sprint54_alert_triggers.py` TC-54-21~23 | 완료 (API 통합) |
| DURATION_EXCEEDED | `test_duration_validator.py` | 완료 (DB 검증) |
| REVERSE_COMPLETION | `test_duration_validator.py` | 완료 (DB 검증) |
| PROCESS_READY | `test_process_validator.py` + `test_alert_all20_verify.py` TC-AL20-02 | 완료 (간접 → 명시적 보강) |
| BREAK_TIME_PAUSE | `test_break_time_scheduler.py` | 완료 (DB 검증) |
| BREAK_TIME_END | `test_break_time_scheduler.py` | 완료 (DB 검증) |
| TASK_REMINDER | `test_scheduler.py` + `test_scheduler_integration.py` | 완료 (DB 검증) |
| SHIFT_END_REMINDER | `test_scheduler.py` + `test_scheduler_integration.py` | 완료 (DB 검증) |
| TASK_ESCALATION | `test_scheduler.py` + `test_scheduler_integration.py` | 완료 (DB 검증) |
| UNFINISHED_AT_CLOSING | `test_alert_all20_verify.py` TC-AL20-09 | 완료 (서비스 직접 호출) |
| RELAY_ORPHAN | `test_alert_all20_verify.py` TC-AL20-07~08 | 완료 (서비스 직접 호출 + 중복방지) |
| WORKER_APPROVED | `test_alert_all20_verify.py` TC-AL20-03 | 완료 (API 통합) |
| WORKER_REJECTED | `test_alert_all20_verify.py` TC-AL20-04 | 완료 (API 통합) |
| WORKER_DEACTIVATION_REQUEST | `test_alert_all20_verify.py` TC-AL20-05 | 조건부 (endpoint 존재 시) |
| CHECKLIST_ISSUE | `test_alert_all20_verify.py` TC-AL20-06 | 완료 (서비스 직접 호출) |
| DUPLICATE_COMPLETION | `test_alert_all20_verify.py` TC-AL20-32 | 미사용 enum 하위호환 |
| LOCATION_QR_FAILED | `test_alert_all20_verify.py` TC-AL20-33 | 미사용 enum 하위호환 |

**전체 enum 검증**: `test_alert_all20_verify.py` TC-AL20-01 (DB enum 20종 존재 확인)
**API readback**: `test_alert_all20_verify.py` TC-AL20-10~31 (20종 INSERT → GET/읽음 정상 동작)

---

## 추가 검토 필요 알람

| 제안 | 트리거 | 수신자 | 상태 |
|------|--------|--------|------|
| QI 완료 → 출하 준비 가능 | QI 품질검사 통과 | SI 관리자 | 미구현 |
| 전체 공정 완료 → 출하 가능 | 모든 공정 완료 | Admin/GST 관리자 | 미구현 |
| 작업 시작 알림 | 작업자가 task 시작 | 해당 팀 관리자 | 미구현 |
