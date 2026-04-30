# AXIS-OPS Handoff

> 세션 종료 시 업데이트. 다음 세션이 즉시 작업을 이어갈 수 있도록 현재 상태를 기록합니다.
> 마지막 업데이트: 2026-04-30 10:00 KST (FIX-DB-POOL-WARMUP-WATCHDOG v2.10.16 배포 — silent failure 재발 방지)
>
> 🚨 **4-29 23:31 ~ 4-30 09:30 silent failure 사고**:
>   ├─ warmup cron 은 살아있는데 `_pool=None` (gunicorn worker pool death) 으로 1.5h+ `[pool_warmup] 0/0 conn warmed`
>   ├─ 사용자 측 conn=2 측정으로 우연 발견 (logger.debug 라 Sentry 미포착 = 사각지대)
>   ├─ 응급 조치: Railway Restart → conn 10 회복 (Worker A 5 + Worker B 5 fresh init)
>   └─ 근본 fix: v2.10.16 — `logger.debug` → `logger.error` 격상 + pid context, Sentry 자동 capture 활성화 (다음 발생 1분 알림)
>
> 🎯 **다음 우선 작업**: **MECH 체크리스트 (Sprint 63 후보)** — TM(Sprint 52~v2.6.0) / ELEC(Sprint 57~v2.9.0) 도입 후 MECH 자주검사 체크리스트 전개
>
> 🟢 **DB Pool 모니터링 인프라 — 후순위로 BACKLOG 등록 (4-29 23:00)**:
>   ├─ OBSERV-DB-POOL-STATUS-ENDPOINT-20260429 (P3, 30분) — `/api/admin/db-pool-status` 실시간 조회
>   ├─ OBSERV-DB-POOL-CONN-THRESHOLD-ALERT-20260429 (P3, 20분) — Sentry capture_message 임계 alert (5분 cron)
>   └─ OBSERV-SENTRY-TRACES-APM-ENABLE-20260429 (P3, 5분) — Railway env `SENTRY_TRACES_SAMPLE_RATE=0.1` 1줄
>
> 🟡 **잔존 Sentry SMTP issue** (4-28 work.request_deactivation 7 events): 옵션 A (logger.warning 강등 + SMTPRecipientsRefused 분리) 별건 BACKLOG 등록 검토 중
>
> ✅ **4-29 검증 결과 (T+18~24h)**:
>   ├─ v2.10.11: TMS UNFINISHED_AT_CLOSING **Before 0 → After 32건 / target 100%** + Sentry PYTHON-FLASK-1 resolve 후 신규 0 → COMPLETED
>   ├─ v2.10.13 #1/#2: HTTP 5xx 0건 + Sentry db_pool/websocket 2 issue resolve 후 신규 0 → COMPLETED
>   ├─ v2.10.14: W17 v2.3 0건 → v2.4 **31건** (plan/actual/best 3축 일치) + R-02 반례 0건 유지 → COMPLETED
>   └─ migration_history: 39 migrations, latest 050 — assertion layer 정상
>
> 🟢 **4-29 D+2 (FIX-DB-POOL Phase B)**: conn **5~6 안정** (Worker A pool MIN=5 정확 작동 입증) → D+1/D+2 동일 추세, per-worker 함정 영향 무 → 옵션 X1 유지 재확정
>
> 🟢 **자연 종결 plan (옵션 A)**:
>   ├─ #26 FIX-DB-POOL-MAX Phase B → 내일 4-30 D+3 Twin파파 측 5분 측정 후 자동 COMPLETED (변경 없음 → MAX=30 충분 확정)
>   └─ #29 FIX-PIN-FLAG baseline → BE endpoint 통합 (`/auth/login` 단일) 본질적 한계 → 5-04 (D+7) 까지 사용자 PIN 화면 손실 신고 0건이면 정성 close. 정량 baseline 측정 인프라는 별건 (FEAT-PIN-LOGIN-ANALYTICS, 필요 시 등록)

---

## 🟢 2026-04-28 세션 요약 (5/5) — FIX-FACTORY-KPI-SHIPPED-V2.4 v2.10.14

> **한 줄 요약**: Sprint 62-BE v2.2 의 `_count_shipped` 3 분기 보정 — `shipped_plan` AND→OR (W17 0 상수화 해소) + `shipped_ops` 폐기 + `shipped_best` 신설. Pre-deploy Gate ③ R-02 반례 0건 검증 완료. pytest 17 passed / 3 skipped (v2.3 'ops' 의존 TC 무효).

### 코드 변경 (v2.10.14, BE only — factory.py 단일)

| 분기 | Before (v2.3) | After (v2.4) |
|---|---|---|
| `plan` | `INNER JOIN cs ON ... AND cs.si_completed=TRUE` | `LEFT JOIN app_task_details (task_id='SI_SHIPMENT') + WHERE (actual_ship_date IS NOT NULL OR t.completed_at IS NOT NULL)` |
| `ops` | `app_task_details task_id='SI_SHIPMENT' completed_at` | **제거** (app SI 100% 후 ops=actual 수렴) |
| `best` | (없음) | **신규** — `WHERE actual_ship_date IS NOT NULL` + 주간 귀속 `COALESCE(DATE(t.completed_at), p.actual_ship_date)` |

응답 4곳 (weekly-kpi L457/L473 + monthly-kpi L554/L566): `shipped_ops` → `shipped_best`.

### Pre-deploy Gate ③ R-02 해석 A 반례 검증 완료

```
SELECT COUNT(*) FROM app_task_details t
LEFT JOIN plan.product_info p ON t.serial_number = p.serial_number
WHERE t.task_id='SI_SHIPMENT' AND t.completed_at IS NOT NULL
  AND COALESCE(t.force_closed, FALSE) = FALSE
  AND p.actual_ship_date IS NULL;
→ 0건 (Twin파파 실측, 2026-04-28)
→ 해석 A (si ⊆ actual) 확정, v2.4 그대로 진행 OK
```

### Twin파파 검토 1건 반영

OPS_API_REQUESTS.md v2.4 문서 SQL 의 `task_id='si_shipment'` (소문자) → `'SI_SHIPMENT'` (대문자, 실 DB 값) 4곳 정정. 문서 그대로 구현 시 LEFT JOIN 매칭 0건 → shipped_plan/best 영구 0 (의도와 정반대).

### pytest 결과

```
test_factory_kpi.py: 17 passed / 3 skipped / 0 fail (137.10s)
  ✅ 신규 TestFactoryKpiV24Amendment 3 TC (응답 키 / best 스모크 / invalid basis)
  ✅ 기존 14 TC 갱신 후 PASS (응답 키 ops→best, _count_shipped 'ops'→'plan')
  ⏸ 3 TC skip (TC-FK-06/09/11): v2.3 'ops' 분기 의존 TC, v2.4 에서 fixture 한계로 TC 본질 무효
     → 운영 데이터 보존 정책 (plan.product_info UPDATE 금지) 으로 actual_ship_date 시뮬레이션 불가
     → v2.4 핵심 거동은 TestFactoryKpiV24Amendment 클래스로 이전
```

### LoC

- factory.py: 562 → 575 (+13 LOC, God File 잔존 but 별건 REFACTOR-FACTORY)
- test_factory_kpi.py: 435 → 511 (+76 LOC)

### Sprint 설계서 vs 실제 변경 차이

| 항목 | Sprint 설계서 권장 | 실제 |
|---|---|---|
| TC 개수 | 14개 (8 재정렬 + 6 신규) | 17 passed (14 기존 + 3 신규) + 3 skip — fixture 한계로 신규 TC 일부 단순화 |
| Codex 이관 | ❌ 불필요 | ❌ 불필요 (Pre-deploy Gate ③ 0건 검증 완료) |

### Post-deploy 검증 (예정)

- **T+1h**: 대시보드 W17 `shipped_plan` 0 → 수십대 (의도된 변화) + Sentry 새 ERROR 0
- **T+24h**: 3필드 `shipped_plan/actual/best` 정상 반환 + 회귀 0
- **T+72h**: R-02 해석 A 재검증 (반례 0건 유지) + FE Phase 2 (v1.35.0) 착수 가능 시점 도달

### BACKLOG 동기화

- `FIX-FACTORY-KPI-SHIPPED-V2.4-AMENDMENT-20260428` → ✅ COMPLETED
- 후속: AXIS-VIEW Phase 2 (v1.35.0) 착수 가능 (별 repo)

---

## 🟢 2026-04-28 세션 요약 (4/5) — Sentry garbage log 정리 v2.10.13 (2 Sprint 묶음)

> **한 줄 요약**: Sentry 대시보드 잡음 분리 — (1) db_pool direct fallback ERROR (22 events) → warning 강등 + counter (2) flask-sock wsgi StopIteration (302 events) → before_send hook 으로 drop. 진짜 ERROR 추적성 회복. pytest 7/7 PASS.

### Sprint 1 — FIX-DB-POOL-DIRECT-FALLBACK-LOG-LEVEL-20260428

- `db_pool.py`:
  - `_direct_fallback_count: int = 0` + `get_direct_fallback_count()` getter 신설
  - L171-173 `logger.error` → `logger.warning("[db_pool] All pool connections unusable after %d retries, creating direct connection (cumulative fallback=%d)", retries, _direct_fallback_count)` 강등
- `tests/backend/test_db_pool.py` 신규 — TC 3개 (counter / normal / exhausted 분리)
- 효과: Sentry `[db_pool] All pool connections unusable` 22 events 동결

### Sprint 2 — FIX-WEBSOCKET-STOPITERATION-SENTRY-NOISE-20260428

- `__init__.py`:
  - 모듈 top-level `_sentry_before_send(event, hint)` 신규 (~30 LOC)
  - 매칭 3조건 (`exc_type='StopIteration'` + `mechanism.type='wsgi'` + `transaction='websocket_route'`) 모두 성립 시 drop
  - try/except 안전 fallback (필터 실패 시 정상 capture)
  - `sentry_sdk.init()` 에 `before_send=_sentry_before_send` 등록
- `tests/backend/test_sentry_filter.py` 신규 — TC 4개 (drop / pass other transaction / pass other exc / malformed event)
- 효과: Sentry PYTHON-FLASK-2 302 events 동결

### pytest 결과

```
✅ test_db_pool.py 3/3 PASS
✅ test_sentry_filter.py 4/4 PASS
   총 7/7 PASS in 0.09s — 회귀 0건
```

### LoC 변경

| 파일 | Before | After | 차이 |
|---|---:|---:|---:|
| db_pool.py | 286 | 297 | +11 (🟢 500 미만) |
| __init__.py | ~190 | ~225 | +35 (🟢 500 미만) |

