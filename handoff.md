# AXIS-OPS Handoff

> 세션 종료 시 업데이트. 다음 세션이 즉시 작업을 이어갈 수 있도록 현재 상태를 기록합니다.
> 마지막 업데이트: 2026-04-23

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

### 🏁 Sprint 62-BE v2.2 전체 종결 (2026-04-23)

- ✅ v2.10.0 배포 (factory.py + migration 050 + 11 TC)
- ✅ v2.10.1 PATCH 교정 (weekly-kpi WHERE finishing_plan_end)
- ✅ Notices bump (id=102, v2.10.1)
- ✅ Netlify FE 배포 2회 (v2.10.0 + v2.10.1)
- ✅ Migration 050 Railway 적용 + migration_history 기록
- ✅ POST-REVIEW EXPLAIN ANALYZE Q3 A 해소
- ⏸ Q5 네이밍 부채 관찰형 7일 유지

**다음 세션 최우선**: 없음. Sprint 62-BE 종결. 다른 Sprint 착수 대기.

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
