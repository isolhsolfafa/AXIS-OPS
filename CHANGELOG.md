# Changelog

All notable changes to AXIS-OPS are documented here.

Format: [Semantic Versioning](https://semver.org/) — MAJOR.MINOR.PATCH

---

## [2.11.3] - 2026-05-04 — Sprint 63 후속 hotfix: check_result null 차단 + phase=2 read-only UI (FE only, P0 hotfix)

> v2.11.2 prod 배포 후 사용자 운영 검증 (TEST-333/TEST-1111) — `PUT /api/app/checklist/mech/check → 400 INVALID_CHECK_RESULT: 'None'` + 2차 검사인원 읽기 전용 UI 부재. Codex 라운드 1 A3-F2 advisory 미구현 영역.

### 진단 SQL 결과 (DB 직접 쿼리)
- TEST-1111: CHECK 2 + SELECT 7 + INPUT 1 모두 정상 저장 ✅
- TEST-333 (DRAGON): CHECK 2 + SELECT 7 + INPUT 10 (INLET L/R 8 + Speed × 2) 모두 정상 저장 ✅
- → BE upsert 정상 작동 확정. **FE only 정정 충분** (BE 무관)

### Root cause 2건
- **R1**: `_upsertNow` 의 `cr.isEmpty ? null : cr` → null 전송 시 BE 400 거부
- **R2**: phase=2 시 TextField/DropdownButton 둘 다 enabled → 관리자가 1차 데이터 임의 변경 가능 (권한 위반)

### 변경 (FE only, 1 파일 ~13 LoC)

`frontend/lib/screens/checklist/mech_checklist_screen.dart` 3 위치:
1. **`_upsertNow`** L278~ — `cr.isEmpty` 시 PUT skip (R1, ELEC `_toggleResult` 패턴 정합)
2. **`_buildInputField`** L803~ — phase=2 시 `readOnly: true` + `fillColor: GxColors.cloud` + `onChanged: null` (R2)
3. **`_buildSelectDropdown`** L723~ — phase=2 시 `onChanged: null` + `fillColor: GxColors.cloud` (R2)

### 검증
- 진단 SQL: TEST-1111/TEST-333 phase=1 모든 항목 정상 저장 확인 ✅
- flutter analyze: 0 error (info 2건만, 빌드 차단 X) ✅
- flutter build web --release: ✓ Built ✅

### 회귀 영향
- 0건 (FE UI 변경만, BE/타 화면 무관)
- migration/DB 변경 없음 → git revert 1건으로 v2.11.2 복귀 가능

---

## [2.11.2] - 2026-05-04 — Sprint 63 후속 BUGFIX: 체크리스트 진입점 누락 fix (BE+FE, P0 hotfix)

> v2.11.1 prod 배포 직후 사용자 검증 — "체크리스트 자동 전환 안 됨" + "task 상세 메뉴 버튼 없음" 발견. Sprint 63-BE 설계 시 ELEC 패턴 차용 영역에서 토스트만 매핑하고 진입점(entry point) 영역 누락. P0 hotfix.

### Root cause
- Sprint 63-BE 설계 catch 누락: trigger_task_id 토스트만 매핑 + work/start 응답 분기 + task 상세 메뉴 버튼 누락
- Sprint 63-FE `_navigateToChecklist` 함수는 task_management_screen 에만 MECH 분기 추가, task_detail_screen 의 동일 이름 함수는 누락 (dead code 상태)

### 변경 (BE 1 파일 + FE 1 파일, 2 파일 ~25 LoC)

**BE (`backend/app/routes/work.py`)**:
- L177~ MECH 분기 추가: `MECH_CHECKLIST_TASK_IDS = {UTIL_LINE_1, UTIL_LINE_2, WASTE_GAS_LINE_2, SELF_INSPECTION}`
- 4 task 시작 시 응답에 `checklist_ready=True + checklist_category='MECH'`

**FE (`frontend/lib/screens/task/task_detail_screen.dart`) — 5 위치**:
1. L7-8 import: `mech_checklist_screen.dart` 추가
2. L760-770 `_hasChecklistAccess`: MECH 4 trigger task_id 분기
3. L737-746 `_buildChecklistButton` onTap (in_progress 시): MECH 분기
4. L767-780 `_navigateToChecklist`: MECH 분기 (`MechChecklistScreen`)
5. **L658-672 `_buildCompletedBadge` onTap (completed 시)**: MECH 분기 (추가 검토 5번째 catch)

### Codex 라운드 1 + 추가 검토 (M=1 / A=3 / N=1 + AV=2 + 추가 catch 1)
- M-R1: `_hasChecklistAccess` taskCategory + taskId 양쪽 매칭 risk indicator (현재 코드 OK)
- A1+AV1: trigger_task_id 권위 소스 정정 — `task_seed.py` → `migrations/051a_mech_checklist_seed.sql:106`
- A2: pytest TC 신규 6 assertions
- A3: BE+FE 단일 atomic commit (Railway half-state 차단)
- AV2: 선택 3 (work/complete MECH) → 별 sprint `FEAT-MECH-WORK-COMPLETE-CHECKLIST-NUDGE-20260504` (P3) 분리
- 추가 검토: 5번째 위치 (`_buildCompletedBadge` onTap) 누락 — 4 → 5 위치로 갱신

### Test
- `tests/backend/test_mech_checklist.py` `TestWorkStartMechChecklistEntry` 6 TC 신규:
  - UTIL_LINE_1/2 + WASTE_GAS_LINE_2 + SELF_INSPECTION 시작 시 checklist_ready=True
  - WASTE_GAS_LINE_1 (의도적 제외) negative 검증
  - ELEC INSPECTION 회귀 검증 (category='ELEC' 유지)
- 누적 24 → 30 TC

### 회귀 영향
- 0건 (BE response 키 추가 + FE 분기 추가만, additive)
- migration/DB 변경 없음 → git revert 1건으로 v2.11.1 복귀 가능

---

## [2.11.1] - 2026-05-04 — Sprint 63-FE Flutter UI + R2-1 BE patch + N1/N2 정정 (BE+FE)

> Sprint 63 전체 종료 piece. v2.11.0 (BE 인프라) + R2-1 BE patch + Flutter UI 통합 release.

### 추가 (BE patch — R2-1, Codex 라운드 2)
- `services/checklist_service.py` `get_mech_checklist()` 응답에 `tank_in_mech: bool` 추가
- model_config LEFT JOIN longest-prefix 매칭 (FE `_isScopeMatched` 활용)
- HOTFIX-08 표준 `conn.rollback()` 적용

### 추가 (FE 신규)
- `frontend/lib/screens/checklist/mech_checklist_screen.dart` 신규 (~844 LoC)
  - 입력 UI 3종 분기 (CHECK 라디오 / SELECT 드롭다운 / INPUT 텍스트)
  - scope_rule disabled NA UI ('N/A' 일관)
  - judgment_phase 토글 + role gate (`is_manager` / `is_admin`)
  - INLET 8개 Left/Right subgroup 시각 분리 (Q1-B)
  - debounce 500ms (Q6-C) + 번들 PUT (M5)
  - dispose() controller + timer 정리 (A4-F2)
- `frontend/lib/models/alert_log.dart` `CHECKLIST_MECH_READY` priority + iconName 추가
- `frontend/lib/screens/admin/alert_list_screen.dart`:
  - `_handleAlertTap` MECH 분기 → `MechChecklistScreen` 진입
  - title 매핑 + color 매핑 추가
- `frontend/lib/screens/task/task_management_screen.dart` `MechChecklistScreen` 라우팅 추가

### 정정 (Codex 라운드 2 Must 4건)
- M-R2-A/B: DUAL split-token 매칭 — `model.split(RegExp(r'[\s\-]')).contains('DUAL')` ('DUAL-300' / 'GAIA-DUAL-X' false-positive 차단)
- M-R2-C: DUAL 도면 qr_doc_id 정책 — `_qrDocIdForItem` DRAGON+INPUT+DUAL 만 hint 강제, 도면 SINGLE fallback
- M-R2-D: pytest 3 TC 신규 (`TestR21TankInMechResponse`)

### 정정 (N1+N2 본 세션 추가)
- N1: WebSocket `CHECKLIST_MECH_READY` alert provider 분기 추가 (alert_list_screen + alert_log)
- N2: pytest 3 TC 신규 — `tank_in_mech` 응답 키 회귀 + 모델별 boolean 검증

### Test
- `tests/backend/test_mech_checklist.py` 21 → 24 TC
- `TestR21TankInMechResponse` 3 TC: 모든 모델 응답 키 / DRAGON/GALLANT/SWS=TRUE / GAIA/MITHAS/SDS=FALSE
- 결과: **3/3 PASS** (85.54s)

### 회귀 영향
- 0건 (응답 키 추가 + 신규 FE 파일 + 기존 alert_log/alert_list 분기 추가만)

### Push 전 검증 (commit 21c581e GxColors 정정 포함)
- pytest test_mech_checklist 24/24 PASS (229.55s) — 위험 1 통과
- flutter analyze: 7 error → 0 error (info 2건만, 빌드 차단 X) — 위험 2-1
  * `GxColors.background` → `cloud` / `surface` → `white` / `mistLight` → `cloud` (7곳, ELEC 패턴 차용)
- flutter build web --release: ✓ Built build/web (12.3s) — 위험 2-2

### 후속 (별 sprint)
- AXIS-VIEW Sprint 39: BLUR 해제 + AddModal 토글 (~0.5d, 별 repo)
- BUG-TM-CHECKLIST-AUTO-FINALIZE-STALE-TC-20260504 (P3, 1h, Sprint 63-BE 무관)

---

## [2.11.0] - 2026-05-04 — Sprint 63-BE MECH 체크리스트 BE 인프라 (BE only, +1,415 LoC)

> 양식 73 항목 / 20 그룹 도입 — TM(Sprint 52)/ELEC(Sprint 57) 후 MECH 자주검사 체크리스트 디지털화. BE 단독 배포, FE/VIEW 별 sprint.

### 추가 (Schema)
- `migrations/051_mech_checklist_extension.sql`: `scope_rule` + `trigger_task_id` 컬럼 + `item_type` CHECK constraint 'INPUT' 추가 + `alert_type_enum` 'CHECKLIST_MECH_READY' ADD VALUE
- `migrations/051a_mech_checklist_seed.sql`: 73 INSERT (CHECK 56 / INPUT 10 / SELECT 7, all 56 / tank_in_mech 9 / DRAGON 8, INLET S/N L/R 8개 분리 v2)

### 추가 (BE)
- `services/checklist_service.py` 신규 함수 5개:
  - `_normalize_qr_doc_id()` — TM/ELEC/MECH 공유 normalizer (Sprint 59-BE 재발 방지)
  - `_resolve_active_master_ids()` — scope_rule + phase1_applicable Python helper
  - `check_mech_completion()` — SINGLE/DUAL 분기 + (c)안 phase=2 record-only 카운트
  - `get_mech_checklist()` — 73 항목 + scope_rule/trigger_task_id 응답
  - `upsert_mech_check()` — INPUT type 지원
- `_get_checklist_by_category()` SELECT 절에 `scope_rule` + `trigger_task_id` 추가 (TM/ELEC 응답에도 새 필드, 기존 키 무변경)
- `routes/checklist.py` MECH endpoints 3개: GET / PUT / GET status
- `task_service.py` `_trigger_mech_checklist_alert()` hook — UTIL_LINE_1/UTIL_LINE_2/WASTE_GAS_LINE_2 시작 시 `CHECKLIST_MECH_READY` alert
- `production.py` `_check_sn_checklist_complete()` MECH 분기 활성화

### 변경 (Refactor)
- `_check_tm_completion` → `check_tm_completion` rename (9 hits, private→public 일관 인터페이스): checklist_service 5 + production 2 + test_alert_all20 2

### 추가 (Test)
- `tests/backend/test_mech_checklist.py` 21 TC 신규 (+554 LoC):
  - `[A]` _normalize_qr_doc_id pure function 6 TC (DB 불필요)
  - `[B]` scope_rule + phase1 7 TC (all/tank_in_mech/DRAGON × 모델별 매핑)
  - `[C]` trigger_task_id 매핑 3 TC (Speed 4 / MFC+FS 7 / INLET 8)
  - `[D]` seed count 1 TC (51a 실파일 분포 자동 검증)
  - `[E]` rename gate 1 TC (rg "_check_tm_completion" = 0)
  - `[F]` phase=2 (c)안 2 TC (1차 record 미강제)
  - `[G]` WebSocket emit 1 TC (mock create_alert 호출 검증)
- 결과: **21/21 PASS** (186.84s)

### 검증
- pytest test_mech_checklist 21/21 PASS ✅
- rename gate `rg "_check_tm_completion" backend/ tests/` → 0 hits ✅
- syntax `ast.parse` 4 modified files OK ✅
- 회귀 영향: 0건 (신규 응답 필드 추가만, 기존 키 무변경)

### 정정 trail 11건 적용 (Codex 라운드 1+2+3 + 사용자 결정 4건)
- 라운드 1 (M=4 / A=2 / 추가 3): CLAUDE drift / rename grep / qr_doc_id normalizer / seed 총계+pytest / INLET 표 / enum / Python helper 통일
- 라운드 2 (M=3 / A=2 / N=1 / 추가 6): 핵심 통찰 "설계서 정정 ≠ 실코드 미구현" / atomic / silent failure / ELEC qr_doc_id 별 BACKLOG / models drift / lint hook / cross-repo
- 라운드 3 (M=3 / A=7 / N=8 / 추가 2): ALTER TYPE non-transactional 보증 (migration_runner autocommit=True 확인) / test 파일 경로 정정 / Pre-deploy Gate #7 신규
- 사용자 결정 v2: INLET S/N L/R 8 master 분리 (옵션 A 변형) / judgment_phase=2 (c)안 / BE/FE 분리 / Minor 3건

### 후속 Sprint (별 sprint, BE 배포 후 착수)
- Sprint 63-FE: `mech_checklist_screen.dart` 신규 (~1,000~1,200 LoC, 2~3d)
- AXIS-VIEW Sprint 39: BLUR 해제 + AddModal 토글 (~0.5d, 별 repo)

---

## [2.10.17] - 2026-05-01 — HOTFIX-09 access_log cleanup `get_db_connection` import 누락 (BE only, 1 line)

> Sprint 32 (v1.9.0, 2026-03-19) 도입 access_log cleanup cron 이 **43일간 매일 03:00 NameError silent failure**. 사용자 영향 0 (access_log 30 MB 누적, DB 한도 6%) but cleanup 자체 작동 0회.

### 사고 trail (Sentry 가치 입증 #4)

```
2026-03-19  Sprint 32 (v1.9.0) — _cleanup_access_logs cron 등록
              get_db_connection import 누락 → 매일 03:00 NameError
              ↓
2026-03-19 ~ 04-27  Sentry 미도입 → silent failure (40일)
              ↓
2026-04-27  Sentry 정식 활성화 (v2.10.8)
2026-04-28  03:00 cron 첫 capture
2026-04-29 ~ 05-01  4 events 누적
              ↓
2026-05-01  Sentry dashboard 우연 발견 → 본 fix
```

**확정 증거**: 4-29 측정 시 89,076 rows / 41일 누적 (3-19 ~ 4-29) — cleanup 한 번도 작동 안 했음.

### Fixed (BE only — import 1줄 추가)

- `backend/app/services/scheduler_service.py L1122 _cleanup_access_logs()`:
  - 함수 본체에 `from app.models.worker import get_db_connection` 1줄 추가
  - 다른 11개 함수 (L370/L418/L468/L654/L756/...) 와 동일 패턴 (lazy import)
  - docstring 에 HOTFIX-09 trail 추가

### 효과 (5-02 03:00 cron 부터)

```
다음 5-02 03:00 cron 실행 시:
  - 90일+ rows 삭제 대상 = 0건 (43일 누적이라)
  - 정상 작동 logger.info 출력
  
6-17 (3-19 + 90일) 이후:
  - 90일+ rows 삭제 시작 (정상 운영)
```

### Tests

- syntax check ✅
- 신규 TC 4개 (Codex Q4 advisory 보강 후, 5-01 동일일 commit 전 추가):
  - `test_cleanup_access_logs_imports_get_db_connection_correctly` — import 회귀 catch (mock patch)
  - `test_cleanup_access_logs_uses_90_days_interval` — v2.10.15 90일 retention 정적 검증
  - `test_cleanup_access_logs_full_flow_execute_commit_put_conn` — execute SQL + commit + put_conn 정상 흐름
  - `test_cleanup_access_logs_rollback_on_exception` — 예외 시 rollback + put_conn (예외 흡수)
- pytest 4/4 PASS (37.05s)

### Codex 라운드 1 합의 trail (5-01 사후 검토)

- Q1 (Severity S3): N (적정)
- Q2 (Proactive audit): **M** — `services/` 전체 grep audit + `_get_db_connection()` helper 통일 검토 → **별 BACKLOG `OBSERV-SCHEDULER-IMPORT-AUDIT-20260501` 등록**
- Q3 (lint pre-commit): **M** — flake8/pyflakes/ruff 도입으로 F821/E0602 차단 → **별 BACKLOG `INFRA-LINT-PRECOMMIT-HOOK-20260501` 등록**
- Q4 (TC 충분성): A → 본 commit 에서 TC 2개 → 4개로 보강 ✅
- Q5 (framing): A → "Sentry 가치 입증 #4" 보다 "Sprint 32 design/QA 부족 + Sentry 는 latent defect 탐지 layer" 가 정확. **결함 원인은 Sprint 32, Sentry 는 탐지 성공**
- Q6 (CHANGELOG sync): A → 본 commit 에서 "TC 없음" 표기 정정 ✅

### 정확한 framing — Sprint 32 design/QA 부족 + Sentry 탐지 성공

```
이전 latent defect 탐지 trail:
  #1 HOTFIX-07 (v2.10.9): row[0] KeyError 5일 silent → assertion 도입 첫 호출 시 즉시 노출
  #2 HOTFIX-08 (v2.10.10): db_pool transaction 정리 + 046a Docker artifact silent gap
  #3 v2.10.11 FIX-PROCESS-VALIDATOR-TMS-MAPPING: 4-22 silent failure 후속 Sentry 8h 자동 감지

본 사례 #4:
  결함 원인: Sprint 32 (3-19) design/QA 부족 — module-top import 또는 lazy import 표준 부재
  → 다른 11개 함수는 lazy import 사용 but _cleanup_access_logs() 만 누락
  → flake8/pyflakes pre-commit hook 부재 (lint-time F821 catch 가능했음)
  → 단위 test 부재 (43일간 한 번도 호출 안 됨 검증)

탐지 성공: Sentry layer 가 latent defect 를 4-28 부터 자동 capture
  → 사용자 영향 0 시점에 발견, 5-01 fix
```

### Deploy

- BE only (frontend version 만 동시 bump)
- Railway 자동 배포

### Related

- 사고 trail: 본 issue Sentry "[cleanup] Access log cleanup failed: name 'get_db_connection' is not defined" 4 events / 3 days
- v2.10.15 (FIX-ACCESS-LOG-RETENTION-90D) 가 사실상 효과 0 였음 (cleanup 자체 미작동) → 본 fix 후 정상 작동

---

## [2.10.16] - 2026-04-30 — FIX-DB-POOL-WARMUP-WATCHDOG (BE only, watchdog log 격상)

> **Sprint**: `FIX-DB-POOL-WARMUP-WATCHDOG-20260430`
> 4-29 23:31 ~ 4-30 09:30 사이 1.5h+ silent failure 사고 재발 방지. warmup cron 은 살아있는데 `_pool=None` 인 silent failure 가 `logger.debug` 로 묻혀 있던 사각지대 fix.

### 사고 배경

```
4-29 23:21 [pool_warmup] 5/5 conn warmed   ✅ 정상
4-29 23:26 [pool_warmup] 5/5 conn warmed   ✅ 정상
4-29 23:31 [pool_warmup] 0/0 conn warmed   ❌ silent 시작
... (1.5h+ 0/0 지속)
4-30 09:30 사용자 측 conn=2 측정으로 발견
```

### 원인

scheduler 가 도는 gunicorn worker 의 메모리 변수 `_pool` 이 None 으로 변환됨 (gunicorn worker 재시작 후 init_pool() 미호출 가능성). warmup cron 은 살아있어 5분마다 함수 호출 → `_pool is None` 분기 → `logger.debug(...)` → `return (0, 0)`. **Railway logs `--log-level=info` 라 미출력 + Sentry capture 안 됨** → silent failure.

### Fixed (BE only — 1줄 격상 + pid context)

- `backend/app/db_pool.py warmup_pool()` L266-268:
  - `logger.debug("[db_pool] warmup skipped — pool not initialized")` → `logger.error("[db_pool] warmup called but _pool=None — gunicorn worker pool died (pid=%d)", os.getpid())`
  - `LoggingIntegration(event_level=ERROR)` 가 자동 Sentry event capture (`__init__.py` L87) → Twin파파 1분 안에 알림
  - pid context 포함 — Worker A/B 어느 쪽이 죽었는지 식별

### Tests

- `tests/backend/test_db_pool.py`:
  - 신규 TC `test_warmup_logs_error_when_pool_none` — `_pool=None` 시 logger.error 호출 + 'gunicorn worker pool died' 메시지 검증
- pytest test_db_pool.py: **4/4 PASS** ✅ (신규 1 + 기존 3 회귀 0)

### LoC

- db_pool.py: 297 → 305 (+8 LOC, 1 분기 격상 + 주석)
- test_db_pool.py: ~70 → ~85 (+15 LOC, TC 1개)

### 효과 — silent failure 재발 방지

```
Before: warmup cron 0/0 출력 1.5h+ 지속 → 사용자 우연 발견
After:  warmup cron 0/0 발생 시점 logger.error → Sentry alert → 1분 안에 알림
```

### Codex 이관 미해당

단순 log level 격상 + Sentry 자동 capture (LoggingIntegration). 표준 패턴 (v2.10.13 동일).

### Deploy

- BE only (frontend version 만 동시 bump)
- Railway 자동 배포

### Related

- 사고 trail: 4-29 23:31 ~ 4-30 09:30 (1.5h+ silent)
- 후속 (선택): HOTFIX-06b per-worker warmup — Worker A/B 모두 자체 warmup + _pool=None 자동 재초기화 (영구 해결)

---

## [2.10.15] - 2026-04-29 — FIX-ACCESS-LOG-RETENTION-90D (BE only, 1줄)

> **Sprint**: `FIX-ACCESS-LOG-RETENTION-90D-20260429`
> Sprint 32 (v1.9.0, 2026-03-19) 도입 access log 30일 자동 삭제 정책을 90일로 완화. 분기 추세 분석 + 사고 사후 검증 윈도우 확보.

### Changed (BE only)

- `backend/app/services/scheduler_service.py`:
  - L1128 `INTERVAL '30 days'` → `INTERVAL '90 days'`
  - L111 주석 + L116 job name 동기 갱신

### 결정 근거

- 현재 (4-29 기준): 89,076 rows / 30 MB (table 14 + index 15) / 348 bytes/row / 일평균 ~2,144 rows
- 시뮬레이션 (90일): ~193,000 rows / **64 MB** — Railway Hobby plan 0.5 GB 한도 12.8% (무시 가능)
- 4-22 silent failure 5일 누적 사고 같은 사례에서 사후 1~2개월 분석 윈도우 확보 (이전 30일 부족)

### 회귀 위험 0

- 1줄 변경 (cron 빈도 동일, 삭제 조건만 완화)
- pytest 신규 TC 불필요 (행동 차이 자명)

### Deploy

- BE only — Railway 자동 배포

### Related

- BACKLOG: `FIX-ACCESS-LOG-RETENTION-90D-20260429` → COMPLETED (1줄 수정)

---

## [2.10.14] - 2026-04-28 — FIX-FACTORY-KPI-SHIPPED-V2.4 (BE only)

> **Sprint**: `FIX-FACTORY-KPI-SHIPPED-V2.4-AMENDMENT-20260428`
> Sprint 62-BE v2.2 의 `_count_shipped` 보정 — `shipped_plan` 의 si_completed AND 조건이 app SI 도입률 ≈0% 환경에서 무효 (W17 0 상수화) → OR 로 교정 + `shipped_ops` 폐기 + `shipped_best` 신설.

### Fixed (BE only — factory.py 단일)

#### `_count_shipped()` 재작성 (3 분기)

- **basis='plan'**: `INNER JOIN completion_status ... AND cs.si_completed=TRUE` 제거 → `LEFT JOIN app_task_details (task_id='SI_SHIPMENT') + WHERE (actual_ship_date IS NOT NULL OR t.completed_at IS NOT NULL)`
- **basis='ops'**: 분기 **제거** (app SI 100% 도입 후 ops=actual 수렴, 영구 무의미)
- **basis='best'**: 신규 — reality 경계 = `actual_ship_date IS NOT NULL` / 주간 귀속 = `COALESCE(DATE(t.completed_at), p.actual_ship_date)` (해석 A: si ⊆ actual, Pre-deploy Gate ③ 0건 검증 완료)
- ValueError 메시지: `'plan' | 'actual' | 'ops'` → `'plan' | 'actual' | 'best'`
- task_id `'SI_SHIPMENT'` 대문자 (Twin파파 검토 — 실 DB 값과 일치, OPS_API_REQUESTS.md v2.4 문서의 소문자 typo 정정)

#### weekly-kpi + monthly-kpi 응답 4곳 (`shipped_ops` → `shipped_best`)

- L457 weekly-kpi `_count_shipped` 호출
- L473 weekly-kpi 응답 dict
- L554 monthly-kpi `_count_shipped` 호출
- L566 monthly-kpi 응답 dict

### Tests (test_factory_kpi.py)

- 신규 클래스 `TestFactoryKpiV24Amendment` 3 TC:
  - `test_fk_v24_shipped_ops_field_removed_from_response` — 응답에 `shipped_ops` 부재 + `shipped_best` 존재 검증
  - `test_fk_v24_count_shipped_best_basis_smoke` — `basis='best'` 호출 스모크
  - `test_fk_v24_count_shipped_invalid_basis_raises` — `'ops'` (제거됨) + 임의 basis → ValueError + 메시지에 `plan | actual | best` 포함
- 기존 TC 갱신:
  - TC-FK-01 / TC-FK-03: 응답 키 `shipped_ops` → `shipped_best` (단순 교체)
  - TC-FK-07 / TC-FK-10: `_count_shipped` 직접 호출 `'ops'` → `'plan'` (force_closed 검증 의미 보존)
- 기존 TC skip 처리 (3건):
  - TC-FK-06 / TC-FK-09 / TC-FK-11: `@pytest.mark.skip` (사유: TC 본질이 v2.3 'ops' 분기의 +1 증가 검증, v2.4 에서 'ops' 제거 + fixture (SI_SHIPMENT INSERT only) 의 ship_plan_date / actual_ship_date 미설정 한계로 'plan'/'best' 분기 +1 시뮬레이션 불가, 운영 데이터 보존 정책 — UPDATE 금지). v2.4 핵심 거동은 신규 TestFactoryKpiV24Amendment 클래스로 이전.

### LoC

- factory.py: 562 → 575 (+13 LOC) — ⛔ God File 임계 미만이지만 500 초과 잔존 (별건 REFACTOR-FACTORY 추후 검토)
- test_factory_kpi.py: 435 → 511 (+76 LOC, 신규 TC 3개 + skip mark + 응답 키 갱신)

### Pre-deploy Gate (Twin파파 측 사전 검증 완료)

- ③ R-02 해석 A 반례 — `SELECT COUNT(*) ... WHERE task_id='SI_SHIPMENT' AND completed_at IS NOT NULL AND p.actual_ship_date IS NULL` → **0건** 확인 (해석 A 확정)

### Tests 요약

```
test_factory_kpi.py: 17 passed / 3 skipped / 0 fail (137.10s)
  ├─ 기존 14개 갱신 후 PASS
  └─ 신규 TestFactoryKpiV24Amendment 3개 PASS
```

### Codex 이관 미해당

OPS_API_REQUESTS.md v2.4 합의안 + 실 DB 값 검증 + Pre-deploy Gate 5종 명시 완료. Sprint 설계서 분석 단계에서 모든 결정 trail 보유.

### Deploy

- BE only (frontend version 만 동시 bump)
- Railway 자동 배포

### Post-deploy 검증 (예정)

- T+1h: 대시보드 W17 `shipped_plan` 0 → 수십대 (의도된 변화) + Sentry 새 ERROR 0
- T+24h: 3필드 `shipped_plan/actual/best` 정상 반환 + 회귀 0
- T+72h: R-02 해석 A 재검증 (반례 0건 유지) + FE Phase 2 (v1.35.0) 착수 가능 시점 도달

### Rollback (1 파일 atomic)

- git revert <commit-sha>
- v2.3 상태 복귀 (shipped_plan 0 상수화 재발 + shipped_ops 복원)
- 해석 A 가정 깨짐 시 (R-02 반례 발생): `_count_shipped basis='best'` WHERE 의 `p.actual_ship_date IS NOT NULL` 제거 + UNION 재도입 별건 hotfix

### Related

- 설계서: `AGENT_TEAM_LAUNCH.md` § FIX-FACTORY-KPI-SHIPPED-V2.4-AMENDMENT-20260428 (L33255+)
- BACKLOG: `FIX-FACTORY-KPI-SHIPPED-V2.4-AMENDMENT-20260428` → ✅ COMPLETED
- 후속: AXIS-VIEW Phase 2 (v1.35.0) — TEMP-HARDCODE 제거 + FactoryDashboardSettingsPanel + shipped_ops → shipped_best 타입 교체

---

## [2.10.13] - 2026-04-28 — Sentry garbage log 정리 2건 (BE only)

> **Sprint 묶음 배포**: `FIX-DB-POOL-DIRECT-FALLBACK-LOG-LEVEL-20260428` + `FIX-WEBSOCKET-STOPITERATION-SENTRY-NOISE-20260428`
> Sentry 대시보드 잡음 분리 → 진짜 ERROR 추적성 회복.

### Fixed (BE only — 4 파일)

#### Sprint 1 — db_pool direct conn fallback log level 강등 + counter

- `backend/app/db_pool.py`:
  - `_direct_fallback_count: int = 0` 모듈 변수 신설 + `get_direct_fallback_count()` getter 추가
  - L171-173 `logger.error("All pool connections unusable, ...")` → `logger.warning(... cumulative fallback=%d)` 강등 + counter 증가
  - 의미론 정합 (fallback 자체는 의도된 안전망 → warning 적정)
- `tests/backend/test_db_pool.py` 신규 (+~60 LOC, TC 3개):
  - `test_fallback_increments_counter` — 3 retry 모두 unusable → counter 증가 + warning level
  - `test_normal_path_no_counter_increment` — 정상 conn 획득 시 무변화
  - `test_pool_exhausted_does_not_increment_fallback_counter` — exhausted 경로는 별도 (counter 분리)
- 효과: Sentry `[db_pool] All pool connections unusable` issue (16h 22 events) 동결, ERROR level 미발생

#### Sprint 2 — flask-sock wsgi StopIteration Sentry 필터

- `backend/app/__init__.py`:
  - `_sentry_before_send(event, hint)` 모듈 top-level 함수 신설 (~30 LOC)
  - 매칭 조건 3개 모두 성립 시 `None` 반환 (drop): `exc_type='StopIteration'` + `mechanism.type='wsgi'` + `transaction='websocket_route'`
  - try/except 안전 fallback (필터 자체 실패 시 정상 capture)
  - `sentry_sdk.init()` 에 `before_send=_sentry_before_send` 등록
- `tests/backend/test_sentry_filter.py` 신규 (+~50 LOC, TC 4개):
  - `test_filters_websocket_stopiteration` — 3 조건 매칭 시 drop
  - `test_passes_other_transaction_stopiteration` — 다른 transaction 의 StopIteration 정상 전달
  - `test_passes_non_stopiteration_at_websocket` — websocket_route 의 다른 exception 정상 전달
  - `test_safe_on_malformed_event` — 이상한 event 구조 안전 fallback
- 효과: Sentry PYTHON-FLASK-2 issue (16h 302 events / Escalating) 동결, 정상 종료 시그널 분리

### Tests

- pytest tests/backend/test_db_pool.py: 3/3 PASS ✅
- pytest tests/backend/test_sentry_filter.py: 4/4 PASS ✅
- 총 7/7 PASS (0.09s, 회귀 0건)

### LoC

- db_pool.py: 286 → 297 (+11 LOC) — 🟢 500 미만 Pass
- __init__.py: ~190 → ~225 (+35 LOC) — 🟢 500 미만 Pass

### Codex 이관 미해당

두 Sprint 모두 표준 패턴 (log level 강등 + counter / Sentry SDK before_send hook). Sprint 설계서에서 분석 완료, Codex 이관 불필요.

### Deploy

- BE only (frontend version 만 동시 bump)
- Railway 자동 배포

### Post-deploy 검증 (예정)

- T+1h: Sentry 본 issue 2건 events 카운트 증가 멈춤 (22 / 302 동결)
- T+24h: 다른 issue 정상 capture 확인 (PYTHON-FLASK-1 4-22 enum cast / PYTHON-FLASK-4 TMS mapping 후속)
- T+7d: 본 Sprint 효과 정량 입증 → COMPLETED
- Railway logs `cumulative fallback=N` 추세 → 별건 OBSERV-WARMUP-INTERVAL-TUNE 우선순위 결정

### Rollback (4 파일 atomic)

- git revert <commit-sha>
- 부분 revert 안전 (각 Sprint 독립 작동)
- 영향 범위 0 (잡음 분리 only, 비즈니스 로직 무관)

### Related

- Sprint 1: `AGENT_TEAM_LAUNCH.md` § FIX-DB-POOL-DIRECT-FALLBACK-LOG-LEVEL-20260428 (L32942+)
- Sprint 2: `AGENT_TEAM_LAUNCH.md` § FIX-WEBSOCKET-STOPITERATION-SENTRY-NOISE-20260428 (L33255+)

---

## [2.10.12] - 2026-04-28 — FIX-26 DURATION_WARNINGS 응답 키 일관성 (BE only)

> **Sprint**: `FIX-26-DURATION-WARNINGS-FORWARD-20260428`
> 4-22 등록 BACKLOG L362 `BUG-DURATION-VALIDATOR-API-FIELD` 본격 fix. 4-28 FIX-PROCESS-VALIDATOR-TMS-MAPPING (v2.10.11) 회귀 시 동일 fail 재출현 → Codex 라운드 2 A 합의 (별건 확정) → 본 Sprint 진행.

### Fixed (BE only — 응답 키 contract 일관성)

#### 1. `task_service.py` L497-499 — unconditional 응답 키

- Before: `if duration_warnings: response['duration_warnings'] = duration_warnings` (조건부 키)
- After: `response['duration_warnings'] = duration_warnings` (항상 키 존재, 빈 리스트 [] 라도)
- API 계약 명확화: FE 가 `data.duration_warnings` 안전 접근 가능

#### 2. `work.py` L265-266 — default fallback forward

- Before: `if 'duration_warnings' in response: result['duration_warnings'] = response['duration_warnings']`
- After: `result['duration_warnings'] = response.get('duration_warnings', [])`
- 방어적 forward — task_service / work.py 양 끝 모두 보장 (옵션 C 채택)

### Tests (test_duration_validator.py)

- `test_normal_duration_no_warnings` L75-76: `assert 'duration_warnings' not in data` → `assert 'duration_warnings' in data; assert data['duration_warnings'] == []` (신 계약 정합)
- 신규 클래스 `TestDurationWarningsAlwaysPresent::test_normal_completion_returns_empty_duration_warnings` 추가 — 정상 완료 시 빈 리스트 반환 검증
- `TestReverseDuration::test_reverse_completion` `@pytest.mark.skip` 추가 — 사유: 시작/종료 timestamp 서버 자동 기록 (`task_service.py:146/256` `datetime.now(Config.KST)`), 운영 발생 불가 (prod 0건 실측, 4-04~4-28 24일 누적). REVERSE_COMPLETION 은 서버 시계 NTP jump back / SQL 직접 조작 / timezone 버그 같은 인프라 사고에서만 발생하는 방어적 안전망

### LoC 변경

| 파일 | Before | After | 차이 |
|---|---:|---:|---:|
| task_service.py | 1486 | 1486 | ±0 (조건부 → unconditional) |
| work.py | (이전) | (동일) | -1/+1 (조건부 → default get) |
| test_duration_validator.py | 246 | 308 | +62 (skip mark + 신규 TC) |

### 사용자 영향 0 — silent failure 우려는 무의미

본 Sprint 검토 중 "Sprint 55 multi-worker early return path 가 silent failure 일으키는가" 우려 제기됐으나:
- 시작/종료 timestamp 서버 `datetime.now()` 자동 기록 → 클라이언트 시간 입력 path 0
- prod 실측: REVERSE_COMPLETION 발생 0건 (24일 누적)
- 대시보드 Rollback 키로 사후 복구 메커니즘 별도 존재
- 시나리오 자체가 인프라 사고 차원

→ 별건 BACKLOG 등록 불필요 (P3 INFO 수준 이하). 본 Sprint 는 응답 contract 일관성만 fix 하고 종결.

### Codex 합의 trail

- 라운드 2 (2026-04-28, FIX-PROCESS-VALIDATOR-TMS-MAPPING 후속): Q1/Q2 모두 A — `duration_warnings` 키 누락은 응답 키 생성 경로의 4-22 부터 누락된 별건 확정. v2.10.11 회귀 0건. v2.10.12 별도 Sprint 처리.

### Deploy

- BE only (frontend version 만 동시 bump)
- Railway 자동 배포

### Rollback (3 파일 atomic)

- git revert <commit-sha> → 3 파일 원복
- Railway 자동 재배포 ~1분
- 부분 revert 안전 (각 파일 독립 작동)

### Related

- 설계서: `AGENT_TEAM_LAUNCH.md` § FIX-26-DURATION-WARNINGS-FORWARD-20260428 (L32717+)
- BACKLOG: L362 `BUG-DURATION-VALIDATOR-API-FIELD` → COMPLETED

---

## [2.10.11] - 2026-04-28 — FIX-PROCESS-VALIDATOR-TMS-MAPPING (옵션 D-2, BE only)

> **Sprint**: `FIX-PROCESS-VALIDATOR-TMS-MAPPING-20260428`
> 4-22 HOTFIX-ALERT-SCHEDULER-DELIVERY 의 표준 패턴이 duration_validator 3곳에 미적용 → TMS 매니저 알람 미수신 (silent failure 매시간 ~10건). Sentry 도입 8h 만에 자동 감지 → 30분 fix.

### Fixed (BE only — 5 파일 atomic refactor)

#### 1. `process_validator.py` (+30 LOC) — 표준 함수 신설

- `_CATEGORY_PARTNER_FIELD` dict 신설 (`'TMS':'module_outsourcing'/'MECH':'mech_partner'/'ELEC':'elec_partner'`)
- `resolve_managers_for_category(serial_number, category)` public 함수 — partner-based / role-based 자동 분기
- 4-22 HOTFIX 의 scheduler private 함수 패턴을 process_validator 로 이전 + public 화 (DRY)

#### 2. `scheduler_service.py` (-15 LOC) — private 함수 + dict 제거 + import 교체

- `_resolve_managers_for_category` 함수 + `_CATEGORY_PARTNER_FIELD` dict 제거
- `from app.services.process_validator import resolve_managers_for_category` 추가
- 3 호출 site (L921 / L1021 / L1110) `_resolve_managers_for_category` → `resolve_managers_for_category` 1:1 교체

#### 3. `task_service.py` (±0 LOC) — Codex M2 누락 발견된 5번째 파일

- L403: `from app.services.scheduler_service import _resolve_managers_for_category` → `from app.services.process_validator import resolve_managers_for_category`
- L410: 호출 1줄 1:1 교체
- ORPHAN_ON_FINAL alert (Sprint 61-B) 경로

#### 4. `duration_validator.py` (±0 LOC) — 본 Sprint 핵심 fix 대상

- L16 import: `get_managers_for_role` → `resolve_managers_for_category`
- L74 (REVERSE_COMPLETION) / L100 (DURATION_EXCEEDED) / L179 (UNFINISHED_AT_CLOSING):
  - Before: `get_managers_for_role(task.task_category)` → SQL `WHERE role='TMS'` → enum cast 실패 → silent skip
  - After: `resolve_managers_for_category(sn, category)` → module_outsourcing 매니저 정상 도착

#### 5. `tests/conftest.py` (+50 LOC) — Codex M1 옵션 D 격리 fixture

- `seed_test_managers_for_partner` — TEST_WORKERS 의 partner worker (FNI/BAT/TMS(M)/TMS(E)/P&S/C&A) 일시 매니저 promote
- teardown 명시적 원복 (`name != 'GST관리자'` 보호 조건) → 다른 테스트 영향 0

#### 6. `tests/backend/test_process_validator.py` (+130 LOC) — TC 7개

- TestResolveManagersForCategory 6 TC: TMS-GAIA partner / TMS-DRAGON 회귀 / MECH partner / ELEC partner / PI role fallback / unknown empty
- e2e TC 1개 (Codex A2 흡수): `test_duration_validator_tms_alert_creation_e2e` — `validate_duration()` 직접 호출 + alert_logs INSERT 검증

### LoC 변경 (Line 규칙 모두 통과 ✅)

| 파일 | Before | After | 차이 |
|---|---:|---:|---:|
| process_validator.py | 259 | 289 | +30 (🟢 500 미만) |
| scheduler_service.py | 1153 | 1138 | **-15** (⛔ God File 잔존, LoC 감소) |
| task_service.py | 1486 | 1486 | ±0 (⛔ God File 잔존, mechanical 1:1) |
| duration_validator.py | 204 | 204 | ±0 (🟢 import 1줄 + 호출 3곳 1:1) |

→ "🔴 새 로직 추가 금지" 규정 우회 (scheduler/task_service 모두 LoC 감소 또는 ±0). REFACTOR-SCHEDULER-SPLIT 의 부분 선행 효과.

### Tests

- pytest 신규 TC: **7/7 PASS** ✅
- pytest 회귀 (test_scheduler / test_scheduler_integration / test_task_seed): **51 passed / 5 skipped / 0 fail** ✅
- 1건 무관 fail: `test_duration_validator.py::TestReverseDuration::test_reverse_completion` — BACKLOG L362 `BUG-DURATION-VALIDATOR-API-FIELD` (4-22 기존 별건). **Codex 라운드 2 (2026-04-28) Q1/Q2 모두 A 라벨 합의** — 본 Sprint 응답 키 생성 경로 (duration_validator → task_service → work.py) 영향 0, 별도 Sprint 처리

### Codex 합의 기록

- **라운드 1 (Sprint 설계 검증)**: M=2 / A=2 / N=2 — M1 fixture 정합성 (옵션 D 격리 fixture) + M2 Rollback 5 파일 (task_service.py L403-410 누락 발견) + A1 DRAGON gap (별건 BACKLOG `BUG-DRAGON-TMS-PARTNER-MAPPING-20260428`) + A2 e2e 회귀 TC. 모두 반영
- **라운드 2 (pytest 회귀 라벨링)**: Q1/Q2 모두 A — 본 Sprint 회귀 0건 + BUG-DURATION-VALIDATOR-API-FIELD 별건 확정

### Deploy

- BE only (frontend version 만 동시 bump)
- 배포: Railway 자동 (git push origin main)
- Production: https://axis-ops-api.up.railway.app

### Post-deploy 검증 (예정)

- 즉시 (1h): Sentry PYTHON-FLASK-4 issue events 카운트 증가 멈춤 확인 (31 → 정착)
- 매시간 정각 (UTC) 7번: TMS / MECH / ELEC / PI 매니저 도달 회귀 검증
- D+7 종합: Sentry events 31 그대로 → COMPLETED 판정

### Rollback (5 파일 atomic)

```
git revert <commit-sha>   # 5 파일 동시 원복
→ Railway 자동 재배포 ~1분
부분 revert 절대 금지 (ImportError → 앱 boot 실패 → 503 폭주 위험)
```

### Related

- 설계서: `AGENT_TEAM_LAUNCH.md` L32249 FIX-PROCESS-VALIDATOR-TMS-MAPPING-20260428
- BACKLOG: L352 (본 Sprint, COMPLETED) / L353 (BUG-DRAGON-TMS-PARTNER-MAPPING 후속) / L362 (BUG-DURATION-VALIDATOR-API-FIELD 별건)
- 메타 가치: assertion + Sentry layer 가치 입증 #3 (memory.md ADR-019)

---

## [2.10.10] - 2026-04-27 — HOTFIX-08 db_pool transaction 정리 누락 + 046a 자동 적용 (BE only)

> **HOTFIX-08** — v2.10.9 배포 후 Railway log 에 `046a_elec_checklist_seed.sql 실행 실패: set_session cannot be used inside a transaction` 발생. assertion 자동 감지 layer 가 두 번째 잠재 버그 (db_pool transaction 정리 누락 + 046a silent gap) 사용자 영향 0 시점에 발견.

### Fixed

- **`backend/app/db_pool.py _is_conn_usable()`** — SELECT 1 실행 후 `conn.rollback()` 추가:
  - psycopg2 default `autocommit=False` → SELECT 도 BEGIN 자동 시작 → INTRANS 상태로 풀 반납
  - 이 conn 을 받아 `m_conn.autocommit=True` 시도 시 `set_session cannot be used inside a transaction` 거부 (migration_runner 사례)
  - 동일 SELECT 1 검증 패턴인 `warmup_pool()` 에도 동일 1줄 (총 2곳)

### Side Effect (긍정)

- **046a_elec_checklist_seed.sql 자동 적용** — 4-22 049 와 동일한 Docker artifact silent gap 사례로 추정. `ON CONFLICT DO NOTHING` idempotent 보장으로 prod 31항목 안전 재적용. 사용자 영향 0.

### Tests

- pytest 회귀 0건
- Railway log 검증: `[migration] ✅ 046a_elec_checklist_seed.sql 실행 완료` + `[migration-assert] ✅ sync OK (13 migrations applied)` (12 → 13 갱신)

### Deploy

- BE only — Railway 자동 (git push origin main)
- git commit: `72579e1`

### Related

- assertion 자동 감지 layer 가치 입증 trail: 도입 당일 잠재 버그 2건 발견 (HOTFIX-07 row[0] + HOTFIX-08 transaction 정리)

---

## [2.10.9] - 2026-04-27 — HOTFIX-07 RealDictCursor row[0] KeyError 긴급 복구 (BE only)

> **HOTFIX-07** — v2.10.8 배포 직후 `assert_migrations_in_sync()` 첫 호출 시 worker boot 503 발생. assertion 자체 도입이 5일 누적된 silent 버그를 즉시 노출시킨 사례 (assertion 가치 1차 입증).

### Fixed

- **`backend/app/migration_runner.py _get_executed()`** L51 — `row[0]` → `row['filename']`:
  - `db_pool` 이 `RealDictCursor` 사용 → row 가 dict-like → `row[0]` 은 `KeyError: 0`
  - 이전 `run_migrations()` 의 outer try/except 가 silent 흡수 → 5일간 무인지
  - v2.10.8 의 `assert_migrations_in_sync()` 는 try/except 없이 호출 → KeyError 가 그대로 propagate → gunicorn worker boot 실패 → 503
- **`backend/app/migration_runner.py assert_migrations_in_sync()`** L165+ — outer try/except 안전망 추가:
  - assertion 자체 실패가 worker boot 막지 않도록 (HOTFIX-07 같은 사고 예방)
  - 실패 시 `logger.error(exc_info=True)` + `sentry_sdk.capture_exception(e)` (best-effort)

### Tests

- pytest 회귀 0건
- Railway log: worker boot 정상화, `[migration-assert] ✅ sync OK (12 migrations applied)` 정상 출력

### Deploy

- BE only — Railway 자동 (git push origin main)

### Lesson

- **assertion 도입 자체가 사고 발견 trigger 가 됨** — 5일간 silent 흡수된 row[0] KeyError 가 try/except 없는 호출 경로에서 즉시 노출. 향후 신규 assertion 도입 시 outer try/except 안전망 표준화 권장.

---

## [2.10.8] - 2026-04-27 — 알람 시스템 사후 검증 마무리 3건 (BE only)

> **Sprint**: OBSERV-RAILWAY-LOG-LEVEL-MAPPING + POST-REVIEW-MIGRATION-049-NOT-APPLIED + OBSERV-ALERT-SILENT-FAIL
> 4-22 발생 알람 silent failure (5일간 52건 NULL) 의 사후 검증 마무리. 외부 자동 감지 layer (Sentry) + log level 정확화 + migration sync assertion 도입.

### Changed (BE only — 인프라 강화)

#### 1. OBSERV-RAILWAY-LOG-LEVEL-MAPPING (Sentry alert rule 선행 조건)

- **`backend/app/__init__.py`**:
  - `import sys` 추가
  - `logging.basicConfig(... stream=sys.stdout, force=True)` 명시 (기본 stderr 금지)
- **`backend/Procfile`**:
  - gunicorn `--access-logfile=- --log-level=info` 추가
- 효과: Python `logger.info()` 호출이 Railway 에서 'error' level 로 잘못 태깅되던 문제 해소. Sentry alert rule 의 `level=error` 필터 정확 작동.

#### 2. OBSERV-ALERT-SILENT-FAIL (Sentry 정식 연동)

- **`backend/requirements.txt`**: `sentry-sdk[flask]>=2.0` 추가
- **`backend/app/__init__.py`**: `_init_sentry()` 함수 신규 (~50 LOC)
  - DSN env 없으면 graceful skip (로컬/test 환경 호환)
  - `FlaskIntegration` + `LoggingIntegration` (INFO breadcrumb / ERROR event capture)
  - `release` 자동 binding (version.py)
  - `send_default_pii=False` (PII 보호)
  - 환경변수: `SENTRY_DSN` (필수), `SENTRY_ENVIRONMENT` (기본 production), `SENTRY_TRACES_SAMPLE_RATE` (기본 0.0)
- **`backend/app/migration_runner.py`**: 실패 시 `sentry_sdk.capture_exception(e)` 추가
- 효과: scheduler 죽음 / migration 실패 / target_worker_id NULL 다발 등 silent failure 외부 자동 감지

#### 3. POST-REVIEW-MIGRATION-049-NOT-APPLIED + OBSERV-MIGRATION-RUNNER-STARTUP-ASSERTION

- **`backend/app/migration_runner.py`** `assert_migrations_in_sync()` 함수 신규 (~40 LOC):
  - disk(코드) vs DB(`migration_history`) 동기화 검증
  - `not_yet_applied` 발견 시 logger.error + `sentry_sdk.capture_message`
  - 4-22 049 미적용 사례 같은 silent gap 즉시 외부 알림
- **`backend/app/__init__.py`**: `run_migrations()` 직후 `assert_migrations_in_sync()` 호출
- **신규 산출물**: `POST_MORTEM_MIGRATION_049.md` — 4가지 가설 검증 (가설 ④ "Docker artifact / Railway build cache" 가장 유력) + 재발 방지 권장 3건

### Twin파파 측 작업 (배포 후)

1. **Sentry 가입 + project 생성**:
   - https://sentry.io 가입
   - "Create Project" → Platform: Python → Framework: Flask
   - DSN 발급 (예: `https://abc123@o123.ingest.sentry.io/456`)
2. **Railway env 추가**:
   ```
   SENTRY_DSN = <발급받은 DSN>
   SENTRY_ENVIRONMENT = production  (선택, 기본 production)
   SENTRY_TRACES_SAMPLE_RATE = 0.0  (선택, performance tracing OFF)
   ```
3. **Sentry alert rule 설정** (Sentry Dashboard):
   - Issues → Alert rules
   - Rule: `level == error AND message contains "[migration-assert]" or "[scheduler]"` → 즉시 알림
4. **검증**:
   - Railway logs: `[sentry] initialized (env=production, release=2.10.8)`
   - Railway logs: `[migration-assert] ✅ sync OK (12 migrations applied)`
   - Sentry test event 자동 발송 확인

### Tests

- pytest test_scheduler.py 8 passed / 1 skipped / 회귀 0건 ✅ (logging 변경 영향 0)
- BE syntax check (init/migration_runner) ✅

### Codex 이관 미해당

- LOG-LEVEL: 코드 ~10 LOC (인프라 설정 only)
- POST-REVIEW: 분석 보고서만 (코드 변경 분리)
- SENTRY: 코드 ~90 LOC, 인증/스키마/API 무관 + 1파일 수준

→ Codex 이관 체크리스트 6항목 미충족. Claude Code 자체 검토 + pytest 회귀 충분.

### Deploy

- BE only (frontend 변경 0)
- 배포: Railway 자동 (git push origin main)
- Production: https://axis-ops-api.up.railway.app (BE)
- Sentry DSN 설정은 Twin파파 측 별도 (위 작업 1~2번)

### Rollback

- LOG-LEVEL: `__init__.py` + Procfile git revert
- SENTRY: `__init__.py` + `requirements.txt` git revert (또는 `SENTRY_DSN` env 제거로 graceful skip)
- migration assertion: `__init__.py` 호출 + `migration_runner.py` 함수 git revert

### Related

- 설계 상세: 본 commit + `POST_MORTEM_MIGRATION_049.md`
- 4-22 사건 trail: `BACKLOG.md` L319 (HOTFIX-ALERT-SCHEMA-RESTORE), L324 (POST-REVIEW), L333 (POST-REVIEW-MIGRATION-049-NOT-APPLIED)

---

## [2.10.7] - 2026-04-27 — HOTFIX-06 warmup_pool() 시계 리셋 누락 수정 (사후 보충)

> ⚠️ **사후 보충 entry** (2026-04-27 정리). v2.10.7 commit 시 CHANGELOG 추가 누락.

### Fixed

- **`backend/app/db_pool.py warmup_pool()`** L240+ — `_conn_created_at[id(conn)] = time.time()` 1줄 추가:
  - v2.10.6 OBSERV-DB-POOL-WARMUP 배포 후 결함 발견: warmup 외형상 작동하지만 SELECT 1 만 실행하고 시계 리셋 안 함 → `_is_conn_usable()` 가 expired 판정 → discard → direct conn fallback
  - 동일 파일 내 `_create_direct_conn() L112`, `get_conn() L154-155` 의 검증된 패턴 그대로 적용 (명백한 누락 정정)

### Tests

- pytest test_scheduler.py 8 passed / 1 skipped / 회귀 0건 (327.32s)

### Deploy

- BE only — Railway 자동 (git push origin main)
- git commit: `7a13085`

### Limitation (per-worker 함정)

본 fix 는 fcntl lock 으로 1 worker (Worker A) 만 scheduler 실행 → Worker A 의 pool 만 시계 리셋. **Worker B 의 pool 은 자연 만료**. 결과: conn 7~11 진동 (영구 10 의도는 절반 달성). 사용자 영향 0 입증 후 D+1 측정 결과 따라 v2.10.8 HOTFIX-06b (각 worker 자체 warmup) 진행 결정.

### Related

- v2.10.6 OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP 후속
- 별건 잠재 BACKLOG: HOTFIX-06b (per-worker warmup, D+1 측정 후 결정)

---

## [2.10.6] - 2026-04-27 — FEAT-PIN-STATUS-BACKEND-FALLBACK + OBSERV-DB-POOL-WARMUP

> **PIN 자동 복구 (FE) + DB Pool warmup (BE) 병행 배포**.
> FIX-PIN-FLAG v2.10.5 (1차 보호) + 본 v2.10.6 의 backend fallback (2차 보호) 으로 PIN 손실 사용자 자동 복구. 동시에 실측으로 입증된 MIN=5 무효 문제 (10:14→10:24 conn 10→9→7) 도 warmup cron 으로 해결.

### Added (FE — FEAT-PIN-STATUS-BACKEND-FALLBACK-20260427, P1 격상)

- **`frontend/lib/services/auth_service.dart`** `getBackendPinStatus()` 신규 (~15 LOC):
  - `/auth/pin-status` (BE 엔드포인트, JWT 보호) 호출 → `{"pin_registered": bool}` 응답 파싱
  - 호출 실패 (네트워크/서버) 시 `false` 반환 → 정상 흐름 fallback (debugPrint 로그)
- **`frontend/lib/main.dart`** L275~ 라우팅 분기 추가 (~16 LOC):
  - `tryAutoLogin()` 성공 후 `getBackendPinStatus()` 호출
  - `pin_registered=true` → `savePinRegistered(true)` 로 로컬 양방향 sync 복구 + PinLoginScreen 으로 진입
  - `pin_registered=false` → 정상 흐름 (마지막 경로 복원, HomeScreen)
- 효과: PIN 사용자가 로컬 storage 잃어도 (IndexedDB 손실 시) backend 가 진실의 source 로 자동 복구 → 사용자 보안 의도 유지

### Added (BE — OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP-20260427, P2)

- **`backend/app/db_pool.py`** `warmup_pool() -> tuple[int, int]` public 함수 신규 (~40 LOC):
  - `_MIN_CONN` 만큼 `getconn()` → `SELECT 1` → `putconn()`
  - 모든 idle conn 의 `max_age` 시계 리셋 → MIN 강제 유지
  - finally 블록으로 반납 보장
  - Claude Code advisory 1차 A1 반영 (private `_pool` 직접 import 회피, public API 노출)
- **`backend/app/services/scheduler_service.py`** L17, L23 import 추가 (`IntervalTrigger`, `warmup_pool`):
  - `_pool_warmup_job()` 신규 함수 (warmup_pool 호출 + 결과 로그)
  - `add_job` 등록 — `IntervalTrigger(minutes=5)` + `next_run_time=datetime.now(Config.KST) + timedelta(seconds=10)` (timezone-aware, A5 반영)
  - 스케줄러 job 수: **11 → 12**

### 실측 데이터 (OBSERV-WARMUP 트리거 근거)

```
2026-04-27 KST (DB_POOL_MIN=5, DB_POOL_MAX=30, max_age=300s):
  10:14:00  풀 초기화 직후     OPS 10 conn (5×2 worker)  baseline
  10:19:00  5분 경과            OPS  9 conn (-1)          max_age 1차 만료
  10:24:00  10분 경과           OPS  7 conn (-3)          감소 가속
```

→ Codex 라운드 3 A4 advisory ("MIN=5 효과는 max_age 만료 직전~직후 변동 가능, 실측 필요") 가 10분만에 실측으로 입증.

### Claude Code advisory 1차 (M=0 / A=5, OBSERV-WARMUP)

| # | Advisory | 반영 |
|:---:|:---|:---|
| A1 | `_pool` private API 직접 import → public `warmup_pool()` 노출 권장 | ✅ db_pool.py 에 public 함수 추가 |
| A2 | pytest TC test env `_pool=None` skip 처리 명시 | ✅ warmup_pool 자체에서 None 처리 |
| A3 | `IntervalTrigger` 명시 import 권장 | ✅ scheduler_service.py L17 |
| A4 | ThreadPool max=10 - warmup 5 = 여유 5 (burst 차단 위험 낮음) | ✅ 위험 평가 완료 |
| A5 | `next_run_time=datetime.now()` → timezone 명시 권장 | ✅ `Config.KST` 적용 |

### Codex 이관 여부

- **FEAT-PIN-STATUS-BACKEND-FALLBACK**: ❌ 6항목 미충족 (FE 2파일 + main.dart 분기 추가만, 인증 흐름은 `getBackendPinStatus` 호출 추가 + `savePinRegistered(true)` 호출 — 인증 로직 신규 X). FIX-PIN-FLAG v2.10.5 의 후속이라 같은 검토 컨텍스트.
- **OBSERV-DB-POOL-WARMUP**: ❌ 6항목 미충족 (BE 1함수 신규 + scheduler 1 job 추가). Claude Code 자체 검토만으로 진행.

### Tests

- `tests/backend/test_scheduler.py` 8 passed / 1 skipped / 회귀 0건 ✅
- BE syntax check (db_pool.py + scheduler_service.py) ✅

### Deploy

- 빌드: flutter build web --release ✓ 12.1s
- 배포 (FE): Netlify Deploy ID `69eef28fca3b7ffce577068d` (2026-04-27 KST)
- 배포 (BE): Railway 자동 (git push origin main)
- Production URL: https://gaxis-ops.netlify.app

### Post-deploy 검증

#### Railway logs (배포 직후)

```
[scheduler] Scheduler initialized with 12 jobs   ← 11 → 12 확인
[pool_warmup] 5/5 conn warmed                    ← 10초 후 첫 실행
```

#### 1시간 관찰 (`pg_stat_activity`)

매 5분마다 conn 수 측정 → **10 영구 유지** = 성공. 7 이하로 감소 시 Phase C (warmup 효과 미진).

### 신규 BACKLOG 갱신

- `FEAT-PIN-STATUS-BACKEND-FALLBACK-20260427` 🔴 P1 → ✅ COMPLETED (v2.10.6)
- `OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP-20260427` 🟡 P2 → ✅ COMPLETED (v2.10.6)
- `AUDIT-PWA-SW-INDEXEDDB-PRESERVE-20260427` 🟡 P2 (대기, 30분 audit)
- `UX-LOGIN-FALLBACK-PIN-RESET-LINK-20260427` 🟢 P3 (대기)
- `FEAT-AUTH-STORAGE-MIGRATION-FULL-20260427` 🟡 P2 (대기, 보안 trade-off 검토)

### Rollback

- FEAT-PIN-STATUS: `main.dart` + `auth_service.dart` git revert → flutter build → Netlify
- OBSERV-WARMUP: `db_pool.py` + `scheduler_service.py` git revert → Railway 자동 재배포 (~1분)
- 둘 다 부수 효과 없음

### Related

- 설계 상세: `AGENT_TEAM_LAUNCH.md`
  - FEAT-PIN-STATUS-BACKEND-FALLBACK-20260427 섹션 (L31772+)
  - OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP-20260427 섹션 (L32002+)
- 별건 (관찰 중): `FIX-DB-POOL-MAX-SIZE-20260427` Phase B (D+0 ~ D+3 화/수/목)

---

## [2.10.5] - 2026-04-27 — FIX-PIN-FLAG-MIGRATION-SHAREDPREFS

> **PIN 등록 플래그 storage 안정화** — `pin_registered` 를 SecureStorage (IndexedDB) → SharedPreferences (localStorage) 양방향 sync 이전. 4 라운드 advisory review (Claude Code 1차 + Codex 1차 — M 8건 + 추가 리스크 2건 전수 반영) 후 적용.

### Changed

- **`frontend/lib/services/auth_service.dart`** L20, L243-360 — `pin_registered` 플래그 양방향 sync 패턴 적용:
  - `hasPinRegistered()`: SharedPrefs 우선 read, fallback SecureStorage + 자동 sync (양방향, SecureStorage 유지 — rollback 안전)
  - `savePinRegistered()`: SharedPrefs 주 저장소 + SecureStorage best-effort try/catch (atomic 보장 불가 → non-fatal 로 처리, debugPrint 로그)
  - `logout()` (L243): SharedPrefs `pin_registered` 도 정리 (양방향 cleanup)
- `package:flutter/foundation.dart` import 추가 (debugPrint 사용)

### 부수 변경

- **`frontend/lib/screens/home/home_screen.dart`** — 알림 화면에서 돌아올 때 `alertProvider.refreshUnreadCount()` 호출 (배지 카운트 동기화). FIX-PIN-FLAG 와 무관한 별건 개선, 같은 commit 에 포함.

### 4 라운드 advisory trail (M=8/8 + 추가 리스크 2/2 반영)

- **Claude Code 1차** (사전 자체 검증, 6건):
  - A1 인증 로직 영향 → Codex 이관 결정
  - A2 connection 인과 정량 입증 부재 → baseline SQL 3종 추가
  - A3 ⛔ 단방향 마이그레이션 시 rollback 위험 → 양방향 sync 채택
  - A4 `savePinRegistered()` 양방향 write 패턴
  - A5 race condition (낮은 위험)
  - A6 IndexedDB 손실 trigger 정확성

- **Codex 1차** (M=8 / 추가 리스크 2):
  - M1/Q1.a atomic 보장 불가 → best-effort try/catch + 로그 명시
  - M2/Q3.f baseline SQL `request_path` LIKE 패턴 정정
  - M3/Q4.i SW 업데이트 ≠ IndexedDB 손실 정정
  - Q2.d Rollback 표 5번째 케이스 (SharedPrefs 'true' + SecureStorage write 실패)
  - Q2.e Cohort 정의 (cohort_A/B + secure_write_ok/fail)
  - Q3.g 다른 가설 구분 cohort (device_id, UA, 시간대)
  - Q3.h D+7 통계 신뢰성 (3일 pre/post + active worker 정규화)
  - Q4.j iOS Safari localStorage 도 영향
  - 추가 리스크 1: refresh_token + worker_id + worker_data 도 SecureStorage → BACKLOG `FEAT-AUTH-STORAGE-MIGRATION-FULL` 신규
  - 추가 리스크 2: backend `/auth/pin-status` 가 진짜 root fix → BACKLOG `FEAT-PIN-STATUS-BACKEND-FALLBACK` P2 → P1 격상

### Limitation

본 Sprint = 1차 보호 layer. `pin_registered` 만 단독 손실 케이스 (드뭄) 보호. **4개 키 함께 손실 (Clear site data, Storage quota evict, iOS Safari 7일 idle) 시 효과 없음** — `FEAT-PIN-STATUS-BACKEND-FALLBACK` (P1 격상) 이 진짜 root fix.

### Deploy

- 빌드: flutter build web --release ✓ 12.2s
- 배포: Netlify Deploy ID `69eed5d26147a9d3c6966ecf` (2026-04-27 KST)
- Production URL: https://gaxis-ops.netlify.app

### Baseline 측정 (Twin파파 pgAdmin 배포 전 1회 권장)

설계서 L31644~31691 SQL 3종 — PIN 손실 의심 사용자 / login attempts 추세 / auth_pct. 결과는 D+7 재측정과 비교하여 본 Sprint 효과 정량 입증.

### Rollback

`frontend/lib/services/auth_service.dart` 변경 git revert → flutter build web → Netlify 배포. 양방향 sync 채택으로 rollback 안전 (단, SecureStorage write 실패한 cohort 만 잔존 위험).

### 신규 BACKLOG (4개 후속 Sprint)

- `FEAT-PIN-STATUS-BACKEND-FALLBACK-20260427` 🔴 P1 (격상 — 진짜 root fix)
- `AUDIT-PWA-SW-INDEXEDDB-PRESERVE-20260427` 🟡 P2
- `UX-LOGIN-FALLBACK-PIN-RESET-LINK-20260427` 🟢 P3
- `FEAT-AUTH-STORAGE-MIGRATION-FULL-20260427` 🟡 P2 (Codex 신규 권장)

### Related

- 설계 상세: `AGENT_TEAM_LAUNCH.md` FIX-PIN-FLAG-MIGRATION-SHAREDPREFS-20260427 섹션
- Codex 1차 advisory: `CODEX_REVIEW_FIX_PIN_FLAG_20260427.md`
- 별건 (병행): `FIX-DB-POOL-MAX-SIZE-20260427` Phase B 관찰 중

---

## [Infra] - 2026-04-27 — FIX-DB-POOL-MAX-SIZE-20260427

> **인프라 변경 only — 코드 변경 0, 버전 bump 없음**.
> Railway env `DB_POOL_MAX` **20 → 30** 변경 (MIN=5 유지). 4 라운드 advisory review (Codex 1차 + Claude Code 2차 + Codex 3차 + Twin파파 fact-check 4차) 로 약점 12건 정정 후 적용.

### Changed (Railway env only)

- `DB_POOL_MAX`: 20 → **30** (per-worker 독립 pool × 2 worker = Postgres 60/100 점유)
- `DB_POOL_MIN`: 5 (변경 없음, 기존 운영값 유지)

### 결정 근거 (Q-B 결정적 데이터)

- **2026-04-21 화요일 출근 burst 측정** (4-25 ~ 4-27 진단):
  - peak 31 동시 in-flight (08:06:07 KST)
  - 21 동시 in-flight 17회 (07:46~08:55, 70분간)
  - MAX=20 환경에서 fallback 1건/peak 발생 (라운드 4 정정 — 이전 추정 ~100건/일은 코드 default 가정 오류 기반)
- **per-worker 독립 pool 구조** (`backend/app/__init__.py:60-62` `init_pool()` in `create_app()`):
  - gunicorn `-w 2` (preload 없음) → 각 worker fork 후 독립 pool 생성
  - Worker A (scheduler owner, fcntl lock): HTTP 8 + scheduler peak 4 + 여유 = 15 conn 필요
  - Worker B (HTTP only): 8 + 여유 2 = 10 conn 필요
  - MAX=30 채택으로 worker A 100% 안전 + 미래 2x (62 in-flight) 까지 dimensioning

### 4 라운드 advisory trail (M=0 / A=12)

- 라운드 1 (Codex 1차): scheduler peak 8 conn 재계산, 단계적 25→30 한 번에 직행, fallback 비용 (200~500ms) 명시 (4건)
- 라운드 2 (Claude Code 2차): ⛔ per-worker 독립 pool 구조 발견 (단일 pool 가정 정정), Phase B 1일→3일 통계 신뢰성, pg_stat_activity SQL pid+client_addr 정밀화 (4건)
- 라운드 3 (Codex 3차): Q-B 일자 오기 (4-27→4-21) 정정, 5x 산수 오류 (31×5=155 in-flight, MAX=30 으로 부족), MIN=5 ↔ max_age=300s 상호작용, grep `\b` 경계 + `get_db_connection` 함수명 누락 정정 (4건, M=0)
- 라운드 4 (Twin파파 fact-check): ⚠️ 코드 default (1/10) 가정 오류 — 실제 prod 가 이미 5/20 운영 중. 결론 (MAX=30) 유지하되 fallback 빈도 추정 정정 (3건)

### Codex 공식 이관 미해당

본 작업은 단순 env 변경 + 코드 변경 0 + S1/S2 미해당으로 **Codex 이관 체크리스트 6항목 미충족**. Advisory review 만 4 라운드 수행 (정식 Codex 이관 절차 미적용).

### Phase B 관찰 계획 (D+0 ~ D+3)

- D+0 (2026-04-27 월) 16:30~17:00 KST 퇴근 peak — `Pool exhausted` grep
- D+1 (4-28 화) 07:30~09:00 출근 peak
- D+2 (4-29 수) 07:30~09:00 출근 peak
- D+3 (4-30 목) 07:30~09:00 출근 peak + Phase C 결정
- off-peak (12:00) Q-B 동시 in-flight 재측정 SQL (peak 후 O(N²) 부담 회피)

### Rollback

`DB_POOL_MAX = 30 → 20` env 복원 → 자동 재배포 ~1분, 코드 영향 0.

### Related

- 설계 상세: `AGENT_TEAM_LAUNCH.md` FIX-DB-POOL-MAX-SIZE-20260427 섹션 (약점 trail 12건 + 4 라운드 검증 기록)
- 별건 BACKLOG: `OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP` (P3, 격하 — MIN=5 가 cold-start 일부 흡수), `OBSERV-RAILWAY-HEALTH-TTFB-15S-INTERMITTENT` (P2, 별건), `OBSERV-SLOW-QUERY-ENDPOINT-PROFILING` (P2, 신규 분리)

---

## [2.10.4] - 2026-04-25 — 긴급 health timeout 보정 (사후 보충)

> ⚠️ **사후 보충 entry** (2026-04-27 정리). 이전 세션 (2026-04-25) 배포 시 CHANGELOG 보충 누락. handoff.md 4-27 세션 (2/3) "부수 발견" 으로 추적.

### Fixed (긴급, 현장 영향)

- **`frontend/lib/services/api_service.dart` L209-210** `getPublic()` Dio 인스턴스 timeout 보정:
  - `connectTimeout: 5s` → **10s**
  - `receiveTimeout: 5s` → **20s**
- 트리거: 2026-04-25 KST "System Offline" UX 발생. Railway `/health` 200 OK 정상 응답 + TTFB 12~15s 간헐 (외부 원인) → Flutter health check 5s timeout 초과 → 클라이언트가 false-positive `System Offline` 표시
- 해결: 일반 API timeout (15s) 와 일관성 + 5s 여유 → 20s. Railway TTFB 지연 근본 원인은 별건 (`OBSERV-RAILWAY-HEALTH-TTFB-15S-INTERMITTENT` BACKLOG 추적).

### Deploy

- 빌드: flutter build web --release ✓ 45.2s
- 배포: Netlify Deploy ID `69ec09a231e1446389627519` (2026-04-25 KST)
- git commit: `cd701e2` "fix: v2.10.4 health check timeout 5s→20s — System Offline false positive 긴급 해소"

### Related

- 별건 BACKLOG: `OBSERV-RAILWAY-HEALTH-TTFB-15S-INTERMITTENT` 🟡 P2 — Railway TTFB 15s 근본 원인 조사 + 외부 모니터링 도입 검토
- v2.10.6 OBSERV-DB-POOL-WARMUP 적용 후 `direct conn fallback` 빈도 0 도달 시 → TTFB 자연 안정화 가능 (부수 효과 검증 필요)

---

## [2.10.3] - 2026-04-24

> FIX-ORPHAN-ON-FINAL-DELIVERY — v2.10.2 배포 후 Q4-5 48h 관찰에서 발견된 숨은 4번째 delivery 실패 경로 수정. 2026-04-22 HOTFIX-ALERT-SCHEDULER-DELIVERY 가 `scheduler_service.py` 3곳만 고쳤는데 `task_service.py` 내 `complete_task` 경로에 동일 패턴의 **target_worker_id 미지정 버그** 가 숨어있어 2026-04-23~24 4일간 8건 legacy NULL 발생.

### Fixed

- **`task_service.py:391~419` ORPHAN_ON_FINAL alert INSERT** — `_create_alert_61(...)` 호출 시 `target_role` 만 지정하고 `target_worker_id` 누락 → `role_ELEC`/`role_TMS` room broadcast → 구독자 0 → **관리자 전원 alert 수신 실패**
- 수정: `_resolve_managers_for_category` (scheduler_service.py 표준 패턴) 재사용 + 관리자별 개별 INSERT 로 전환. `target_worker_id=manager_id` 지정
- 부수: 로그 메시지에 `managers={N}` 추가 (delivery count 가시화)

### 실측 피해 (2026-04-23 Codex 사후 Q4-5 관찰 기반)

| 구간 | NULL 건수 | 상태 |
|---|---|---|
| 2026-04-23 14:51 ~ 04-24 08:07 KST | 8건 | 미전달 (legacy, 자연 소거 대상) |
| 이후 (v2.10.3 배포 이후) | 0건 예상 | ✅ |

### Tests

- **TC-61B-22B 신규** (`test_sprint61_alert_escalation.py::TestOrphanOnFinal`)
  - ORPHAN_ON_FINAL alert INSERT 시 `target_worker_id IS NOT NULL` 보장 회귀 가드
  - `_resolve_managers_for_category('ELEC')` 반환 매니저 수만큼 개별 INSERT 검증
- pytest 4/4 GREEN (TC-61B-20/21/22/22B)

### Related

- **HOTFIX-ALERT-SCHEDULER-DELIVERY-20260422** 의 숨은 4번째 경로 — v2.10.3 으로 완전 종결
- 신규 BACKLOG: `CASCADE-ALERT-NEXT-PROCESS` 🟢 DRAFT — ORPHAN_ON_FINAL 의 원래 설계 의도 (현재 공정 + 다음 공정 관리자 동시 알림 = 공정 연쇄 차단 알림) 는 사내 공정 (PI/QI/SI) 활성화 계획 변동 이슈로 후순위 보류. 현재는 A안 (해당 공정 관리자만) 유지.

---

## [2.10.2] - 2026-04-23

> FIX-CHECKLIST-DONE-DEDUPE-KEY — 2026-04-22 HOTFIX 4건 일괄 Codex 사후 검토 (Phase A) 결과 발견된 M1 (Q4-4) + Q4-2 advisory 일괄 수정.
> **프로덕션 알람 누락 리스크 해소**: 동일 S/N 내 복수 ELEC task (IF_1 + IF_2 등) 가 open 상태일 때 첫 alert 이후 나머지 3일 suppress 되는 버그.

### Fixed

- **CHECKLIST_DONE_TASK_OPEN dedupe key 오류 수정** (`scheduler_service.py:1064~1070`, Codex 사후 Q4-4 M)
  - dedupe 쿼리에 `task_detail_id = %s` 누락 → 같은 S/N 내 서로 다른 ELEC task 의 alert 가 서로 suppress 되는 버그
  - 수정: `WHERE serial_number = %s` → `WHERE serial_number = %s AND task_detail_id = %s`
  - 부수 효과: `idx_alert_logs_dedupe` partial index (`WHERE task_detail_id IS NOT NULL`) 활용 가능
- **RELAY_ORPHAN dedupe `message LIKE` → `task_detail_id` 전환** (`scheduler_service.py:883~913`, Codex 사후 Q4-2 advisory)
  - 기존: `message LIKE '%task_name%'` — 동명 task 중복 매칭 가능 + 인덱스 miss
  - 수정: `task_detail_id = orphan['task_detail_id']` — 정확한 dedupe + index 활용
  - 부수: INSERT dict 에도 `'task_detail_id': orphan['task_detail_id']` 추가

### Tests

- **TC-61B-19B 신규** (`test_sprint61_alert_escalation.py::TestChecklistDoneTaskOpen`)
  - 동일 S/N 에 ELEC open task 2건 (`PANEL_WORK` + `WIRING`) 상황에서 **각각 DISTINCT alert 발송** 검증
  - v2.10.2 이전 버그 회귀 가드 (이전 버전으로 롤백 시 FAIL)
- **setup_sprint61 fixture 보강** — `product_info` INSERT 에 `mech_partner='FNI'` + `elec_partner='TMS'` 추가
  - `_resolve_managers_for_category` 가 partner 필드로 관리자 찾기 때문에 누락 시 alert 0건 → 기존 TC-61B-17 도 불안정
  - 사전 누락된 fixture 정정 (v2.10.2 변경과 별개, 동일 커밋에 포함)

### Codex 사후 검토 결과 반영 (POST-REVIEW-HOTFIX-BATCH 2026-04-23)

- **HOTFIX #1 (PHASE1.5)**: Close ✅ — Q1-1/1-3 Advisory 는 `OBSERV-ALERT-SILENT-FAIL` 흡수
- **HOTFIX #2 (SCHEMA-RESTORE)**: Close ✅ — Q2-1/2-2/2-3 Advisory 는 기존 BACKLOG 흡수 (runbook / MIGRATION-049 / STARTUP-ASSERTION)
- **HOTFIX #3 (DUP)**: Close ✅ — Q3-2/3-3/3-4 Advisory 는 신규 FIX 엔트리 + Redis 조건부 유지
- **HOTFIX #4 (DELIVERY)**: **본 PATCH 로 Close** ✅ — Q4-4 M 수정 + Q4-2 동시 해결
- **Q4-1 role 경로 company 필터**: 🟠 신규 `SEC-ROLE-COMPANY-FILTER` 엔트리 등록 (leakage 리스크)
- **Q4-3 N+1 query**: `REFACTOR-SCHEDULER-SPLIT` 흡수
- **Q4-5 48h 관찰 SQL**: 실행 권장 (본 배포 후)

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