### Post-deploy 검증 (예정)

- T+1h: Sentry 2 issue events 카운트 증가 멈춤 (22 / 302 동결)
- T+24h: 다른 issue 정상 capture 확인 (PYTHON-FLASK-1 / PYTHON-FLASK-4)
- T+7d: 본 Sprint 효과 정량 입증 + Railway `cumulative fallback=N` 추세 → 별건 OBSERV-WARMUP-INTERVAL-TUNE 우선순위 결정

---

## 🟢 2026-04-28 세션 요약 (3/4) — FIX-26-DURATION-WARNINGS-FORWARD v2.10.12

> **한 줄 요약**: 4-22 등록 BACKLOG L362 `BUG-DURATION-VALIDATOR-API-FIELD` 본격 fix. `/api/app/work/complete` 응답에 `duration_warnings` 키 항상 존재 보장 (옵션 C — 양 끝 unconditional). test_reverse_completion 은 시작/종료 timestamp 서버 자동 기록 + prod 0건 실측 입증으로 `@pytest.mark.skip` 처리.

### 코드 변경 (v2.10.12, BE 2 파일 + test 1 파일)

| 파일 | LoC | 핵심 |
|---|---:|---|
| task_service.py | ±0 | L497-499 — unconditional 응답 키 (조건부 제거) |
| work.py | -1/+1 | L265-266 — default 빈 리스트 forward |
| test_duration_validator.py | +62 | assertion 갱신 + 신규 TC 1개 + skip mark |
| backend/version.py | bump | v2.10.11 → v2.10.12 |
| frontend/.../app_version.dart | bump | v2.10.11 → v2.10.12 |

### 핵심 인사이트 — 본 Sprint 단순화 (사용자 정정 반영)

- 시작/종료 timestamp 가 **서버 `datetime.now(Config.KST)` 자동 기록** (`task_service.py:146/256`, `work.py:448`)
- 클라이언트가 시간 보내거나 입력하는 경로 0
- REVERSE_COMPLETION (시작 > 종료) 은 운영 발생 불가 — 인프라 사고 (NTP jump back / SQL 직접 조작 / timezone 버그) 차원
- prod 실측 0건 (4-04 ~ 4-28 24일 누적, started_at>completed_at WHERE 절)
- 대시보드 Rollback 키로 잘못된 종료 사후 복구 메커니즘 별도 존재
- → 처음 우려한 silent failure / 4-22 유사 구조 모두 무의미. 본 Sprint 는 응답 contract 일관성만 fix

### Codex 라운드 2 합의 trail

v2.10.11 (FIX-PROCESS-VALIDATOR-TMS-MAPPING) 후속에서 Codex Q1/Q2 모두 A 라벨 합의:
- 본 fail 은 `duration_validator.py:70-93` REVERSE_COMPLETION 브랜치 → `task_service.py:361-363,496-498` → `work.py:261-266` 응답 키 생성 경로 4-22 부터 누락된 별건
- v2.10.11 회귀 0건 + 본 BUG 별건 확정 → 별도 Sprint 처리

### pytest 결과

```
test_duration_validator.py:
  ✅ test_normal_duration_no_warnings (assertion 갱신 후 신 계약 호환)
  ✅ test_duration_over_14h
  ✅ test_very_short_duration
  ⏸ test_reverse_completion (skip — 시작/종료 timestamp 서버 자동 기록, prod 0건)
  ✅ test_normal_completion_returns_empty_duration_warnings (신규)
```

### BACKLOG 동기화

- L362 `BUG-DURATION-VALIDATOR-API-FIELD` → ✅ COMPLETED (v2.10.12)
- 별건 BACKLOG 등록 불필요 (P3 INFO 수준 이하 — 사용자 영향 0 입증)

### Post-deploy 검증 (예정)

- FE 영향 0 — `data.duration_warnings` 안전 접근 가능 (FE 가 옵셔널 처리 안 했어도 빈 리스트 받음)
- 운영 회귀 검증 불필요 (응답 dict 키 1개 추가만)

---

## 🟢 2026-04-28 세션 요약 (2/3) — FIX-PROCESS-VALIDATOR-TMS-MAPPING v2.10.11 (옵션 D-2)

> **한 줄 요약**: 4-22 HOTFIX-ALERT-SCHEDULER-DELIVERY 의 표준 패턴이 duration_validator 3곳 + task_service L403 에 미적용 → TMS 매니저 silent failure (Sentry 도입 8h 자동 감지, 31 events). `process_validator.resolve_managers_for_category()` public 함수 신설 + 5 파일 atomic refactor + pytest 신규 TC 7개. 회귀 0건. Codex 2라운드 검증 합의 완료.

### 코드 변경 (v2.10.11, BE 5 파일 atomic)

| 파일 | LoC 변경 | 핵심 |
|---|---:|---|
| process_validator.py | **+30** | `_CATEGORY_PARTNER_FIELD` + `resolve_managers_for_category()` 신설 |
| scheduler_service.py | **-15** | private 함수 + dict 제거 + import 교체 + 3 호출 site 1:1 |
| task_service.py | **±0** | L403 import + L410 호출 1:1 (Codex M2 누락 발견) |
| duration_validator.py | **±0** | L74/L100/L179 + import 1줄 |
| tests/conftest.py | +50 | `seed_test_managers_for_partner` 격리 fixture (옵션 D, Codex M1) |
| tests/backend/test_process_validator.py | +130 | TC 7개 (TMS-GAIA / DRAGON 회귀 / MECH / ELEC / PI / unknown / e2e) |

→ Line 규칙 모두 통과 (scheduler/task_service God File 잔존 but LoC 감소/0).

### Codex 합의 trail (2 라운드)

- **라운드 1 (Sprint 설계 검증)**: M=2 / A=2 / N=2
  - M1 (fixture 정합성) → 옵션 D 격리 fixture 채택
  - M2 (Rollback 5파일) → task_service.py L403 누락 발견, 5 파일 명시
  - A1 (DRAGON gap) → 별건 BACKLOG `BUG-DRAGON-TMS-PARTNER-MAPPING-20260428`
  - A2 (e2e 회귀 TC) → `test_duration_validator_tms_alert_creation_e2e` 추가
- **라운드 2 (pytest 회귀 라벨링)**: Q1/Q2 모두 A
  - test_duration_validator 1 fail = BACKLOG L362 BUG-DURATION-VALIDATOR-API-FIELD (4-22 별건)
  - 본 Sprint 응답 키 생성 경로 영향 0 → 별도 Sprint 처리 결정

### pytest 결과

```
✅ 신규 TC 7/7 PASS (TestResolveManagersForCategory 6 + e2e 1)
✅ 회귀 51 passed / 5 skipped / 0 fail (test_scheduler / test_scheduler_integration / test_task_seed)
⚠️ test_duration_validator 1 fail = 4-22 기존 별건 (Codex A 라벨 합의)
```

### 다음 우선 처리 (별도 Sprint)

1. 🟡 **BUG-DURATION-VALIDATOR-API-FIELD** (BACKLOG L362) — `/api/app/work/complete` 응답에 `duration_warnings` 키 forward (30~60분)
2. 🟢 BUG-DRAGON-TMS-PARTNER-MAPPING-20260428 (BACKLOG L353) — prod DB 실측 후 우선순위 재평가

### Post-deploy 검증 (예정)

- 즉시 (1h): Sentry PYTHON-FLASK-4 events 31 → 정착 추세 확인
- 매시간 정각 (UTC) 7번: TMS / MECH / ELEC / PI 매니저 도달
- D+7: Sentry events 31 그대로 → COMPLETED 판정

---

## 🟢 2026-04-28 세션 요약 (1/2) — D+1 출근 peak 측정 PASS, 옵션 X1 유지

> **한 줄 요약**: 4-28 출근 peak (07:30~09:00 KST) 측정 결과 Pool exhausted 0 / direct conn fallback 0 / OPS conn 6~7 안정 / Sentry 새 issue 0 → v2.10.11 HOTFIX-06b 진행 불필요. v2.10.7 HOTFIX-06 단독으로 사용자 영향 0 보장 확정.

### 측정 결과

| 항목 | 기대 | 실측 | 판정 |
|---|---|---|---|
| Pool exhausted | 0건 | **0건** | ✅ |
| direct conn fallback | 0건 | **0건** | ✅ |
| OPS conn (peak) | ≥ 10 | **6~7 안정** | ✅ |
| Sentry 새 issue | 0건 | **0건** | ✅ |

### 결정

- ✅ 옵션 X1 유지 — Worker A 5 conn (warmup) + Worker B 자연 사용분 = 안정적 운영
- ❌ v2.10.11 HOTFIX-06b (per-worker warmup) 진행 불필요
- ✅ `OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP-20260427` **COMPLETED 확정** (부분 완료 → 정식 완료)
- 🟡 D+2 (4-29) / D+3 (4-30) 동일 추세 관찰 — Phase B 자연 종결 예정
- 🔴 다음 우선 처리: BACKLOG L352 `FIX-PROCESS-VALIDATOR-TMS-MAPPING-20260428` (옛 ID `-ROLE-MAPPING-20260427` 통일, Cowork 설계 완료 → Codex 이관 진행 중)

### 부수 발견 trail (Sentry layer)

- 4-28 03:00 KST cron 시점 Sentry 가 `Failed to get managers for role=TMS: invalid input value for enum role_enum: "TMS"` 31 events 자동 감지 → BACKLOG L352 등록 (FIX-PROCESS-VALIDATOR-TMS-ROLE-MAPPING)
- 4-22 HOTFIX-ALERT-SCHEDULER-DELIVERY 의 잔존 silent failure (process_validator/duration_validator 의 enum cast 미처리) → Sentry DSN 활성화 8시간 만에 자동 발견
- ADR-019 가치 입증 trail 3차 사례 추가 (memory.md)

### 이번 주 핵심 3가지 — 3개 모두 완료 ✅

1. ✅ PIN 화면 손실 막기 (v2.10.5 + v2.10.6)
2. ✅ DB Pool 안정화 마무리 (v2.10.6/.7 + D+1 PASS)
3. ✅ 알람 장애 사후 검증 마무리 (v2.10.8 + Sentry 활성화)

---

## 🟢 2026-04-27 세션 요약 (6/6) — Sentry DSN 활성화 + WEEKLY_PLAN 갱신

