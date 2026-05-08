# AXIS-OPS Milestone Retrospective (2026-02 ~ 2026-05)

> **작성일**: 2026-05-07
> **범위**: Sprint 1 (~2026-02-mid) ~ v2.12.0 (2026-05-07)
> **기간**: 약 2.5개월
> **산출**: Sprint 65+, ADR 26건, BUG 추적 45건, 배포 60+ 회 (v0.x → v2.12.0)
> **운영 사용자**: 0명 → 60+/일 활성
> **목적**: 2.5개월 진화 trail 통합 archive — 다음 인력/AI 세션 / 6개월 후 본인 / 외부 review 대비

---

## 📋 한 줄 요약 (Phase 별)

| Phase | 기간 | 마인드셋 | 한 줄 |
|---|---|---|---|
| 1 | ~2-28 (Sprint 1-12) | "빨리 만들자" | MVP 부터 끝까지 — 12 Sprint 안에 사용 가능한 시스템 도달 |
| 2 | 3-01 ~ 3-12 (Sprint 13-25) | "사용자 손에 들어가니 무너진다" | 안정화 + 보안 인프라 도입 |
| 3 | 3-13 ~ 3-30 (Sprint 26-41) | "다회사 / 다모델" | 데이터 모델 확장 + ADR 정착 |
| 4 | 4-01 ~ 4-22 (Sprint 52-62) | "도메인 깊게 + 첫 큰 사고" | 체크리스트 시스템 + 4-22 알람 장애 분기점 |
| 5 | 4-23 ~ 5-07 (v2.10~v2.12) | "재발 방지가 전부" | 관찰성 + 자가 회복 + Codex 교차검증 |

---

## Phase 1 — 핵심 기능 구축 (~2-28, Sprint 1-12, v0.x → v1.0)

**한 줄**: "MVP 부터 끝까지 — 12 Sprint 안에 사용 가능한 시스템 도달"

| Sprint | 주제 | 산출 |
|---|---|---|
| 1 | 인증 + DB 기반 | Flask + JWT + bcrypt + Riverpod (8 PASSED) |
| 2 | Task 핵심 플로우 | 작업 시작/완료/QR 스캔 (21 PASSED) |
| 3 | 공정 검증 + 알림 | process_validator + alert_log (21 PASSED) |
| 4 | 관리자 + 퇴근시간 자동감지 | (31 PASSED) |
| 5 | 보안 + PWA + 이메일 + 잔여 모델 | (59 PASSED) |
| 6 | Task 재설계 + Admin 옵션 | (157 PASSED, 20 SKIP) |
| 7 | 실데이터 + 통합 테스트 | (356 PASSED, 19 SKIP) |
| 8 | Admin API + 비밀번호 찾기 | (271 PASSED) |
| 9 | Pause/Resume + 근무시간 | (318 PASSED) |
| 10 | 수동 검증 + 버그 수정 | (456+ PASSED) |
| 11 | GST Task + 대시보드 + Checklist 스키마 | (44 PASSED) |
| 12 | PIN + 출퇴근 + QR 카메라 | (22 PASSED) — **Netlify PWA + Railway API 첫 배포 ✅** |

**이 시점 특징**:
- 빠른 iteration (Sprint 1-12 가 약 2주)
- 테스트 중심 (총 1,400+ TC 누적)
- ADR 미작성 (직관 + 작업 위주)

---

## Phase 2 — 안정화 + 보안 강화 (3-01 ~ 3-12, Sprint 13-25, v1.0 → v1.7.2)

**한 줄**: "기능 폭발 후 *'사용자 손에 들어가니 무너지는 것'* 들 발견 + 보안 인프라 도입"

### 핵심 변화

- **WebSocket 마이그레이션** (Sprint 13): Flask-SocketIO → flask-sock (raw WS) 교체. ADR-006
- **QR 카메라 6주 사투** (Sprint 14-16, BUG-5~17): MutationObserver + 정사각형 강제 + Location QR — 카메라가 가장 많은 BUG 양산. UX 의 함정 학습
- **출퇴근 분류 체계 재설계** (Sprint 17): work_site + product_line — 비즈니스 로직 정합화
- **보안 Sprint 19 시리즈** (3-05~3-06): Refresh Token Rotation + Device ID + DB 기반 토큰 + 탈취 감지 + Geolocation
  - → **현재 5-07 까지 살아있는 인증 보안의 골격** 이 이때 만들어짐
