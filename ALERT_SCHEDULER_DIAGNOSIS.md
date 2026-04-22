# Alert Scheduler 장애 진단 플랜

> **작성**: 2026-04-21 심야 (2026-04-22 출근 후 진행)
> **증상**: `app_alert_logs` 에 **2026-04-17 이후 5일간 0건**. 마지막 알람 id 657, `RELAY_ORPHAN`, 2026-04-16 21:00:00
> **우선순위**: 🔴 긴급 — 운영 알람 시스템 완전 정지
> **관련 배포**: 2026-04-17 Sprint 61-BE + Sprint 61-BE-B + HOTFIX-01/02/03/04/05 (6건 연속)

---

## 1. 확정된 사실

| 항목 | 값 |
|------|----|
| 마지막 알람 id | 657 |
| 마지막 알람 시각 | 2026-04-16 21:00:00.989+09 |
| 마지막 알람 타입 | RELAY_ORPHAN (`check_orphan_relay_tasks_job`) |
| 누적 기간 | 4/17 ~ 현재 (5일+) |
| 일자별 건수 | 4/10=17, 4/11=12, 4/12=13, 4/13=15, 4/14=23, 4/15=17, **4/16=60**, 4/17~=0 |
| 4/17 이후 배포 횟수 | 여러 번 (HOTFIX 5건 + FIX-24 + FIX-25 + 문서 커밋) |
| 재배포로 복구 안 됨 | 확인됨 — 원인이 결정론적으로 재현 |

---

## 2. 원인 후보 (재배포 무효를 설명 가능한 것만)

**배제됨**:
- ❌ `_SCHEDULER_STARTED` env persist — 매 deploy마다 새 container, env 초기화됨
- ❌ 일회성 thread death — 매번 반복 안 됨

**남은 3가지**:

### 후보 A (가장 유력): migration 049 silent fail
- `ALTER TYPE alert_type_enum ADD VALUE IF NOT EXISTS 'TASK_NOT_STARTED'` 는 PostgreSQL에서 **transaction block 안에서 실행 불가** 제약 존재
- `migration_runner.py` 가 transaction 감싸면 049 실패
- 결과: enum 3종 미등록 → 알람 생성 시 DB 제약 위반 → `create_alert()` 가 예외 → try/except 로 삼켜짐 → 로그만 찍히고 0건 insert
- 매 배포마다 같은 migration 재시도 + 같은 실패 → 결정론적 재현

### 후보 B: Scheduler 정상 실행, 쿼리만 0건 반환
- Sprint 61-BE 또는 61-BE-B(BUG-44 LATERAL JOIN) 변경이 scheduler 내부 쿼리에 영향
- job은 정상 실행되지만 `SELECT` 결과 0건 → INSERT 없음
- 로그에는 "Running X job" 찍히고 에러 없음

### 후보 C: Scheduler 부팅 자체 실패
- `__init__.py:70-78` 스케줄러 초기화 경로가 Gunicorn preload 환경에서 문제
- 앱은 살아있지만 BackgroundScheduler 가 start 안 됨
- 로그: "Scheduler initialized" / "Scheduler started" 메시지 누락

---

## 3. 진단 쿼리 (Railway Data tab 에서 순서대로 실행)

### Q1. migration 049 적용 여부
```sql
SELECT filename, applied_at, success, error_message
FROM migration_history
WHERE filename LIKE '%049%' OR filename LIKE '%escalation%' OR filename LIKE '%alert%'
ORDER BY applied_at DESC;
```
- 049 가 applied_at NULL 이거나 success=false → **후보 A 확정**

### Q2. alert_type_enum 신규 3종 존재
```sql
SELECT enumlabel
FROM pg_enum
WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'alert_type_enum')
ORDER BY enumsortorder;
```
- 기대값: `TASK_NOT_STARTED`, `CHECKLIST_DONE_TASK_OPEN`, `ORPHAN_ON_FINAL` 포함 15~20건
- 없으면 **후보 A 확정**

### Q3. admin_settings 알람 토글
```sql
SELECT setting_key, setting_value, updated_at
FROM admin_settings
WHERE setting_key LIKE 'alert_%' OR setting_key LIKE '%_enabled'
ORDER BY setting_key;
```
- 전부 false 또는 누락 → 후보 B 의심
- alert_task_not_started_enabled 가 'true' 여야 정상

### Q4. 진행 중 task 실존 여부 (알람 대상 있는지)
```sql
SELECT
  COUNT(*) FILTER (WHERE started_at IS NOT NULL AND completed_at IS NULL) AS active,
  COUNT(*) FILTER (WHERE started_at IS NULL AND completed_at IS NULL) AS not_started,
  COUNT(*) FILTER (WHERE completed_at IS NOT NULL) AS completed
FROM app_task_details;
```
- active 가 0 에 가까우면 task_reminder 대상 없음 (정상적으로 0 알람일 수도)
- active 가 많은데 알람 0 → **후보 A 또는 B 확정**

### Q5. task_detail_id 컬럼 존재 확인
```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'app_alert_logs' AND table_schema = 'public'
ORDER BY ordinal_position;
```
- `task_detail_id` 컬럼 없으면 migration 049 부분 실패 → **후보 A 확정**

### Q6. Orphan task 실존 — 현재 시점 (빠른 스냅샷, 2026-04-22 추가)
```sql
-- check_orphan_relay_tasks_job 가 INSERT 대상으로 삼는 조건 직접 실행 (현재 시각 기준)
SELECT
  COUNT(*) AS orphan_count,
  MIN(started_at) AS oldest_started,
  COUNT(DISTINCT serial_number) AS distinct_sn
FROM app_task_details
WHERE started_at IS NOT NULL
  AND completed_at IS NULL
  AND started_at < NOW() - INTERVAL '4 hours';
```
- ⚠️ **시점 제약**: `NOW()` 기준 = **현재 순간**만 반영. 4-17 이후 5일간의 과거 상태는 확인 불가
- 반드시 **Q6-HIST 와 병행 실행** 필요

### Q6-HIST. Orphan task 과거 히스토리 복원 (🔴 **핵심**, Codex 지적 반영 — 2026-04-22 추가)

> **왜 필요한가**: Q6 는 현재 스냅샷만 본다. 4-17 이후 5일간 매 정각마다 cron job 이 SELECT 한 시점에 실제로 orphan 이 있었는지 복원해야 가능성 1/2 판정의 객관 근거가 확보됨. Interview 없이 데이터로 현장 영향 확정 가능.

```sql
-- 4-17 00:00 KST ~ 현재까지 매 시간 정각 시점의 orphan 개수 재구성
-- 각 시점에 "started_at < 시점 - 4시간 AND (completed_at IS NULL OR completed_at > 시점)" 이면 그 시점의 orphan
WITH hourly_times AS (
  SELECT generate_series(
    '2026-04-17 00:00:00+09'::timestamptz,
    NOW(),
    INTERVAL '1 hour'
  ) AS check_time
)
SELECT
  h.check_time,
  COUNT(*) FILTER (
    WHERE td.started_at IS NOT NULL
      AND td.started_at < h.check_time - INTERVAL '4 hours'
      AND (td.completed_at IS NULL OR td.completed_at > h.check_time)
  ) AS orphan_count_at_time
FROM hourly_times h
CROSS JOIN app_task_details td
GROUP BY h.check_time
HAVING COUNT(*) FILTER (
    WHERE td.started_at IS NOT NULL
      AND td.started_at < h.check_time - INTERVAL '4 hours'
      AND (td.completed_at IS NULL OR td.completed_at > h.check_time)
  ) > 0
ORDER BY h.check_time;
```
- 결과가 **비어있음** (모든 시점 0건) → **가능성 1 확정** (실제 장애 아님, 현장 패턴 반영)
- 결과에 **시점 다수 행** 존재 → **가능성 2 확정** (실제 orphan 있었는데 cron job 이 놓침 = 쿼리 버그)
- 결과가 **일부 시점만** 존재 → 해당 시점의 알람 누락 = 가능성 2 부분 확정

**주의**: 데이터 볼륨이 크면 `app_task_details(started_at, completed_at)` 인덱스 확인 후 실행. 30초~2분 예상.

### Q7. Active task 실존 여부 (task_reminder_job 대상 — 2026-04-22 추가)
```sql
SELECT
  COUNT(*) AS active_count,
  MIN(started_at) AS oldest_started
FROM app_task_details
WHERE started_at IS NOT NULL
  AND completed_at IS NULL;
```
- active_count = 0 → 가능성 1
- active_count > 0 인데 알람 0건 → task_reminder 쿼리 버그 (Q8 검증)

### Q8. worker_id NULL 분포 (Sprint 55 Worker별 Pause 영향 — 2026-04-22 추가)
```sql
SELECT
  COUNT(*) FILTER (WHERE worker_id IS NOT NULL) AS with_worker,
  COUNT(*) FILTER (WHERE worker_id IS NULL) AS without_worker
FROM app_task_details
WHERE started_at IS NOT NULL AND completed_at IS NULL;
```
- without_worker 다수 → Sprint 55 worker_id 필터가 과도하게 엄격 → 알람 대상 놓침

---

## 4. Railway 로그 검색 (진단 쿼리와 병행)

**OPS BE service → Logs 탭**, 최근 24시간 범위에서 검색:

| 검색어 | 정상 동작 | 없으면 의미 |
|--------|---------|-----------|
| `Scheduler initialized with 11 jobs` | init_scheduler() 완료 | 후보 C 또는 A |
| `Scheduler started` | start_scheduler() 완료 | 후보 C 확정 |
| `Scheduler already running in another worker, skipping` | 있음 = 후보 C 서브케이스 | — |
| `Running task_reminder_job` (시간별) | job 정상 실행 | 없으면 후보 C |
| `Running check_orphan_relay_tasks_job` (시간별) | 매 정각 실행 | 없으면 후보 C |
| `migration` + `ERROR` | — | 있으면 후보 A 확정 |
| `Unfinished task check job failed` | 있으면 job 내부 예외 | 로그 내용 확인 |

---

## 5. 후보별 복구 조치

### 후보 A 확정 시
```sql
-- Option 1: autocommit 으로 migration 049 수동 실행
-- (pgAdmin Query Tool 에서 각 문장을 개별 실행)

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

-- migration_history 에 성공 기록 수동 삽입
INSERT INTO migration_history (filename, applied_at, success)
VALUES ('049_alert_escalation_expansion.sql', NOW(), true)
ON CONFLICT DO NOTHING;
```
후속: `migration_runner.py` 에 `ALTER TYPE` 계열은 autocommit 실행하도록 가드 추가

### 후보 B 확정 시
- scheduler job 함수 5~6개 쿼리 리뷰 (Sprint 61-BE-B LATERAL JOIN 영향 확인)
- `check_orphan_relay_tasks_job`, `task_reminder_job` 등 WHERE 절 diff 확인
- 원인 쿼리 수정 후 hotfix 배포

### 후보 C 확정 시
- `__init__.py:70-78` 가드 로직 단순화
- `_SCHEDULER_STARTED` 판단을 Gunicorn pre_fork hook 으로 이관
- Flask-APScheduler 등 안정 라이브러리 대체 검토

---

## 6. 부가 조치 (후보 무관)

### 모니터링 추가
- `/api/admin/scheduler/status` 엔드포인트 신설 — 현재 등록된 job 목록 + 다음 실행 시각 노출
- Railway 외부 monitoring 에서 주기적으로 호출 (일간 알람 0건이면 Slack 알림)

### 알람 생성 실패 감지
- `create_and_broadcast_alert()` try/except 내부에서 에러 로그 **ERROR 레벨 + Sentry 연동** 권장
- 현재 silent fail 패턴이 원인 추적을 늦춤

---

## 7. 내일 세션 시작 시 프롬프트 예시

```
AXIS-OPS/ALERT_SCHEDULER_DIAGNOSIS.md 읽고 진단 Q1~Q5 쿼리 돌려줘.
Railway 로그도 내가 확인해서 결과 알려줄게.
```

---

## 8. 연관 문서

- `BACKLOG.md` Sprint 61-BE / 61-BE-B / BUG-44 / HOTFIX-01~05 상세
- `backend/migrations/049_alert_escalation_expansion.sql`
- `backend/app/services/scheduler_service.py` (11 jobs 등록)
- `backend/app/services/alert_service.py` (`sn_label`, `create_and_broadcast_alert`)
- `backend/app/__init__.py:70-78` (scheduler 초기화 경로)
- `tests/backend/test_alert_all20_verify.py` (38 TC, Sprint TEST-AL20)
- `DB_ROTATION_PLAN.md` (병행 보안 작업)

---

## 9. 2026-04-22 심층 진단 (Claude Cowork 코드 레벨 분석)

> Twin파파가 pgAdmin에서 실측한 `app_alert_logs` 데이터 3종(일자별 count, 최신 5건 타입, 4-16 상세)을 근거로 코드 5개 파일(`__init__.py`, `scheduler_service.py`, `alert_service.py`, `models/alert_log.py`, `migration_runner.py`, `migrations/049`) 정적 분석 교차 검증.

### 9.1 Twin파파 DB 증거 요약 (2026-04-22 스크린샷)

**쿼리 결과 1 — 일자별 분포**:
| 날짜 | 건수 | 타입 수 |
|---|---|---|
| 4-10 | 17 | 4 |
| 4-11 | 12 | 2 |
| 4-12 | 13 | 2 |
| 4-13 | 15 | 3 |
| 4-14 | 23 | 4 |
| 4-15 | 17 | 3 |
| **4-16** | **60** | **3** |
| 4-17~4-22 | **0** | — |