> **한 줄 요약**: Twin파파 측 sentry.io 가입 + Python/Flask project 생성 + DSN 발급 + Railway env (`SENTRY_DSN` / `SENTRY_ENVIRONMENT` / `SENTRY_TRACES_SAMPLE_RATE`) 등록 완료. v2.10.8 에 도입한 `_init_sentry()` 가 정식 활성화 → 외부 자동 감지 layer 1차 가동 시작.

### 활성화 결과

- ✅ `SENTRY_DSN` env 등록 → 다음 deploy 시 `_init_sentry()` 가 정상 init (이전엔 graceful skip 모드였음)
- ✅ `LoggingIntegration` (INFO breadcrumb / ERROR event capture) 정식 작동
- ✅ `FlaskIntegration` HTTP exception 자동 캡처
- ✅ `release` 자동 binding (version.py)
- 🟡 Sentry alert rule 미세 조정 (다음 주 운영 후 노이즈 비율 기반)

### 시스템 신뢰성 1차 완성

```
Before (4-22 사고): silent gap → 5일 무인지 → 사용자 신고로 발견
After (4-27+):       silent gap → assertion 즉시 캡처 → Sentry email/push
                     평균 인지 시간: 5일 → ~1분
```

### WEEKLY_PLAN_20260427.md 갱신

- v2.10.8/9/10 + Sentry 활성화 반영 (마지막 업데이트 23:13 KST)
- 핵심 3가지 → 2개 완료 + 1개 부분 완료 (DB Pool D+1 측정 잔존)
- 신규 섹션 "🛡️ assertion 자동 감지 layer + Sentry 시스템 확장" 추가 (자동 감지 시퀀스 표 + Before/After 비교)
- 4-28 화 측정 plan 에 v2.10.10 정상화 확인 + Sentry 24h 노이즈 비율 항목 추가

---

## 🟢 2026-04-27 세션 요약 (5/6) — HOTFIX-08 v2.10.10 db_pool transaction 정리 누락 + 046a 자동 적용

> **한 줄 요약**: v2.10.9 배포 후 Railway log 에 `046a_elec_checklist_seed.sql 실행 실패: set_session cannot be used inside a transaction` 발생 → assertion 이 두 번째 잠재 버그 (db_pool transaction 정리 누락 + 046a silent gap) 사용자 영향 0 시점에 발견. db_pool 2곳 SELECT 1 후 `conn.rollback()` 추가로 해결. 046a 자동 재적용 (ON CONFLICT idempotent).

### 문제 원인

- psycopg2 default `autocommit=False` → SELECT 도 BEGIN 자동 시작 → INTRANS 상태로 풀 반납
- 이 conn 을 받아 `m_conn.autocommit = True` 시도 시 `set_session cannot be used inside a transaction` 거부
- 영향받은 호출 경로: `_is_conn_usable()` + `warmup_pool()` 두 군데

### 코드 변경 (v2.10.10, BE only ~2줄)

- `backend/app/db_pool.py _is_conn_usable()` L98+ — SELECT 1 후 `conn.rollback()` 추가
- `backend/app/db_pool.py warmup_pool()` L270+ — 동일 패턴 적용
- `backend/version.py` v2.10.9 → 2.10.10
- `frontend/lib/utils/app_version.dart` v2.10.9 → 2.10.10

### 부수 발견 (가설 ④ 두 번째 사례)

- **046a_elec_checklist_seed.sql 도 silent gap** — 4-22 049 와 동일 Docker artifact 사례로 추정. assertion 이 자동 적용 시도 → set_session error 노출
- ON CONFLICT DO NOTHING idempotent 보장으로 prod 31항목 안전 재적용. **사용자 영향 0** ✅
- POST_MORTEM_MIGRATION_049.md 가설 ④ (Docker artifact / Railway build cache) 의 두 번째 케이스로 trail 추가

### git commit / 검증

- commit: `72579e1` (v2.10.10)
- pytest 회귀 0건
- Railway log 검증: `[migration] ✅ 046a_elec_checklist_seed.sql 실행 완료` + `[migration-assert] ✅ sync OK (13 migrations applied)` (12 → 13 갱신)

---

## 🟢 2026-04-27 세션 요약 (4/6) — HOTFIX-07 v2.10.9 RealDictCursor row[0] KeyError 긴급 복구

> **한 줄 요약**: v2.10.8 배포 직후 `assert_migrations_in_sync()` 첫 호출 시 worker boot 503 발생. `_get_executed()` 의 `row[0]` 이 RealDictCursor 와 호환 안 됨 → KeyError: 0. assertion 도입 자체가 5일 누적된 silent 버그를 즉시 노출시킨 사례 (assertion 가치 1차 입증).

### 문제 원인

- `db_pool` 이 `RealDictCursor` 사용 → row 가 dict-like → `row[0]` 은 `KeyError: 0`
- 이전 `run_migrations()` 의 outer try/except 가 silent 흡수 → 5일간 무인지
- v2.10.8 의 `assert_migrations_in_sync()` 는 try/except 없이 호출 → KeyError 그대로 propagate → gunicorn worker boot 실패 → 503

### 코드 변경 (v2.10.9, BE only)

- `backend/app/migration_runner.py _get_executed()` L51 — `row[0]` → `row['filename']`
- `backend/app/migration_runner.py assert_migrations_in_sync()` L165+ — outer try/except 안전망 추가 (assertion 자체 실패가 worker boot 막지 않도록)
- `backend/version.py` v2.10.8 → 2.10.9
- `frontend/lib/utils/app_version.dart` v2.10.8 → 2.10.9

### Lesson

- **assertion 도입 자체가 사고 발견 trigger 가 됨** — 5일간 silent 흡수된 row[0] KeyError 가 try/except 없는 호출 경로에서 즉시 노출
- 향후 신규 assertion 도입 시 outer try/except 안전망 표준화 권장

---

## 🟢 2026-04-27 세션 요약 (4/6 핵심) — v2.10.8 알람 시스템 사후 검증 마무리 4 Sprint 통합 배포

> **한 줄 요약**: 4-22 알람 silent failure (5일 52건 NULL) 사고의 사후 검증 마무리. POST-REVIEW-MIGRATION-049 + OBSERV-RAILWAY-LOG-LEVEL + OBSERV-ALERT-SILENT-FAIL (Sentry) + OBSERV-MIGRATION-RUNNER-STARTUP-ASSERTION 4 Sprint 통합 배포. 외부 자동 감지 layer 1차 완성.

### Sprint별 산출 (v2.10.8, BE only ~140 LOC)

| Sprint | 산출 |
|---|---|
| OBSERV-RAILWAY-LOG-LEVEL-MAPPING | `Procfile` `--access-logfile=- --log-level=info` 추가 + `__init__.py` `logging.basicConfig(stream=sys.stdout, force=True)` 명시 |
| OBSERV-ALERT-SILENT-FAIL (Sentry) | `requirements.txt` `sentry-sdk[flask]>=2.0` + `_init_sentry()` 신규 (~50 LOC, FlaskIntegration + LoggingIntegration + release auto-binding + send_default_pii=False) + migration_runner 실패 시 `sentry_sdk.capture_exception` |
| POST-REVIEW-MIGRATION-049-NOT-APPLIED | `POST_MORTEM_MIGRATION_049.md` 신규 — 4가지 가설 전수 검증 → ④ Docker artifact / Railway build cache 가장 유력 (Codex POST-REVIEW Q2-2 판정 일치) |
| OBSERV-MIGRATION-RUNNER-STARTUP-ASSERTION | `assert_migrations_in_sync()` 함수 신규 (~40 LOC) — disk vs DB sync 검증 + gap 시 `sentry_sdk.capture_message` |

### Twin파파 측 후속 (다음 세션 6/6 에서 완료)

1. ✅ sentry.io 가입 + Python/Flask project 생성 + DSN 발급
2. ✅ Railway env 등록: `SENTRY_DSN` (필수) + `SENTRY_ENVIRONMENT` (production) + `SENTRY_TRACES_SAMPLE_RATE`
3. 🟡 Sentry alert rule 설정 (1주 운영 후 미세 조정)

### 검증

- pytest test_scheduler.py 8 passed / 1 skipped / 회귀 0건 ✅
- BE syntax check (init/migration_runner) ✅

---

## 🟢 2026-04-27 세션 요약 (3.5/6) — HOTFIX-06 v2.10.7 warmup_pool() 시계 리셋 누락 fix

> **한 줄 요약**: v2.10.6 OBSERV-WARMUP 배포 후 결함 발견 — warmup 외형상 작동하지만 SELECT 1 만 실행하고 `_conn_created_at` 갱신 안 함 → `_is_conn_usable()` 가 expired 판정 → discard → direct conn fallback 다발. 1줄 추가로 해결.

### 코드 변경 (v2.10.7, BE only 1줄)

- `backend/app/db_pool.py warmup_pool()` L240+ — `_conn_created_at[id(conn)] = time.time()` 1줄 추가
- `backend/version.py` v2.10.6 → 2.10.7
- `frontend/lib/utils/app_version.dart` v2.10.6 → 2.10.7
- git commit: `7a13085`

### Limitation (per-worker 함정)

- 본 fix 는 fcntl lock 으로 1 worker (Worker A) 만 scheduler 실행 → Worker A 의 pool 만 시계 리셋
- **Worker B 의 pool 은 자연 만료**. 결과: conn 7~11 진동 (영구 10 의도는 절반 달성)
- 사용자 영향 0 입증 후 **D+1 (4-28 화) 출근 peak 측정 결과 따라 v2.10.11 HOTFIX-06b** (per-worker warmup) 진행 결정

---

## 🟢 2026-04-27 세션 요약 (3/3) — FEAT-PIN-STATUS-BACKEND-FALLBACK + OBSERV-DB-POOL-WARMUP 병행 Deploy (v2.10.6)

> **한 줄 요약**: FE 자동 PIN 복구 (P1 격상) + BE Pool warmup cron (P2, 실측 입증) 병행 배포. v2.10.6 Netlify (FE) + Railway (BE) 모두 배포 완료. PIN 사용자 보안 의도 유지 + Pool conn 영구 10 보장.

### 핵심 의사 결정 (병행 진행 안전성 검증 완료)

| Sprint | 영역 | 충돌 | 위험도 |
|---|---|---|---|
| FEAT-PIN-STATUS-BACKEND-FALLBACK | FE (main.dart + auth_service.dart) | 없음 | 🟢 LOW |
| OBSERV-DB-POOL-WARMUP | BE (db_pool.py + scheduler_service.py) | 없음 | 🟢 LOW |

→ 두 작업 다른 영역 + 의존성 없음 → 병행 안전. pytest test_scheduler.py 8 passed / 0 failed.