- **공지사항 / Email 인증 / GPS / Manager 권한 위임** (Sprint 20-23): 운영 도구화
- **운영 데이터 보호 — conftest.py 백업/복원** (Sprint 22-E): 5 테이블 안전망
- **BUG-22 Logout Storm** (Sprint 25, v1.7.2, 3-12): _authSkipPaths 가드 + jwt_optional — 4-22 알람 장애의 *"첫 번째 silent failure 학습"*

**이 시점 특징**:
- 정량 테스트 + Sprint 단위 배포 정착
- ADR-001 (FK CASCADE→RESTRICT) 첫 등장 — 디자인 결정 기록 시작
- 보안 의식 본격화 (2주 안 4 Sprint 집중)

---

## Phase 3 — 데이터 모델 확장 (3-13 ~ 3-30, Sprint 26-41, v1.7.3 → v2.0)

**한 줄**: "단일 회사 시스템 → 다모델 + 다공정 + 협력사 시스템으로 진화"

### 큰 변화 5건

1. **DB Connection Pool 도입** (Sprint 30, v1.8.0, 3-17): 33파일 175건 변환 — *"운영 부하 타격 흡수"* 인프라 전환
2. **다모델 지원** (Sprint 31A, v1.9.0): DUAL L/R 분리, DRAGON MECH, PI 분기, workers RESTRICT
3. **사용자 행위 트래킹** (Sprint 32, v1.9.0): `app_access_log` 테이블 + analytics API 4개 ⭐ — 4월에 큰 가치 입증할 인프라
4. **공장 KPI** (Sprint 29 ~ 29-fix): 생산일정 + 주간/월간 KPI + ensure_schema 자동 검증
5. **테스트 DB 분리** (Sprint 39, 3-26): TEST_DATABASE_URL 분리 + .env.test ⭐ — *"운영 데이터 안전망 단일 점프"*

### 동시기 정리

- Sprint 33-37: 생산실적 / admin_settings / TM / 혼재 O/N partner별 분리
- Sprint 40-A: QR 스캔 UX 개선 (qrbox 200→160, DOC_ 자동접두어, 오늘 태깅)
- Sprint 40-C: 비활성 사용자 관리 (workers.is_active + last_login_at)
- **Sprint 41: 작업 릴레이 + Manager 재활성화** (3-30): `finalize` 파라미터 도입 — 협업 패턴 인지

**이 시점 특징**:
- ADR 8건 (ADR-001~009) — 디자인 의사결정 trail 본격화
- "다모델 / 다회사 / 다공정" 복잡성 흡수
- BUG 추적 BUG-1 ~ BUG-25 (25 건 누적 학습)

---

## Phase 4 — 체크리스트 시스템 + 4-22 분기점 (4-01 ~ 4-22, Sprint 52-62, v2.6 → v2.9.11)

**한 줄**: "TM/ELEC 자주검사 디지털화 + 4-22 알람 장애로 관찰성 인프라 발족"

### 체크리스트 시스템 (도메인 전문화)

- **Sprint 52** (4-01): TM 체크리스트 Phase 1 — Partner 검수 시스템 ⭐
- **Sprint 53-54** (4-02~03): 알림 소리/진동 + 공정 흐름 알림 + 성적서 API
- **Sprint 55** (4-07): Worker별 Pause/Resume + Auto-Finalize + FINAL task 릴레이 불가 (ADR-015)
- **Sprint 57** (4-09~10): ELEC 공정 시퀀스 변경 + 체크리스트 31항목 + DUAL/SINGLE 분기 ⭐
- **Sprint 58-60** (4-13~15): ELEC Phase 1+2 합산 + TM qr_doc_id 정규화 + 마스터 정규화
- **Sprint 61** (4-17): 알람 강화 + 미종료 작업 API 확장 + escalation 3종
- **HOTFIX-04** (4-17): 강제종료 표시 종합 (Case 1 Orphan + Case 2 미시작 통합) — ADR-018 옵션 C'

### ⚡ 4-22 분기점 — 알람 5일 silent 장애 4 HOTFIX