**쿼리 결과 2 — 최신 5건 (id 653~657)**: 전부 `RELAY_ORPHAN`, 2026-04-16 21:00:00.84~0.99 (1초 이내 연달아 생성)

**쿼리 결과 3 — 마지막 15건(id 322~336)**: 전부 `target_role=TMS`, alert_type `RELAY_ORPHAN`, message "[릴레이 미완료] GBWS-XXXX Tank Module — 작업자 1명 참여 후 4시간 이상 미완료 상태입니다"

### 9.2 코드 정적 분석 결과 (파일별 증거)

#### 9.2.1 `backend/app/__init__.py` L70-78 — 스케줄러 초기화
```python
if not app.config.get('TESTING', False):
    if not os.environ.get('_SCHEDULER_STARTED'):
        os.environ['_SCHEDULER_STARTED'] = '1'
        init_scheduler()
        start_scheduler()
```
- Gunicorn multi-worker에서 첫 worker만 스케줄러 시작 (중복 방지)
- 컨테이너 재시작 시 env 초기화되므로 재배포 시 정상 재시작 **되어야 함**
- 재배포 무효 사실과 모순 → 다른 원인 존재

#### 9.2.2 `backend/app/services/scheduler_service.py` — 11 jobs 등록 (L54-148)
```
1. task_reminder_job           — CronTrigger(minute=0)     매 1시간 정각
2. check_unfinished_tasks      — CronTrigger(hour=18)      매일 18:00
3. shift_end_reminder_17       — CronTrigger(hour=17)
4. shift_end_reminder_20       — CronTrigger(hour=20)
5. task_escalation_job         — CronTrigger(hour=9)       매일 09:00
6. check_break_time_job        — CronTrigger(second=0)     매 분
7. cleanup_access_logs         — CronTrigger(hour=3)       매일 03:00
8. check_orphan_relay_tasks    — CronTrigger(minute=0)     매 1시간 정각 (Sprint 41-B)
9. check_not_started_tasks     — CronTrigger(hour=9)       매일 09:00 (Sprint 61-BE)
10. check_checklist_done_09    — CronTrigger(hour=9)       매일 09:00 (Sprint 61-BE)
11. check_checklist_done_15    — CronTrigger(hour=15)      매일 15:00 (Sprint 61-BE)
```
- BackgroundScheduler 단일 인스턴스 (L51)
- misfire_grace_time 설정 **없음** (APScheduler 기본값 = 1초) 🔴 **중요**

#### 9.2.3 `backend/app/models/alert_log.py` L113-126 — INSERT 쿼리
```sql
INSERT INTO app_alert_logs (
    alert_type, serial_number, qr_doc_id,
    triggered_by_worker_id, target_worker_id, target_role, message,
    task_detail_id          ← 8번째 컬럼
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
```
- `task_detail_id` 컬럼 **명시적 참조**
- 컬럼 부재 시 모든 INSERT가 PsycopgError → silent fail (`return None`)

#### 9.2.4 `backend/app/migration_runner.py` L83-122 — autocommit + 정교한 분할
```python
m_conn.autocommit = True   # ENUM ADD VALUE 호환
statements = _split_statements(sql)  # 세미콜론 기준 (dollar quote + single quote 처리)
for stmt in statements:
    m_cur.execute(stmt)
```
- `_split_statements()` 함수(L137-210): 달러 인용·단일 인용·라인 주석 모두 정교 처리
- PostgreSQL 15에서 `ALTER TYPE ADD VALUE IF NOT EXISTS`는 autocommit 하에 안전

#### 9.2.5 `backend/migrations/049_alert_escalation_expansion.sql` — 6 statements
```sql
ALTER TYPE alert_type_enum ADD VALUE IF NOT EXISTS 'TASK_NOT_STARTED';
ALTER TYPE alert_type_enum ADD VALUE IF NOT EXISTS 'CHECKLIST_DONE_TASK_OPEN';
ALTER TYPE alert_type_enum ADD VALUE IF NOT EXISTS 'ORPHAN_ON_FINAL';
ALTER TABLE app_alert_logs ADD COLUMN IF NOT EXISTS task_detail_id INTEGER NULL;
CREATE INDEX IF NOT EXISTS idx_alert_logs_dedupe ...;
INSERT INTO admin_settings ... ON CONFLICT DO NOTHING;
```
- 단순·안전 구조. IF NOT EXISTS로 재실행 멱등성 확보.

### 9.3 후보 재평가 (리뷰어 지적 반영 — 2026-04-22 2차 개정)

> ⚠️ 1차 진단(§9.4)에서 후보 D를 "최유력"으로 표기했으나 리뷰어 반박 수용하여 **강등**. Procfile 실측 증거 기반으로 후보 E 상위, 후보 F 신규 추가.

**Procfile 실측 결과**:
```
web: gunicorn --bind 0.0.0.0:$PORT --worker-class gthread --threads 8 -w 2 --timeout 30 --graceful-timeout 10 "app:create_app()"
```
- `-w 2` = multi-worker / `--preload` 없음 / `--timeout 30` = worker recycling 가능 조건 성립

**후보 재평가표**:

| 후보 | 1차 평가 | 2차 재평가 | 근거 |
|---|---|---|---|
| **A** migration 049 silent fail | 🔴 | 🟢 **약화 유지** | 4-16 RELAY_ORPHAN 60건 INSERT 성공 = `task_detail_id` 컬럼 존재 |
| **B** 쿼리 0건 반환 | 🟡 | 🟡 **부분 유효 유지** | `worker_id IS NOT NULL` 필터 영향 있을 수 있으나 RELAY_ORPHAN 0건 설명 불가 |
| **C** 스케줄러 부팅 실패 | 🟠 | 🟠 **유지** | 배포 초 시점 부팅 실패 + Railway 로그로 확정 가능 |
| **D** APScheduler misfire + Railway sleep | 🔴 신규 최유력 | 🟢 **강등** | Railway는 기본 sleep 정책 없음(§9.4 리뷰어 반박 3건 반영) — 가능성 낮음 |
| **E** 🆕 Gunicorn worker recycling + env 가드 oneshot | — | 🔴 **신규 최유력** | 리뷰어 가설 + Procfile 증거 — §9.4a 상세 |
| **F** 🆕 DB connection pool 고갈 / thread deadlock | — | 🟠 **신규 병행 의심** | job 내 `put_conn` 누락 시 pool 고갈 → 모든 job 영구 block + Flask 정상 응답 패턴과 부합 — §9.4b 상세 |

### 9.4 후보 D 반박 (리뷰어 지적 수용)

**반박 논거 3가지** (리뷰어 제공):
1. **Railway는 기본 sleep 정책 없음** — Hobby plan 이상에서 idle 시에도 컨테이너 계속 실행. Heroku/Replit free tier와 구조 다름
2. **BackgroundScheduler는 Flask 프로세스 내부 thread** — Flask가 HTTP 응답 중이면 같은 프로세스의 scheduler thread도 live여야 정상
3. **misfire_grace_time=1초가 정각 실행을 막는다는 전제 오류** — APScheduler는 내부 wait/sleep으로 다음 job까지 대기하므로 정밀도 문제 아님

**추가 반례**:
- 컨테이너 sleep이면 `/api/health` 응답도 sleep-wake 지연 패턴 보여야 하는데 운영 중 그런 보고 없음
- 4-16 60건 급증은 §9.5 대안 해석(정상 threshold 일시 통과)으로도 설명 가능

**결론**: 후보 D는 Railway 컨텍스트에서 **부적합**. `misfire_grace_time` 수정은 **단독으로는 효과 불확실**하나 부가 방어로만 포함.

### 9.4a 🆕 후보 E — Gunicorn worker recycling + env 가드 oneshot (리뷰어 가설, 현재 최유력)

**가설**: `_SCHEDULER_STARTED` env 가드가 master→worker 상속 구조에서 **oneshot 효과**를 냄. 스케줄러 보유 worker가 recycled되면 후속 worker들은 env 가드로 skip → 프로세스 live / scheduler dead.

**메커니즘**:
```
1. Railway 컨테이너 시작
2. Gunicorn master fork worker 1 → create_app() → env 가드 pass → 스케줄러 시작
3. master fork worker 2 → create_app() → env=1 상속/동일 프로세스 env 체크에 따라 skip
4. worker 1이 max_requests / timeout / OOM으로 recycled
5. master가 새 worker fork → master env (또는 상속 체인)에 _SCHEDULER_STARTED=1 남아있음 → skip
6. 결과: 어떤 worker에도 scheduler thread 없음
7. Flask/Gunicorn은 정상 응답 / 알람만 0건
8. 재배포도 동일 경로 반복 → 결정론적 재현
```

**증거**:
1. **Procfile `-w 2 --timeout 30`** — recycling 조건 성립 (timeout exceed 시 worker kill)
2. **재배포 무효** = 프로세스 start-up의 결정론적 실패 경로
3. **Flask 정상 / scheduler만 dead** = thread 레벨 종료 + 재시작 실패
4. **`_SCHEDULER_STARTED` env 가드** (`__init__.py` L72): master→worker 상속 시 재fork 후에도 persist

**확인 방법** (Railway 로그 최근 24시간):
| 검색어 | 해석 |
|---|---|
| `Scheduler already running in another worker, skipping` 횟수 | **많이 뜨면 후보 E 확정** |
| `Scheduler initialized with 11 jobs` 최근 배포에서 몇 번 | **0~1회만이면 후보 E 강력 의심** |
| `[CRITICAL] WORKER TIMEOUT` 또는 `Worker exited` | worker recycling 증거 |

### 9.4b 🆕 후보 F — DB connection pool 고갈 / thread deadlock (병행 의심)

**가설**: 스케줄러 job 내부에서 `put_conn` 누락 또는 예외 경로에서 conn 미반환 → Sprint 30 도입 DB pool 고갈 → 이후 모든 `get_conn()` 영구 block → scheduler thread가 살아있지만 job 실행 불가.

**증거 후보** (추가 검증 필요):
- `scheduler_service.py` 각 job의 try/finally put_conn 패턴 전수 검토 필요
- 4-16 21:00 시점에 RELAY_ORPHAN 60건이 **1초 이내** 생성됨 = 짧은 시간에 60회 conn 획득/반환 반복 = pool stress 상황
- 이후 갑자기 0건 = pool 고갈 시점과 부합

**구분 진단**:
- 후보 E면 Railway 로그에 "Scheduler already running" 다수
- 후보 F면 Railway 로그에 **"Pool exhausted" / "connection timeout"** 메시지 또는 Flask 요청 일부도 느려짐

### 9.5 "4-16 60건 급증 + RELAY_ORPHAN 편중" 현상 — 대안 해석

**1차 해석** (후보 D 기반, 부분 철회):
- APScheduler catch-up으로 누적분 토출 → **Railway sleep 전제 오류로 약화**

**2차 해석** (리뷰어 제안, 더 유력):
- **그날 오후 작업된 60개 task가 일시에 4시간 threshold 통과** = `check_orphan_relay_tasks_job`의 정상 동작
- 실제 현장 패턴: 오후 2~3시 릴레이 작업 활발 → 17~18시 이후 task 완료 못 한 상태 누적 → 21:00 정각 job 실행 시 4시간 threshold 대량 통과
- 60건이 **1초 이내 생성**은 단일 job 1회 실행 내 loop = 정상 동작
- 즉 4-16 21:00은 **"마지막 정상 실행 시점"**이고 특이 현상 아님

**4-17 이후 0건의 의미**:
- 4-16 21:00 실행 직후 뭔가 발생(worker recycling or pool 고갈) → 이후 모든 job 실행 안 됨
- 후보 E 또는 후보 F의 트리거 시점이 4-16 21:00 전후

### 9.6 확정 진단을 위한 즉시 실행 항목 (리뷰어 제안 반영)

**Phase 1 — Railway 로그 검색 (10분, 최우선)**:

아래 3개 문구만 확인하면 후보 E/D/C 판정 가능:

| # | 검색어 | 해석 |
|---|---|---|
| 1 | `Scheduler already running in another worker, skipping` 발생 횟수 | **많으면 후보 E 확정** |
| 2 | `Scheduler initialized with 11 jobs` 최근 배포 시 횟수 | **0~1회만이면 후보 E 강력 의심** (multi-worker에서 여러 번 나와야 정상) |
| 3 | `Run time of job ... was missed` 또는 `misfire` 키워드 | **있으면 후보 D 부활**, 없으면 후보 D 확정 기각 |

**보조 검색**:
| 검색어 | 해석 |
|---|---|
| `Scheduler started` 최근 횟수 | 0이면 후보 C (부팅 실패) |
| `[CRITICAL] WORKER TIMEOUT` / `Worker exited` | 있으면 후보 E 메커니즘 증거 (worker recycling) |
| `Pool exhausted` / `connection timeout` | 있으면 **후보 F 확정** |
| `Running task_reminder_job` 매 정각 있는지 | 마지막 실행 시각 확인 (4-16 21:00 vs 그 이후) |
| `ALTER TYPE` + `ERROR` + `migration_runner` | 후보 A 부분 확정 (가능성 낮음) |

**Phase 2 — DB 진단 쿼리** (기존 §3 Q1~Q5 순차 실행):
- Q1 (migration_history) → 후보 A 즉시 확정/반박
- Q4 (active task 수) → 후보 B 검증
- Q5 (task_detail_id 컬럼 존재) → 이미 존재 추정

### 9.7 즉시 복구 방안 (🚨 S2 Severity — 긴급 HOTFIX 예외 조항 적용 가능)

> CLAUDE.md § 🚨 긴급 HOTFIX 예외 조항: S2(부분 장애) 판정 시 Opus 단독 리뷰 → 배포 → 다음 Sprint 전 Codex 사후 검토.

**후보별 효과성 매트릭스**:

| Option | 후보 D (sleep) | 후보 E (recycling) | 후보 F (pool) | 복잡도 |
|---|---|---|---|---|
| 1. misfire_grace_time 확대 | ⚠️ 효과 있을 수도 | ❌ 무효 (thread 자체 죽음) | ❌ 무효 | 낮음 (1줄) |
| 2. 파일 lock 가드 | ❌ 무관 | ✅ **직접 해결** | ❌ 무효 | 중간 (~10줄) |
| 3. 스케줄러 재시작 엔드포인트 | ✅ 임시 복구 | ✅ 임시 복구 | ✅ 임시 복구 | 중간 (~15줄) |
| 4. 각 job put_conn 감사 | ❌ 무관 | ❌ 무관 | ✅ **직접 해결** | 중간 (감사) |
| 5. Railway Cron 이관 | ✅ 근본 해결 | ✅ 근본 해결 | ✅ 근본 해결 | 높음 (Sprint) |

**Option 1 — BackgroundScheduler misfire_grace_time 확대** (🟡 부가 방어, 단독 의존 금지)
```python
# scheduler_service.py L51
_scheduler = BackgroundScheduler(
    timezone=Config.KST,
    job_defaults={'misfire_grace_time': 3600, 'coalesce': True}
)
```
- 후보 E/F 확정 시 **효과 없음** — Option 2/4와 병행 적용
- 부가적 방어로만 포함 (무해함)

**Option 2 — 파일 lock 기반 가드** (🔴 후보 E 확정 시 핵심 수정, 리뷰어 제안)
```python
# __init__.py L70-78 교체
import fcntl, os
lock_file = '/tmp/_scheduler.lock'
try:
    fd = os.open(lock_file, os.O_CREAT | os.O_WRONLY)
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    from app.services.scheduler_service import init_scheduler, start_scheduler
    init_scheduler()
    start_scheduler()
    app._scheduler_fd = fd   # GC 방지용 참조 보관
    logger.info("Scheduler initialized and started (file lock acquired)")
except BlockingIOError:
    logger.info("Scheduler already running in another worker (file lock)")
```
- **후보 E 직접 해결**: worker 종료 시 OS가 file lock 자동 해제 → 다음 worker가 인계 가능
- env 상속 oneshot 효과 우회
- 전제: Railway 컨테이너 `/tmp` 쓰기 가능 (일반적으로 허용)
- **병행 필요**: `/api/admin/scheduler/status` 엔드포인트로 모니터링

**Option 3 — 스케줄러 강제 재시작 엔드포인트** (🟠 임시 복구용, 보조)
```python
@admin_bp.route('/scheduler/restart', methods=['POST'])
@jwt_required
@admin_required
def restart_scheduler():
    from app.services.scheduler_service import stop_scheduler, init_scheduler, start_scheduler
    stop_scheduler()
    global _scheduler
    _scheduler = None
    init_scheduler()
    start_scheduler()
    return jsonify({"status": "restarted"})
```
- 복구 패치 배포 전 Twin파파가 현장에서 수동 호출 가능 (긴급 대응)
- `/api/admin/scheduler/status` 엔드포인트도 같이 추가 (등록된 job + next_run_time 노출)

**Option 4 — 스케줄러 job 함수 `put_conn` 누락 감사** (🟠 후보 F 대응)
- `scheduler_service.py` 11개 job 함수 전수 try/finally put_conn 확인
- 예외 경로에서 conn 반환 누락 시 수정
- `test_alert_all20_verify.py`에 pool exhaustion 테스트 추가

**Option 5 — Railway Cron Jobs 이관** (🟢 장기 구조 전환, 별도 Sprint)
- APScheduler 전면 제거
- Railway 외부 cron이 HTTP 엔드포인트 주기 호출: `POST /api/internal/cron/task_reminder`
- **모든 후보(E/F/D) 근본 해결** — worker recycling·pool·sleep 영향 전부 제거
- 1~2주 Sprint 필요

### 9.8 권장 복구 순서 (리뷰어 Phase 1/2/3 구조 반영)

**Phase 1 — 진단 (10분)**:
- Railway 로그 §9.6 3개 문구 검색
- 후보 E / D / F 확정

**Phase 2 — 복구 (후보별 30분~1시간)**:
| 확정 후보 | 적용 조합 |
|---|---|
| 후보 E 단독 | Option 2 (파일 lock) + Option 3 (재시작 엔드포인트) |
| 후보 D 단독 | Option 1 (misfire) + Option 3 |
| 후보 F 단독 | Option 4 (put_conn 감사) + Option 3 |
| 후보 E + F 복합 | Option 1 + 2 + 3 + 4 (병행 안전, 서로 독립적) |
| 모호함 | **Option 1 + 2 + 3 병행 배포** (서로 독립, 리스크 낮음) |

**Phase 3 — 장기 구조 전환 (1~2주 Sprint)**:
- Option 5 (Railway Cron 이관) 설계서 작성 → Codex 교차검증 → 구현
- 구조적 재발 방지

### 9.9 별도 BACKLOG 등록 제안