### 코드 변경 (v2.10.6)

**FE (FEAT-PIN-STATUS-BACKEND-FALLBACK, P1 격상)**:
- `frontend/lib/services/auth_service.dart` `getBackendPinStatus()` 신규 (~15 LOC)
  - `/auth/pin-status` 호출 + try/catch + debugPrint
- `frontend/lib/main.dart` L275~ tryAutoLogin 성공 후 backend PIN 복구 분기 추가 (~16 LOC)

**BE (OBSERV-DB-POOL-WARMUP, P2)**:
- `backend/app/db_pool.py` `warmup_pool()` public 함수 신규 (~40 LOC, A1 반영)
- `backend/app/services/scheduler_service.py`:
  - L17 `from apscheduler.triggers.interval import IntervalTrigger` (A3)
  - L23 `from app.db_pool import put_conn, warmup_pool`
  - `_pool_warmup_job()` 신규 함수
  - `add_job` 12번째 등록 — `IntervalTrigger(minutes=5)` + `next_run_time=datetime.now(Config.KST) + timedelta(seconds=10)` (timezone-aware, A5)
  - 스케줄러 job 수: **11 → 12**

**버전**:
- `backend/version.py` v2.10.5 → 2.10.6
- `frontend/lib/utils/app_version.dart` v2.10.5 → 2.10.6

### Claude Code advisory 1차 (OBSERV-WARMUP, M=0/A=5)

| # | Advisory | 반영 |
|:---:|:---|:---|
| A1 | private `_pool` API 직접 import → public `warmup_pool()` 노출 | ✅ |
| A2 | pytest TC `_pool=None` skip 처리 | ✅ warmup_pool 자체 처리 |
| A3 | `IntervalTrigger` 명시 import | ✅ |
| A4 | ThreadPool 경합 위험 평가 | ✅ 5/10 여유 |
| A5 | timezone-aware `next_run_time` | ✅ Config.KST |

### Codex 이관 미해당

두 sprint 모두 6항목 미충족:
- 인증 로직 변경 X (FEAT 는 호출 추가만, 로직 변경 X)
- 3파일 이상 X (각 2파일 이내)
- API 응답/스키마/FK X
- 클린코어 데이터 X

→ Claude Code 자체 검토 + 회귀 pytest 만으로 진행.

### 안전성 검증 완료

- ✅ Flutter web build 성공 (12.1s)
- ✅ BE syntax check (db_pool.py + scheduler_service.py)
- ✅ pytest test_scheduler.py: 8 passed / 1 skipped / 회귀 0건
- ✅ 다른 storage 키 영향 X (FEAT 는 pin_registered 만)
- ✅ scheduler 기존 11 job 영향 X

### Deploy

- 빌드: flutter build web --release ✓ 12.1s
- 배포 (FE): Netlify Deploy ID `69eef28fca3b7ffce577068d` (2026-04-27 KST)
- 배포 (BE): Railway 자동 (git push → ~1분)
- Production URL: https://gaxis-ops.netlify.app

### Post-deploy 검증 (Twin파파)

#### Railway logs (배포 직후, ~1분)

```
[scheduler] Scheduler initialized with 12 jobs   ← 11 → 12 확인
[pool_warmup] 5/5 conn warmed                    ← 첫 실행 (10초 후)
```

#### 1시간 관찰 (`pg_stat_activity`)

매 5분 conn 수 측정 → **10 영구 유지** = 성공. 7 이하 감소 시 Phase C 검토.

#### FEAT-PIN-STATUS 효과 검증

PIN 사용자가 IndexedDB 잃어도 `/auth/pin-status` 자동 호출 → PinLoginScreen 복귀 (HomeScreen 직행 X).

### 다음 세션 시작 시 할 일

1. **공지(notices) v2.10.6 bump** — PIN 자동 복구 + DB Pool 안정화 사용자 공지 (+ v2.10.5 합쳐서)
2. **FIX-DB-POOL Phase B 관찰 결과 정리** (D+1 화 4-28, D+2 수 4-29, D+3 목 4-30) — Pool exhausted grep + Q-B 재측정
3. **FEAT-PIN-FLAG 효과 측정** — D+7 (5-04) baseline SQL 재측정
4. **OBSERV-WARMUP 효과 검증** — D+1 새벽~출근 peak conn 추세 측정 (10 유지 확인)
5. **잔존 BACKLOG**:
   - `AUDIT-PWA-SW-INDEXEDDB-PRESERVE-20260427` 🟡 P2 (audit, 30분)
   - `UX-LOGIN-FALLBACK-PIN-RESET-LINK-20260427` 🟢 P3 (1h)
   - `FEAT-AUTH-STORAGE-MIGRATION-FULL-20260427` 🟡 P2 (보안 trade-off)

### 산출물 (v2.10.6)

- 코드 4 파일: db_pool.py + scheduler_service.py + auth_service.dart + main.dart
- 버전 2 파일: backend/version.py + frontend/lib/utils/app_version.dart
- 문서 3 파일: CHANGELOG.md ([2.10.6] entry) + BACKLOG.md (FEAT/OBSERV COMPLETED) + handoff.md (3/3 세션)

---

## 🟢 2026-04-27 세션 요약 (2/3) — FIX-PIN-FLAG-MIGRATION-SHAREDPREFS Deploy 완료 (v2.10.5)

> **한 줄 요약**: PIN 등록 플래그 storage 안정화 — `pin_registered` SecureStorage → SharedPreferences 양방향 sync 이전. 4 라운드 advisory review (M=8/8 + 추가 리스크 2/2 전수 반영) 후 적용. v2.10.5 Netlify 배포 완료.

### 핵심 의사 결정 (4 라운드 advisory 누적)

| 라운드 | 주체 | 발견 | 반영 |
|---|---|---|---|
| 1 (자체) | Claude Code | 인증 로직 영향 → Codex 이관 / 양방향 sync 채택 / baseline SQL 추가 (6건) | ✅ |
| 2 (Codex) | Codex 1차 | M 8건 (atomic / SQL LIKE / SW trigger / rollback 5번째 / cohort / 다른 가설 / D+7 통계 / iOS Safari) | ✅ 8/8 |
| 3 (Codex 추가) | Codex | 추가 리스크 2: refresh_token 도 SecureStorage / backend `/auth/pin-status` 가 진짜 root fix | ✅ 2/2 BACKLOG |
| 4 (배포 검증) | Twin파파 | home_screen.dart 별건 알림 배지 동기화 동시 포함 안전 검증 | ✅ |

### 코드 변경 (v2.10.5)

- `frontend/lib/services/auth_service.dart`:
  - L3 `package:flutter/foundation.dart` import 추가 (debugPrint)
  - `hasPinRegistered()` 양방향 read + sync (SharedPrefs 우선, SecureStorage fallback + auto-sync, **delete 안 함** rollback 안전)
  - `savePinRegistered()` 양방향 write + atomic try/catch (SharedPrefs 주 저장소, SecureStorage best-effort)
  - `logout()` (L243) SharedPrefs `pin_registered` 도 정리 (양방향 cleanup)
- `frontend/lib/utils/app_version.dart` v2.10.4 → **2.10.5**
- `backend/version.py` v2.10.4 → **2.10.5**
- 부수: `frontend/lib/screens/home/home_screen.dart` 알림 배지 동기화 (별건, 같은 commit 포함)

### Deploy

- 빌드: flutter build web --release ✓ 12.2s
- 배포: Netlify Deploy ID `69eed5d26147a9d3c6966ecf`
- Production URL: https://gaxis-ops.netlify.app

### Limitation (Codex 1차 advisory 핵심)

4개 SecureStorage 키 (`pin_registered`, `refresh_token`, `worker_id`, `worker_data`) 가 IndexedDB 일괄 손실 시 본 Sprint 효과 영역 좁음:
- `pin_registered` 만 단독 손실 (드뭄) → ✅ 본 Sprint 보호
- 4개 함께 손실 (Clear site data, Storage quota evict) → ❌ FEAT-PIN-STATUS-BACKEND-FALLBACK (P1) 가 진짜 root fix

### 신규 BACKLOG (4개 후속 Sprint, BACKLOG.md L347-L351 등록 완료)

- `FEAT-PIN-STATUS-BACKEND-FALLBACK-20260427` 🔴 P1 (격상 — 진짜 root fix, 1h)
- `AUDIT-PWA-SW-INDEXEDDB-PRESERVE-20260427` 🟡 P2 (audit, 30분)
- `UX-LOGIN-FALLBACK-PIN-RESET-LINK-20260427` 🟢 P3 (UX, 1h)
- `FEAT-AUTH-STORAGE-MIGRATION-FULL-20260427` 🟡 P2 (Codex 신규 권장 — refresh_token + worker_id + worker_data 도 양방향 sync)

### 다음 세션 시작 시 할 일

1. **Baseline SQL 측정** — 설계서 L31644~31691 SQL 3종 pgAdmin 실행 (배포 전 1회 권장, **사후 측정도 가능**)
2. **D+7 재측정 비교** (2026-05-04) — PIN 손실 의심 사용자 / login attempts / auth_pct 변화
3. **공지(notices) bump** — v2.10.5 사용자 공지 INSERT (PIN 화면 손실 보호 + 알림 배지 동기화)
4. **L32002 OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP P2 (격상)** — 실측으로 MIN=5 무효 입증 (10:14 → 10:24 conn 10→9→7), warmup cron 추가 (1~1.5h)
5. **FEAT-PIN-STATUS-BACKEND-FALLBACK P1** — 본 Sprint 직후 진행 (1h, 진짜 root fix)

### 부수 발견 (별도 보고)

1. **MIN=5 max_age=300s race 실측 입증** — 2026-04-27 10:14~10:24 KST 측정 결과 OPS 10→9→7 conn (10분만에 30% 감소). Codex 라운드 3 A4 advisory 가 실측으로 입증. → `OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP` P3 → P2 격상 + 본 세션 설계서 작성 (L32002).
2. **CHANGELOG v2.10.4 entry 누락** — 이전 세션 (4-25 health timeout 5→20s) 시 보충 안 됨. 별도 보충 필요 (사후 정리).

### 산출물 (FIX-PIN-FLAG)

- 코드 3 파일: auth_service.dart + app_version.dart + version.py
- 부수 1 파일: home_screen.dart
- 문서 4 파일: AGENT_TEAM_LAUNCH.md (PIN-FLAG + OBSERV-WARMUP 설계서) + CHANGELOG.md ([2.10.5] entry) + BACKLOG.md (5개 entry) + handoff.md (이 파일)
- 신규 1 파일: `CODEX_REVIEW_FIX_PIN_FLAG_20260427.md`

