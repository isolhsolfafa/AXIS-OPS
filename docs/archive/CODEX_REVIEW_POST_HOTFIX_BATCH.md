# Codex 사후 교차검증 프롬프트 — 2026-04-22 HOTFIX 4건 일괄

> 생성일: 2026-04-23 | 대상: Codex (독립 검증자) | 작성자: Claude Code Opus Lead
> 검증 유형: S2 HOTFIX 긴급 배포 후 **24h 이내 사후 Codex 검토 의무** (CLAUDE.md § 🚨 HOTFIX 예외 조항)
> 실행 지연 사실: 배포일 2026-04-22, 사후 검토일 2026-04-23 (약 24h~36h 경과, 기한 임박/초과)
> BACKLOG 로드맵: `BACKLOG.md` L180~185 Phase A 4건

---

## 공통 배경

2026-04-17~22 발생한 5일 알람 장애 (`app_alert_logs` INSERT 0건) 를 복구하기 위해 2026-04-22 **하루 동안 4 HOTFIX S2 연속 배포**:

```
PHASE1.5 → SCHEMA-RESTORE → DUP → DELIVERY
(로깅 도구)   (DB 수동복구)    (중복실행)   (target_worker_id)
```

CLAUDE.md § 🚨 HOTFIX 예외 조항 S2 는 각 배포당 24h 이내 Codex 사후 검토를 의무화. 4건 모두 독립적으로 거쳐야 하나, **일괄 검토로 효율 확보** (동일 장애 시퀀스 내 연계된 fix 들).

---

## 공통 참조 자료 (필독)

1. **Diagnosis 문서**: `/Users/twinfafa/Desktop/GST/AXIS-OPS/ALERT_SCHEDULER_DIAGNOSIS.md` §11.14.7 (근본 원인 확정) + §12 (Schema Restore)
2. **AGENT_TEAM_LAUNCH.md**: HOTFIX-SCHEDULER-PHASE1.5 / HOTFIX-ALERT-SCHEMA-RESTORE / HOTFIX-SCHEDULER-DUP / HOTFIX-ALERT-SCHEDULER-DELIVERY 섹션
3. **BACKLOG.md** L180~185, L266~290 (각 HOTFIX 엔트리 + POST-REVIEW 엔트리)
4. **CHANGELOG.md**: `[2.9.11] - 2026-04-22` 섹션

---

## HOTFIX #1 — PHASE1.5 (Alert silent fail ERROR 로깅)

### 배포 개요
- **commit**: `4a6caf8` (2026-04-22 10:47 KST)
- **배포 직후 효과**: 단일 hourly tick (02:00 UTC) 에서 `[alert_insert_fail]` 로그 4건 포착 → 5일 장애 근본 원인 (migration 049 미적용 + task_detail_id 컬럼 부재) 확정의 결정적 도구
- **상태**: ✅ COMPLETED — 역할 완수 후 `OBSERV-ALERT-SILENT-FAIL` 로 영구 승격 대기

### 검토 범위 (3건)

**Q1-1**: Silent fail ERROR 로깅 3지점 구현의 **정확성·일관성**
- `backend/app/models/alert_log.py` `create_alert()` — `[alert_insert_fail]` prefix
- `backend/app/services/alert_service.py` `create_and_broadcast_alert()` — `[alert_silent_fail]` / `[alert_create_none]` prefix
- 세 지점의 **로그 구조 일관성** / **상호 호출 체인** / **누락 경로 존재 여부**

**Q1-2**: Sentry import guard 패턴 안전성
```python
# 이런 패턴으로 구현됨:
try:
    import sentry_sdk
    sentry_sdk.capture_exception(e)
except ImportError:
    pass
```
- 패턴 안전성 (import 부재 시 NameError 발생 가능성)
- `requirements.txt` 에 sentry-sdk 없는 상태 → 개발 환경 보호 vs 프로덕션 Sentry 연동 시 전환 용이성
- 재현/테스트 가능성 (pytest 에서 mock 필요한지)

**Q1-3**: 임시 로깅의 영구 코드 승격 (`OBSERV-ALERT-SILENT-FAIL`) 시 고려사항
- 현재 `[prefix]` 문자열 기반 로그 → 구조화 payload (`contexts={"alert": ...}`) 전환 가이드
- release/environment tag 권고
- Sentry alert rule 권고 (1시간 내 5회 이상 발생 시 paging)

---

## HOTFIX #2 — SCHEMA-RESTORE (Railway 운영 DB 수동 복구)

