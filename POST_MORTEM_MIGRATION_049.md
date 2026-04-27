# Post-Mortem: Migration 049 prod 미적용 원인 조사

> **사건**: 2026-04-17 ~ 2026-04-22 사이 Railway prod 에 `049_alert_escalation_expansion.sql` 자동 적용 누락 → 5일간 알람 시스템 일부 기능 (TASK_NOT_STARTED, CHECKLIST_DONE_TASK_OPEN, ORPHAN_ON_FINAL) silent failure
> **복구**: 2026-04-22 11:25 KST `HOTFIX-ALERT-SCHEMA-RESTORE` SQL 수동 실행 (5 블록)
> **본 보고서**: 자동 적용 누락 원인 조사 + 재발 방지 권장
> **작성일**: 2026-04-27 KST
> **상태**: 결정적 원인 미확정 + 재발 방지 권장

---

## 1. 사실 관계

### Migration 049 내용 (`backend/migrations/049_alert_escalation_expansion.sql`)

```sql
ALTER TYPE alert_type_enum ADD VALUE IF NOT EXISTS 'TASK_NOT_STARTED';
ALTER TYPE alert_type_enum ADD VALUE IF NOT EXISTS 'CHECKLIST_DONE_TASK_OPEN';
ALTER TYPE alert_type_enum ADD VALUE IF NOT EXISTS 'ORPHAN_ON_FINAL';

ALTER TABLE app_alert_logs ADD COLUMN IF NOT EXISTS task_detail_id INTEGER NULL;
CREATE INDEX IF NOT EXISTS idx_alert_logs_dedupe
    ON app_alert_logs (alert_type, serial_number, task_detail_id)
    WHERE task_detail_id IS NOT NULL;

INSERT INTO admin_settings (setting_key, setting_value) VALUES
  ('alert_task_not_started_enabled', 'true'),
  ('alert_checklist_done_task_open_enabled', 'true'),
  ('alert_orphan_on_final_enabled', 'true'),
  ('task_not_started_threshold_days', '2')
ON CONFLICT (setting_key) DO NOTHING;
```

→ 6개 statement, 모두 `IF NOT EXISTS` / `ON CONFLICT` 로 idempotent.

### 시점 추적 (2026-04-17 ~ 2026-04-22)

| 날짜 | 이벤트 | 증거 |
|---|---|---|
| 2026-04-17 | Sprint 61-BE 완료, 049 commit + push | BACKLOG L297 |
| 2026-04-17 ~ 04-22 | Railway prod 자동 배포 N회 | git log |
| ~04-22 | 알람 silent failure 5일 누적 (52건 NULL) | HOTFIX-ALERT-SCHEDULER-DELIVERY 진단 |
| 2026-04-22 11:25 | HOTFIX-ALERT-SCHEMA-RESTORE 수동 SQL 실행 | migration_history 049 record |
| 2026-04-22 | Q1 검증: `migration_history max id=36, 049 기록 없음` | handoff.md L453 |

### migration_history 현재 상태 (2026-04-27 측정)

```
047_elec_checklist_seed_fix.sql    | 2026-04-10 11:27:20  ✅ 자동
048_elec_master_normalization.sql  | 2026-04-15 23:06:52  ✅ 자동
049_alert_escalation_expansion.sql | 2026-04-22 11:25:17  ⚠️ HOTFIX 수동
050_factory_kpi_indexes.sql        | 2026-04-23 13:38:08  ✅ 자동
```

→ 047/048 정상 자동 적용. **049 만 자동 누락** + 050 정상 자동.

---

## 2. 4가지 가설 검증

### 가설 ① — DATABASE_URL 분기 (test vs prod) ❌ **기각**

**가설**: Railway 환경변수가 4-17~22 사이에 다른 DB 를 가리켰을 가능성.

**검증**:
- Railway DATABASE_URL 단일. `maglev.proxy.rlwy.net:38813/railway` 도메인.
- 환경변수 history 추적 어렵지만 구조상 staging/prod 분리 없음 (단일 Railway DB).
- 같은 시점 047/048 은 정상 적용 → 같은 DB 가리킴.

**결론**: ❌ **기각**.

### 가설 ② — migration_runner idempotent 판정 버그 ❌ **기각**