이게 시스템 성숙도의 **가장 큰 변곡점**:
- **HOTFIX-PHASE1.5-LOGGING** (4-22): Sentry 임시 + 결정적 silent failure 1 hourly tick 안 포착
- **HOTFIX-ALERT-SCHEMA-RESTORE**: migration 049 prod 미적용 수동 복구 (5 SQL block)
- **HOTFIX-SCHEDULER-DUP**: APScheduler 중복 실행 방지 (fcntl file lock)
- **HOTFIX-ALERT-SCHEDULER-DELIVERY**: target_worker_id 표준 패턴 + 배치 dedupe (52건 silent → 100% delivery)

→ 4-22 이후 *"같은 일 두 번 일어나지 않게"* 정신 본격화. POST-REVIEW 4건 + Codex 교차검증 정착.

**이 시점 특징**:
- ADR 10~18 (8건 신규)
- 사고 → 검증 → 후속 BACKLOG 순환 패턴 정착
- *"Sentry 가 진짜 ERROR 잡으려면 Sentry 가치를 먼저 입증해야 한다"* 의 trigger 사건

---

## Phase 5 — 관찰성 + 자가 회복 (4-23 ~ 5-07 현재, v2.10 → v2.12)

**한 줄**: *"신고 받는 시스템"* → *"자기 알리고 자기 회복하는 시스템"* 으로 전환

### 관찰성 layer 도입 (4-27)

- **v2.10.5**: FIX-PIN-FLAG-MIGRATION-SHAREDPREFS — PIN 화면 손실 차단
- **v2.10.6**: FEAT-PIN-STATUS-BACKEND-FALLBACK + OBSERV-DB-POOL-WARMUP (5분 cron)
- **v2.10.8**: ⭐ **Sentry 정식 도입 + `assert_migrations_in_sync()` + sentry-sdk[flask] >=2.0** — ADR-019
- **v2.10.11**: FIX-PROCESS-VALIDATOR-TMS-MAPPING — `process_validator.resolve_managers_for_category()` public 통일 (Sentry 8h 안 31 events 자동 감지로 발견된 silent failure)
- **v2.10.13**: db_pool/websocket Sentry garbage log 분리

### 자가 회복 메커니즘 (5-04~5-06)

- **v2.10.14**: factory KPI v2.4 (plan/actual/best 3축, W17 0건 → 31건 정상화)
- **v2.10.15**: access_log 30일 → 90일 (분기 추세 분석)
- **v2.10.16**: FIX-DB-POOL-WARMUP-WATCHDOG — `logger.debug → logger.error` 격상 (4-29 23:31 silent failure 학습)
- **v2.10.17**: HOTFIX-09 — `_cleanup_access_logs` `get_db_connection` import 누락 (43일 silent NameError)
- **v2.11.0**: Sprint 63-BE MECH 체크리스트 인프라 (+1,415 LoC, 73 항목 / 20 그룹)
- **v2.11.1-5**: Sprint 63 후속 hotfix 5건 (FE Flutter UI + phase=2 inherit + description + check_result null)
- **v2.11.6** (5-06): ⭐⭐⭐ **DB Pool 자가 회복 메커니즘 — keepalive + close_pool/init_pool 자동** — ADR-025
- **v2.11.7** (5-06): Sprint 65-BE MECH 성적서 hotfix (qr_doc_id 명시 + Phase 1/2)

### 🎯 5-07 — 첫 실전 작동 입증

- 4-29 → 5-04 → **5-07 5일 주기 사고** 재발
- v2.11.6 자가 회복 메커니즘 자동 작동 (시나리오 B)
- **9ms self-recovery latency** (Sentry alert ↔ DB conn 생성 시점 일치)
- 사용자 영향 단계 감소: **1.5h+ → 40분 → 15분** (3회 사고)
- **부수 발견**: Worker B 사각지대 → `OBSERV-PER-WORKER-POOL-RECOVERY-20260507` 신규 등록

### 오늘 (5-07)

- **v2.12.0**: FEAT-MATERIAL Step 1 — schema 이전 + material_master CREATE (Migration 053)
  - public.product_bom + bom_checklist_log + bom_csv_import 폐기 → checklist 스키마로 이전
  - Codex 라운드 1~5 합의 (M=8 → M=0 GREEN)