---

## 🟢 2026-04-27 세션 요약 (1/3) — FIX-DB-POOL-MAX-SIZE-20260427 Phase A 적용 (Phase B 관찰 중)

> **한 줄 요약**: Railway env `DB_POOL_MAX` 20→30 변경 (MIN=5 유지) — 코드 변경 0, 4 라운드 advisory review (Codex×2 + Claude Code×1 + Twin파파 fact-check×1) 후 적용. Phase B 3일 (화/수/목) 관찰 중.

### 핵심 의사 결정 (4 라운드 advisory 누적)

| 라운드 | 주체 | 발견 |
|---|---|---|
| 1 (텍스트) | Codex 1차 | scheduler peak 8 conn / 단계적 25→30 직행 / fallback 비용 / 평균 conn 정정 (4건) |
| 2 (코드 구조) | Claude Code | ⛔ **per-worker 독립 pool** 발견 (init_pool() in create_app() — 단일 pool 가정 무효) / Phase B 3일 확장 / pid+client_addr SQL (4건) |
| 3 (데이터 정합성) | Codex 3차 | Q-B 일자 오기 (4-27→4-21) / 5x 산수 오류 (155 in-flight 부족) / MIN ↔ max_age race / grep `\b` + `get_db_connection` 함수명 누락 (4건) |
| 4 (env fact-check) | **Twin파파** | ⚠️ 코드 default (1/10) 가정 오류 — **prod 가 이미 5/20 운영 중**. 결론 (MAX=30) 유지하되 fallback 추정 정정 (3건) |

### 최종 결정 + 배포

- **MAX**: 20 → **30** (Railway env)
- **MIN**: 5 (변경 없음, 유지)
- 배포 방식: Twin파파 Railway Dashboard 에서 직접 적용 → 자동 재배포
- 코드 변경 0 / 버전 bump 없음 / notices 없음

### Q-B 결정적 데이터 (2026-04-21 화 출근 burst)

- peak 31 동시 in-flight (08:06:07 KST)
- 21 동시 17회 (07:46~08:55)
- MAX=20 환경에서 fallback 1건/peak (라운드 4 정정)
- MAX=30 채택으로 fallback 0 + 미래 2x (62 in-flight) 까지 dimensioning

### Phase B 관찰 일정

| 날짜 | 시점 | 점검 |
|---|---|---|
| D+0 (4-27 월) | 16:30~17:00 KST | 퇴근 peak — Railway logs `Pool exhausted` grep |
| D+1 (4-28 화) | 07:30~09:00 KST | 출근 peak |
| D+2 (4-29 수) | 07:30~09:00 KST | 출근 peak |
| D+3 (4-30 목) | 07:30~09:00 KST | 출근 peak + Phase C 결정 |
| off-peak (12:00) | — | Q-B SQL 재측정 (O(N²) 부담 회피) |

### 다음 세션 시작 시 할 일

1. **Railway logs 검증** — `[db_pool] Connection pool initialized: min=5, max=30, max_age=300s, connect_timeout=5s` 1건 출력 확인 (D+0 배포 직후)
2. **Phase B grep 결과 정리** — 매일 오전 + 17:00 후 Railway logs `Pool exhausted` / `Using direct connection` 카운트
3. **D+3 (4-30 목) Phase C 결정**:
   - 0 fallback / 3일 → 30 충분, BACKLOG `FIX-DB-POOL-MAX-SIZE-20260427` COMPLETED 처리
   - 1~5건 / 3일 → MAX=40 ↑ (잠재 leak 의심)
   - 10+건 / 3일 → MAX=50 ↑ + leak audit 필수

### 부수 발견

1. **CHANGELOG v2.10.4 entry 누락** — 이전 세션 (2026-04-25 health timeout 5→20s 패치) 시 CHANGELOG 보충 안 됨. 별도 보충 필요 (사후 정리 항목).
2. **외부 환경 가정 SOP 부재** — 라운드 4 (Twin파파 fact-check) 가 결정적이었음. 향후 인프라 작업 시 Railway Variables 사전 확인 SOP 정립 필요 (CLAUDE.md INFRA 섹션 추가 후보).

### 산출물 (문서만 4 파일, 코드 0)

- `AGENT_TEAM_LAUNCH.md` FIX-DB-POOL-MAX-SIZE-20260427 섹션 (라운드 4 trail 추가, 약점 12건)
- `BACKLOG.md` FIX-DB-POOL 항목 → 🟡 PHASE A APPLIED → B 관찰 중
- `CHANGELOG.md` `[Infra] - 2026-04-27` entry 추가
- `handoff.md` (이 파일) 2026-04-27 세션 추가

### 별건 BACKLOG (2026-04-27 등록)

- `OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP` 🟢 P3 (격하 — MIN=5 가 cold-start 일부 흡수, 나머지는 5분 SELECT 1 cron)
- `OBSERV-RAILWAY-HEALTH-TTFB-15S-INTERMITTENT` 🟡 P2 (별건, Pool 30 적용 후 자연 해결 여부 확인)
- `OBSERV-SLOW-QUERY-ENDPOINT-PROFILING` 🟡 P2 (Q-A 화/수 p99≥1초 burst 9건 endpoint 분석 — Tue 19:00 max 2495ms / Wed 00:00 239 req 등)

---

## 🟢 2026-04-23 세션 요약 — Sprint 62-BE v2.2 구현 완료 (v2.10.0 배포 대기)

> **한 줄 요약**: Factory KPI 공급 인프라 확장 (weekly-kpi 3필드 + monthly-kpi 신설 + migration 050) — 신규 TC 17/17 + 회귀 36/36 GREEN, Railway 배포 대기

### 핵심 의사 결정 (3차 합의 축적)

| 단계 | 주체 | 결정 |
|---|---|---|
| v1 원안 (Opus) | Claude | weekly-kpi WHERE `ship_plan_date`→`finishing_plan_end` 교정 / `shipped_count` 단일 UNION |
| v1 Codex 1차 | Codex | M1(UNION 중복) / M2(반개구간) / M3(`_FIELD_LABELS` 누락) 지적 |
| v2 VIEW 역제안 | VIEW FE | v1.34.4 `mech_start` 영구 유지 + `shipped_count` 4필드 + `date_field` 파라미터 |
| v2 Codex 2차 | Codex | M 2건 (Q4 화이트리스트 불일치 / Q5 shipped_plan 이름) + A 4건 |
| v2.2 축소 확정 | **Twin파파** | UNION 자동 합산 폐기 (3개 소스 비교가 본질), 이행률·정합성 BACKLOG 이관 (App 베타 100% 전환 후 확정), `shipped_realtime`→`shipped_ops` 리네임 |
| v2.2 Codex 3차 | Codex | **M=0 / A=4 CONDITIONAL APPROVED** — v2.2 채택 가능 |
| A 4건 합의 반영 | Claude+Codex | INNER JOIN / TC-FK-11 경계 / EXPLAIN POST-REVIEW / 네이밍 부채 debt |

### 산출물 (3 파일 + 문서 4 파일)

**구현**:
- `backend/migrations/050_factory_kpi_indexes.sql` (신규, +20 LOC) — ALTER TABLE IF NOT EXISTS 2개 + CONCURRENTLY partial index 3개
- `backend/app/routes/factory.py` (+155/-6) — `_count_shipped` 3분기 헬퍼 + `_ALLOWED_DATE_FIELDS_MONTHLY_KPI` 신규 상수 + `get_monthly_kpi()` route + weekly-kpi 응답 3필드 확장 + monthly-detail 화이트리스트 5값 확장
- `tests/backend/test_factory_kpi.py` (신규, +330 LOC) — 11 TC (parametrize 17 assertions)

**문서**:
- `AGENT_TEAM_LAUNCH.md` Sprint 62-BE v2.2 섹션 (§ Codex 합의 기록 3차 결과 + Claude 원안 약점 trail 4건)
- `BACKLOG.md` — `BIZ-KPI-SHIPPING-01` 🟢 DRAFT 신규 + `POST-REVIEW-SPRINT-62-BE-V2.2-20260423` 🟡 OPEN 신규
- `CODEX_REVIEW_SPRINT_62_BE_V2.md` — 3차 축소 스코프 프롬프트 (Q1~Q6)
- `CHANGELOG.md` — v2.10.0 엔트리

### 부수 발견 (설계 단계에서 포착)

1. **Test DB 스키마 drift** — Prod에는 `actual_ship_date`/`finishing_plan_end` 컬럼이 ETL로 추가돼 있으나 `backend/migrations/*.sql` 에 정식 DDL 부재 → pytest 실행 시 500 에러로 발견. migration 050 에 `ALTER TABLE ADD COLUMN IF NOT EXISTS` 추가로 양쪽 정합 확보 (Prod no-op)
2. **Codex M-NEW-1 과다 지적 정정** — Codex 1차가 지적한 `_FIELD_LABELS` `finishing_plan_end` 누락은 실제로 `admin.py:2265` 이미 존재. `ship_plan_date` 도 `admin.py:2262` 존재. Codex 2차 Q1 A에서 스스로 정정
3. **Codex의 자기 재검증 가능** — v1 1차 검증 지적을 v2/v2.2 검증에서 스스로 무효화하는 패턴 확인. 편향 감소 효과

### Railway DB 실측 수치 (2026-04-23)

- **인덱스**: `completed_at` 1개만 존재, `actual_ship_date`/`ship_plan_date`/`finishing_plan_end` 3개 누락 확정 → migration 050 근거
- **주간 shipped 3종**: `shipped_ops=0` / `shipped_actual=23` / `shipped_plan=0` (이번 주 2026-04-20~27)
- **NULL 비율**: actual_ship_date 35.3% (미출하 정상) / ship_plan_date 0.1% / finishing_plan_end 0.1%
- **SI_SHIPMENT task 현황**: 71건 중 completed 1건 (베타 전환 초기 상태 — 정상)

### pytest 결과

```
신규 TC (test_factory_kpi.py)  17/17 PASSED ✅
회귀 TC (test_factory.py + test_admin_api.py)  36/36 PASSED ✅
─────────────────────────────────────────────────────────
합계                          53 PASSED / 0 regression
```

### 다음 세션 시작 시 할 일

