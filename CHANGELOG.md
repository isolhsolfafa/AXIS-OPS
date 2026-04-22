# Changelog

All notable changes to AXIS-OPS are documented here.

Format: [Semantic Versioning](https://semver.org/) — MAJOR.MINOR.PATCH

---

## [2.9.11] - 2026-04-22

> 2026-04-22 하루 동안 발생한 5일 알람 장애 (4-17~22 `app_alert_logs` INSERT 0건) 근본 원인 확정 및 복구. 4 HOTFIX 통합 PATCH release.

### Fixed

- **Alert delivery 복구** (HOTFIX-ALERT-SCHEDULER-DELIVERY-20260422) — `scheduler_service.py` 3곳 (RELAY_ORPHAN / TASK_NOT_STARTED / CHECKLIST_DONE_TASK_OPEN) 이 `target_worker_id` 미지정 + `target_role` 만으로 broadcast 하여 `role_TMS` / `role_elec_partner` 등 `role_enum` 외 값 room 으로 알람 발송 → 구독자 0 → 52+17 = 69건 완전 undelivered. `task_service.py` L571 표준 패턴 (`get_managers_by_partner` / `get_managers_for_role` → 관리자별 개별 INSERT) 로 통일
- **Alert 중복 발송 제거** (HOTFIX-SCHEDULER-DUP-20260422, commit `f1af8a4`) — Gunicorn multi-worker 환경에서 `_SCHEDULER_STARTED` env 가드가 fork 이후 COW semantics 로 worker 간 전파되지 않음 → 2~3개 scheduler 동시 실행 (R1 실측 37.5% 중복, GPWS-0773 3중복). `fcntl.flock(LOCK_EX | LOCK_NB)` + `/tmp/axis_ops_scheduler.lock` OS 레벨 lock 으로 단일 실행 보장
- **DB schema 복구** (HOTFIX-ALERT-SCHEMA-RESTORE-20260422) — Railway 운영 DB 에 migration 049 미적용 상태 → `app_alert_logs.task_detail_id` 컬럼 부재 + `alert_type_enum` 신규 3종 (`TASK_NOT_STARTED` / `CHECKLIST_DONE_TASK_OPEN` / `ORPHAN_ON_FINAL`) 미등록 → 모든 INSERT `PsycopgError`. pgAdmin 수동 SQL 5 블록 실행으로 복구
- **Dedupe legacy 간섭 차단** (Codex M2 수용) — 3곳 dedupe 쿼리에 `target_worker_id IS NOT NULL` 필터 추가 → legacy 69건 (`target_worker_id=NULL`) 이 window 내에서도 신규 INSERT 차단하지 않도록

### Added

- **Alert silent fail ERROR 로깅** (HOTFIX-SCHEDULER-PHASE1.5, commit `4a6caf8`) — `create_and_broadcast_alert()` / `create_alert()` 에 `[alert_silent_fail]` / `[alert_create_none]` / `[alert_insert_fail]` prefix 추가. Sentry SDK 선택적 import 가드. 본 장애 근본 원인 포착의 결정적 도구
- **`_resolve_managers_for_category` 헬퍼** (scheduler_service.py) — task_category → 관리자 worker_id 리스트 변환. Partner 기반 (TMS/MECH/ELEC) 또는 Role 기반 (PI/QI/SI) 자동 분기
- **AI 검증 워크플로우 ⑦ 단계 강제 절차** (CLAUDE.md) — pytest 실패 발견 시 Claude 단독 "범위 외 판단" 금지, Codex 합의 후 조치 강제. HOTFIX-ALERT-SCHEDULER-DELIVERY 세션 위반 사례 반영

### Infrastructure

- Phase 1.5 로깅 → 본 장애 근본 원인 5분 내 포착 (추론 5일 vs 실로그 5분 — "관찰성 우선" 원칙 재확인)
- 4 HOTFIX 통합 PATCH v2.9.11 로 버전 정리 (이전 누락된 bump 소급 반영)
- FE version skew 명시: 저장소 v2.9.11 vs Netlify 배포 v2.9.10 (FE 코드 변경 0, 다음 FE 배포 시 자동 반영)

### BACKLOG 이관 (후속 Sprint)

- `OBSERV-RAILWAY-LOG-LEVEL-MAPPING` (P1, Sentry 연동 blocker)
- `FIX-LEGACY-ALERT-TMS-DELIVERY` (P3, 69건 복구 옵션)
- `REFACTOR-SCHEDULER-SPLIT` (P2, ~1090 LOC 분할)
- `TEST-ALERT-DELIVERY-E2E` (P2, WebSocket 통합 테스트)
- `TEST-SCHEDULER-EMPTY-MANAGERS` (P3, PI/QI/SI 엣지)
- `BUG-DURATION-VALIDATOR-API-FIELD` (P2, Codex 합의 미실행 — 착수 전 합의 필수)
- `POST-REVIEW-HOTFIX-ALERT-SCHEDULER-DELIVERY-20260422` (S2, 7일 이내 Codex 사후 검토 필수)

---

> 이 이전 변경사항은 `handoff.md` 및 git tag 이력 참조.