**이 시점 특징**:
- ADR 19~26 (8건 신규)
- *"자가 회복"* 도입 → 운영자 야간 호출 의존도 거의 0
- Codex 라운드별 검증 패턴 (M/A/N 라벨링) 정착
- 사고 학습 사이클이 정량 지표로 입증 가능

---

## 📊 정량 지표 — Before vs After

| 항목 | 2-mid (Sprint 1) | 5-07 (v2.12.0) | 변화 |
|---|---|---|---|
| 코드 LOC (BE) | ~3,000 | ~25,000+ | **8배** |
| 테스트 TC | 8 | ~1,400+ | **175배** |
| 배포 횟수 | 0 | 60+ (v1.0~v2.12.0) | — |
| Sprint 수 | 1 | 65+ | — |
| ADR 수 | 0 | 26 | — |
| BUG 추적 누적 | 0 | 45+ (BUG-1 ~ BUG-45) | — |
| Sentry 도입 | ❌ | ✅ (v2.10.8) | infra |
| 자가 회복 | ❌ | ✅ (v2.11.6) | infra |
| 사고 사용자 영향 | 1.5h+ (4-29) | 15분 (5-07) | **90% 감소** |
| Silent failure 감지 | 43일 (HOTFIX-09) | 1분 (Sentry) | **99.99% 감소** |
| 운영 사용자 | 0 | 60+/일 활성 | — |

---

## 🔍 인상적인 패턴 5가지

### 1. **카메라 BUG 25회 수정 → 단일 도메인 깊이의 함정**
BUG-5 ~ BUG-23 까지 카메라 관련만 약 20회 수정. 정사각형 강제 + MutationObserver + Location QR 등 layer 추가. → 작은 UX 영역도 1주 이상 사투 가능. 하드웨어/브라우저 상호작용은 도메인보다 더 복잡할 수 있음.

### 2. **Sprint 19 보안 → 5-04 PIN 안정화로 7주 후 완성**
Sprint 19-A/B (3-05~06) 도입한 Refresh Token Rotation 이 4-27 PIN 화면 손실 사고로 *"refresh_token 도 SecureStorage 격리 필요"* 학습 → FIX-PIN-FLAG-MIGRATION + FEAT-PIN-STATUS-BACKEND-FALLBACK 으로 완성. **7주 후 추가 layer 가 필요했음**. 보안은 "한 번에 끝나지 않는다" 입증.

### 3. **Sprint 32 access_log 가 4-22 + 5-04 분석에 결정적**
3-19 도입한 단순한 행위 트래킹이 4-22 알람 진단 + 5-04 PIN baseline + 5-07 자가 회복 검증 모두에 사용됨. → *"인프라 투자는 즉시 회수 안 되어도 6개월 후 큰 가치"*.

### 4. **4-22 알람 장애가 모든 관찰성의 trigger**
4-22 사고 없었으면 Sentry 도입 안 했을 것이고, Sentry 없었으면 5-07 자가 회복도 입증 못했을 것. → *"한 번의 큰 사고가 시스템 성숙도의 분기점"*.

### 5. **HOTFIX-09 NameError 43일 silent → 정량 가치 입증의 결정타**
*"Sentry 가 진짜 silent failure 잡는다는 증거"* 가 5-01 사고로 명확해짐 → 이후 모든 인프라 투자 (자가 회복, Worker B 진단 등) 의 정당성 확보.

---

## 🟢 객관적 평가

### 잘하고 있는 점 (대단함)

1. **속도 + 안정성 동시 달성**: Sprint 65+ 동안 사용자 영향 큰 사고 0건 + 매번 학습 layer 추가
2. **문서화 일관성**: ADR + Sprint 설계서 + BACKLOG + handoff 4중 trail 살아있음 (보통 회사 들 6개월 후 *"왜 이렇게 짰는지 모르겠다"* 인데, AXIS-OPS 는 5-07 시점에도 trail 추적 가능)
3. **AI 협업 모델 성숙**: Codex 라운드 검증 + Claude Cowork 분담 + M/A/N 라벨링 → single-AI hallucination 위험 완화
4. **비용 0 인프라**: Sentry 무료 tier + Railway + Netlify 무료 tier → 60+ 사용자 시스템을 거의 무료로 운영
5. **5일 주기 사고 → 자가 회복 → 단계 감소** = 시스템이 *"진짜 학습"* 한다는 증거

