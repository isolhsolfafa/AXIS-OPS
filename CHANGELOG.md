# Changelog

All notable changes to AXIS-OPS are documented here.

Format: [Semantic Versioning](https://semver.org/) — MAJOR.MINOR.PATCH

---

## [2.10.1] - 2026-04-23

> Sprint 62-BE 보정 PATCH — VIEW 측 입장 재검토 후 요청 반영. v2.2 에서 "숫자 변동 없음(31대 유지)" 근거로 `ship_plan_date` 유지 결정했으나, 주간 생산량의 **의미** (생산 완료 기준) 측면에서 `finishing_plan_end` 가 라벨 [Planned Finish] 과 일치. 실측 기반 수치 변동 투명 공개.

### Fixed

- **`weekly-kpi` WHERE 절 교정** (`backend/app/routes/factory.py` L322) — `ship_plan_date` → `finishing_plan_end` 1줄 수정. v2.2 에서는 "31대 유지 우선"으로 보류했으나 VIEW v1.34.4/Sprint 36 논의 결과 "주간 생산량 = 완료 기준" 의미 일치 우선 결정. 응답 `production_count` 숫자 변경 유의 (하위 3필드 `shipped_plan/actual/ops` 는 영향 없음)
- **TC-FK-02 업데이트** — "ship_plan_date 유지 회귀" → "finishing_plan_end 교정 검증" 으로 의미 반전. DB 직접 COUNT 와 응답 `production_count` 일치 assertion

### 실측 수치 변동 (2026-04-23 Railway)

| 기간 | ship_plan_date 기준 (기존) | finishing_plan_end 기준 (신규) | 차이 |
|---|---|---|---|
| 이번 주 (2026-04-20~26) | 31 | 48 | +17 (+55%) |
| 지난 주 (2026-04-13~19) | 30 | 51 | +21 (+70%) |

### Claude 원안 약점 기록 (CLAUDE.md ④ 맹목 동조 방지)

- v2.2 확정 당시 "주간 숫자 불변"을 설계 가치로 높게 평가 → 실제 중요한 건 **의미 일치**였음. "숫자 변경 리스크"를 과대 평가하여 의미 정확성 교정을 1 cycle 지연시킴
- 이번 PATCH 를 v2.10.0 배포 직후 즉시 적용 → 사용자 혼란 최소화

### Tests

- TC-FK-02 업데이트 후 17/17 GREEN
- 기존 TestWeeklyKpi 5/5 GREEN (스키마 의존만이라 WHERE 변경 무관)

---

## [2.10.0] - 2026-04-23

> Sprint 62-BE v2.2 — 공장 대시보드 Factory KPI 확장 (데이터 공급 인프라). VIEW Sprint 35 (v1.34.4 `mech_start` 영구 유지) + Sprint 36 (옵션 토글) 연계 배포. 경영 KPI 계산 로직 (이행률·정합성)은 `BACKLOG-BIZ-KPI-SHIPPING-01` 이관 (App 베타 100% 전환 후 확정).

### Added

- **`GET /api/admin/factory/monthly-kpi`** (신규 엔드포인트) — 월간 공장 KPI. `date_field` 쿼리 파라미터 4옵션 (`mech_start` / `finishing_plan_end` / `ship_plan_date` / `actual_ship_date`, 기본 `mech_start`). `completion_rate`/`by_stage`/`pipeline`/`by_model` 제외 (monthly-detail 엔드포인트가 담당)
- **`weekly-kpi` 응답 확장** — `shipped_plan` / `shipped_actual` / `shipped_ops` 3필드 + `defect_count=null` placeholder 추가. 기존 `pipeline.shipped` 는 backward compat 유지 (`today` 제한 기존 의미 보존)
- **`_count_shipped(conn, start, end, basis)` 헬퍼** — 출하 카운트 3분기 (plan/actual/ops). 자동 합산(UNION) 없이 3개 소스 독립 반환. 경영 KPI 레이어에서 비교 분석 가능. `force_closed = false` 클린 코어 원칙 적용
- **`monthly-detail` 화이트리스트 확장** — `_ALLOWED_DATE_FIELDS` 3값 → 5값 (`finishing_plan_end`/`ship_plan_date`/`actual_ship_date` 추가). `ProductionPlanPage` 기존 `pi_start`/`mech_start` 토글 유지
- **`_ALLOWED_DATE_FIELDS_MONTHLY_KPI`** (신규 상수) — monthly-kpi 전용 4값 (pi_start 제외). Codex 2차 Q4 M 반영 (화이트리스트 분리)
- **pytest 11 TC** (`tests/backend/test_factory_kpi.py`) — 17 assertions (parametrize 확장). 반개구간 `[start, end)` 경계 TC 포함 (Codex 3차 Q6 A)

### Infrastructure

- **Migration 050** (`050_factory_kpi_indexes.sql`) — `plan.product_info` 에 `actual_ship_date` / `finishing_plan_end` 컬럼 `ALTER TABLE ADD COLUMN IF NOT EXISTS` (Prod 기존 존재 → no-op, Test DB → 신규 생성). Partial index 3개 `CREATE INDEX CONCURRENTLY IF NOT EXISTS` (`actual_ship_date` / `ship_plan_date` / `finishing_plan_end`, `WHERE IS NOT NULL` 조건)
- Test DB 스키마 drift 발견 및 해결 — Prod엔 `actual_ship_date` 등이 ETL 시스템에 의해 추가돼 있으나 migration SQL 부재 → migration 050 에 DDL 명시로 양쪽 정합 확보

### AI 교차 검증

- **Codex 1차** (v1): M1(UNION 경계 중복), M2(반개구간), M3(`_FIELD_LABELS` `finishing_plan_end` 누락) 지적
- **Codex 2차** (v2 VIEW 역제안): M 2건 (Q4 화이트리스트 불일치 / Q5 `shipped_plan` 의미 모호) + A 4건
- **Codex 3차** (v2.2 축소): **M=0 / A=4 CONDITIONAL APPROVED**. A 4건 전부 합의 기반 반영 (INNER JOIN / EXPLAIN 배포 후 검증 / 네이밍 부채 debt / 반개구간 경계 TC)
- Claude 원안 약점 4건 trail 기록 (CLAUDE.md ④ 맹목 동조 방지 규칙 준수)

### Tests

- 신규 TC 17/17 GREEN (test_factory_kpi.py)
- 회귀 TC 36/36 GREEN (test_factory.py + test_admin_api.py)
- 총 53 PASSED / 0 regression

### Deferred (BACKLOG)

- `BACKLOG-BIZ-KPI-SHIPPING-01` (🟢 DRAFT) — 경영 대시보드 이행률(`fulfillment_rate = actual/plan`) / 정합성(`app_coverage_rate = ops/actual`) 지표. App 베타 100% 전환 후 착수 검토
- `POST-REVIEW-SPRINT-62-BE-V2.2-20260423` (🟡 OPEN, 7일 내) — Railway EXPLAIN ANALYZE 검증 + 네이밍 부채 FE 혼동 사례 모니터링

### BE 합의 (VIEW Sprint 35/36 연계)

| 항목 | v2.2 최종 |
|---|---|
| weekly-kpi WHERE | `ship_plan_date` 유지 (현 31대 유지) |
| monthly-kpi `date_field` | 4옵션, 기본 `mech_start` (pi_start 제외) |
| `_ALLOWED_DATE_FIELDS` (monthly-detail) | 5값 (pi_start 포함 유지) |
| 출하 응답 | **3필드** (`shipped_plan/actual/ops`, `shipped_count`/`union` 폐기) |
| `shipped_ops` 네이밍 | 기존 `shipped_realtime` 리네임 (AXIS-OPS 정체성) |

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
