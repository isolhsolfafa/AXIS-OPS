# DB Pool 사이즈 보정 검증 쿼리 모음

> Sprint: `FIX-DB-POOL-MAX-SIZE-20260427`
> 적용 시각: 2026-04-27 01:13:55 UTC = **2026-04-27 10:13:55 KST**
> 적용 변경: `DB_POOL_MAX: 20 → 30` (MIN=5 그대로)
> 적용 확인 로그:
> ```
> [db_pool] Connection pool initialized: min=5, max=30, max_age=300s, connect_timeout=5s
> ```
>
> 이 파일은 Phase B (3일 관찰) 동안 매일 실행할 검증 쿼리 + Railway logs grep 명령을 한 곳에 모음.
> 결과 기록란은 각 쿼리 아래 `결과:` 섹션에 채워나감.
> 3일 관찰 종료 후 (D+3 = 2026-04-30 목) Phase C 결정 + 종합 결과 정리 → `PROGRESS.md` 이동 또는 archive.

---

## 🟢 Phase A — 적용 직후 (D+0, 2026-04-27 월 10:14 KST 기준)

### A.1 — Railway logs 적용 확인

```bash
# Railway dashboard logs 또는 CLI
railway logs --service axis-ops-api | grep "Connection pool initialized" | tail -1
```

**기대**: `min=5, max=30, max_age=300s, connect_timeout=5s`

**결과**:
- ✅ 2026-04-27 01:13:55 UTC = 10:13:55 KST 확인
- ```
  [db_pool] Connection pool initialized: min=5, max=30, max_age=300s, connect_timeout=5s
  ```

---

### A.2 — 적용 직후 conn 분포 (배포 1분 시점)

```sql
-- 현재 Pool conn 상태 확인 (배포 직후)
SELECT
  application_name,
  COUNT(*) AS conn_count,
  COUNT(*) FILTER (WHERE state = 'active') AS active_count,
  COUNT(*) FILTER (WHERE state = 'idle') AS idle_count,
  MAX(EXTRACT(EPOCH FROM (now() - state_change)))::INT AS max_idle_sec
FROM pg_stat_activity
WHERE datname = 'railway'
GROUP BY application_name
ORDER BY conn_count DESC;
```

**기대**:
- OPS (application_name NULL 또는 빈 값): 10 conn (MIN=5 × 2 worker, 풀 초기화 직후 즉시 5 생성)
- pgAdmin: 1~2

**결과** (2026-04-27 10:14 KST 측정):

| application_name | conn_count | active | idle | max_idle_sec |
|:---|---:|---:|---:|---:|
| (NULL) — OPS | **10** | _ | _ | _ |
| pgAdmin 4 - CONN | 1 | _ | _ | _ |
| pgAdmin 4 - DB | 1 | _ | _ | _ |

→ ✅ MIN=5 × 2 worker = 10 정상. 풀 초기화 직후 즉시 5 conn 보장.

---

### A.3 — 5분 후 재측정 (max_age 만료 race 가시화 검증)

> 적용 시각 + 5~10분 사이 (10:18~10:23 KST) 1회 실행

```sql
-- 동일 SQL, A.2 와 비교
SELECT
  application_name,
  COUNT(*) AS conn_count,
  COUNT(*) FILTER (WHERE state = 'active') AS active_count,
  COUNT(*) FILTER (WHERE state = 'idle') AS idle_count,
  MAX(EXTRACT(EPOCH FROM (now() - state_change)))::INT AS max_idle_sec
FROM pg_stat_activity
WHERE datname = 'railway'
GROUP BY application_name
ORDER BY conn_count DESC;
```

**관찰 포인트**:
- conn_count 그대로 10 유지 → MIN=5 보장 강함
- 7~9 로 떨어짐 → max_age 만료 lazy 재생성 race 가시화 (Codex A4 가설 입증) → OBSERV warmup 우선순위 ↑

**결과** (2026-04-27 10:19 KST 측정, A.2 후 5분 경과):

| application_name | conn_count | 변동 | 비고 |
|:---|---:|---:|:---|
| (NULL) — OPS | **9** | -1 (10→9) | ⚠️ max_age 만료 lazy 재생성 race 가시화 |
| pgAdmin 4 - CONN | 1 | 0 | |
| pgAdmin 4 - DB | 1 | 0 | |

### 🔴 결정적 발견 — Codex A4 가설 정확 입증