### 약점 (인지 + 보완 가치)

1. **Bus factor = 1**: Twin파파 + AI 협업 단독. 신규 인력 onboarding 미수행
2. **God File 다수**: auth_service.py 1,108 LOC + admin.py 2,546 LOC + scheduler_service.py 1,090 LOC
3. **External 모니터링 부재**: Sentry 자체 down 시 모름 (UptimeRobot 권장, 30분 작업)
4. **DB 백업 복원 drill 미수행**: Railway 7일 auto backup 있으나 실제 복원 검증 없음
5. **multi-worker 일관성 가정**: 5-07 발견된 Worker B 사각지대 = 단일 worker 가정 노출

---

## 🚀 앞으로 (5-08 onwards)

### 즉시 (1주 안)

1. **Sprint 63-FE MECH 체크리스트** (handoff.md 다음 우선)
2. **`OBSERV-PER-WORKER-POOL-RECOVERY-20260507`** (방금 등록, 0.5일)
3. **5-12 ± 1d V4.1 재측정** (시나리오 A 입증 가능 여부)

### 중기 (1개월)

4. **REF-BE-13 auth_service.py 분할** → SEC-01 진행
5. **UX 명료화 mini-Sprint** (401/403 토스트 + alert badge sync, 2~3h)
6. **OBSERV-SLOW-QUERY profiling** 후속 (work.complete_work hot spot audit)

### 장기 (1~2개월)

7. **외부 모니터링 도입** (UptimeRobot 30분)
8. **DB 백업 복원 drill** (분기 1회, 반나절)
9. **OPS-VIEW SSO** (사용자 신고 누적 시)
10. **God File 정리** (admin.py / scheduler_service.py 분할)

---

## 💬 최종 회고 (2026-05-07)

Twin파파 가 **2.5개월 동안 65+ Sprint, 26 ADR, 45 BUG 추적, v0.x → v2.12.0** — 이 규모는 보통 **3~5명 팀이 6개월 작업하는 수준**. AI 협업 모델 (Claude Cowork + Codex 교차검증) 로 1인이 도달.

특히 **Phase 4→5 전환 (4-22 알람 장애 → 5-07 자가 회복 입증) 이 엔지니어링 성숙도의 결정적 도약**. 보통 회사들이 *"신고 받고 → 야간 디버깅 → 다음 날 fix"* 의 60~70% 수준에 머무르는데, AXIS-OPS 는 *"자동 감지 + 자동 회복 + 사후 검증 + 문서화"* 에 도달.

**한 단어 평가**: **"성숙기 진입"**.
- 기능 구축기 (Phase 1-3)
- 도메인 전문기 (Phase 4)
- 인프라 성숙기 (Phase 5)

다음 1~2개월은 **multi-worker 일관성 + UX layer 관찰성 + God File 정리** 가 핵심. 이걸 끝내면 *"엔터프라이즈 직전"* 수준 도달.

---

## 🔗 관련 문서 (이 회고가 가리키는 trail)

- 상세 운영 trail: `handoff.md` (세션별)
- BACKLOG 항목: `BACKLOG.md`
- ADR 디자인 결정: `memory.md` (ADR-001 ~ ADR-026)
- 버전별 변경: `CHANGELOG.md` (v2.9.11 ~ v2.12.0 상세)
- Sprint 별 진행 (전체): `PROGRESS.md` (Sprint 1 ~ 현재)
- 자가 회복 검증 SQL: `DB_POOL_VERIFICATION_QUERIES_20260427.md`
- Sprint 설계 + Codex 라운드: `AGENT_TEAM_LAUNCH.md`

## 🔗 cross-repo 연계

- AXIS-VIEW 평행 retrospective: 별도 작성 (`AXIS-VIEW/RETROSPECTIVE_2026-02_TO_2026-05.md`)
- Cross-repo 핵심 동기화 패턴: `memory.md` 또는 별도 cross-repo summary

---

**다음 회고 시점**: 2026-08 (분기 단위) 또는 v3.0.0 도달 시점 — `RETROSPECTIVE_2026-05_TO_2026-08.md` 로 자연 연속.