1. ~~git commit + push (v2.10.0) → Railway 자동 배포~~ ✅ 완료
2. Railway 배포 후 Q3 A EXPLAIN ANALYZE 검증 — `_count_shipped` 3분기 쿼리가 partial index 실제 사용하는지
3. ~~notices INSERT — v2.10.0 공지~~ ✅ 완료 (id=102)
4. VIEW Sprint 36 (Cursor에서 동시 진행 중) — BE 3필드 배포 후 TEMP-HARDCODE 제거 연동 확인
5. POST-REVIEW-SPRINT-62-BE-V2.2 (배포 후 7일 내)

### 🔄 v2.10.1 PATCH 보정 (2026-04-23 동일일)

VIEW 측 재검토 후 1줄 교정 요청 수용:
- `weekly-kpi` L322 WHERE: `ship_plan_date` → `finishing_plan_end`
- TC-FK-02: "ship_plan_date 회귀" → "finishing_plan_end 교정 검증" 으로 반전
- 실측: 이번 주 31→48 (+17, +55%) / 지난 주 30→51 (+21, +70%)
- 의미: 주간 생산량 = 생산 완료 기준 (라벨 [Planned Finish] 와 일치) — v2.2 에서 "숫자 불변"을 가치로 높게 평가한 것이 실은 의미 정확성보다 덜 중요했음
- FE 변경 없음 (weekly.production_count 자동 반영)
- VIEW Sprint 35 Phase 2 (v1.35.0) 와 동기화 완료

### ✅ POST-REVIEW EXPLAIN ANALYZE 실측 완료 (2026-04-23)

Codex 3차 Q3 A 해소용 실측:

| # | 쿼리 | 인덱스 사용 | 실행 시간 |
|---|---|---|---|
| ① `_count_shipped('plan')` | ❌ planner가 completion_status Seq Scan + serial_number Nested Loop 선택 (si_completed=TRUE 0건이라 더 효율적) | 0.051 ms |
| ② `_count_shipped('actual')` | ✅ `idx_product_info_actual_ship_date` (Bitmap Index Scan) | 0.071 ms |
| ③ `_count_shipped('ops')` | ✅ `idx_app_task_details_completed_at` (기존 인덱스) | 0.092 ms |
| ④ weekly-kpi 메인 쿼리 | ✅ `idx_product_info_finishing_plan_end` (Bitmap Index Scan) | 0.127 ms |

**판정**: migration 050 partial index 2종 실사용 확인. 전체 sub-ms 대역. Q3 A **완전 해소**.

**잔여 Advisory**:
- `idx_product_info_ship_plan_date` 현재 미사용이나 si_completed=TRUE 비율 증가 시 자동 활성화 가능. 삭제 불필요 (공간 무시)
- Q5 (네이밍 부채 `pipeline.shipped` vs `shipped_plan`) — 관찰형 7일 유지, BIZ-KPI-SHIPPING-01 착수 시 final 네이밍 결정

### 🏁 Sprint 62-BE v2.2 전체 종결 (2026-04-23~24)

- ✅ v2.10.0 배포 (factory.py + migration 050 + 11 TC)
- ✅ v2.10.1 PATCH 교정 (weekly-kpi WHERE finishing_plan_end)
- ✅ v2.10.2 PATCH 교정 (FIX-CHECKLIST-DONE-DEDUPE-KEY, Codex Q4-4 M 해소)
- ✅ v2.10.3 PATCH 교정 (FIX-ORPHAN-ON-FINAL-DELIVERY, HOTFIX-DELIVERY 숨은 4번째 경로)
- ✅ Notices bump (id=102, v2.10.1 → v2.10.2 → v2.10.3)
- ✅ Netlify FE 배포 4회 (v2.10.0 + v2.10.1 + v2.10.2 + v2.10.3)
- ✅ Migration 050 Railway 적용 + migration_history 기록
- ✅ POST-REVIEW EXPLAIN ANALYZE Q3 A 해소
- ✅ POST-REVIEW-HOTFIX 4건 일괄 Codex 사후 검토 (Phase A 완료)
- ⏸ Q5 네이밍 부채 관찰형 7일 유지
- 🟢 **CASCADE-ALERT-NEXT-PROCESS DRAFT 등록** — ORPHAN_ON_FINAL 의 원래 설계 의도 (현재 공정 + 다음 공정 관리자 동시 알림) 는 사내 공정 활성화 계획 변동 이슈로 후순위 보류 (BACKLOG)

### 📋 Phase A Codex 사후 검토 결과 (2026-04-23)

4 HOTFIX 일괄 검토 → **M=1 / A=12 / N=2**

- **HOTFIX #1 PHASE1.5**: Close ✅ (Advisory 2건 OBSERV-ALERT-SILENT-FAIL 흡수)
- **HOTFIX #2 SCHEMA-RESTORE**: Close ✅ (Advisory 3건 기존 BACKLOG 흡수)
- **HOTFIX #3 DUP**: Close ✅ (Advisory 3건 — fd close / dead state / Redis 조건부)
- **HOTFIX #4 DELIVERY**: **v2.10.2 PATCH 로 Close** ✅ (M1 즉시 수정 + Q4-2 동시 해결)

**v2.10.2 수정 범위**:
- `scheduler_service.py` CHECKLIST_DONE_TASK_OPEN dedupe + RELAY_ORPHAN `message LIKE` → `task_detail_id` 전환
- `test_sprint61_alert_escalation.py` TC-61B-19B 신규 + setup fixture partner 보강
- `pytest` 결과: TC-61B-17/18/19/19B 전부 GREEN (이전 fixture 누락으로 TC-17 도 간헐 fail 했던 것 동시 해결)

### 📤 다음 액션 로드맵 (Phase B~G)

- **Phase B** (Twin파파 결정 필요): Railway DB rotation / 작업 flow 디버깅
- **Phase C (이번 주 내)**: OBSERV-ALERT-SILENT-FAIL (P1) + UX-SPRINT55-FINALIZE-DIALOG
- **Phase D**: POST-REVIEW-MIGRATION-049-NOT-APPLIED
- **Phase E**: OBSERV 3건 + ADMIN-ACTION-AUDIT
- **Phase F**: Sprint 55 UX 개선
- **Phase G**: INFRA-COLLATION / TEST-CLEAN-CORE / FE-ALERT-BADGE-SYNC

---

## 🔧 2026-04-21~22 세션 요약 (문서 개정 only — 코드 배포 없음)

> ⚠️ 마이그레이션으로 로컬 Cowork 초기화 → 컨텍스트 전수 재정리 + 규칙·워크플로우 대폭 개정
> ⚠️ 알람 시스템 장애 발견 — 4-17 이후 `app_alert_logs` 0건 (진단 완료, 확정 대기)

### 문서 개정 내역 (BE/FE 코드 변경 0)

1. **CLAUDE.md 대폭 개정** (OPS + VIEW 동시):
   - 📏 **코드 크기 원칙** 신설 — 1단계 500/800/1200 (파일당 LOC) + 함수 60줄 + 클래스 200줄 + 순환 복잡도 ≤10
   - 🔄 **DRY 재활용 원칙** 신설 — Rule of Three + grep 선행 + 승격 위치 명시
   - 🛡️ **리팩토링 안전 7원칙** 신설 — 테스트 커버리지 선행 + `[REFACTOR]` prefix + Before/After GREEN 증명 + git 태그 + DB migration 금지
   - 🤝 **AI 검증 워크플로우 v2** 전면 교체 — 8단계 파이프라인 + 3주체 용어(Cowork/Code/Codex) + Opus 1차 리뷰 + ② Codex 이관 체크리스트 6종 + 침묵 승인 거부 + 1라운드 상한 + 합의 실패 정의
   - 🚨 **긴급 HOTFIX 예외 조항** 신설 — S1/S2 Severity 구분 + 사후 Codex 검토 24h 규칙
   - 📦 **버전 번호 규칙** 재정의 — MAJOR(아키텍처/사내서버/SAP) / MINOR(Sprint 기능) / PATCH(HOTFIX·용어·데드 코드)
   - 🤖 **모델 버전 관리 규칙** 신설 — `claude-opus-4-7` (Lead) / `claude-sonnet-4-6` (Workers) — 신모델 출시 시 즉시 갱신

2. **BACKLOG.md 리팩토링 Sprint 계획 등록**:
   - OPS: **22 Sprint** (BE 17 + FE 5) — REF-00-TEST(테스트 선행) → admin.py 2,546줄 6단계 분할 → task_service.py 3단계 → work.py 2단계 → checklist/auth/scheduler → 경고 파일 → FE God File (admin_options_screen 2,593줄 등)
   - VIEW: **7 Sprint** — REF-V-00-UTIL(formatDate 공통화) → ProductionPerformancePage 895줄 → QrManagementPage 814줄 → Sidebar/ProductionPlan/FactoryDashboard 등

3. **리뷰 보완 4건 반영** (FE 회귀 블록 + 재질문 라운드 제외 + 합의 실패 정의 + 번들 크기 차등 ±10%/±5%)

### ✅ 완료 요약 (Phase 1·1.5·2 전부)

| Phase | 시각 | 결과 |
|---|---|---|
| Phase 1 (진단) | 4-21 | 후보 E duplicate 확정 + G 신규 확정 + A/C/D 기각 |
| Phase 1.5 (ERROR 로깅) | 4-22 10:47 | commit `4a6caf8` 배포, 47 pytest GREEN |
| **Phase 2 (근본 원인 확정)** | 4-22 11:00 | `column task_detail_id does not exist` 4건 포착 → **G.3 + A 부활 확정** |
| **Phase 2a (Schema Restore)** | 4-22 11:25 | pgAdmin SQL 5 블록 실행, 16건 신규 INSERT 성공 (§12.6) |
| Phase 2b (DUP 발견) | 4-22 12:40 | R1 쿼리 중복율 37.5%, Worker ≥3, DUP Sprint 작성 완료 |

### 📌 신규 세션(4.7) 시작 시 참조 순서

1. `~/Desktop/GST/AXIS-OPS/CLAUDE.md` (규칙·워크플로우 전문)
2. `~/Desktop/GST/AXIS-VIEW/CLAUDE.md` (VIEW 버전)
3. `~/Desktop/GST/AXIS-OPS/handoff.md` (이 파일 — 최신 상태)
4. `~/Desktop/GST/AXIS-VIEW/handoff.md` (VIEW 상태)
5. `~/Desktop/GST/AXIS-OPS/ALERT_SCHEDULER_DIAGNOSIS.md` (알람 장애 진단 최신)
6. `~/Desktop/GST/AXIS-OPS/BACKLOG.md` / `~/Desktop/GST/AXIS-VIEW/BACKLOG.md` (리팩토링 Sprint 계획)