**가설**: `_get_executed()` 또는 `pending` 계산 로직 버그.

**검증**:
```python
# migration_runner.py L41-44
def _get_executed(cur) -> set:
    cur.execute("SELECT filename FROM migration_history")
    return {row[0] for row in cur.fetchall()}

# L66-74
executed = _get_executed(cur)
files = sorted([f for f in os.listdir(MIGRATIONS_DIR) if _FILE_PATTERN.match(f)], key=_sort_key)
pending = [f for f in files if f not in executed]
```

→ filename set 비교만. 049 가 `migration_history` 에 없고 `MIGRATIONS_DIR` 에 있으면 pending 에 포함됨.

**결론**: ❌ 코드 버그 없음. **기각**.

### 가설 ③ — 047/048 간 runtime 오류로 049 skip ❌ **모순**

**가설**: migration_runner.py L116-118 의 `raise` 로 이후 migration skip.

**검증**:
- 047 (4-10), 048 (4-15) 정상 적용 → raise 발생 안 함.
- 만약 049 실행 중 raise → 050 도 미적용 상태여야 함.
- 그러나 050 도 정상 자동 적용 (4-23) → **모순**.
- 즉 049 실패 → 050 가 다음 배포에서 별도 시도된 흐름.
- 그런데 그 다음 배포에서 049 + 050 모두 pending 에 들어갔어야 → 049 도 함께 적용되어야.

**결론**: ❌ **모순**으로 기각. raise 가설은 049 만 단독 누락 설명 못 함.

### 가설 ④ — Docker artifact / build 캐시 ⭐ **가장 유력**

**가설**: Sprint 61-BE 배포 시 Docker image 에 049 파일이 포함되지 않음.

**시나리오**:
1. 4-17 commit + push → Railway 자동 빌드
2. Railway buildkit 이 `backend/migrations/` 디렉토리를 **캐시** 에서 가져옴 (이전 image layer)
3. 결과: image 안에 049 파일 없음 → `os.listdir(MIGRATIONS_DIR)` 결과 049 미포함
4. migration_runner 는 049 가 존재하지 않으니 처리 안 함
5. 4-22 까지 5일간 같은 image 사용 (재배포 시도가 캐시로 같은 결과)
6. HOTFIX-ALERT-SCHEMA-RESTORE 수동 SQL 후 정상 복구
7. Sprint 62-BE (4-23 050 추가 시) **새 image 빌드** 시 캐시 무효화 → 050 정상 포함
8. 다만 이 시점에 049 는 이미 수동 적용됨 → migration_history 있음 → skip

**증거**:
- Codex POST-REVIEW 판정 (BACKLOG L324): "prod artifact/deploy-path 문제 가장 유력"
- 같은 시점 047/048 는 적용됨 → 이전 image layer 에 포함됨
- 050 은 4-23 정상 자동 → 새 image 에 포함

**검증 한계**:
- 4-17 ~ 4-22 Railway image build log 무료 tier 보존 X
- 결정적 증거 (그 시점 image 안의 migrations 디렉토리 listing) 확보 어려움

**결론**: ⭐ **가장 유력** (Codex 판정 일치). 결정적 입증은 어렵지만 다른 가설 모두 기각된 후 남는 가능성.

---

## 3. 재발 방지 권장 (Top 3)

### 권장 ① — migration_runner startup assertion ⭐ 핵심

**목적**: 앱 시작 시 expected vs actual migration count 비교. 누락 즉시 감지.

**구현**:
```python
# migration_runner.py 에 새 함수 추가
def assert_migrations_in_sync() -> None:
    """앱 시작 시 코드와 DB 의 migration 동기화 상태 검증."""
    if not os.path.isdir(MIGRATIONS_DIR):
        return
    
    files_in_disk = {f for f in os.listdir(MIGRATIONS_DIR) if _FILE_PATTERN.match(f)}
    
    conn = get_conn()
    try:
        cur = conn.cursor()
        executed = _get_executed(cur)
    finally:
        put_conn(conn)
    
    missing_from_disk = executed - files_in_disk
    not_yet_applied = files_in_disk - executed
    
    if missing_from_disk:
        logger.error(f"[migration-assert] DB 에 적용됐지만 코드에 없음: {missing_from_disk}")
    if not_yet_applied:
        logger.error(f"[migration-assert] 코드에 있지만 DB 미적용: {not_yet_applied}")
        # ⚠️ 이게 바로 049 같은 silent gap. Sentry capture_exception 권장
    else:
        logger.info(f"[migration-assert] sync OK ({len(executed)} migrations)")
```