```
타임라인:
  10:14:00  풀 초기화 직후     → OPS 10 conn (MIN=5 × 2)
  10:13:55 + 5분 = 10:18:55    → max_age=300s 만료 trigger
  10:19:00  재측정              → OPS 9 conn (-1)

해석:
  ├─ max_age 5분 도달 → 1개 conn 자발적 폐기
  ├─ 폐기 후 즉시 재생성 안 됨 (psycopg2 ThreadedConnectionPool 의 lazy 동작)
  └─ 다음 getconn() 호출 시점까지 MIN=5 미달 상태 유지
```

### 📊 의미와 후속 조치

1. **MIN=5 의 한계 확정** — 풀 초기화 직후 5분 동안만 강한 보장
2. **OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP 우선순위 P3 → P2 격상 권고**
3. **추가 관찰 필요**: 10:24 (10분 후), 10:49 (35분 후), 11:14 (1시간 후) 추세 측정

### 🔍 A.3-extended — 추가 추세 추적

| 시각 (KST) | 경과 | OPS conn | 변동 | 비고 |
|:---|:---:|---:|---:|:---|
| 10:14 | 0분 | 10 | baseline | 풀 초기화 직후 (Phase A) |
| 10:19 | 5분 | 9 | -1 | max_age 1차 만료 |
| ~10:24~ | ~10분 | 7 | -3 | 감소 가속 |
| (~수십분~) | — | **2** | -8 | 🔴 MIN=5 완전 무효 입증, Codex A4 100% 확정 |
| **(warmup 배포 직후)** | **0분** | **7** | **+5** | ✅ **OBSERV-WARMUP v2.10.6 배포 후 회복 시작** |
| T+5분 | 5분 | __ | __ | warmup 1차 tick 후 → 10 도달 기대 |
| T+10분 | 10분 | __ | __ | 안정 (영구 10 유지 검증) |
| T+30분 | 30분 | __ | __ | 장기 안정성 |

### 🔴 결론 — MIN=5 무효 입증, OBSERV-WARMUP 즉시 P2 격상

```
가설: max_age 만료 → lazy 재생성 → MIN 미달
예측: 10 → 9 → 7 → 5 또는 그 이하 (점진 감소)
실측: 10 → 9 → 7 (5분, 10분 시점)  ✅ 가설 입증

per-worker 추정:
  Worker A: 5 → 4 (1개 폐기, 재생성 안 됨)
  Worker B: 5 → 3 (2개 폐기, 재생성 안 됨)
  합계: 7

다음 burst 도착 시 비용:
  필요 conn 16 (HTTP threads) - 보유 7 = 9 신규 생성
  TLS handshake × 9 = +900~4500ms 추가 지연 가능
```

→ **OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP Sprint 즉시 P3 → P2 격상 + 작성**.

---

### A.4 — Pool exhausted grep (배포 직후 1시간)

```bash
# Railway logs 1시간 분량
railway logs --service axis-ops-api --since 1h | grep -E "Pool exhausted|Using direct connection"
```

**기대**: 0건

**결과**:
- Pool exhausted: ___건
- Using direct connection: ___건

---

## 🟡 Phase B — 3일 peak 관찰 (D+0 ~ D+3)

### B.1 — D+0 (오늘 월요일) 16:30~17:00 KST 퇴근 peak

```bash
# 17:00 KST 이후 grep
railway logs --service axis-ops-api --since 2h | grep -E "Pool exhausted|Using direct connection" | wc -l
```

**기대**: 0건

**결과**:
- 시각: 2026-04-27 17:00~17:30 KST
- Pool exhausted: ___건
- Using direct connection: ___건
- 비고: ___

---

### B.2 — D+1 (화요일) 07:30~09:00 KST 출근 peak

```bash
# 09:30 KST 이후 grep
railway logs --service axis-ops-api --since 4h | grep -E "Pool exhausted|Using direct connection" | wc -l
```

**기대**: 0건

**결과**:
- 시각: 2026-04-28 09:30 KST 측정
- Pool exhausted: ___건
- Using direct connection: ___건
- 비고: ___

---

### B.3 — D+1 화요일 점심 (12:00 KST) Q-B 동시 in-flight 재측정

> ⚠️ **off-peak 측정 권장** (Codex I3): peak 직후 (07:30~09:00) self-join 부담. 점심 12:00~13:00 KST 또는 18:00 이후.

```sql
-- D+1 (화) 출근 peak 의 동시 in-flight 측정
WITH inflight AS (
  SELECT
    created_at,
    created_at - (duration_ms || ' milliseconds')::interval AS started_at
  FROM app_access_log
  WHERE created_at >= '2026-04-28 07:00:00+09'
    AND created_at <  '2026-04-28 09:00:00+09'
)
SELECT
  TO_CHAR(date_trunc('second', a.started_at AT TIME ZONE 'Asia/Seoul'), 'HH24:MI:SS') AS sec_kst,
  COUNT(*) AS concurrent
FROM inflight a
JOIN inflight b
  ON b.started_at <= a.started_at
  AND b.created_at >= a.started_at
GROUP BY 1
ORDER BY concurrent DESC
LIMIT 20;
```