- `POST-REVIEW-ALERT-SCHEDULER-OUTAGE-20260422` — 사후 Codex 검토 (긴급 HOTFIX 예외 조항 #24h 이내 사후 검토 규칙)
- `REFACTOR-SCHEDULER-RAILWAY-CRON` — Option 5 구조 전환 Sprint
- Sprint 55 Worker별 Pause 이후 `_get_active_tasks` worker_id 필터 영향 재검토 — 후보 B 잔여
- `/api/admin/scheduler/status` + `/api/admin/scheduler/restart` 엔드포인트 도입 — 운영 가시성

### 9.10 2차 개정 요약 (리뷰어 반박 수용 내역)

| 1차 주장 | 2차 수정 | 반영 이유 |
|---|---|---|
| 후보 D 최유력 | 후보 D 강등 (🟢) | Railway는 기본 sleep 없음 + Flask live면 scheduler thread도 live여야 정상 |
| Option 1이 1줄 복구 | Option 1은 부가 방어로만 | 후보 E/F 맞으면 Option 1 단독 무효 |
| Phase 1 진단 항목 6개 | Phase 1 3개 문구로 집중 | 리뷰어 제안 수용 — 진단 속도 3배 |
| 후보 E 언급 없음 | **후보 E 신규 최유력** | 리뷰어 가설 + Procfile `-w 2` 증거 |
| 후보 F 언급 없음 | 후보 F 병행 의심 | put_conn 누락 가능성 (Flask live + scheduler dead 패턴 부합) |

---

## 10. 연관 문서 (9번 진단 기준)

- `backend/app/__init__.py` L63-78 (scheduler 초기화 guard)
- `backend/app/services/scheduler_service.py` L51 (BackgroundScheduler 생성 — misfire 미설정)
- `backend/app/services/scheduler_service.py` L331-373 (`_get_active_tasks` worker_id 필터)
- `backend/app/services/scheduler_service.py` L822-899 (`check_orphan_relay_tasks_job`)
- `backend/app/models/alert_log.py` L113-126 (INSERT 8 컬럼)
- `backend/app/migration_runner.py` L83-210 (autocommit + _split_statements)
- `CLAUDE.md` § 🚨 긴급 HOTFIX 예외 조항 (S2 Severity)
- APScheduler 공식 문서: [misfire_grace_time](https://apscheduler.readthedocs.io/en/3.x/userguide.html#missed-job-executions-and-coalescing)

---

## 11. 2026-04-22 Railway 로그 실측 — 후보 E+F 확정 (메커니즘 수정)

> Twin파파가 Railway OPS BE service Logs 탭에서 제공한 실로그 3건을 분석한 결과. §9.4a(후보 E)의 메커니즘 가설을 **정반대로 수정**하고 후보 F를 **직접 확정**함.

### 11.1 Railway 로그 실증거

#### 증거 A — 스케줄러 초기화 2회 (85ms 간격)
```
2026-04-20 07:49:23,905 - app.services.scheduler_service - INFO - Scheduler initialized with 11 jobs
2026-04-20 07:49:23,990 - app.services.scheduler_service - INFO - Scheduler initialized with 11 jobs
```
- 85ms 간격으로 두 번 = master가 worker 1 → worker 2 순차 fork 후 각 worker가 **독립적으로** `init_scheduler()` 호출
- `_SCHEDULER_STARTED` env 가드가 **완전히 무효** (fork 시점에 가드 미설정 → 두 worker 모두 통과)

#### 증거 B — 매 분 Job 실행 로그 2회 중복
```
2026-04-21 15:54:00,061 - apscheduler.executors.default - INFO - Job "휴게시간 자동 일시정지 (매 분) ..." executed successfully
2026-04-21 15:54:00,067 - apscheduler.executors.default - INFO - Job "휴게시간 자동 일시정지 (매 분) ..." executed successfully
2026-04-21 15:55:00,000 - apscheduler.executors.default - INFO - Running job "휴게시간 자동 일시정지 (매 분) ..."
2026-04-21 15:55:00,000 - apscheduler.executors.default - INFO - Running job "휴게시간 자동 일시정지 (매 분) ..."
2026-04-21 15:55:00,059 - apscheduler.executors.default - INFO - Job "... executed successfully
2026-04-21 15:55:00,115 - apscheduler.executors.default - INFO - Job "... executed successfully
```
- 동일 분 tick에 실행 로그 2회 = **두 scheduler가 동시에 같은 job을 중복 실행**
- "Scheduler already running in another worker, skipping" 메시지 **없음** = 가드 oneshot skip이 아니라 **양쪽 모두 통과**

#### 증거 C — Pool 고갈 직접 로그
```
2026-04-21 15:55:00,000 - app.db_pool - WARNING - [db_pool] Pool exhausted: connection pool exhausted
2026-04-21 15:55:00,000 - app.db_pool - WARNING - [db_pool] Pool exhausted: connection pool exhausted
2026-04-21 15:55:00,000 - app.db_pool - WARNING - [db_pool] Using direct connection
2026-04-21 15:55:00,000 - app.db_pool - WARNING - [db_pool] Using direct connection
```
- `Pool exhausted: connection pool exhausted` 명시 = 후보 F 직접 확정
- `[db_pool] Using direct connection` = fallback 경로 존재 (일부 job은 이 경로로 살아남음)
- 각 로그도 2회 출력 = 두 worker가 모두 pool 고갈

#### 증거 D — Collation Version Drift (별건)
```
WARNING: database "railway" has a collation version mismatch
DETAIL: The database was created using collation version 2.36, but the operating system provides version 2.41
HINT: Rebuild all objects ... and run ALTER DATABASE railway REFRESH COLLATION VERSION
```
- 이번 알람 장애와 **무관** (별도 인프라 이슈)
- Railway PostgreSQL 호스트 OS의 glibc 업그레이드로 발생한 collation library 버전 드리프트
- 인덱스 정합성 위험 잠재 → 별도 BACKLOG 등록 권장

### 11.2 후보 E 메커니즘 정반대 수정 (§9.4a 정정)

**§9.4a 기존 가설 (틀림)**:
> "worker 1이 스케줄러 start → recycled되면 env 가드로 후속 worker skip → scheduler dead"
> = oneshot skip 시나리오

**실측 결과 기반 수정 (확정)**:
> "fork 시점에 `_SCHEDULER_STARTED` 미설정 → **두 worker 모두 가드 통과** → 둘 다 자체 scheduler 시작 → 모든 job 중복 실행 → DB 쿼리 2배 부하 → pool 고갈"
> = **duplicate execution** 시나리오

**근본 원인 (Python fork semantics)**:
- Gunicorn `--preload` 없음 → master는 `create_app()` 실행 안 함
- 각 worker가 독립적으로 `create_app()` 호출
- `os.environ['_SCHEDULER_STARTED'] = '1'` 은 해당 worker 프로세스에만 적용
- 다른 worker 프로세스는 자기 env에 가드 값이 없음 → 가드 통과
- 결과: worker N개 = scheduler N개

**왜 재배포로도 복구 안 됐는가**:
- 같은 구조(Procfile) 유지되는 한 매 재배포마다 worker N개가 scheduler N개 생성
- 결정론적으로 재현 = 문서 §1 "재배포로 복구 안 됨 — 원인이 결정론적으로 재현" 사실과 부합

### 11.3 최종 메커니즘 (2026-04-22 executed successfully 로그 기반 — 후보 F 강등, G 확정)

> 초기(§11.1 증거 C) 후보 F(pool 고갈)를 "직접 확정"으로 표기했으나, 이후 추가 로그 실측 결과 **F는 일시 증상으로 강등**, **G (쿼리 0건 반환) 로 확정** 전환. 아래 실측 증거 타임라인 참조.

#### 11.3.1 Job 트리거 주기 구분 (혼동 방지)

| 구분 | Job | Trigger | 실행 주기 |
|---|---|---|---|
| **매 분** (per-minute) | check_break_time_job | `CronTrigger(second=0)` | HH:MM:**00** 매 분 |
| **매 시간 정각** (hourly) | task_reminder_job, check_orphan_relay_tasks_job | `CronTrigger(minute=0)` | HH:**00**:00 매 시간 |
| 매일 특정 시각 | shift_end_17/20, task_escalation, 기타 | `CronTrigger(hour=N)` | 지정 시각 1회 |

> break_time 은 **매 분**이지 매 시간 정각이 아님. 이후 서술은 이 구분을 따름.

#### 11.3.2 실측 증거 타임라인 (2026-04-21 UTC)

| 시각 (UTC) | Job | 결과 | 해석 |
|---|---|---|---|
| 15:55:00 | (다수 job) | `Pool exhausted: connection pool exhausted` + `Using direct connection` | 일시적 pool 고갈 이벤트 |
| 19:00:00 ~ 23:00:00 | 릴레이 미완료 task 감지 | `Running` (매 시간 정각, 2회 중복) | scheduler 2개 trigger 정상 |
| 22:51:00 ~ 22:54:00 | 휴게시간 자동 일시정지 | `executed successfully` (매 분, 2회 중복, 45~77ms) | 매 분 DB 접근 성공 |
| 23:00:00.046 | 작업자 리마인더 | `executed successfully` (2회 중복, ~46ms) | 매 시간 정각 성공 |
| 23:00:01.855 | 릴레이 미완료 task 감지 | `executed successfully` (2회 중복, **~1.85초 SELECT 실행**) | 무거운 쿼리도 성공 |

#### 11.3.3 실측 결과 해석 — 후보 F 강등

**15:55 UTC Pool exhausted**:
- 4-21 15:55 UTC = KST 04-22 00:55 새벽
- 실측 22:51 ~ 23:00 UTC (KST 08:00 아침) 기준 pool **정상 동작**
- → **일시적·간헐적 이벤트**이지 5일 지속 근본 원인 아님

**후보 F 재분류 근거**:
1. 매 분 job(break_time) 45~77ms 성공 = 가벼운 DB 조회 가능
2. 매 시간 정각 job(릴레이 미완료) 1.85초 성공 = 무거운 SELECT 도 실행 완료
3. 두 주기의 모든 job 이 `executed successfully` = pool 경로 전체적으로 건강
4. 15:55 UTC 고갈은 7시간 전 단발 이벤트 — 5일 연속 알람 0건 설명 불가
- → **후보 F 는 일시 증상, 5일 지속 근본 원인 아님** (별도 pool 튜닝 이슈로 분리)

#### 11.3.4 후보 G 확정 — SELECT 결과 0건 or INSERT silent fail (Codex 지적 반영, 가능성 3 신설)

**확정 근거**:
- 모든 scheduled job 이 DB 접근·쿼리 실행 성공 (executed successfully 로그)
- 그러나 app_alert_logs INSERT 는 4-17 이후 5일간 0건
- 결론: 다음 3가지 경로 중 하나로 **INSERT 가 실제로 발생하지 않았음**

**Codex 지적 반영 — 세 가능성으로 확장 (기존 2개 → 3개)**:

**가능성 1 — 실제로 조건 만족 task 없음** (장애 아님, 현장 패턴 반영, = 재정의 G.1):
- 4-16 RELAY_ORPHAN 60건이 그날 누적분의 마지막 토출
- 이후 현장 작업 패턴 변화로 4시간 이상 미완료 task 자연 감소
- scheduler 및 쿼리는 정상 — 알람 생성 조건을 만족하는 task 가 실제로 없었음
- **확정 쿼리**: **Q6-HIST 결과 비어있음** (Q6 현재 스냅샷 0건만으로는 불충분)
- **조치**: Option 2 (file lock) 로만 배포, 긴급 복구 작업 불필요

**가능성 2 — Sprint 55/61-BE-B 쿼리 필터 과도** (실제 장애, = 재정의 G.2):
- Sprint 55 Worker별 Pause 도입으로 `_get_active_tasks`·`_get_overdue_tasks` 등에 `worker_id IS NOT NULL` 필터 추가
- Sprint 61-BE-B 의 BUG-44 LATERAL JOIN 변경이 orphan 감지 쿼리 조건 변경
- 실제로는 알람 대상 task 존재하는데 쿼리가 걸러냄
- **확정 쿼리**: **Q6-HIST 결과 다수 시점 존재** AND 해당 시점에 알람 0건
- **조치**: Option 6 (쿼리 diff 리뷰) + Option 2

**🆕 가능성 3 — `create_alert()` silent fail** (Codex 지적, = 재정의 G.3):
- job 내부에서 orphan/active task **찾음** (SELECT 결과 > 0건)
- `create_and_broadcast_alert()` 호출 → 내부에서 예외 발생 (WebSocket broadcast, DB INSERT 실패 등)
- `alert_service.py` 또는 `models/alert_log.py` 의 try/except 가 예외를 삼키고 `return None`
- job 에게는 예외 전파 안 됨 → APScheduler 는 `executed successfully` 찍음
- app_alert_logs 는 여전히 0건
- **확정 쿼리 / 방법**: Q6-HIST 다수 시점 존재 + 쿼리 diff 리뷰에서 이상 없음 + **Sentry 로깅 Phase 1.5 (아래) 필요**
- **조치**: alert_service·alert_log 예외 경로 ERROR 레벨 로깅 추가 + Sentry 연동 후 1시간 모니터링 → 실제 silent fail 포착

**Phase 1.5 — 가능성 3 검증용 Sentry 로깅 (Codex 제안)**:
```python
# backend/app/services/alert_service.py create_and_broadcast_alert 수정안
def create_and_broadcast_alert(alert_data):
    try:
        alert_id = create_alert(...)
        if alert_id is None:
            logger.error(f"[alert_silent_fail] create_alert returned None: {alert_data}")
        # ... 기존 로직
    except Exception as e:
        logger.error(f"[alert_silent_fail] exception: {e}, data={alert_data}", exc_info=True)
        # Sentry 연동 시: sentry_sdk.capture_exception(e)
        raise  # 또는 return None (기존 동작 유지)
```
- 배포 후 1~2시간 관찰
- Sentry 또는 Railway ERROR 로그에 `[alert_silent_fail]` 포착되면 **가능성 3 확정**
- 포착 안 되면 가능성 1 or 2 로 좁혀짐

#### 11.3.5 §11 초기 후보 순위 정정 요약 (Codex 지적 반영)

| 후보 | §11 초기 평가 | 실측 추가 후 최종 | 서브 카테고리 |
|---|---|---|---|
| F (pool 고갈) | 🔴 직접 확정 | 🟡 **일시 증상으로 강등** | 4-17~4-21 grep 추가 필요 (체크포인트 2) |
| E (Gunicorn duplicate) | 🔴 메커니즘 정정 | 🔴 **유지** (중복 실행 5일 지속 확인) | - |
| G (쿼리/silent) | — | 🔴 **신규 확정** (executed successfully + INSERT 0건) | G.1 실제 0건 / G.2 쿼리 버그 / G.3 silent fail |

**가능성 1/2/3 ↔ G.1/G.2/G.3 통합 매핑**:
| 표기 | 의미 | 확정 쿼리/방법 |
|---|---|---|
| 가능성 1 = G.1 | 실제 조건 만족 task 없음 (장애 아님) | Q6-HIST 비어있음 |
| 가능성 2 = G.2 | 쿼리 필터 과도로 대상 놓침 | Q6-HIST 다수 시점 + 쿼리 diff 리뷰 |
| 가능성 3 = G.3 | create_alert() silent fail (INSERT 시도 실패) | Q6-HIST 다수 시점 + Phase 1.5 Sentry 로깅 포착 |

### 11.4 휴게시간 OFF 설정인데 매 분 로그 찍히는 이유

**APScheduler의 "등록 계층 ↔ 실행 계층 분리" 특성**:

```
scheduler_service.py add_job 단계 (등록 계층):
  scheduler.add_job(check_break_time_job, CronTrigger(second=0), ...)
  → 매 분 무조건 실행 예약. admin_settings 값은 조회 안 함.

check_break_time_job() 내부 (실행 계층 — 추정):
  def check_break_time_job():
      conn = get_conn()
      try:
          setting = get_admin_setting('break_time_enabled')
          if not setting:
              return                  # 조기 return (실제 pause 로직 미실행)
          # (break 시간 계산, force_pause 등 실제 로직)
      finally:
          put_conn(conn)
```

**결론**:
- OFF여도 **매 분 실행은 됨** (등록된 cron이라 무조건 trigger)
- 내부에서 `admin_settings` 조회 후 조기 return
- "executed successfully" 로그는 **예외 없이 return 됨**만 의미 (실제 pause 동작 여부 아님)

**정상 동작이지만 2가지 개선 여지**:
1. **캐시 도입**: `admin_settings`를 in-memory 캐시 + TTL(5분) 로 감싸 매 분 DB 조회 제거
2. **early return 위치 앞당기기**: `get_conn()` **이전**에 캐시 조회 + OFF면 즉시 return (현재 추정 구조는 conn 획득 후에야 체크)

**이번 장애 주범인가**: **아님**. break_time job 1개가 매 분 2회 × DB 1회 = 분당 2회 쿼리 수준은 부하 주범 아님. 주범은 scheduler **2개 × 11 jobs × 각 job의 다수 쿼리**. 다만 pool 고갈을 **가속**시킨 보조 부하 요인.

### 11.5 Collation Version Drift (별건)

**원인**: Railway PostgreSQL 호스트 OS glibc 업그레이드 (collation library 2.36 → 2.41). 기존 인덱스가 2.36 기준으로 정렬되어 있으나 OS는 2.41 규칙으로 비교 → 문자열 인덱스 조회 실패 가능성 잠재.

**이번 알람 장애와 관련 없음** 근거:
- collation 이슈는 주로 한글·특수문자 ORDER BY / UNIQUE 제약에서 드러남
- app_alert_logs INSERT는 enum·integer 위주 컬럼이라 collation 영향 없음
- 4-16까지 657건 정상 INSERT = collation이 INSERT 자체를 막는 구조는 아님

**권장 조치** (별도 Sprint):
```sql
REINDEX DATABASE railway;                    -- 전체 인덱스 재빌드
ALTER DATABASE railway REFRESH COLLATION VERSION;  -- 시스템 버전 등록 갱신
```
- 실행 시간: DB 크기 따라 5~30분 (운영 중 lock 주의)
- BACKLOG: `INFRA-COLLATION-REFRESH` 등록 제안 (🟡 MEDIUM, APS Lite 이관 전까지)

### 11.6 후보 최종 재평가 (§9.3 → §11.6 → 2026-04-22 추가 실측 반영)

| 후보 | §9.3 평가 | §11 초기 | **§11.3 후 최종** | 결정 증거 |
|---|---|---|---|---|
| **A** migration 049 silent fail | 🟢 약화 | 🟢 기각 | 🟢 **기각** | 증거 B·C에 scheduler 실행 증거, migration 무관 |
| **B** 쿼리 0건 반환 | 🟡 부분 유효 | 🟢 기각 | 🟡 **후보 G로 재등장** | §11.3.4 참조 (실측 근거 확정) |
| **C** 스케줄러 부팅 실패 | 🟠 유지 | 🟢 완전 기각 | 🟢 **완전 기각** | 증거 A·B 에 scheduler 실행 로그 = 부팅 성공 |
| **D** misfire + Railway sleep | 🟢 강등 | 🟢 완전 기각 | 🟢 **완전 기각** | `Run time of job was missed` 로그 없음 + 정각 실행 정상 |
| **E** Gunicorn recycling + env 가드 | 🔴 최유력 (oneshot skip 가설) | 🔴 메커니즘 정정 (중복 실행) | 🔴 **유지 (중복 실행 5일 지속)** | 증거 A·B 2회 중복 로그 |
| **F** DB pool 고갈 | 🟠 병행 의심 | 🔴 직접 확정 | 🟡 **일시 증상으로 강등** | 4-21 15:55 UTC 단발 이벤트, 22:51~23:00 UTC 는 pool 정상 |
| **G** 🆕 SELECT 결과 0건 (쿼리 / 실제 데이터) | — | — | 🔴 **신규 확정** | executed successfully + INSERT 0건 조합, §11.3.4 참조 |

### 11.7 복구 방안 — Q6/Q7/Q8 결과에 따른 분기 (2026-04-22 재조정)

> §11.3.4 에서 후보 G 를 확정했으므로, 복구 방안은 **Q6/Q7/Q8 쿼리 결과로 확정되는 가능성 1/2 에 따라 다름**.

#### 11.7.1 가능성 1 / G.1 (Q6-HIST 비어있음) — 장애 아님

- scheduler 는 정상 실행, 실제로 알람 생성 조건 만족 task 가 없었을 뿐
- **긴급 수정 불필요**. Option 2 만 재발 방지용으로 배포
- Option 4 (put_conn 감사) 는 **필수 아닌 선호** (장기 안정성)

#### 11.7.2 가능성 2 / G.2 (Q6-HIST 다수 시점 + 쿼리 diff 이상) — 쿼리 필터 버그

- Sprint 55 / 61-BE-B 변경이 scheduler job 쿼리에 영향 → 쿼리 diff 리뷰 우선
- Option 2 + Option 6 (쿼리 수정) 병행 배포

#### 11.7.3 🆕 가능성 3 / G.3 (Q6-HIST 다수 시점 + 쿼리 diff 정상 + Phase 1.5 silent fail 포착) — alert_service 예외 경로

- `create_and_broadcast_alert()` 내부 예외 체인에서 silent fail
- WebSocket broadcast 실패, 또는 alert_log INSERT 예외 등
- **조치**: Phase 1.5 배포 (ERROR 로깅 추가) → 1~2시간 관찰 → 포착되면 예외 경로 수정 + 재배포
- Option 2 는 여전히 병행 (중복 실행은 가능성 3 도 증폭시킴)

#### 11.7.4 Option 별 효과 매트릭스 (후보 E/F/G 기준, 가능성 3 반영)

| Option | E (duplicate) | F (pool, 일시) | G.1 (실제 0건) | G.2 (쿼리 버그) | 🆕 G.3 (silent fail) | 복잡도 |
|---|---|---|---|---|---|---|
| 1. misfire_grace_time 확대 | ❌ 무효 | ⚠️ 부가 방어만 | ❌ 무효 | ❌ 무효 | ❌ 무효 | 낮음 (1줄) |
| 2. 파일 lock 가드 | ✅ **직접 해결** | ✅ 부하 절반 → pool 여유 | ⚠️ 장애 아님 재발 방지 | ⚠️ 쿼리 문제는 별개 | ⚠️ 예외 문제는 별개 | 중간 (~10줄) |
| 3. 스케줄러 재시작/status 엔드포인트 | ✅ 임시 복구 | ✅ 임시 복구 | ✅ 운영 가시성 | ✅ 운영 가시성 | ✅ 운영 가시성 | 중간 (~15줄) |
| 4. 각 job put_conn 감사 | ❌ 무관 | ✅ 재발 방지 | ❌ 무관 | ❌ 무관 | ❌ 무관 | 중간 (감사) |
| 5. Railway Cron 이관 | ✅ 근본 해결 | ✅ 근본 해결 | ✅ 장애 아님 확인 | ❌ 쿼리 버그는 이관해도 남음 | ❌ 예외는 이관해도 남음 | 높음 (Sprint) |
| 6. 쿼리 diff 리뷰 | ❌ 무관 | ❌ 무관 | ❌ 무관 | ✅ **직접 해결** | ❌ 무관 | 낮음~중간 (리뷰) |
| **🆕 1.5 Sentry ERROR 로깅** | ❌ 무관 | ❌ 무관 | ❌ 무관 | ⚠️ 보조 | ✅ **직접 해결** | 낮음 (~20줄) |

#### 11.7.5 Option 상세

**Option 1 — misfire_grace_time** (🟡 보류)
- 후보 D 완전 기각 + 후보 E/G 에 무효. 이번 사태 효과 없음. 장기 방어용으로만 병합 가능

**Option 2 — 파일 lock 기반 가드** (🔴 필수, 가능성 1/2/3 공통)
```python
# __init__.py L70-78 교체
import fcntl, os
lock_file = '/tmp/_scheduler.lock'
try:
    fd = os.open(lock_file, os.O_CREAT | os.O_WRONLY)
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    from app.services.scheduler_service import init_scheduler, start_scheduler
    init_scheduler()
    start_scheduler()
    # GC 방지 참조 — Flask app 객체보다 모듈 전역이 안전
    import app.services.scheduler_service as _sched_mod
    _sched_mod._lock_fd = fd
    logger.info("Scheduler initialized and started (file lock acquired)")
except BlockingIOError:
    logger.info("Scheduler already running in another worker (file lock)")
```
- 중복 실행 해소 → scheduler 1개 → DB 부하 절반
- 가능성 1/2/3 어느 쪽이든 배포 정당성 있음 (중복 실행은 silent fail 도 증폭시킴)

**Option 2 안정성 근거 (Codex 체크포인트 4 해소)**:

1. **fcntl.flock 은 atomic** — Linux kernel advisory lock 으로 race condition 없음
   - `os.open(O_CREAT)` + `fcntl.flock(LOCK_EX | LOCK_NB)` 조합에서 kernel 이 atomicity 보장
   - worker 2개가 동시에 fork·init 하더라도 정확히 1개만 lock 획득, 나머지는 `BlockingIOError` 즉시 반환
2. **Railway `/tmp` ephemeral 이 오히려 장점** — container 생명주기 = scheduler 생명주기 정합
   - container 시작 시 `/tmp` 초기 상태 (lock 파일 없음) → 첫 worker 가 생성·획득
   - container 종료 시 `/tmp` 날아감 → 다음 container 에서 또 깨끗하게 시작
   - **stale lock 걱정 없음**. 일반적 EC2 영구 FS 에서 발생하는 "죽은 프로세스의 lock 이 남아있음" 문제 원천 차단
3. **worker 종료 시 OS 자동 해제** — flock 은 프로세스 종료 시 kernel 이 자동으로 lock release
   - `app._scheduler_fd` 가 아니라 `_sched_mod._lock_fd` 에 보관한 이유: Flask `app` 객체는 reload 경로에서 재생성될 수 있음. 모듈 전역은 프로세스 수명과 일치
4. **worker recycling 시에도 안전** — flock 소유 worker 가 OOM/timeout 으로 죽으면 kernel 이 release → 다음 fork 된 worker 가 인계 가능
5. **검증된 패턴** — Python 공식 문서 + 대규모 프로덕션 (Django celery single-worker guard) 에서 널리 사용

**Option 3 — 스케줄러 재시작/status 엔드포인트** (🟠 보조, 운영 가시성)
- `/api/admin/scheduler/status` — 등록된 job + next_run_time 노출
- `/api/admin/scheduler/restart` — 긴급 복구용 (Twin파파 수동 호출)

**Option 4 — put_conn 누락 감사** (🟠 가능성 1 에서는 권장, 가능성 2 에서는 후순위)
- scheduler_service.py 11 job 함수 전수 `try/finally put_conn` 점검
- `alert_service.create_and_broadcast_alert()` 예외 경로 감사
- **장기 재발 방지** 관점에서 어차피 필요 (Sprint 일정에만 추가)

**Option 5 — Railway Cron Jobs 이관** (🟢 장기, 구조 전환 Sprint)
- APScheduler 제거 + 외부 cron HTTP 호출
- 모든 후보 (E/F/G) 구조적 재발 방지
- 단 **쿼리 버그 (후보 G) 는 이관해도 남음** — Option 6 선행 필수

**Option 6 — 쿼리 diff 리뷰** (🔴 **가능성 2 에서 핵심 수정**)
- 대상 파일: `backend/app/services/scheduler_service.py` L331-373 `_get_active_tasks`
- 대상 파일: `backend/app/services/scheduler_service.py` L822-899 `check_orphan_relay_tasks_job`
- 대상 파일: `backend/app/services/duration_validator.py` `check_unfinished_tasks` 기타
- Sprint 55 (Worker별 Pause) diff: `worker_id IS NOT NULL` 필터 추가 여부
- Sprint 61-BE-B (BUG-44 LATERAL JOIN) diff: orphan 감지 쿼리 조건 변경 여부
- **검증 방법**: Q6/Q7 쿼리 실측 값 vs 현재 scheduler job 내부 SELECT 결과 비교

### 11.8 권장 복구 순서 (2026-04-22 Codex 재검증 반영)

**Phase 1 — 진단 (최우선, 5~10분)**:
- pgAdmin Q6 (현재 스냅샷) + **Q6-HIST (필수, 5일 복원)** + Q7 + Q8 실행
- Railway 로그 추가 grep: **`Pool exhausted` 키워드 4-17~4-21 구간 발생 횟수** (체크포인트 2 해소)
  - 1회뿐이면 F 일시 증상 확정
  - 주기적이면 F 근본 원인 후보로 복귀

**Phase 1.5 — 가능성 3 (silent fail) 배제/확정용 로깅 (15분 추가)**:
- `alert_service.create_and_broadcast_alert()` 및 `alert_log.create_alert()` 에 ERROR 레벨 로깅 추가
- Sentry 또는 Railway 로그 1~2시간 모니터링
- `[alert_silent_fail]` 포착 → 가능성 3 확정 → 예외 경로 수정
- 포착 안 됨 → 가능성 1 or 2 로 좁혀짐 (Q6-HIST 결과와 결합 판정)

**Phase 2 — 복구 (확정된 가능성별)**:

| Q6-HIST 결과 | Phase 1.5 silent fail | 판정 | 적용 조합 | 예상 소요 |
|---|---|---|---|---|
| 비어있음 (모든 시점 0건) | 미포착 | **가능성 1 / G.1** (장애 아님) | Option 2 + Option 3 | 30~60분 |
| 다수 시점 존재 | 미포착 | **가능성 2 / G.2** (쿼리 버그) | Option 6 + Option 2 + Option 3 | 1~2시간 |
| 다수 시점 존재 | 포착됨 | **가능성 3 / G.3** (silent fail) | Phase 1.5 고도화 (예외 경로 수정) + Option 2 + Option 3 | 1~3시간 |
| 비어있음 | 포착됨 | 드문 경우 (가짜 silent) | Sentry 내용 기반 재분석 | 미정 |

**Phase 3 — 장기 구조 전환 (1~2주 Sprint)**:
- Option 5 (Railway Cron 이관) 설계 + Codex 교차검증 + 구현
- Option 4 (put_conn 감사) 는 Sprint 내 포함
- Option 5 는 G.2/G.3 해결에는 무효 — Option 6 + Phase 1.5 선행 필수

### 11.9 배포 전 추가 점검 항목

1. **scheduler_service.py 11 job 함수 grep** — `get_conn`/`put_conn` 페어링 전수 확인 (가능성 1 의 재발 방지용)
   - `task_reminder_job`, `check_unfinished_tasks`, `shift_end_reminder_17/20`, `task_escalation_job`, `check_break_time_job`, `cleanup_access_logs`, `check_orphan_relay_tasks_job`, `check_not_started_tasks`, `check_checklist_done_09/15`
2. **`alert_service.create_and_broadcast_alert()` 예외 경로 검토** — silent fail 여부 + Sentry 로깅 추가 권고
3. **`db_pool.py` direct connection fallback 분기 전수 검토** — 어떤 경로가 fallback 을 타고 어떤 경로가 예외를 타는지 정리
4. **file lock 경로 (`/tmp/_scheduler.lock`)** — Railway 컨테이너 재시작 시 `/tmp` 초기화 확인 (재기동 안정성)
5. **가능성 2 확정 시 scheduler job 쿼리 git diff** — Sprint 55 (2026-04-07) 커밋 이전·이후 `_get_active_tasks` / orphan 감지 쿼리 조건 비교

### 11.10 BACKLOG 신규 등록 제안 (Codex 재검증 반영)

- `HOTFIX-SCHEDULER-DUP-20260422` (🔴 S2, Option 2 + Option 3 + (가능성 2 확정 시) Option 6 + (가능성 3 확정 시) Phase 1.5 고도화)
- `POST-REVIEW-HOTFIX-SCHEDULER-DUP-20260422` (CLAUDE.md § 🚨 긴급 HOTFIX 예외 조항 — 다음 Sprint 전 사후 검토)
- `🆕 OBSERV-ALERT-SILENT-FAIL` (Phase 1.5 영구 반영 — `create_and_broadcast_alert()` ERROR 로깅 + Sentry 연동)
- `INFRA-COLLATION-REFRESH` (🟡 MEDIUM, `REINDEX DATABASE` + `ALTER DATABASE REFRESH COLLATION VERSION` 1회 실행)
- `OBSERV-SCHEDULER-STATUS` (Option 3 + Sentry 연동 + 일간 0건 감지 Slack 알림)
- `REFACTOR-SCHEDULER-RAILWAY-CRON` (장기 구조 전환 Sprint, Option 5 — Option 6 / Phase 1.5 선행 필수)
- `REFACTOR-SCHEDULER-PUT-CONN-AUDIT` (Option 4, 가능성 1 배포 후 장기 재발 방지용)

### 11.11 11번 절 작성 요약 (리뷰어·차기 세션 가이드 — 2026-04-22 Codex 재검증 최종)

- §9.4a 의 oneshot skip 가설 → **중복 실행 (duplicate execution)** 으로 메커니즘 정정 (§11.2)
- 후보 C·D 완전 기각 유지
- **후보 F 재분류**: 4-21 15:55 UTC 단발 이벤트 → 일시 증상으로 강등 (§11.3.3). 체크포인트 2 반영으로 4-17~4-21 구간 Pool exhausted grep 추가 검증 필요
- **후보 G 세분화**: G.1 (실제 0건) / G.2 (쿼리 버그) / **🆕 G.3 (silent fail, Codex 지적)** 3개로 재정의 (§11.3.4)
- **Q6 시점 결함 교정**: `NOW()` 기준은 현재 스냅샷만 반영 → **Q6-HIST 로 5일간 과거 시점 복원** (Codex 체크포인트 6)
- Job 트리거 주기 구분 (§11.3.1): break_time = 매 분, task_reminder / 릴레이 미완료 = 매 시간 정각
- **복구 방향**: Q6-HIST 결과 + Phase 1.5 Sentry 포착 여부 조합으로 가능성 1/2/3 확정 후 Option 2/3 + (조건부) Option 6 / Phase 1.5 고도화
- Option 2 file lock 안정성 근거 명시 (체크포인트 4 해소 — flock atomic + `/tmp` ephemeral OK)
- break_time 매 분 로그는 정상 (등록 계층 ↔ 실행 계층 분리 특성, §11.4)
- Collation drift 는 별건 (§11.5)

### 11.12 Cowork 검증 체크포인트 (Codex 교차검증용)

> 2026-04-22 세션 수정분. Codex 가 본 문서를 다시 리뷰할 때 확인해야 할 핵심 논점.

1. **§11.3.4 후보 G 확정 논리**: "executed successfully + INSERT 0건 = SELECT 0건" 추론이 충분한가? 반례 가능성?
   - 예: job 내부에서 INSERT 시도했으나 `create_alert()` 가 silent fail 하고 return None — 이 경우 executed successfully 찍힐 수 있음
   - 반증 방법: `app.services.alert_service` Sentry 로그 또는 ERROR 레벨 로깅 추가 후 1시간 모니터링
2. **§11.3.3 후보 F 강등 타당성**: 단일 시점(15:55 UTC) 증거로 "일시 증상" 판정한 근거가 약하지 않은가?
   - 4-17 00:00 ~ 4-21 22:50 UTC 구간에도 Pool exhausted 로그가 있었는지 로그 추가 검색 필요
   - 반증: 주기적으로 발생하면 F 복귀 필요
3. **§11.6 후보 B (쿼리 0건) 복귀 vs §11.3.4 후보 G 신설 일관성**: 두 후보의 정의 차이가 모호하지 않은가?
   - B: "쿼리 내 조건 분기로 0건" (설계상)
   - G: "쿼리는 실행되나 실제 데이터가 0건 or 필터 과도로 0건" (실제 결과)
   - 두 후보를 **가능성 1 (실제 데이터 없음) / 가능성 2 (쿼리 버그)** 로 통합 표현하는 것이 더 명확한지 검토
4. **Option 2 file lock 안정성**: `/tmp` 가 Railway ephemeral FS 라 컨테이너 재시작 시 초기화됨 — 재기동 타이밍에 race condition 가능성
   - 대안: Python `fcntl` 대신 `multiprocessing.Lock` / Redis lock (Redis 도입 필요)
5. **가능성 1 확정 시 "장애 아님" 판정의 현장 영향**: 실제 작업자 입장에서 알람 0건이 "정상"인가?
   - 현장 관리자 interview 권고 — "4-17 이후 미완료 작업 알림을 기대했는가?"
   - 기대했으나 0건이었다면 task_reminder 기준(4시간)이 현장 현실과 괴리 가능성

### 11.13 Codex 교차검증 1차 결과 기록 (2026-04-22)

> Cowork Opus 4.7 이 본 문서 §11.12 체크포인트에 대해 회신한 내용 + 이 세션에서 반영한 조치 내역.

| # | 체크포인트 | Codex 응답 | 이 세션 조치 | 문서 반영 위치 |
|---|---|---|---|---|
| 1 | G 반례 가능성 (`create_alert` silent fail) | 🔴 미해소 | **가능성 3 / G.3 신설** + Phase 1.5 Sentry 로깅 도입 | §11.3.4, §11.3.5, §11.7.3, §11.8 |
| 2 | F 강등 단일 시점 근거 약함 | 🟡 보강 필요 | 4-17~4-21 구간 Pool exhausted grep Phase 1 에 추가 | §11.8 Phase 1 |
| 3 | B vs G 정의 중복 | 🟡 개선 여지 | G 를 G.1/G.2/G.3 으로 재정의, 가능성 1/2/3 과 1:1 매핑 | §11.3.5 매핑 표 |
| 4 | file lock race 가능성 | 🟢 해소 가능 | Option 2 안정성 근거 5가지 명시 (flock atomic + `/tmp` ephemeral OK) | §11.7.4 Option 2 |
| 5 | 현장 영향 interview 필요 | 🟡 보강 필요 | Q6-HIST 로 데이터 기반 객관 확정 | §3 Q6-HIST, §11.8 |
| 6 | **🔴 Q6 시점 결함** (NOW() 기준) | 🔴 필수 수정 | **Q6-HIST 쿼리 신설 (generate_series 기반 5일 복원)** | §3 Q6-HIST |

---

## 11.14 Phase 1.5 배포 완료 (2026-04-22 세션)

### 11.14.1 HOTFIX-SCHEDULER-PHASE1.5 배포 기록

| 항목 | 값 |
|---|---|
| 커밋 SHA | `4a6caf8` |
| 배포 시각 | 2026-04-22 (Xcode 재설치 완료 후) |
| 변경 파일 | `backend/app/services/alert_service.py`, `backend/app/models/alert_log.py` |
| LOC diff | +80 / -37 (2 files) |
| 커밋 메시지 | `HOTFIX-SCHEDULER-PHASE1.5: alert silent fail ERROR 로깅 추가` |
| GitHub push | `1f059b7..4a6caf8 main -> main` |

### 11.14.2 배포 전 검증 결과

| # | 항목 | 결과 |
|---|---|---|
| pytest test_alert_service.py | 11 passed / 0 failed / 2분 34초 | ✅ |
| pytest test_alert_all20_verify.py | 36 passed / 0 failed / 2 skipped (기존 설계) | ✅ |
| 회귀 0건 확인 | HOTFIX 로깅 추가가 기존 테스트에 영향 없음 | ✅ |
| flake8 (max-line=120) | HOTFIX 신규 violation 0건 (기존 4건은 Sprint 3 원본, 별건) | ✅ |
| py_compile syntax | 두 파일 모두 OK | ✅ |
| scope 엄수 | scheduler_service.py / __init__.py / migrations / requirements.txt 무변경 | ✅ |
| 시그니처 무변경 | `create_and_broadcast_alert`, `create_alert` 그대로 | ✅ |
| return None 동작 유지 | 모든 실패 경로에서 None 반환 | ✅ |

### 11.14.3 추가 확정 증거 (pytest 실행 중 발견)

> **`test_all_enum_values_exist` 경고 메시지**:
> ```
> DB에 예상 외 enum 값 존재: {'TASK_NOT_STARTED', 'CHECKLIST_DONE_TASK_OPEN', 'ORPHAN_ON_FINAL'}
> ```

- 테스트 DB(`centerbeam.proxy.rlwy.net:20196`)에 **migration 049 신규 enum 3종 정상 등록** 확인
- 운영 DB도 동일 `migration_runner.py` 자동 실행 구조 → 같은 상태일 확률 극도로 높음
- **§11.3.5 후보 A (migration 049 silent fail) 추가 기각 근거** — §3 Q2 쿼리 사전 답변 효과
- Q1/Q2/Q5 는 사실상 실행 불필요 (A 기각 확정), Q6-HIST/Q7/Q8 만 Phase 1 에서 집중 실행

> 🔴 **2026-04-22 정정 (§12 참조)**: 위 추정 "운영 DB도 같은 상태일 확률 극도로 높음" 은 **Phase 1.5 배포 후 Railway 로그 + pgAdmin 실측으로 반증**됨. 운영 DB 에 migration 049 미적용 확정 (`task_detail_id` 컬럼 부재 + `migration_history` 에 049 기록 없음, max id=36=048). 테스트 DB 와 운영 DB 가 drift 상태. 후보 A 는 **부활·확정**. 세부는 §12 참조.

### 11.14.4 Mac 마이그레이션 부수 이슈 (별건, 본 HOTFIX 와 무관)

1. **Xcode license 재수락 필요** — `sudo xcodebuild -license accept` 1회 실행으로 해소
2. **`.git/objects/` 부분 손상** — SPRINT_13_PLAN.md blob (`62c3bdbd...`) 누락 확인
   - 우회 복구: `git hash-object -w SPRINT_13_PLAN.md` 로 blob 재생성
   - 추가 archived 파일들(ETL_MODULE_GUIDE.md 외 7건) 은 복원 후 원복 처리
   - **장기 조치 필요**: `git fsck --full` 실행해서 다른 누락 blob 점검, 필요 시 전체 archived blob 재생성
3. **Claude Code Desktop/Documents 접근 차단** — macOS TCC 정책 강화
   - 해결: System Settings → Privacy & Security → Full Disk Access → Claude Code 추가

### 11.14.5 Phase 2 판정 대기 — 관찰 사항 (배포 후 1~2시간)

**Railway Logs 에서 grep (OPS BE service → Logs 탭)**:

| 키워드 | 포착 시 판정 |
|---|---|
| `[alert_silent_fail]` | **가능성 3 / G.3 silent fail 확정** |
| `[alert_create_none]` | G.3 서브타입 (DB insert 실패 후 None 반환 경로) |
| `[alert_insert_fail]` | G.3 + DB 레벨 원인 (PsycopgError 포착) |

**병행 pgAdmin 실행**: §3 Q6-HIST + Q7 + Q8

**판정 매트릭스** (§11.8 Phase 2 표 참조):

| Q6-HIST | `[alert_*]` Sentry 포착 | 확정 | 다음 Sprint |
|---|---|---|---|
| 비어있음 (모든 시점 0건) | 미포착 | **G.1** — 장애 아님 | `HOTFIX-SCHEDULER-DUP-20260422` (Option 2 + 3) |
| 다수 시점 존재 | 미포착 | **G.2** — 쿼리 버그 | `HOTFIX-SCHEDULER-QUERY-FIX-20260422` (Option 6 + 2 + 3) |
| 다수 시점 존재 | 포착됨 | **G.3** — silent fail | `HOTFIX-SCHEDULER-SILENT-FIX-20260422` (예외 경로 수정 + 2 + 3) |

### 11.14.6 관찰 결과 기록 (2026-04-22 02:00:00 UTC = 11:00 KST 정각 tick)

| 항목 | 기록 |
|---|---|
| 배포 성공 시각 | 2026-04-22 10:47 KST (deployment `3907b7d0 Active`) |
| `/api/health` 응답 | 200 OK |
| 배포 후 `Scheduler initialized with 11 jobs` 로그 횟수 | 2회 (중복 실행 여전 — 후보 E 유지) |
| `[alert_insert_fail]` 포착 건수 | **4건 (02:00:00 UTC tick 단일 1분 내)** — GPWS-0773, GBWS-7038, GBWS-7051, GBWS-7038(중복) |
| `[alert_create_none]` 포착 건수 | **4건** (alert_insert_fail 과 1:1 대응) |
| `[alert_silent_fail]` 포착 건수 | 0건 (최상위 create_and_broadcast_alert 단계는 예외 전파 없음 — INSERT 레벨에서 이미 포착) |
| 공통 에러 메시지 | **`column "task_detail_id" of relation "app_alert_logs" does not exist`** (모든 INSERT 동일) |
| Q1 migration_history 스키마 | 3 컬럼: `id`, `filename`, `executed_at` (success/error_message 없음) |
| Q1 migration_history 내용 | **max id=36, `048_elec_master_normalization.sql` 까지** — **049 기록 없음** |
| Q5 app_alert_logs 컬럼 | 12 컬럼: id, alert_type, serial_number, qr_doc_id, triggered_by_worker_id, target_worker_id, target_role, message, is_read, read_at, created_at, updated_at — **`task_detail_id` 부재** |
| 신규 app_alert_logs INSERT 발생 | **0건** (INSERT 시도 자체가 실패, id 657 이후 증가 없음) |
| GBWS-7038 중복 INSERT 간격 | 02:00:00.846 / 02:00:00.941 (≈95ms) — **후보 E 중복 실행 재확인** |
| **최종 확정 판정** | **🔴 G.3 silent fail (DB schema drift) + 후보 A 부활 동시 확정** |
| **다음 Sprint 명칭** | **`HOTFIX-ALERT-SCHEMA-RESTORE-20260422`** (SQL 수동 복구 1회성) + `HOTFIX-SCHEDULER-DUP-20260422` (중복 실행 별도) |

**증거 원문 (Railway Deploy Logs)**:

```
2026-04-22 02:00:00,822 - app.models.alert_log - ERROR - [alert_insert_fail] INSERT failed:
  alert_type=RELAY_ORPHAN, serial_number=GPWS-0773, qr_doc_id=DOC_GPWS-0773,
  task_detail_id=None, target_role=TMS, target_worker_id=None,
  message='[릴레이 미완료] [GPWS-0773 | O/N: 6690] 가압검사 ...',
  error=column "task_detail_id" of relation "app_alert_logs" does not exist

2026-04-22 02:00:00,822 - app.services.alert_service - ERROR - [alert_create_none]
  create_alert returned None: alert_data={'alert_type': 'RELAY_ORPHAN', ...
  'serial_number': 'GPWS-0773', 'qr_doc_id': 'DOC_GPWS-0773', 'target_role': 'TMS'}

[GBWS-7038 02:00:00.846 동일 패턴]
[GBWS-7051 02:00:00.887 동일 패턴]
[GBWS-7038 02:00:00.940~941 중복 execution 동일 패턴]
```

> 이 로그로 G.3 서브타입 = **"DB schema drift (컬럼 부재)"** 로 세분화 확정. 이어서 §12 에 근본 원인 + 복구 플랜 정리.

---

### 11.14.7 복구 실행 후 관찰 결과 (2026-04-22 03:00 UTC = 12:00 KST tick) — 🟢 복구 완료

> §12.6 복구 SQL 을 `11:25:17 KST` pgAdmin prod 에서 수동 실행. 35분 대기 후 다음 정각 tick 에서 관찰한 결과.

| 검증 항목 | 기대값 | 실측 | 결과 |
|---|---|---|---|
| A. `task_detail_id` 컬럼 존재 | YES integer nullable | `integer / YES` | 🟢 PASS |
| B. `migration_history` 049 기록 | `id=37, filename='049_alert_escalation_expansion.sql'` | `id=37, executed_at=2026-04-22 11:25:17.863357+09` | 🟢 PASS |
| C. enum 3종 등록 | 3 rows | `TASK_NOT_STARTED`, `CHECKLIST_DONE_TASK_OPEN`, `ORPHAN_ON_FINAL` 3건 | 🟢 PASS |
| D. `[alert_insert_fail]` 신규 발생 | 0건 | **0건** (03:00~03:01 UTC) | 🟢 PASS |
| E. `[alert_create_none]` 신규 발생 | 0건 | **0건** | 🟢 PASS |
| F. `[alert_silent_fail]` 신규 발생 | 0건 | **0건** | 🟢 PASS |
| G. `Alert created: id=... type=RELAY_ORPHAN` | ≥1건 | **16건** (id=658~673) | 🟢 PASS |
| H. scheduler job executed successfully | ≥3종 | `릴레이 미완료 task 감지`, `작업자 리마인더`, `휴게시간 자동 일시정지`, `Access Log 정리` 모두 정상 완료 | 🟢 PASS |
| I. 후보 E (duplicate scheduler) 잔존 여부 | 2회 실행 (Option 2 전까지 예상) | `작업자 리마인더` 03:00:00,002 + 03:00:00,003 (1ms 간격) 등록, executed_successfully 2회 | ⚠️ **잔존 확정** — Option 2 Sprint 필요 |

**증거 원문 (12:00 KST tick)**

```
2026-04-22 03:00:00,001 - app.services.scheduler_service - INFO - Running check_orphan_relay_tasks_job
2026-04-22 03:00:00,002 - apscheduler.executors.default - INFO - Running job "작업자 리마인더 (매 1시간)..."
2026-04-22 03:00:00,003 - apscheduler.executors.default - INFO - Running job "작업자 리마인더 (매 1시간)..."   ← 후보 E 증거 (1ms 뒤 재등록)
2026-04-22 03:00:00,060 - app.models.alert_log - INFO - Alert created: id=658, type=RELAY_ORPHAN, target_role=MECH
2026-04-22 03:00:00,096 - app.models.alert_log - INFO - Alert created: id=659, type=RELAY_ORPHAN, target_role=MECH
2026-04-22 03:00:00,132 - app.models.alert_log - INFO - Alert created: id=660, type=RELAY_ORPHAN, target_role=TMS
2026-04-22 03:00:00,162 - app.models.alert_log - INFO - Alert created: id=661, type=RELAY_ORPHAN, target_role=MECH
...
2026-04-22 03:00:00,526 - app.models.alert_log - INFO - Alert created: id=673, type=RELAY_ORPHAN, target_role=ELEC
2026-04-22 03:00:00,446 - apscheduler.executors.default - INFO - Job "릴레이 미완료 task 감지" executed successfully
```

**알람 16건 분포 분석 (2026-04-22 R1 쿼리 결과 + 사용자 피드백 반영 최종)**

- target_role=MECH: 3건 (id=658, 659, 661)
- target_role=TMS: 10건
- target_role=ELEC: 3건
- **총 16건 = 10 unique orphan × 1 + 중복 6건 (5 unique × 2x~3x)**

**R1 쿼리 결과 (실측)**

| serial_number | cnt | ids | gap_ms |
|---|---|---|---|
| GBWS-6980 | 2 | 659, 661 | 59.77 |
| GBWS-7017 | 2 | 663, 665 | 18.87 |
| GBWS-7024 | 2 | 666, 667 | 31.50 |
| GBWS-7038 | 2 | 672, 673 | 73.15 |
| **GPWS-0773** | **3** | **668, 669, 671** | **86.37** |

- Unique orphan 수 = **10개** (베타 설비 3대 → 20대+ 확장으로 자연 증가)
- 중복된 orphan 수 = **5개**
- 초과 기록 = **6건** (4×1 + 1×2)
- 중복율 = **6/16 = 37.5%**
- gap_ms 일관된 18~86ms 분포 → **동시 실행 race condition** 의 전형

> **🔴 정정 기록 (2단계)**: 
>
> **1차 정정** — 초안의 "16 = 8×2" 해석 오류 철회. 사용자 피드백으로 beta 설비 확장(3대→20대+) 가설 제시.
>
> **2차 정정 (R1 쿼리 후 최종 확정)** — "`task_reminder_job` 만 영향" 추정도 오류. R1 결과 5건 중복 + GPWS-0773 3중복 관찰로 **`check_orphan_relay_tasks_job` 도 최소 3 worker 에서 동시 실행** 되고 있음이 확정. Railway 로그 공유분에 일부 INFO 가 누락됐던 것이 이전 착시의 원인.

**Candidate E 최종 정의 (2026-04-22 확정)**

| 구분 | 최종 확정 |
|---|---|
| 영향 범위 | **전 scheduler job** (최소 `task_reminder_job` + `check_orphan_relay_tasks_job` 2종 확인. 다른 9종 추정) |
| Worker 수 추정 | **≥3** (GPWS-0773 3중복 근거) |
| RELAY_ORPHAN 중복율 | **37.5% (6/16)** |
| Sprint 우선순위 | 🔴 **S2 — 즉시 착수** |
| 해결책 | Option 2 (fcntl file lock) — GPWS-0773 triple 케이스 고려 시 Option 3 (Redis distributed lock) 까지 병행 검토 권고 |

> 🔴 **3차 정정 — 결정적 모순 발견 (2026-04-22, Pre-flight Check 필수화 근거)**
>
> **모순**: Procfile `gunicorn -w 2` → worker 최대 **2**. 하지만 R1 실측 **3중복** (GPWS-0773) → scheduler 인스턴스 **≥3**. 수학적으로 `-w 2` **단일 컨테이너로는 3을 초과할 수 없음**.
>
> **의미**: Railway 가 **multi-replica 또는 multi-container** 로 배포 중일 가능성 매우 높음. 2 workers × 2 replicas = 4 scheduler 또는 zero-downtime 재시작 중 일시적 겹침 시나리오.
>
> **Option 2 (fcntl file lock) 의 전제 무효화 위험**:
> - 각 컨테이너가 독립 `/tmp` filesystem 을 가지면 `fcntl.flock('/tmp/axis_ops_scheduler.lock')` 은 **모든 컨테이너에서 성공 획득** → 상호 배제 실패 → Option 2 **무용지물**
> - 이 경우 **Option 3 (Redis distributed lock) 필수**
>
> **해결**: HOTFIX-SCHEDULER-DUP-20260422 Sprint 에 **Phase 0 Pre-flight Check 섹션 신설** (AGENT_TEAM_LAUNCH.md). 착수 전 반드시 `ps -ef` / `mount` / diagnostic endpoint 로 Railway topology 실측 → 단일 컨테이너 / multi-replica 판정 → Option 2 또는 3 확정 후 구현.
>
> **보수적 기본값**: 실측 생략 시 **Option 3 (Redis lock) 기본 선택** — R1 3중복 이미 multi-instance 가능성 시사.

**베타 설비 확장 영향**
- 확장 전: 3대 → 일간 12~23건 알람
- 4-16: 60건 (확장 진행 중 이상치)
- 확장 후: 20대+ → tick 당 10 unique 예상 → 일간 ~80~160건 (orphan 특성상 매시간 반복 아님)

**pgAdmin 교차검증 (12:00 KST tick 직후)**

```sql
SELECT MAX(id) FROM app_alert_logs;
-- 결과: 673  (복구 직전 max=657, Δ=+16)
```

| 구분 | 복구 직전 | 03:00 UTC tick 직후 | 증감 |
|---|---|---|---|
| `MAX(app_alert_logs.id)` | 657 (5일간 stuck) | **673** | **+16** |

→ Railway INFO 로그의 `id=658~673` 범위와 pgAdmin `MAX(id)=673` 일치. **알람 파이프라인 전구간 (스케줄러 → create_alert → INSERT → DB commit) 정상화 확증**.

**일자별 집계로 장애 기간 DB 레벨 확증**

```sql
SELECT DATE(created_at AT TIME ZONE 'Asia/Seoul') AS day,
       COUNT(*), COUNT(DISTINCT alert_type) AS types
FROM app_alert_logs
WHERE created_at >= '2026-04-10'
GROUP BY day ORDER BY day;
```

| day | count | types | 해석 |
|---|---|---|---|
| 2026-04-10 | 17 | 4 | 정상 |
| 2026-04-11 | 12 | 2 | 정상 |
| 2026-04-12 | 13 | 2 | 정상 |
| 2026-04-13 | 15 | 3 | 정상 |
| 2026-04-14 | 23 | 4 | 정상 |
| 2026-04-15 | 17 | 3 | 정상 |
| 2026-04-16 | 60 | 3 | **정상 (장애 직전일, 이상치 — 별건 확인 대상)** |
| **(4-17 ~ 4-21)** | **⛔ 결과에 없음** | **⛔** | **🔴 5일 장애 구간 — DB 에 0건 기록 공식 확정** |
| **2026-04-22** | **16** | **1** | **🟢 복구 후 첫 tick (RELAY_ORPHAN 만). 다음 tick 에서 types 자연 증가 예상** |

→ §9 의 "5일 장애" 추정이 **DB GROUP BY 결과에서 row 자체가 존재하지 않음** 으로 공식 확정. 4-17 ~ 4-21 기간 중 단 1건의 app_alert_logs INSERT 도 성공하지 않았음. 4-22 의 16건은 복구 직후 증가분 Δ=+16 과 완전 일치.

**결론**: G.3+A 스키마 drift 는 🟢 완전 해소. 이제 원본 장애 (알람 0건) → 새로운 문제 (2배 기록 축적) 로 전이. **후보 E (Option 2 file lock) Sprint 가 🔴 S2 즉시 우선순위**.

---

## 12. 근본 원인 최종 확정 + 복구 플랜 (2026-04-22 11:00 KST)

> §11.14.6 실측 결과 기반. 5일 알람 장애의 단일 근본 원인이 **"Railway 운영 DB 에 migration 049 미적용"** 으로 확정됨. 후보 A 부활 + G.3 서브타입 구체화. 복구는 SQL 수동 1회 실행으로 가능.

### 12.1 확정된 근본 원인 (단 한 문장)

**Railway 운영 DB 의 `app_alert_logs` 테이블에 `task_detail_id` 컬럼이 존재하지 않아, Sprint 61-BE 배포 이후(4-17~) `alert_log.create_alert()` 의 8-컬럼 INSERT 가 100% PsycopgError 로 실패하고 `try/except` 가 이를 삼켜 `return None` 반환 → `app_alert_logs` 에 5일 연속 0건 기록.**

### 12.2 3-증거 종합

| # | 증거 | 값 | 의미 |
|---|---|---|---|
| 1 | Railway 로그 (Phase 1.5 ERROR 로깅) | `column "task_detail_id" of relation "app_alert_logs" does not exist` × 4건 (02:00 UTC 단일 tick) | DB 레벨 실패 직접 확인 |
| 2 | Q5 `information_schema.columns` | app_alert_logs 12 컬럼, **task_detail_id 부재** | 컬럼 부재 직접 확인 |
| 3 | Q1 `migration_history` | max id=36 (`048_elec_master_normalization.sql`), **049 기록 없음** | migration 049 미실행 직접 확인 |

세 증거 모두 **독립적으로 동일 결론**을 가리킴 — 삼각 검증 완료.

### 12.3 타임라인 복원 (2026-04-16 성공 / 2026-04-17 실패 전환점)

> **🏭 환경 컨텍스트 (2026-04-22 추가 메모)**: 본 장애는 베타 운영 기간 중 발생. **설비 대수 3대 → 20대+ 확장** 과정과 겹침.
> - 4-10~4-15 평균 12~23건/일 = 소수 설비(3대 베타) 기준 기저치
> - 4-16 급증 60건 = 설비 확장 초기 orphan 빈발 구간 + `check_orphan_relay_tasks_job` 4시간 threshold 에 일괄 도달
> - 4-22 복구 후 12:00 tick 16건 = 확장 후 정상 수준(이전 기저치 × 3~7배)
> - **교훈**: 관찰성 지표는 **절대값**(건수) + **상대값**(설비당 건수·일간 편차) 양쪽 모두 확인해야 "갑자기 0건 = 장애" 판정 가능. 포스트모템 시 알람 대시보드에 설비수·활성 task 수 상호 비교 지표 추가 검토.

```
~ 2026-04-16 21:00 KST (id 657, RELAY_ORPHAN)
  alert_log.py INSERT = 7 컬럼 (task_detail_id 명시 없음, 구 코드)
  Railway prod app_alert_logs = 12 컬럼 (task_detail_id 없음)
  → 정상 INSERT 성공 → 4-16 60건 + 누적 657건

2026-04-17 (Sprint 61-BE + 61-BE-B + HOTFIX 01~05 배포)
  alert_log.py 가 8 컬럼 INSERT 로 변경 (task_detail_id 추가)
  backend/migrations/049_alert_escalation_expansion.sql 파일 신규 커밋
  ⚠️ Railway prod 배포: 코드는 반영, migration 049 는 실행 안 됨
  → app_alert_logs 여전히 12 컬럼, 코드는 task_detail_id 참조
  → 모든 INSERT PsycopgError
  → create_alert() try/except → return None
  → create_and_broadcast_alert() → INSERT 재시도 없이 None 반환
  → app_alert_logs 기록 0건

2026-04-17 ~ 2026-04-22 (5일 5시간 — 무증상 outage)
  설비 확장으로 orphan 감지량 증가 + INSERT 전부 실패 조합
  매시 정각 check_orphan_relay_tasks_job + task_reminder_job
  → 수백 건 INSERT 시도 → 전부 silent fail
  → 알람 0건 지속 (일자별 집계에서 4-17~21 row 자체 부재로 DB 레벨 확정)

2026-04-22 10:47 KST (Phase 1.5 HOTFIX 배포, deployment 3907b7d0)
  alert_service.py / alert_log.py ERROR 로깅 추가
  → 이후 모든 INSERT 실패가 ERROR 레벨로 Railway 로그에 기록

2026-04-22 11:00:00 KST (02:00 UTC 정각 tick, 배포 후 최초 hourly)
  check_orphan_relay_tasks_job 중복 실행 (후보 E)
  3개 orphan 감지: GPWS-0773, GBWS-7038, GBWS-7051
  INSERT 시도 4회 (GBWS-7038 중복 2회 포함) → 전부 실패
  → [alert_insert_fail] × 4 + [alert_create_none] × 4 로 근본 원인 포착

2026-04-22 11:25:17 KST (pgAdmin 수동 복구 SQL 실행)
  enum 3종 ADD + task_detail_id 컬럼 ADD + idx_alert_logs_dedupe + admin_settings
  migration_history id=37 (049_alert_escalation_expansion.sql) 수동 기록
  → 검증 A/B/C 3종 PASS (§11.14.7)

2026-04-22 12:00:00 KST (03:00 UTC 정각 tick, 복구 후 최초 hourly)
  check_orphan_relay_tasks_job 실제 3 worker 동시 실행 (후보 E 정량 확정)
  10 unique orphan + 5 중복 (GPWS-0773 3중복 포함) = 총 16건 INSERT 성공
  → id=658~673, 에러 0건
  → 3중 확증 (Railway 로그 + MAX(id)=673 + 일자별 집계 `4-22 count=16 types=1`)

2026-04-22 12:40 KST (R1 중복 쿼리 실행)
  RELAY_ORPHAN 5 serial_number 에서 중복 발견 — GBWS-6980/7017/7024/7038 각 2중복
  GPWS-0773 3중복, gap_ms 18~86ms (동시 실행 race condition)
  → 중복율 37.5% (6/16)
  → Worker ≥3 추정 (3중복 근거)
  → HOTFIX-SCHEDULER-DUP-20260422 🔴 S2 우선순위 확정
```

### 12.4 후보 평가 최종 정정 (§9.3 / §11.6 / §11.14.3 반영)

| 후보 | 이전 평가 | **최종 평가** | 근거 |
|---|---|---|---|
| **A** migration 049 silent fail | 🟢 기각 (§11.6) | 🔴 **부활·확정** | Q1: migration_history max id=36, 049 기록 없음 |
| **B** 쿼리 0건 반환 | 🟡 → G 로 재등장 | 🟢 **완전 기각** | orphan 쿼리가 실제로 3건 감지 |
| **C** 스케줄러 부팅 실패 | 🟢 완전 기각 | 🟢 완전 기각 유지 | §11.6 과 동일 |
| **D** misfire + Railway sleep | 🟢 완전 기각 | 🟢 완전 기각 유지 | §11.6 과 동일 |
| **E** Gunicorn duplicate | 🔴 유지 | 🔴 **유지** (독립 문제) | GBWS-7038 95ms 간격 중복 INSERT 시도 로그로 재확인 |
| **F** DB pool 고갈 | 🟡 일시 증상 | 🟡 일시 증상 유지 | 본 장애 주원인 아님 확정 |
| **G.1** 실제 0건 | 🔴 가능성 중 하나 | 🟢 **명확히 기각** | orphan task 실재 (GPWS-0773 등) |
| **G.2** 쿼리 버그 | 🔴 가능성 중 하나 | 🟢 **명확히 기각** | 쿼리가 정확히 orphan 찾음 |
| **G.3** silent fail | 🔴 신규 확정 | 🔴 **구체 확정** — DB schema drift (컬럼 부재) | §12.2 3-증거 전부 |

**결론**: 본 장애의 근본 원인은 **A = G.3 (A 의 새로운 관점 + G.3 의 새로운 서브타입)** 으로 통합 확정.

### 12.5 왜 migration 049 가 Railway 운영 DB 에 실행 안 됐나 — 가능성 4 (복구 후 조사 대상)

1. **Railway 배포 스크립트에서 migration_runner 호출 누락** — start-up hook 에서 누락됐을 가능성
2. **`.dockerignore` / `.railwayignore` 또는 build 설정으로 049.sql 이 이미지에 포함 안 됨** — 파일이 배포 이미지에 없으면 runner 가 찾을 수 없음
3. **migration_runner 가 049 실행 시도했으나 오류로 중단 + history 미기록** — 현재 migration_history 에 `success`/`error_message` 컬럼이 없어서 실패 이력 추적 불가 (관찰성 부족)
4. **runner 의 파일 스캔·정렬 로직 버그** — 048 이후 파일을 찾지 못하는 엣지 케이스 (예: 파일명 prefix sort, 특정 길이 filter 등)

**구분 진단** (복구 배포 후 실행):
- test DB 에는 049 enum 3종 등록됨 (§11.14.3) → test 환경에서는 runner 정상 동작
- prod DB 에는 049 미기록 → prod 환경 한정 문제
- 따라서 가능성 **1 또는 2** 가 유력. 가능성 3/4 는 test 도 동일하게 실패해야 하는데 그렇지 않음.

### 12.6 즉시 복구 SQL (Option A — Railway prod pgAdmin 수동 실행)

> **실행 위치**: Railway PostgreSQL prod → pgAdmin Query Tool (autocommit 기본값)
> **예상 소요**: ~10초
> **주의**: `BEGIN`/`COMMIT` 으로 감싸지 말 것. `ALTER TYPE ADD VALUE` 는 PostgreSQL 에서 transaction block 안에서 실행 불가.

```sql
-- 049_alert_escalation_expansion.sql 본문을 수동 재실행

-- (1) alert_type_enum 3종 추가
ALTER TYPE alert_type_enum ADD VALUE IF NOT EXISTS 'TASK_NOT_STARTED';
ALTER TYPE alert_type_enum ADD VALUE IF NOT EXISTS 'CHECKLIST_DONE_TASK_OPEN';
ALTER TYPE alert_type_enum ADD VALUE IF NOT EXISTS 'ORPHAN_ON_FINAL';

-- (2) app_alert_logs.task_detail_id 컬럼 추가 (🔴 핵심 — 이것만으로 INSERT 실패 중단)
ALTER TABLE app_alert_logs ADD COLUMN IF NOT EXISTS task_detail_id INTEGER NULL;

-- (3) dedupe 인덱스
CREATE INDEX IF NOT EXISTS idx_alert_logs_dedupe
  ON app_alert_logs (alert_type, serial_number, task_detail_id)
  WHERE task_detail_id IS NOT NULL;

-- (4) admin_settings 4종
INSERT INTO admin_settings (setting_key, setting_value) VALUES
  ('alert_task_not_started_enabled', 'true'),
  ('alert_checklist_done_task_open_enabled', 'true'),
  ('alert_orphan_on_final_enabled', 'true'),
  ('task_not_started_threshold_days', '2')
ON CONFLICT (setting_key) DO NOTHING;

-- (5) migration_history 수동 기록 (이후 runner 재시도 방지)
INSERT INTO migration_history (filename, executed_at)
VALUES ('049_alert_escalation_expansion.sql', NOW());
```

### 12.7 복구 후 즉시 검증 쿼리 (3-step)

```sql
-- (A) task_detail_id 컬럼 추가 확인
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name='app_alert_logs' AND column_name='task_detail_id';
-- 기대: 1 row (integer, YES)

-- (B) migration_history 049 기록 확인
SELECT id, filename, executed_at
FROM migration_history
WHERE filename LIKE '%049%';
-- 기대: 1 row (id=37, 049_alert_escalation_expansion.sql, NOW())

-- (C) enum 3종 등록 확인
SELECT enumlabel
FROM pg_enum
WHERE enumtypid=(SELECT oid FROM pg_type WHERE typname='alert_type_enum')
  AND enumlabel IN ('TASK_NOT_STARTED','CHECKLIST_DONE_TASK_OPEN','ORPHAN_ON_FINAL');
-- 기대: 3 rows
```

### 12.8 복구 후 관찰 (다음 hourly tick 이후)

| 시각 (KST) | 관찰 항목 | 기대값 |
|---|---|---|
| 복구 실행 직후 | Railway 로그 — `[alert_insert_fail]` / `[alert_create_none]` | 신규 발생 **중단** |
| 다음 정각 (예: 12:00 KST = 03:00 UTC) | check_orphan_relay_tasks_job 실행 + INSERT 성공 | `SELECT MAX(id) FROM app_alert_logs` → id 658 이상 |
| 다음 정각 | Railway 로그 — `Job ... executed successfully` | 여전히 표시 (정상) |
| 다음 정각 | Railway 로그 — `Running ... job` 중복 2회 | **여전히 2회** (후보 E 미해결, 정상) |
| 다음 정각 | app_alert_logs 신규 INSERT 건수 | 1건당 **2배 기록** 가능 (후보 E 영향 — Option 2 file lock 전까지) |
| 24시간 관찰 | 일간 알람 수 | 4-16 수준 (17~60건/일) 회복 |

### 12.9 후속 BACKLOG 재조정 (2026-04-22 확정)

| 항목 | 상태 | 범위 / 비고 |
|---|---|---|
| `HOTFIX-ALERT-SCHEMA-RESTORE-20260422` | 🔴 **OPEN → 🟢 COMPLETED (SQL 실행 + 검증 통과 시)** | §12.6 SQL 수동 실행 + §12.7 검증 통과 |
| `HOTFIX-SCHEDULER-DUP-20260422` | 🔴 OPEN | Option 2 (file lock) — 중복 INSERT 2배 기록 방지. Phase 1.5 완료 후 별도 Sprint |
| `POST-REVIEW-MIGRATION-049-NOT-APPLIED` | 🔴 OPEN | §12.5 가능성 4 중 어느 것인지 조사. Railway 배포 스크립트 + Dockerfile + migration_runner 로직 교차 검증 |
| `OBSERV-MIGRATION-HISTORY-SCHEMA` | 🟡 OPEN | `migration_history` 에 `success BOOLEAN`, `error_message TEXT`, `checksum VARCHAR` 컬럼 추가. 다음 실패를 즉시 포착 |
| `OBSERV-MIGRATION-RUNNER-STARTUP-ASSERTION` | 🟡 OPEN | 앱 부팅 시 migrations/ 디렉토리 max filename vs migration_history max id 비교 → 불일치 시 배포 중단 / Sentry 알림 |
| `OBSERV-ALERT-SILENT-FAIL` | 🔴 OPEN | Phase 1.5 임시 ERROR 로깅 → 영구 반영 + Sentry 정식 연동 Sprint 승격 |
| `HOTFIX-SCHEDULER-PHASE1.5-LOGGING` | 🟢 COMPLETED (배포 + 포착 완료) | 본 진단의 결정적 도구. 포스트모템 기록 대상 |
| `POST-REVIEW-HOTFIX-PHASE1.5-20260422` | 🔴 OPEN | 긴급 HOTFIX 예외 조항 #24h 이내 Codex 사후 검토 |
| `INFRA-COLLATION-REFRESH` | 🟡 MEDIUM 유지 | 별건, Sprint 62 이후 처리 |

### 12.10 AGENT_TEAM_LAUNCH.md Sprint 재조정

- `HOTFIX-SCHEDULER-PHASE1.5` (작성 완료, 배포 완료) — 포스트모템만 남음
- **`HOTFIX-ALERT-SCHEMA-RESTORE-20260422`** (신설 필요) — pgAdmin SQL 수동 실행 절차 + 검증 체크리스트. 팀 에이전트 불필요, Twin파파 단독 작업
- `HOTFIX-SCHEDULER-DUP-20260422` (신설 예정) — Option 2 file lock. BE teammate 1명. 복구 확인 후 별도 Sprint 로 진행

### 12.11 다음 세션 실행 순서 (체크리스트)

1. ✅ §12.6 복구 SQL 을 pgAdmin prod 에서 실행 — **완료 (2026-04-22 11:25:17 KST)**
2. ✅ §12.7 검증 쿼리 A/B/C 실행 — 모든 기대값 일치 확인 (§11.14.7 A/B/C 3종 PASS)
3. ✅ 다음 정각 tick (12:00 KST = 03:00 UTC) 대기 — **완료**
4. ✅ Railway 로그: `[alert_insert_fail]` / `[alert_create_none]` 신규 발생 중단 확인 — **0건 확정**
5. ✅ `SELECT MAX(id) FROM app_alert_logs` — 신규 INSERT 확인 → **657 → 673 (+16)**
6. ✅ 중복 INSERT 건수 확인 — **R1 쿼리 실행 완료. 최종 확정: 10 unique orphan + 5 duplicate (그중 GPWS-0773 3중복). Candidate E 가 RELAY_ORPHAN 에도 영향, 최소 3 worker 동시 실행. Sprint 🔴 S2 승격 확정**
7. ✅ §11.14.6 판정 row → §11.14.7 신설로 "🟢 복구 완료" 섹션 기록
8. ☐ `AGENT_TEAM_LAUNCH.md` 에 `HOTFIX-ALERT-SCHEMA-RESTORE-20260422` 신설 항목 추가 ← **다음 작업**
9. ☐ `AGENT_TEAM_LAUNCH.md` 에 `HOTFIX-SCHEDULER-DUP-20260422` 신설 항목 추가 (🔴 S2, Option 2 file lock)
10. ☐ `BACKLOG.md` 에 §12.9 표의 9개 항목 등록
11. ☐ `handoff.md` 에 "2026-04-22 알람 장애 root cause 확정 + 복구" 섹션 추가
12. ☐ 24시간 후 일간 알람 수 회복 여부 확인 (4-16 수준 기대) — 내일 확인
13. ☐ `POST-REVIEW-MIGRATION-049-NOT-APPLIED` 조사 착수 — Railway 배포 스크립트 / Dockerfile / migration_runner 3개 파일 교차 검토

### 12.12 본 장애의 핵심 교훈 (포스트모템 초안)

1. **migration_history 의 관찰성 부재가 5일 장애의 결정적 지연 요인** — `success` / `error_message` 컬럼이 있었으면 4-17 배포 직후 즉시 포착 가능했음
2. **Phase 1.5 ERROR 로깅이 근본 원인을 5분 만에 포착** — §9 ~ §11 의 5일간 지적 추론보다 실로그 1회가 결정적. **"관찰성 우선"** 원칙 재확인
3. **test DB 와 prod DB 가 drift 상태로 잠복** — test 에서 통과한 migration 이 prod 에 적용되지 않아도 알림 없음. `OBSERV-MIGRATION-RUNNER-STARTUP-ASSERTION` 으로 부팅 시 차이 감지 필요
4. **silent fail 패턴의 위험성** — `try/except ... return None` 구조가 장애를 infinite queue 로 저장. CLAUDE.md 에 "예외 삼킴 금지, 최소 ERROR 레벨 로깅 의무화" 원칙 추가 고려
5. **중복 실행 (후보 E) 이 복구 후 새 문제로 전이** — 컬럼 복구 후 같은 알람 2배 기록 우려. Option 2 file lock 이 후속 필수