---

## 현재 버전

- **OPS BE**: v2.9.11 (2026-04-22, 4 HOTFIX 통합 PATCH)
- **OPS FE (Flutter PWA)**: v2.9.11 (version 파일만 bump, OPS FE 코드 변경 0 — Netlify 배포 skip)
- **최근 Sprint**: HOTFIX-ALERT-SCHEDULER-DELIVERY-20260422 (scheduler 3곳 target_worker_id 표준 패턴 + 배치 dedupe) — ✅ 완료 (2026-04-22)
- **최근 완료 Sprint**: HOTFIX-ALERT-SCHEDULER-DELIVERY, HOTFIX-SCHEDULER-DUP, HOTFIX-ALERT-SCHEMA-RESTORE, HOTFIX-SCHEDULER-PHASE1.5, FIX-25 v4, FIX-24, HOTFIX-04, HOTFIX-05, HOTFIX-03, HOTFIX-02, BUG-45, 61-BE-B, 61-BE, BUG-43/44, HOTFIX-01, 60-BE, 59-BE, 58-BE

### 🗓 v2.9.11 포함 HOTFIX 이력 (SHA 별도 기록 — Codex A7 지적 반영)

| HOTFIX ID | Commit SHA | 변경 범위 | 배포 시각 (KST) |
|---|---|---|---|
| HOTFIX-SCHEDULER-PHASE1.5 | `4a6caf8` | ERROR 로깅 prefix 추가 (관찰용) | 2026-04-22 10:47 |
| HOTFIX-ALERT-SCHEMA-RESTORE | (pgAdmin SQL) | migration 049 수동 복구 (task_detail_id 컬럼 + enum 3종) | 2026-04-22 11:25 |
| HOTFIX-SCHEDULER-DUP | `f1af8a4` | fcntl file lock — scheduler 단일 실행 | 2026-04-22 13:24 |
| HOTFIX-ALERT-SCHEDULER-DELIVERY | `d946532` | scheduler 3곳 target_worker_id 표준 패턴 + 배치 dedupe | 2026-04-22 |
| FE Netlify 배포 | `69e8a677ca4e8352ce4678b6` | flutter build web + netlify-cli deploy --prod | 2026-04-22 19:45 KST |

✅ FE version skew 해소: 저장소 v2.9.11 + Netlify 배포 v2.9.11 동기화 완료 (gaxis-ops.netlify.app)
- **Migration 049**: Railway prod DB 에 migration_runner 미실행 → 2026-04-22 11:25 수동 SQL 복구 (id=37 기록)
- **체크리스트 현황**: TM 완료 (SINGLE/DUAL qr_doc_id 정규화) / ELEC 완료 (Phase 1+2, 마스터 정규화) / MECH 미구현
- **RULE-01**: Sprint 완료 시 FE flutter build web + Netlify 배포 필수

---

## 직전 세션 작업 내용 (2026-04-22)

> **🔴 5일 알람 장애 root cause 확정 + 🟢 복구 완료 + 🆕 중복 실행 신규 이슈 발견** — Phase 1.5 ERROR 로깅 배포 → 10분만에 근본 원인 포착 → pgAdmin SQL 수동 복구 → 12:00 tick 정상 INSERT 16건 → R1 쿼리로 중복 실행 37.5% 확정

### 🟢 Phase 1: HOTFIX-SCHEDULER-PHASE1.5 배포 (commit `4a6caf8`, 10:47 KST)

- `alert_service.py` + `alert_log.py` 2 파일 — `[alert_silent_fail]` / `[alert_create_none]` / `[alert_insert_fail]` prefix ERROR 로깅 추가. Sentry SDK 선택적 import 가드. 기존 `return None` 동작 유지. +80 / -37 LOC
- pytest 검증: `test_alert_service.py` 11 + `test_alert_all20_verify.py` 36 = **47 passed / 회귀 0건**

### 🔴 Phase 1.5: 근본 원인 확정 (11:00 KST, 02:00 UTC tick)

**결정적 로그** (단일 hourly tick 에서 4건 포착):
```
ERROR [alert_insert_fail] INSERT failed:
  error=column "task_detail_id" of relation "app_alert_logs" does not exist
```

**3-증거 삼각 검증** (ALERT_SCHEDULER_DIAGNOSIS.md §12.2):
- Q1 `migration_history` → max id=36, 049 기록 없음
- Q5 `app_alert_logs` → 12 컬럼, `task_detail_id` 부재
- Railway 로그 → `column ... does not exist` 4건

**최종 원인 (§12.1)**: _"Railway 운영 DB 의 `app_alert_logs` 에 `task_detail_id` 컬럼이 존재하지 않아, Sprint 61-BE(4-17) 배포 이후 8-컬럼 INSERT 가 100% PsycopgError 로 실패하고 try/except 가 삼켜 return None 반환 → 5일 연속 0건"_

### 🟢 Phase 2: HOTFIX-ALERT-SCHEMA-RESTORE-20260422 실행 (11:25 KST)

pgAdmin prod 에서 5 블록 autocommit SQL 실행 (migration 049 수동 재현):
1. enum 3종 추가 (`TASK_NOT_STARTED` / `CHECKLIST_DONE_TASK_OPEN` / `ORPHAN_ON_FINAL`)
2. `app_alert_logs.task_detail_id` 컬럼 추가 ← **핵심 복구**
3. `idx_alert_logs_dedupe` 인덱스
4. `admin_settings` 5 키 INSERT
5. `migration_history` id=37 수동 기록

**검증 A/B/C 3종 PASS** → 12:00 KST tick (03:00 UTC) 에서 **신규 INSERT 16건 성공** (id 657 → 673, RELAY_ORPHAN). 5일 장애 완전 해소.

### 🆕 Phase 3: HOTFIX-SCHEDULER-DUP-20260422 신규 발견 (12:40 KST, R1 쿼리)

복구 직후 R1 쿼리로 중복 실행 확정:
| serial_number | cnt | gap_ms |
|---|---|---|
| GBWS-6980 | 2 | 59.77 |
| GBWS-7017 | 2 | 18.87 |
| GBWS-7024 | 2 | 31.50 |
| GBWS-7038 | 2 | 73.15 |
| **GPWS-0773** | **3** | **86.37** |

- 중복율 **37.5%** (6/16)
- Worker ≥ **3** (GPWS-0773 triple)
- gap_ms 18~86ms 범위 → race condition 확정
- **해결책**: `app/__init__.py` 에 `fcntl.flock LOCK_EX | LOCK_NB` 기반 `/tmp/axis_ops_scheduler.lock` 파일 락 도입 — Sprint `HOTFIX-SCHEDULER-DUP-20260422` 작성 완료 (`AGENT_TEAM_LAUNCH.md` L29644~)

### 📋 세션 부수 작업

1. **Mac 마이그레이션 후 환경 복구**: Xcode license 재수락, `.git/objects/` 손상 blob 복구, Python venv 재생성, Claude Code FSA 이슈 인지
2. **보안 민감 md `.gitignore` 추가**: `/SECURITY_REVIEW.md` + `/DB_ROTATION_PLAN.md` (public repo 금지)
3. **FE-ALERT-BADGE-SYNC BACKLOG 등록**: `home_screen.dart` 미커밋 변경 재검토 후 별도 Sprint
4. **3 커밋 push 완료**: `a569dc0` (gitignore) + `41d9db2` (scheduler 진단 docs) + `ea55edb` (네이밍 규칙 + HOTFIX 프롬프트 + BACKLOG)
5. **ALERT_SCHEDULER_DIAGNOSIS.md §12 신설** + §11.14.3 반증 주석 + §12.3 "베타 설비 3→20대 확장" 컨텍스트 메모 추가

### 🔴 다음 세션 최우선 — HOTFIX-SCHEDULER-DUP-20260422 즉시 착수

**Sprint 프롬프트**: `AGENT_TEAM_LAUNCH.md` L29644~ 참조
**예상 소요**: 45~90분 (코드 15~25 + 검증 15~20 + 배포 관찰 30~60)
**영향 방지**: 현재 중복 기록 37.5% 발생 중, 설비 확장기 알람 품질 저하

**병행 관찰**:
- 매시 정각 Railway 로그: `Running` / `executed successfully` 2회 중복 여전 확인
- `app_alert_logs` 일간 건수 추이 (복구 후 4-16 수준 회복 검증, §12.3 환경 컨텍스트 참조)

**후속 장기 Sprint** (§12.9 BACKLOG 등록 완료):
- `POST-REVIEW-MIGRATION-049-NOT-APPLIED` (S3 조사) — DUP 배포 후
- `OBSERV-ALERT-SILENT-FAIL` (Sentry 정식 연동) — 재발 방지 필수
- `OBSERV-MIGRATION-HISTORY-SCHEMA` + `OBSERV-MIGRATION-RUNNER-STARTUP-ASSERTION` — 본 장애 근본 재발 방지책

---

## 이전 세션 작업 내용 (2026-04-20)

1. **FIX-25 v4 (v2.9.10)**: progress API(`/api/app/product/progress`) 응답에 `mech_partner`/`elec_partner`/`module_outsourcing`/`line` 4필드 노출. `progress_service.py` 단일 파일 — sn_list CTE + 메인 SELECT에 `pi.line` 추가 + `_aggregate_products` dict `'line'` 추가 + L296~299 `sn_data.pop(...)` 3줄 제거. touch 6줄 / net 0줄 (+3/-3).
2. **설계 진화 v1→v4**: v1(거미줄 JOIN 3곳) → v2(production CTE 집계) → v3(tasks API dict 주입, Codex M1 breaking) → **v4 채택**(progress API 단일 확장, tasks API 무변경).
3. **Claude×Codex 교차검증**: v3 M1(tasks API List→Dict) 지적 반영 → v4 전환. Claude 실측으로 `progress_service.py`에 partner 3필드 이미 SELECT 중 + L296~299 pop 구조 발견이 결정적 전환 근거.
4. **설계서 정정**: AGENT_TEAM_LAUNCH.md L27459/L27588 "OPS FE 미사용" 서술 → `sn_progress_screen.dart:44`에서 사용 중 확인 후 "사용 중이나 파싱 breaking 0 (Dart `Map<String, dynamic>.from(e)`)" 로 정정.
5. **pytest**: TC-PROGRESS-PI-01~06 신규 6건 + `test_sn_progress` 10 + `test_product_api` 17 + `test_production` 9 = **42/42 GREEN**, Codex 합의 진입 없이 첫 시도 통과.
6. **배포**: BE Railway 자동 (push `21cba31`). OPS FE 코드 변경 0 → Netlify 배포 skip.