### 배포 개요
- **시점**: 2026-04-22 11:25 KST
- **방식**: pgAdmin 수동 SQL 5 블록 실행 (code 배포 아님)
  1. enum 3종 추가 (`TASK_NOT_STARTED` / `CHECKLIST_DONE_TASK_OPEN` / `ORPHAN_ON_FINAL`)
  2. `app_alert_logs.task_detail_id` 컬럼 추가
  3. `idx_alert_logs_dedupe` 인덱스
  4. `admin_settings` 기본값
  5. `migration_history` 049 소급 INSERT
- **검증**: 12:00 KST tick 에서 신규 INSERT 16건 (id=658~673) 확인
- **상태**: ✅ COMPLETED

### 검토 범위 (3건)

**Q2-1**: 5 블록 SQL 의 **정확성·순서 의존성**
- `ALERT_SCHEDULER_DIAGNOSIS.md` §12.6 의 SQL 블록 순서 (enum → column → index → settings → history)
- 순서 변경 시 실패 가능성 (e.g., 컬럼 없이 인덱스 생성 시도)
- 멱등성 (IF NOT EXISTS / ON CONFLICT) 보장 여부

**Q2-2**: migration 049 prod 미적용 **원인 가설 4가지** 중 가장 유력한 것
- §12.5 의 4가지: ① DATABASE_URL 분기 / ② migration_runner idempotent 판정 버그 / ③ 047/048 런타임 오류로 049 skip / ④ Railway volume/layer 캐시
- 현재 증거 (migration_history 내용, Railway 로그) 로 어떤 가설이 가장 설명력 높은가?
- **이것이 `POST-REVIEW-MIGRATION-049-NOT-APPLIED` (Phase D) 의 선행 재료** 이므로 상세 권고 필요

**Q2-3**: 향후 **동일 drift 재발 방지책** 우선순위
- `OBSERV-MIGRATION-HISTORY-SCHEMA` (success/error_message/checksum 추가) vs `OBSERV-MIGRATION-RUNNER-STARTUP-ASSERTION` (부팅 시 drift 감지)
- 어느 쪽이 더 결정적 방어선인가?

---

## HOTFIX #3 — DUP (fcntl file lock 기반 scheduler 단일 실행)

### 배포 개요
- **commit**: `f1af8a4` (2026-04-22 13:00~14:00 KST 추정)
- **근본 원인**: Gunicorn multi-worker 환경에서 `_SCHEDULER_STARTED` env 가드가 fork 이후 COW semantics 로 worker 간 전파되지 않음 → 2~3개 scheduler 동시 실행 (R1 실측 37.5% 중복, GPWS-0773 3중복)
- **해결책**: `fcntl.flock(LOCK_EX | LOCK_NB)` + `/tmp/axis_ops_scheduler.lock` OS 레벨 lock 도입
- **구현 위치**: `backend/app/__init__.py` L70-78
- **상태**: ✅ COMPLETED — 배포 후 중복 INSERT 재발 없음

### 검토 범위 (4건)

**Q3-1**: fcntl.flock 패턴의 **corner case**
- SIGKILL / OOM kill 시 lock 파일 잔존 가능성 (`/tmp/axis_ops_scheduler.lock`)
  - Linux `flock()` 은 프로세스 종료 시 자동 release (OS 보장) — 이 보장이 **Railway 환경에서도 유효한지**
  - `/tmp` 이 Railway volume 에서 persistent 인지 ephemeral 인지
- Railway graceful shutdown (SIGTERM) 시 `atexit` handler 정상 호출 여부
- 재배포 시 lock 획득 실패 → **1 worker 도 scheduler 시작 못하는 시나리오** 재현 가능성

**Q3-2**: `_lock_fd` 모듈 레벨 참조의 GC 방지 패턴 안전성
- `_lock_fd = os.open(lockfile, ...)` 를 모듈 레벨에 두어 GC 방지
- Python GIL 환경에서 이 패턴이 정말로 fd leak 없이 안전한지

**Q3-3**: 기존 `_SCHEDULER_STARTED` env 가드 **보조 유지** 의 실질 가치
- fcntl 도입 후에도 env 가드를 제거 안 한 이유 (defense in depth?)
- 보조 가드가 오히려 테스트 환경에서 혼란 일으킬 가능성

**Q3-4**: Redis distributed lock 병행 필요성
- 현재 fcntl 은 **단일 Railway 인스턴스** 전제. 다중 인스턴스 (horizontal scaling) 로 전환 시 fcntl 이 실패
- Redis SETNX / Redlock 으로의 이관 계획 적절성 + 트리거 조건 (언제 전환해야 하나)

---

## HOTFIX #4 — DELIVERY (scheduler 3곳 target_worker_id + 배치 dedupe)