**기대**: peak `< 60` (per-worker × 2). 30 부근이면 정상, 50+ 이면 Phase C 상향 트리거.

**결과** (TOP 5):

| sec_kst | concurrent | 비고 |
|:---|---:|:---|
| __ | __ | peak |
| __ | __ | |
| __ | __ | |
| __ | __ | |
| __ | __ | |

비교 baseline: **2026-04-21 (화) peak 31 동시** (Q-B 원본).

---

### B.4 — D+1 화요일 peak 직후 정밀 진단 (B.5 in Sprint)

> peak (08:00 KST) 직후 즉시 1회 실행

```sql
-- pid + client_addr 추가로 worker A/B 분리 진단 (Claude Code A4)
SELECT
  pid,
  state,
  application_name,
  client_addr,
  EXTRACT(EPOCH FROM (now() - state_change))::INT AS idle_sec,
  TO_CHAR(query_start AT TIME ZONE 'Asia/Seoul', 'HH24:MI:SS.MS') AS query_start_kst,
  SUBSTRING(query, 1, 60) AS query_snippet
FROM pg_stat_activity
WHERE datname = 'railway'
  AND (application_name IS NULL OR application_name = '')
ORDER BY pid;
```

**해석 가이드**:
- pid 그룹 2개 보이면 worker A/B 정상 분리
- 한 그룹의 conn 이 5+ 면 그 worker 가 scheduler owner (peak 직후 idle 여유 분포)
- `idle in transaction` 0건 확인 (있으면 leak 의심)

**결과**: (피크 직후 캡처)
- 총 conn: ___
- Worker A pid 그룹: ___개 (idle ___, active ___)
- Worker B pid 그룹: ___개
- idle in transaction: ___건

---

### B.5 — D+2 (수요일) 07:30~09:00 KST 출근 peak

```bash
railway logs --service axis-ops-api --since 4h | grep -E "Pool exhausted|Using direct connection" | wc -l
```

**결과**:
- Pool exhausted: ___건
- Using direct connection: ___건

---

### B.6 — D+2 수요일 12:00 KST Q-B 재측정

```sql
-- D+2 (수) 출근 peak 의 동시 in-flight
WITH inflight AS (
  SELECT created_at, created_at - (duration_ms || ' milliseconds')::interval AS started_at
  FROM app_access_log
  WHERE created_at >= '2026-04-29 07:00:00+09'
    AND created_at <  '2026-04-29 09:00:00+09'
)
SELECT TO_CHAR(date_trunc('second', a.started_at AT TIME ZONE 'Asia/Seoul'), 'HH24:MI:SS') AS sec_kst,
       COUNT(*) AS concurrent
FROM inflight a
JOIN inflight b ON b.started_at <= a.started_at AND b.created_at >= a.started_at
GROUP BY 1 ORDER BY concurrent DESC LIMIT 20;
```

**결과** (TOP 5):

| sec_kst | concurrent | 비고 |
|:---|---:|:---|
| __ | __ | peak |
| __ | __ | |

---

### B.7 — D+3 (목요일) 07:30~09:00 KST 출근 peak

```bash
railway logs --service axis-ops-api --since 4h | grep -E "Pool exhausted|Using direct connection" | wc -l
```

**결과**:
- Pool exhausted: ___건
- Using direct connection: ___건

---

### B.8 — D+3 목요일 12:00 KST Q-B 재측정

```sql
-- D+3 (목) 출근 peak 의 동시 in-flight
WITH inflight AS (
  SELECT created_at, created_at - (duration_ms || ' milliseconds')::interval AS started_at
  FROM app_access_log
  WHERE created_at >= '2026-04-30 07:00:00+09'
    AND created_at <  '2026-04-30 09:00:00+09'
)
SELECT TO_CHAR(date_trunc('second', a.started_at AT TIME ZONE 'Asia/Seoul'), 'HH24:MI:SS') AS sec_kst,
       COUNT(*) AS concurrent
FROM inflight a
JOIN inflight b ON b.started_at <= a.started_at AND b.created_at >= a.started_at
GROUP BY 1 ORDER BY concurrent DESC LIMIT 20;
```

**결과** (TOP 5):

| sec_kst | concurrent | 비고 |
|:---|---:|:---|
| __ | __ | peak |
| __ | __ | |

---

## 🔵 Phase C — 종합 결정 (D+3 이후)

### C.1 — 3일 누적 Pool exhausted 카운트