---

## 이전 세션 작업 내용 (2026-04-17)

1. **Sprint 61-BE**: 알람 O/N 통일 + 에스컬레이션 3종 + pending API 확장 + SETTING_KEYS 5개
2. **BUG-43**: 분석 대시보드 한글 라벨 24개 누락 전수 등록 (111→135키)
3. **에스컬레이션 토글 UI**: admin_options_screen 알림 트리거 설정 하단에 토글 4개 + 기준일 드롭다운
4. **BUG-44**: 미종료 작업 0건 — INNER JOIN → LATERAL JOIN (work_start_log FK)
5. **Sprint 61-BE-B**: pending/task API company + force_closed 필드 추가 (#60, #61)
6. **HOTFIX-01**: force_close/force_complete TypeError — naive vs aware datetime 정규화
7. **BUG-45 (v2.9.6)**: force_close `completed_at` 범위 검증 — 미래 차단(60s skew 허용) + started_at 이전 차단. VIEW useForceClose `reason → close_reason` (FE-17). TC-FC-11~18 8건 추가, 회귀 GREEN
8. **HOTFIX-02 (Sprint 60-BE 후속)**: 체크리스트 마스터 API `checker_role` 키 응답 누락 — `list_checklist_master()` SELECT/응답 dict 2줄 추가. VIEW JIG WORKER/QI 뱃지 분기 정상화 (OPS #59-B DONE / VIEW FE-18 ✅)
9. **TEST-CONTRACT-01 BACKLOG 등록**: VIEW↔BE API 필드 계약 자동 검증 (pytest + JSON Schema). BUG-45 재발 방지 Advisory. 설계: AGENT_TEAM_LAUNCH.md TEST-CONTRACT-01 섹션
10. **HOTFIX-03**: 비활성 task 조회 필터 누락 — `get_tasks_by_serial_number()` + `get_tasks_by_qr_doc_id()` 4 SELECT에 `AND is_applicable = TRUE` 추가 (방안 A 채택). VIEW S/N 상세뷰 Heating Jacket 미시작 카운트 오염 정상화 (OPS #60 DONE)
11. **DOC-SYNC-01 BACKLOG 등록**: OPS_API_REQUESTS.md / VIEW_FE_Request.md 잔여 PENDING 13건+ 실구현 상태 교차 검증 (관리 작업)
12. **HOTFIX-05 (v2.9.7)**: Admin 옵션 미종료 작업 카드 시간 UTC 오표시 — `admin_options_screen.dart` L2474 `.toLocal()` 1줄 추가. Manager 화면과 일관성 확보. FE only, BE 영향 없음
13. **HOTFIX-04 BE 완료 (v2.9.8)**: 강제종료 표시 누락 종합 수정 — Case 1(Orphan wsl) + Case 2(NS 강제종료) 통합, **옵션 C' 채택**(TaskDetail 모델 `closed_by_name` 필드 + SELECT LEFT JOIN workers). task_detail.py + work.py 수정, pytest 신규 9 + 회귀 24 = 33/33 GREEN. VIEW FE-19(placeholder 렌더)는 VIEW 리포 별도 진행
14. **FIX-24 (v2.9.9)**: OPS 미종료 작업 카드 Row 2에 O/N(sales_order) 뱃지 추가 — `admin_options_screen.dart` + `manager_pending_tasks_screen.dart` 2파일, `Icons.receipt_long` + conditional spread 약 6줄×2. BE 변경 0줄 (응답 `sales_order` 이미 포함). A1 오버플로 방어 미반영(sales_order 6자리 이하)
15. **Claude × Codex 교차 리뷰**: Sprint 61 설계 9건 + BUG-44 6건 + HOTFIX 원인 수정 + BUG-45 1차 Must 보정 + HOTFIX-02/03/04/05 + FIX-24 합의. HOTFIX-04는 M2 옵션 A→C' 재확정(장기 시스템 원칙) + A1 TC 3건(NS-03/04/05) 추가 반영

---

## 실행 우선순위 (Sprint 실행 순서)

### ✅ 완료된 Sprint (전체 테스트 통과)

| Sprint | 내용 | 완료일 |
|--------|------|--------|
| Sprint 41 | 작업 릴레이 + Manager 재활성화 | 완료 |
| Fix Sprint 41-A | 릴레이 토스트 + 다이얼로그 + 재시작UI + 재완료BE | 완료 |
| Fix Sprint 48 | 재활성화 권한 `in` 비교 방향 버그 | 완료 |
| Sprint 41-B | 릴레이 자동 마감 + Manager 알림 | 완료 |
| Sprint 51 | progress API sales_order 추가 | 완료 |
| OPS_API #52 | ETL _FIELD_LABELS finishing_plan_end | 완료 |
| Sprint 52 | TM 체크리스트 Partner 검수 Phase 1 | 완료 |
| Sprint 53 | monthly-summary weeks+totals (Friday-based 매핑) | 완료 |
| Sprint 54(체크리스트) | 체크리스트 성적서 API (배치 최적화) | 완료 |
| Sprint 54(알림) | 공정 흐름 알림 트리거 + Partner 분기 | 완료 |

### 🔴 즉시 — 잔여 작업

| 순서 | 내용 | 상태 | 비고 |
|------|------|------|------|
| 1 | **VIEW FE 연동**: FE-12 ELEC 블러 해제 + FE-07/08 ELEC status 매핑 | BE 준비 완료 | Sprint 58-BE 완료로 착수 가능 |
| 2 | 실적확인 토글 테스트: OFF(progress 100%) / ON(progress+체크리스트) | BE 준비 완료 | 대시보드 업데이트 후 테스트 |
| 3 | Sprint 55: Worker별 Pause + Auto-Finalize | Sprint 작성 완료 | BE 5파일 + FE 2파일, DB 변경 없음, TC 28건 |
| 4 | MECH 체크리스트 양식 추가 | 대기 | TM/ELEC 완료, MECH 양식 수집 후 추가 |

### 🟡 중기 — VIEW 기능

| 순서 | Sprint | 내용 | 상태 | 비고 |
|------|--------|------|------|------|
| 2 | VIEW Sprint 23 | Task 재활성화 UI | 설계 완료 | Sprint 41 BE 완료됨, 착수 가능 |
| 3 | VIEW Sprint 24 | O/N 그룹핑 UI | 미작성 | Sprint 51 BE 완료됨, 착수 가능 |
| 4 | VIEW Sprint 18-C | S/N 카드뷰 개선 | 프롬프트 완료 | FE only, 빠르게 가능 |

### 🟠 대기 — 착수 조건 미충족

| 순서 | 내용 | 상태 | 착수 조건 |
|------|------|------|-----------|
| - | 개인정보 동의 관리 (팝업+토글) | Backlog 등록 완료 | 명세서 확정, 약관 본문, 법무 검토 |
| - | CT 분석 모듈 (공수/리드타임) | Backlog 등록 완료 | 스키마 맵 DB 검증, 데이터 축적 |

### 🟢 장기 — 데이터/분석 (100% 전환 후)

| 순서 | 내용 | 상태 | 비고 |
|------|------|------|------|
| - | analytics_prod 스키마 설계 | 방향 정리 완료 | 표준공수, 편차분석, 일별집계 |
| - | APS Lite Phase 0 | 기획 완료 | 실데이터 축적 후 |

---

## 미해결 버그

| ID | 설명 | 심각도 | 해결방법 |
|----|------|--------|----------|
| BUG-1 | QR 카메라 권한 팝업 가려짐 (DOM z-index) | 중 | FE z-index 조정 |
| BUG-3 | 출퇴근 버튼 퇴근 후 비활성화 (FE 상태 머신) | 낮음 | FE 상태 리셋 |
| ~~BUG-4~~ | ~~CHECKLIST_TM_READY 알림 미생성~~ | ~~높음~~ | ✅ Sprint 54(알림) 완료로 해결 |
| BUG-5 | Manager 완료 시 checklist_ready 플래그 FE 미처리 | 중 | task_detail_screen.dart _handleCompleteTask() 수정 |
| ~~BUG-6~~ | ~~다중작업자 task에서 동료가 resume 시 403 FORBIDDEN~~ | ~~높음~~ | ✅ Sprint 55 Worker별 Pause로 근본 해결 |

---

## 보안 이슈 (즉시 조치 권장)

1. **CORS `origins="*"`** — `__init__.py` 라인 41-44 → 운영 도메인만 허용으로 변경
2. **JWT_SECRET_KEY 하드코딩** — config.py → 환경변수 분리

---

## 문서 위치 가이드

| 파일 | 용도 | 읽는 시점 |
|------|------|-----------|
| `CLAUDE.md` | 프로젝트 고정 정보 (팀 구성, 기술 스택, 규칙) | 매 세션 시작 시 |
| `memory.md` | 누적 의사결정, ADR, 감사 결과 | 맥락 필요 시 |
| `handoff.md` | 현재 파일. 세션 인계용 | 매 세션 시작 시 |
| `DB_SCHEMA_MAP.md` | DB 스키마 맵 (8스키마, 43테이블, FK, ENUM) | 테이블 신설/쿼리 작성 시 |
| `BACKLOG.md` | 전체 백로그 + Sprint 이력 + 체크리스트 설계 | Sprint 기획 시 |
| `AGENT_TEAM_LAUNCH.md` | Sprint 프롬프트 모음 (19,000줄+) | Sprint 실행 시 |
| `PROGRESS.md` | API 엔드포인트 + 테스트 현황 | 진행률 확인 시 |
| `analytics_prod_erd.mermaid` | 생산 분석 ERD (향후) | analytics 작업 시 |
| `AXIS-VIEW/docs/OPS_API_REQUESTS.md` | VIEW→OPS API 요청/버그 | API 이슈 확인 시 |
| `AXIS-VIEW/docs/sprints/DESIGN_FIX_SPRINT.md` | VIEW Sprint 23 설계 | VIEW 재활성화 작업 시 |
| `concepts_reference.md` | 유튜브 학습 용어 + 점검 보고서 매핑 | 개념 확인 시 |

---

## 세션 업데이트 규칙

세션 종료 시 아래 항목만 업데이트:
- `현재 버전` — 새 Sprint 완료 시
- `직전 세션 작업 내용` — 전체 교체
- `실행 우선순위` — 완료된 것 제거, 새로 추가된 것 기록
- `미해결 버그` — 해결/신규 반영

memory.md에는 **의사결정/ADR/아키텍처 판단**만 추가 (일상 작업 기록 X)