### 배포 개요
- **commit**: `d946532` (v2.9.11, 2026-04-22 15:00~ KST 추정)
- **근본 원인**: scheduler_service.py 3곳 (RELAY_ORPHAN L884 + TASK_NOT_STARTED L967 + CHECKLIST_DONE_TASK_OPEN L1044) 이 `target_worker_id` 미지정 + `target_role` 만 broadcast → `role_TMS` / `role_elec_partner` 등 `role_enum` 외 값 room 으로 발송 → 구독자 0 → 52+17=69건 완전 undelivered
- **해결책**: `task_service.py` L571 표준 패턴 (`get_managers_by_partner` / `get_managers_for_role` → 관리자별 개별 INSERT) 로 통일. 신규 헬퍼 `_resolve_managers_for_category` 도입. 배치 dedupe 에 `target_worker_id IS NOT NULL` 필터 추가 (Codex M2 수용)
- **LOC**: +100/-52
- **배포 후 48h 관찰**: 알람 정상 delivery 재개 + legacy 69건 수렴 곡선
- **상태**: ✅ COMPLETED — v2.9.11 release

### 검토 범위 (5건)

**Q4-1**: `_resolve_managers_for_category` 헬퍼의 **정확성**
- `scheduler_service.py` 내 구현 위치 찾아서 읽기
- task_category (MECH/ELEC/TM/PI/QI/SI) 분기 로직 — Partner 기반 (TMS/MECH/ELEC) vs Role 기반 (PI/QI/SI) 자동 분기
- NULL partner / empty manager 리스트 edge case 처리

**Q4-2**: 3곳 배치 dedupe 쿼리 **index 활용 효율**
- `idx_alert_logs_dedupe` 인덱스 구조 확인 (`ALERT_SCHEDULER_DIAGNOSIS.md` §12.6 참조)
- `target_worker_id IS NOT NULL` 필터 추가로 인덱스 사용 가능한지 (partial index 가 필요한지)
- EXPLAIN 권고 쿼리 제시

**Q4-3**: `for manager_id` 루프의 **N+1 query 여부**
- 관리자별 개별 INSERT 루프가 N+1 패턴인가, batch INSERT 가능한가
- `executemany` 또는 `VALUES (%s), (%s), ...` 패턴 전환 권고

**Q4-4**: Codex M1 (Item 2 — `target_worker_id IS NOT NULL` 필터) 해결 완결성
- M1 지적이 3곳 모두에 일관되게 반영됐는지
- legacy 69건 (`target_worker_id=NULL`) 이 dedupe window 에서 **신규 INSERT 차단하지 않는다**는 보장 검증

**Q4-5**: 배포 후 48h 관찰 데이터 권고
- `app_alert_logs` 최근 48h 기준 쿼리 (태그별 / 관리자별 delivery count)
- legacy 69건 자연 소거 예상 시점 (24h / 7d / 3d window)
- 관찰 SQL 예시

---

## 응답 형식

```markdown
# HOTFIX #1 (PHASE1.5)
## Q1-1: 라벨 M/A/N
... 근거 (file:line 인용) ...
## Q1-2: 라벨 M/A/N
...
## Q1-3: 라벨 M/A/N
...

# HOTFIX #2 (SCHEMA-RESTORE)
## Q2-1~3: 각각 M/A/N + 근거

# HOTFIX #3 (DUP)
## Q3-1~4: 각각 M/A/N + 근거

# HOTFIX #4 (DELIVERY)
## Q4-1~5: 각각 M/A/N + 근거

---

# 종합 판정
- HOTFIX 4건 중 Post-deploy 안정성 문제 M 건수: X
- Advisory 권고 건수: Y
- 각 HOTFIX 별로 **BACKLOG close 가능 여부**:
  - PHASE1.5: Close / Keep
  - SCHEMA-RESTORE: Close / Keep
  - DUP: Close / Keep
  - DELIVERY: Close / Keep
- 별도 새 Sprint 발굴 필요 (기존 OBSERV-* 이외): Y/N
```

## CRITICAL RULES

- **침묵 승인 금지** — "LGTM" / "문제 없음" 류 한 줄 응답 시 자동 재질문
- **독립 검증** — Claude Opus 의 v2.9.11 커밋 선택/구조를 비판적 재검증
- **Challenge mode** — 48h 경과 상태라 재발 없음이 확인됐지만, corner case 는 여전히 남아있을 수 있음. "이미 안정화됨" 이라는 이유로 Advisory 회피 금지
- **근거 필수** — 각 Q 답변에 file:line 또는 EXPLAIN/로그 예시 포함
- **Scope** — HOTFIX 4건 + 공통 참조 자료만. 별도 Sprint (62-BE / 55 / 34 등) 로 확장 금지

Begin the review.