```bash
# D+0 ~ D+3 전체 누적 grep
railway logs --service axis-ops-api --since 72h | grep "Pool exhausted" | wc -l
```

### C.2 — 3일 누적 sources by hour

```sql
-- D+0~D+3 시간대별 요청 수 / 응답 시간 분포 (Q-A 재실행)
SELECT
  TO_CHAR(date_trunc('hour', created_at AT TIME ZONE 'Asia/Seoul'), 'Dy HH24') AS hour_kst,
  COUNT(*) AS req_count,
  COUNT(DISTINCT ip_address) AS unique_ips,
  AVG(duration_ms)::INT AS avg_ms,
  MAX(duration_ms) AS max_ms,
  PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms)::INT AS p99_ms,
  COUNT(*) FILTER (WHERE duration_ms >= 1000) AS over_1s,
  COUNT(*) FILTER (WHERE duration_ms >= 5000) AS over_5s
FROM app_access_log
WHERE created_at >= '2026-04-27 00:00:00+09'
  AND created_at <  '2026-05-01 00:00:00+09'
GROUP BY date_trunc('hour', created_at AT TIME ZONE 'Asia/Seoul')
ORDER BY hour_kst;
```

baseline 비교: 2026-04-21~27 의 동일 SQL 결과 (`q-a.csv` 의 7개 평일 peak hours).

**기대**:
- p99 가 baseline 대비 **개선** (특히 화 15:00 의 1981ms → 더 낮아져야 정상)
- `over_5s` = 0 유지
- `over_1s` 가 baseline 대비 감소

### C.3 — Phase C 결정 매트릭스

| 결과 | 결정 | 다음 Sprint |
|:---|:---|:---|
| Pool exhausted **0건/3일** + Q-B peak < 30 | ✅ 30 충분, Sprint 종료 | 없음 |
| **1~5건/3일** | ↑ 40 + leak 의심 | `FIX-DB-POOL-MAX-40-20260501` |
| **10+건/3일** | ↑ 50 + leak audit | `FIX-DB-POOL-MAX-50-20260501` + `OBSERV-DB-CONN-LEAK-AUDIT` |
| Q-B peak **≥ 50** | ↑ 40 (사이즈만) | `FIX-DB-POOL-MAX-40-20260501` |
| **비peak 평균 conn ≥ 8 지속** | leak audit 필수 | `OBSERV-DB-CONN-LEAK-AUDIT` |

---

## 📊 사후 종합 기록 (D+3 종료 후 작성)

```
✅ FIX-DB-POOL-MAX-SIZE-20260427 종합 결과 (작성일: 2026-05-01)

Phase A 적용:
  ├─ 시각: 2026-04-27 10:13 KST
  ├─ 변경: DB_POOL_MAX 20 → 30 (MIN=5 그대로)
  └─ 로그 확인: ✅ "min=5, max=30" 출력

Phase B 3일 관찰:
  ├─ D+0 (월) 퇴근 peak: Pool exhausted ___건
  ├─ D+1 (화) 출근 peak: ___건 / Q-B peak ___ 동시
  ├─ D+2 (수) 출근 peak: ___건 / Q-B peak ___ 동시
  ├─ D+3 (목) 출근 peak: ___건 / Q-B peak ___ 동시
  └─ 3일 누적 Pool exhausted: ___건

Q-A 비교 (baseline 2026-04-21~27 vs 적용 후 2026-04-27~30):
  ├─ Tue 15:00 p99: baseline ___ms → 적용 후 ___ms
  ├─ Wed 09:00 p99: baseline ___ms → 적용 후 ___ms
  └─ over_1s 누적: baseline ___건 → 적용 후 ___건

Phase C 결정:
  ├─ 결정: ___ (30 종료 / 40 ↑ / 50 ↑)
  └─ 사유: ___

OPEN → COMPLETED 전환

후속 Sprint 트리거:
  ├─ OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP: ___ (필요 / 불필요)
  ├─ OBSERV-RAILWAY-HEALTH-TTFB-15S: ___ (개선됨 / 잔존)
  └─ OBSERV-SLOW-QUERY-ENDPOINT-PROFILING: ___
```

---

## 🔗 관련 문서

- Sprint 설계서: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` § FIX-DB-POOL-MAX-SIZE-20260427
- BACKLOG: `AXIS-OPS/BACKLOG.md` § FIX-DB-POOL-MAX-SIZE-20260427
- baseline 데이터: 어제 공유한 q-a.csv / q-b.csv / q-c.csv (2026-04-27 분석)
- 검증 라운드 trail (9건 약점 + 3건 I 정정): Sprint 문서 안 "Claude 원안 약점 trail" 섹션