→ `__init__.py` create_app() 안에서 `run_migrations()` 직후 호출.

**관련 BACKLOG**: `OBSERV-MIGRATION-RUNNER-STARTUP-ASSERTION` 🟡 P2 (이미 등록됨)

### 권장 ② — migration 실패 Sentry capture

**목적**: migration 실행 중 예외 발생 시 Sentry 자동 capture → 즉시 알림.

**구현**:
```python
# migration_runner.py L115-118 변경
except Exception as e:
    logger.error(f"[migration] ❌ {filename} 실행 실패: {e}")
    try:
        import sentry_sdk
        sentry_sdk.capture_exception(e)
    except ImportError:
        pass  # Sentry 미설치 환경
    raise
```

→ `OBSERV-ALERT-SILENT-FAIL` (Sentry 정식 연동) 와 통합 가능.

### 권장 ③ — deploy 후 자동 health check

**목적**: 배포 완료 후 alert API 정상 작동 검증.

**구현**:
- Railway deploy hook 또는 GitHub Actions
- `/api/admin/alert-health` 같은 endpoint 신설 (alert_type_enum 값 + admin_settings 키 + index 존재 검증)
- 미달 시 Slack/이메일 알림

**관련 BACKLOG 신규**: `INFRA-DEPLOY-HEALTH-CHECK-20260427` 🟡 P3 (선택적)

---

## 4. 결론

### 원인 (가설 기반)

- **결정적 원인 미확정** (4-17~22 Railway logs 접근 한계)
- **가장 유력**: Docker artifact / Railway build cache 로 049 파일이 image 에 누락 (가설 ④)
- 다른 3가지 가설은 검증으로 기각

### 영향 (이미 복구됨)

- 5일간 알람 시스템 silent failure (52건 NULL delivery)
- 2026-04-22 11:25 HOTFIX-ALERT-SCHEMA-RESTORE 로 완전 복구
- 후속 HOTFIX-ALERT-SCHEDULER-DELIVERY (v2.9.11), FIX-ORPHAN-ON-FINAL-DELIVERY (v2.10.3) 도 종결

### 재발 방지

| 우선순위 | 항목 | 예상 소요 |
|:---:|:---|:---:|
| 🔴 핵심 | `OBSERV-MIGRATION-RUNNER-STARTUP-ASSERTION` (권장 ①) | 1h |
| 🟡 통합 | `OBSERV-ALERT-SILENT-FAIL` 와 통합 (권장 ②) | Sentry 작업에 포함 |
| 🟢 선택 | `INFRA-DEPLOY-HEALTH-CHECK` 신규 (권장 ③) | 2~3h |

### 본 POST-REVIEW 종결 조치

- ✅ 4가지 가설 전수 검증 완료
- ✅ 결정적 원인 미확정 명시 + 가장 유력 가설 (가설 ④) 명시
- ✅ 재발 방지 권장 3건 제시
- 🟡 권장 ① 진행은 별건 BACKLOG (`OBSERV-MIGRATION-RUNNER-STARTUP-ASSERTION` 이미 등록)
- 🟡 권장 ② 는 `OBSERV-ALERT-SILENT-FAIL` 진행 시 통합

→ **본 POST_MORTEM 보고서 산출로 BACKLOG `POST-REVIEW-MIGRATION-049-NOT-APPLIED` COMPLETED**.

---

## 5. 참조

- `backend/app/migration_runner.py` (Sprint 45 INFRA-1 산출물)
- `backend/migrations/049_alert_escalation_expansion.sql`
- `BACKLOG.md` L319/324/333 — 관련 entry
- `handoff.md` L453, L461 — 4-22 HOTFIX 진단 + 수동 복구 SQL 5 블록
- `ALERT_SCHEDULER_DIAGNOSIS.md` (있다면 §12.5/§13)
- Codex POST-REVIEW Phase A Q2-2 판정 (BACKLOG L324)
