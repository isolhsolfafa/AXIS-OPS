# AUDIT_TRAIL_GUIDE.md — DB 추적 가이드

> **목적**: `app_task_details` 테이블 close 영역 누가/언제/왜/어떻게 4W 추적 가이드. 운영 분석 + 디버깅 + 정합성 검증 + 통계용.
>
> **도입**: v2.15.14 (2026-05-15) — BUG-SECOND-CLOSE-FORCE-CLOSED-FALSE-POSITIVE 후 audit trail 4 trigger 함수 통일.
> **갱신**: v2.15.16 (2026-05-15) — force_closed 의미론 변경 (auto-close = FALSE 통일 / 강제종료 = manager force-close API 전용) + Sprint 41-B 레거시 루프 제거 (AUTO_CLOSED_LEGACY 신규 발생 종료) + duration_source `PREV_DAY_CAP` enum 추가.

---

## 1. 추적 4W 매트릭스

| 4W | 컬럼 | 의미 |
|----|------|------|
| **언제** | `completed_at` | task 정확히 close된 시각 |
| **누가** | `closed_by` | 자동 close = last_completion_worker_id (마지막 본인 완료 worker, audit trail 보존) / 수동 = 관리자 worker_id |
| **왜** | `close_reason` | First/Second Final trigger 영역 어느 경로 + 어느 task |
| **어떻게** | `force_closed` + `duration_minutes` | 자동 close = FALSE 통일 (v2.15.16 부터) / 수동 강제종료 = TRUE (manager force-close API 전용) |

### closed_by 정책 (v2.15.16, 옵션 B 채택)

- **자동 close**: `closed_by = last_completion_worker_id` 보존 (audit trail 정합).
  - close_reason prefix `AUTO_CLOSED_BY_*` 영역 자동/수동 구분 가능 → 별 컬럼 불필요.
  - 운영 영역 VIEW closed_by_name 표시 영역 정보 가치 보존 (마지막 작업자 trail).
- **수동 강제종료**: `closed_by = 관리자 worker_id` + `close_reason = 'MANUAL_FORCE_CLOSE'`.

---

## 2. close_reason 라벨 정의 (Sprint 71 분류 규칙 정합, 2026-05-26 갱신)

### 2.1 전체 라벨 매트릭스

| 라벨 | 발동 시점 | 영향 task | trigger 함수 | Sprint 71 분류 |
|------|---------|---------|------|------|
| `AUTO_CLOSED_BY_FIRST_FINAL_TRIGGER:TANK_DOCKING` | TANK_DOCKING 시작 시점 | gas1/util1/HEATING_JACKET | `_trigger_first_close()` | **자동 마감** ✅ |
| `AUTO_CLOSED_BY_FIRST_FINAL_TRIGGER:IF_2` | IF_2 시작 시점 | panel/cabinet/wiring/IF_1 | `_trigger_first_close()` | **자동 마감** ✅ |
| `AUTO_CLOSED_BY_SECOND_FINAL_TRIGGER:SELF_INSPECTION` | SELF_INSPECTION 완료 시점 또는 체크리스트 100% PUT 시점 | gas2/util2 + SELF_INSPECTION 본인 | `_trigger_second_close()` / `_try_mech_close()` | **자동 마감** ✅ |
| `AUTO_CLOSED_BY_SECOND_FINAL_TRIGGER:IF_2` | INSPECTION 완료 시점 또는 체크리스트 100% PUT 시점 | IF_2 본인 | `_trigger_second_close()` / `_try_elec_close()` | **자동 마감** ✅ |
| `MANUAL_FORCE_CLOSE` | 관리자 수동 강제종료 | 임의 task | `/api/admin/tasks/{id}/force-close` (v2.9.6 v2.15.20) | **수동 마감** ⚠️ |
| `SHIP_COMPLETE` | 출하 완료 (v2.17.0 Sprint 68) | SI_FINISHING + SI_SHIPMENT | `shipment_service.ship_complete()` | 분류 제외 (정상 출하) |
| `ADMIN_COMPLETE` | PI/QI admin 종료 (v2.18.0 Sprint 69) | PI/QI 카테고리 | `shipment_service.admin_complete()` | 분류 제외 (정상 관리자 완료) |
| `NULL` (또는 없음) | 작업자 본인 완료 | 임의 task | `task_service.complete_work()` | 분류 제외 (자연 close) |
| `AUTO_CLOSED_LEGACY` | ⚠️ v2.15.13 이전 fallback (LEGACY trail) | ⚠️ 정보 손실 | (이전 코드, 추적 어려움) | 별 분석 영역 (회귀 catch) |

### 2.2 Sprint 71 분류 규칙

`close_reason LIKE 'AUTO_CLOSED_BY_%'` = **자동 마감** (Sprint 41-D 트리거 한정).
`close_reason = 'MANUAL_FORCE_CLOSE'` = **수동 마감**.
나머지 (`SHIP_COMPLETE` / `ADMIN_COMPLETE` / `NULL` / `AUTO_CLOSED_LEGACY`) = **본 dashboard 분류 제외**.

→ Sprint 71 (자동 마감 분석 페이지) BE 측 WHERE 절 정합:
- KPI 카운트 (auto_closed.count) = `WHERE close_reason LIKE 'AUTO_CLOSED_BY_%'`
- KPI 카운트 (manual_closed.count) = `WHERE close_reason = 'MANUAL_FORCE_CLOSE'`
- 분류 제외 = 본 페이지 통계 영역 미포함

⚠️ v2.15.16 후 `force_closed=FALSE` 일괄 통일됨 → **`force_closed` 만으로는 자동/수동 구분 불가**. `close_reason` LIKE 패턴 필수.

### 2.3 사용 안 하는 라벨 — 회귀 catch 의무

- `AUTO_CLOSED_LEGACY` = v2.15.16 이후 = 신규 발생 종료 확정.
  - v2.15.14 도입 시점 영역 — `_trigger_second_close()` 단일 경로 통일 의도.
  - **v2.15.16 (5-15) 최종 정리** — Sprint 41-B 레거시 루프 (`task_service.py` L843~L864) 영역 잔존 발견 → 제거 → `_trigger_second_close()` 단일 경로 확정.
  - **1건+ 신규 발생 시 = 회귀 catch 필요** (회귀 catch SQL):
    ```sql
    SELECT id, serial_number, completed_at, close_reason
    FROM app_task_details
    WHERE close_reason = 'AUTO_CLOSED_LEGACY'
      AND completed_at >= '2026-05-15';  -- v2.15.16 이후 신규
    ```

---

## 3. force_closed 의미

> **⚠️ v2.15.16 (2026-05-15) 의미론 변경**: 자동 close trigger 영역 force_closed=FALSE 통일. 강제종료(TRUE) 영역 manager force-close API 전용 의미. 사용자 분석 (5-15) — close trigger 가 근무시간 내 발동 → 미완료 worker 존재해도 자연 close 처리 정합.

| 값 | 의미 | 발동 경로 |
|----|------|---------|
| `FALSE` (자연 close) | 자동 trigger 영역 — 모든 자동 close 경로 (FIRST/SECOND Final trigger, MECH/ELEC Dual-Trigger) | task_service.py trigger 함수 5곳 + checklist_service.py Dual-Trigger 3곳 |
| `TRUE` (강제종료) | 관리자 수동 강제종료 전용 | `/api/admin/tasks/{id}/force-close` API (manager 권한) |

### v2.15.15 이전 정책 (참조)

> v2.15.14 (5-15) ~ v2.15.15 (5-15) 영역 단기 정책 — `unfinished_workers_count > 0` 일 때 TRUE 처리. 사용자 5-15 운영 catch 후 폐기:
> - 사용자 분석: close trigger 가 근무시간 내 발동 → 조건 1 (attendance check_out) + 조건 2 (17:00 fallback) 무의미
> - v2.15.16 영역 자동 close = FALSE 통일

### 판정 SQL (참조 — unfinished_workers_count)

```sql
SELECT COUNT(DISTINCT wsl.worker_id) AS unfinished_count
FROM work_start_log wsl
WHERE wsl.task_id = $TASK_ID
  AND NOT EXISTS (
    SELECT 1 FROM work_completion_log wcl
    WHERE wcl.task_id = wsl.task_id
      AND wcl.worker_id = wsl.worker_id
  );
```

→ v2.15.16 영역 본 SQL 결과 영역 force_closed 결정 영역 사용 안 함. 별 분석 영역 미완료 worker 카운트만 제공.

## 3-1. duration_source enum (v2.15.16 갱신)

| enum | 발동 경로 | close_at 결정 |
|------|---------|----------|
| `NORMAL_COMPLETION` | 정상 worker complete_work() | 본인 work_completion_log 영역 시각 |
| `PREV_DAY_CAP` | **v2.15.16 신규** — trigger 영역 익일/주말 발동 | started 날짜 17:00 KST (음수 보호 분기: started ≥ 17:00 시 started 그대로) |
| `NORMAL_COMPLETION` (priority 1) | orphan 영역 work_completion_log 본인 row 있음 | 그대로 사용 |
| `ATTENDANCE_OUT` | orphan worker attendance check_out 있음 | MIN(check_out, trigger_time) |
| `FALLBACK_TRIGGER_DATE_17` | 위 3건 모두 없음 | MIN(trigger_date 17:00, trigger_time) |
| `INVALID_WARNING` | duration_validator 비정상 검출 | 운영 이상치 표시 |

### PREV_DAY_CAP 발동 매트릭스 (v2.15.16)

| 시나리오 | started | trigger | cap 발동? | close_at |
|----------|---------|---------|-----------|----------|
| 정상 (운영 99%) | 5-15 09:00 | 5-15 14:00 | ❌ | trigger_time |
| 같은 날 야간 | 5-15 09:00 | 5-15 19:00 | ❌ | fallback 17:00 |
| **익일 trigger** | 5-14 14:00 | 5-15 09:00 | ✅ | **5-14 17:00** |
| **주말 후** | 5-10 (금) 14:00 | 5-13 (월) 09:00 | ✅ | **5-10 17:00** |
| started ≥ 17:00 | 5-14 18:00 | 5-15 09:00 | ✅ + 보호 | started 그대로 (음수 차단) |

---

## 4. SQL 활용 사례

### 사례 1: 운영 통계 — trigger 별 close 비율

```sql
-- 최근 7일 자동 close된 task 영역 trigger 유형별 통계
SELECT
  CASE
    WHEN close_reason LIKE 'AUTO_CLOSED_BY_FIRST_FINAL_TRIGGER:%' THEN 'First Final'
    WHEN close_reason LIKE 'AUTO_CLOSED_BY_SECOND_FINAL_TRIGGER:%' THEN 'Second Final'
    WHEN close_reason = 'MANUAL_FORCE_CLOSE' THEN 'Manual'
    WHEN close_reason = 'AUTO_CLOSED_LEGACY' THEN '⚠️ LEGACY (추적 불가)'
    ELSE 'Unknown'
  END AS trigger_category,
  COUNT(*) AS task_count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct
FROM app_task_details
WHERE completed_at > NOW() - INTERVAL '7 days'
  AND close_reason IS NOT NULL
GROUP BY trigger_category
ORDER BY task_count DESC;
```

→ "First Final 60% / Second Final 35% / Manual 5%" 같은 패턴 확보 가능.

### 사례 2: 디버깅 — 특정 S/N close 경로 추적

```sql
-- TEST-1111 영역 close된 task 영역 trigger / 처리자 / 강제종료 여부
SELECT
  task_id,
  task_category,
  completed_at,
  duration_minutes,
  close_reason,
  closed_by,
  force_closed
FROM app_task_details
WHERE serial_number = 'TEST-1111'
  AND completed_at IS NOT NULL
ORDER BY completed_at;
```

→ "gas2 영역 worker 819 영역 SELF_INSPECTION trigger 영역 자연 close됨" 1초 만에 확정.

### 사례 3: 정합성 검증 — LEGACY trail 잔존 추적

```sql
-- v2.15.14 prod 배포 후 LEGACY trail 발생 0건 확인
SELECT COUNT(*) AS legacy_count
FROM app_task_details
WHERE completed_at > '2026-05-15 22:00:00+09'
  AND close_reason = 'AUTO_CLOSED_LEGACY';
```

→ 0건 = 정합 정상 / 1건+ = 어디서 새고 있는지 root cause 추적 필요.

### 사례 4: 책임 분포 — manager 강제종료 vs 자연 close 비율

```sql
-- 최근 30일 영역 force_closed 분포
SELECT
  force_closed,
  COUNT(*) AS task_count,
  COUNT(DISTINCT closed_by) AS unique_workers,
  ROUND(AVG(duration_minutes), 1) AS avg_duration_min
FROM app_task_details
WHERE completed_at > NOW() - INTERVAL '30 days'
GROUP BY force_closed;
```

→ force_closed=TRUE 비율 ↑ = manager 개입 많음 = UX/프로세스 catch / FALSE 비율 ↑ = 자연 흐름 정상.

### 사례 5: trigger task별 자동 close 발동 빈도

```sql
-- SELF_INSPECTION / IF_2 / TANK_DOCKING 영역 trigger 발동 빈도
SELECT
  SUBSTRING(close_reason FROM ':(.*)') AS trigger_task,
  COUNT(*) AS auto_close_count,
  COUNT(DISTINCT serial_number) AS affected_serials
FROM app_task_details
WHERE close_reason LIKE 'AUTO_CLOSED_BY_%_FINAL_TRIGGER:%'
  AND completed_at > NOW() - INTERVAL '30 days'
GROUP BY trigger_task
ORDER BY auto_close_count DESC;
```

### 사례 6: 작업자별 trigger 발동 분포

```sql
-- 어느 작업자가 trigger 가장 자주 발동시키나
SELECT
  w.name AS worker_name,
  w.company,
  COUNT(*) AS triggered_close_count
FROM app_task_details td
JOIN workers w ON w.id = td.closed_by
WHERE td.closed_by IS NOT NULL
  AND td.close_reason LIKE 'AUTO_CLOSED_BY_%_FINAL_TRIGGER:%'
  AND td.completed_at > NOW() - INTERVAL '30 days'
GROUP BY w.name, w.company
ORDER BY triggered_close_count DESC
LIMIT 10;
```

---

## 5. 1년 운영 시점 활용 시나리오

| 시나리오 | 이전 trail (LEGACY) | v2.15.14 trail (통일) |
|---------|---|---|
| 특정 S/N close 경로 추적 | 거의 불가능 (LEGACY 만) | SQL 1줄로 정확 |
| trigger 별 close 비율 분석 | 데이터 손실 (모두 LEGACY) | 정확 통계 |
| 작업자별 close 책임 분포 | closed_by NULL → 불가능 | worker_id로 분포 분석 |
| incident 사후 분석 (잘못 close된 task) | Railway logs 30일 보존 한계 | DB 영구 보존 |
| Sprint 41-D 트리거 정합성 검증 | LEGACY 라벨로 추적 어려움 | trigger 별 SQL 검증 가능 |
| manager 개입 빈도 (UX 평가) | force_closed 만 측정 가능 | force_closed + 작업자 + trigger 통합 |

---

## 6. 트러블슈팅 가이드

### Q1: "특정 task 영역 갑자기 close됐는데 누가?"

```sql
SELECT
  task_id, completed_at, close_reason,
  w.name AS closed_by_name,
  force_closed
FROM app_task_details td
LEFT JOIN workers w ON w.id = td.closed_by
WHERE td.id = $TASK_ID;
```

### Q2: "force_closed=FALSE 인데 사용자가 'manager 강제종료' 라고 catch함"

→ FE 표시 catch 영역 진단. close_reason + closed_by + duration_minutes 확인 후 사용자 화면 영역 라벨 영역 mismatch 영역 추적.

### Q3: "trigger 발동 자체 안 됐다고 의심"

```sql
-- task 영역 close 발동 history
SELECT
  id, task_id, started_at, completed_at,
  close_reason, force_closed, duration_source
FROM app_task_details
WHERE serial_number = $SERIAL_NUMBER
  AND task_category = $CATEGORY
ORDER BY id;
```

→ `close_reason IS NULL` + `completed_at IS NULL` = trigger 발동 안 됨 → Sentry/Railway logs 확인.

---

## 7. 변경 이력

| 버전 | 일자 | 변경 |
|------|------|------|
| **(문서 갱신)** | **2026-05-30** | § 11 신규 — close_at 설계 정합성 점검(우려사항 6건) + 분석 SQL. 노션 「📚 개발 재학습 노트」 5-2 close_at 정본과 정합 |
| **(문서 갱신)** | **2026-05-26** | § 2 close_reason 라벨 정의 갱신 — Sprint 68/69 신규 라벨 (`SHIP_COMPLETE` / `ADMIN_COMPLETE`) 추가 + § 2.2 Sprint 71 분류 규칙 명문화 (5-22 deadline POST-REVIEW-AUDIT-TRAIL-CONSISTENCY 정리) + § 2.3 `AUTO_CLOSED_LEGACY` 회귀 catch SQL 명시 |
| v2.18.0 | 2026-05-19 | Sprint 69 `ADMIN_COMPLETE` 라벨 추가 (PI/QI admin 정상완료) |
| v2.17.0 | 2026-05-19 | Sprint 68 `SHIP_COMPLETE` 라벨 추가 (출하 완료) |
| **v2.15.14** | 2026-05-15 | 4 trigger 함수 영역 audit trail 통일 (close_reason + closed_by) — `_trigger_first_close`, `_trigger_second_close`, `_try_mech_close`, `_try_elec_close` 모두 동일 trail 형식. Codex 라운드 1 옵션 b 채택 |
| v2.15.13 이전 | ~2026-05-14 | checklist 경로 = `AUTO_CLOSED_LEGACY` + closed_by NULL (정보 손실) / task_service 경로 = `AUTO_CLOSED_BY_*_TRIGGER:...` + closed_by worker_id |

---

## 8. 관련 BACKLOG 영역

- `POST-REVIEW-AUDIT-TRAIL-CONSISTENCY-20260515` — ✅ **5-26 해소** (§ 2 close_reason 분류 명문화 + Sprint 71 분류 규칙 정합 — 본 문서 갱신으로 deadline 처리)
- `BUG-SECOND-CLOSE-FORCE-CLOSED-FALSE-POSITIVE-20260514` — v2.15.14 완료
- `BACKLOG-SPRINT71-*` — Sprint 71 v3 진입 시 분류 규칙 본 문서 참조 (close_reason LIKE 'AUTO_CLOSED_BY_%')

---

## 9. 연관 파일

- `backend/app/models/task_detail.py` `auto_close_relay_task()` L714 — 마감 처리 핵심 함수
- `backend/app/services/task_service.py` `_trigger_first_close()` / `_trigger_second_close()` — task complete 경로 trigger
- `backend/app/services/checklist_service.py` `_try_mech_close()` / `_try_elec_close()` — checklist 100% PUT 경로 trigger
- `backend/migrations/056_add_duration_source.sql` — duration_source 컬럼 도입

---

## 10. 향후 확장 영역 (TODO)

- [ ] `DURATION_SOURCE_ENUM` 영역 추적 가이드 (NORMAL_COMPLETION / ATTENDANCE_OUT / FALLBACK_TRIGGER_DATE_17 / INVALID_WARNING)
- [ ] `force_close` 외 manager 권한 trail (수동 force-close API trail)
- [ ] FE 표시 라벨 영역 close_reason mapping 표 (UX consistency)
- [ ] 6개월 / 1년 운영 시점 누적 통계 dashboard 권고

---

## 11. 우려사항 분석 — close_at 설계 정합성 점검 (2026-05-30)

> **배경**: close_at 4단계 폴백(0 PREV_DAY_CAP → 1 NORMAL_COMPLETION → 2 ATTENDANCE_OUT → 3 FALLBACK_17) 설계 리뷰에서 나온 6개 우려. 재설계 필요한 게 아니라 "엣지 정확도·설정 유연성·문서 일치" 보완 후보. 아래 SQL로 **실제 얼마나 자주 발생하는지 숫자로 확인**한 뒤 우선순위 결정.
> **모두 read-only 진단 쿼리** (수정 없음). 정본: 노션 「📚 개발 재학습 노트」 § 5-2.
>
> ### ✅ 해소 상태 — FIX-DURATION v9 (interval-union)
> 본 §11 우려는 `AGENT_TEAM_LAUNCH.md` **v9 갱신(L47308~, 2026-06-02)** 에서 대부분 해소됨. F9 표(L47363) 참조.
> - **핵심 변화 (AS-IS → TO-BE)**: 작업시간 계산을 "시작~닫힘 **한 덩어리**" → "사람별 실제 구간 합산(**interval-union**)" 으로 전환. 완료로그가 있으면 **실제 완료시각 사용**, 안 닫힌 꼬리만 cap.
> - **완료로그 유무 분기 (C9)**: 완료로그 ≥1건 → interval-union(정확) / 0건 → 단일 `[MAX(last_started), close_at] − manual`(뻥튀기 방지).
> - **우려별**: ①(192건, 완료로그 사용으로 해소) · (나)(478건 0분 정정) · ⑤(audit 현행보존 명문화) · ③(started_at 가드) = ✅ / ②(완료로그 있으면 실측, 0건은 admin_settings 별 sprint) = △ / ④(backstop 244건, duration 무관) = 별 sprint.
> - **배경 trail**: 초기 설계 의도(사람별 구간)가 sprint 진행 중 **단일구간으로 변질** → 운영 데이터 비교(§11 진단)로 재점검 → interval-union 복원.

### 우려 ① — cross-day cap이 더 정확한 완료로그를 덮음

**문제**: 우선순위 0(PREV_DAY_CAP)이 1(NORMAL_COMPLETION)보다 먼저 검사됨 → 어제 본인 완료로그(예: 16:00)가 있는데도 다음날 trigger 시 "어제 17:00"로 cap. 실제값을 두고 추측값을 씀.

```sql
-- PREV_DAY_CAP으로 닫혔지만 본인 완료로그가 존재하는 건 (덮어쓴 케이스)
SELECT td.id, td.serial_number, td.task_category, td.task_id,
       td.completed_at                    AS capped_close,    -- 17:00로 cap된 값
       MAX(wcl.completed_at)              AS actual_log,       -- 실제 더 정확한 값
       (td.completed_at - MAX(wcl.completed_at)) AS overcount_gap
FROM app_task_details td
JOIN work_completion_log wcl ON wcl.task_id = td.id
WHERE td.duration_source = 'PREV_DAY_CAP'
  AND td.completed_at > NOW() - INTERVAL '90 days'
GROUP BY td.id
ORDER BY ABS(EXTRACT(EPOCH FROM (td.completed_at - MAX(wcl.completed_at)))) DESC;
```

→ **건수 많고 gap 크면 ① 실재** = "완료로그가 있으면 cross-day라도 우선" 순서 변경 검토. 0건이면 무시 가능.

### 우려 ② — 17:00 cap이 잔업을 깎음

**문제**: PREV_DAY_CAP / FALLBACK_17이 17:00로 자르는데, 그날 실제로 17:00 이후까지 일했으면 그 잔업이 사라짐.

```sql
-- 17:00로 cap됐지만 그날 퇴근기록이 17:00 이후인 건 (잔업 손실 추정)
SELECT td.id, td.serial_number, td.duration_source,
       td.completed_at AS capped_at,
       pa.check_out,
       (pa.check_out - td.completed_at) AS lost_estimate
FROM app_task_details td
JOIN LATERAL (
    SELECT MAX(check_time) AS check_out
    FROM hr.partner_attendance
    WHERE worker_id = td.closed_by
      AND check_type = 'out'
      AND DATE(check_time AT TIME ZONE 'Asia/Seoul')
          = DATE(td.completed_at AT TIME ZONE 'Asia/Seoul')
) pa ON TRUE
WHERE td.duration_source IN ('PREV_DAY_CAP', 'FALLBACK_TRIGGER_DATE_17')
  AND td.completed_at > NOW() - INTERVAL '90 days'
  AND pa.check_out > td.completed_at
ORDER BY lost_estimate DESC;
```

→ lost_estimate 합이 크면 ② 실재 = 17:00을 `admin_settings`(교대/잔업 반영)로 빼는 것 검토.

### 데이터 품질 종합 지표 — duration_source 분포 (가장 중요)

**핵심**: NATURAL/NORMAL_COMPLETION = 깨끗 / 나머지(추정) 비율 = CT 데이터 품질 위험도. 이 "추정 비율"이 앞서 얘기한 **자동마감 적정선**의 측정 대상.

```sql
SELECT COALESCE(duration_source, '(none=자연완료)') AS source,
       COUNT(*) AS cnt,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct
FROM app_task_details
WHERE completed_at > NOW() - INTERVAL '90 days'
GROUP BY duration_source
ORDER BY cnt DESC;
```

→ `PREV_DAY_CAP + ATTENDANCE_OUT + FALLBACK_TRIGGER_DATE_17` 합산 % = **추정 의존도**. 이게 임계(예: 20~30%)를 넘는 task는 CT 통계 보류 대상.

### 우려 ④ — backstop 없음: 오래 OPEN인 작업

```sql
-- 3일 이상 미완료로 떠 있는 작업 (자동 close 안 됨 → 매니저 미처리)
SELECT task_category, COUNT(*) AS open_cnt, MIN(started_at) AS oldest
FROM app_task_details
WHERE completed_at IS NULL AND started_at IS NOT NULL
  AND is_applicable = TRUE
  AND started_at < NOW() - INTERVAL '3 days'
GROUP BY task_category
ORDER BY open_cnt DESC;
```

→ 누적 많으면 "N일 경과 자동 cap-close" backstop 도입 검토.

### 우려 ⑤ — 문서 vs 코드 불일치 (강제종료 duration)

```sql
-- force_closed=TRUE인데 duration이 계산돼 있는 건 (문서엔 "NULL"이라 했으나 코드는 계산)
SELECT
  COUNT(*) FILTER (WHERE COALESCE(duration_minutes, 0) > 0) AS force_with_duration,
  COUNT(*) FILTER (WHERE COALESCE(duration_minutes, 0) = 0) AS force_zero_null
FROM app_task_details
WHERE force_closed = TRUE
  AND completed_at > NOW() - INTERVAL '90 days';
```

→ `force_with_duration > 0` = 코드가 duration 계산함 확인 → 문서(클린코어 NULL)와 코드 중 하나로 통일 (비용 0, 문서만).

### 우려 ③ / (나) — 보조 점검

```sql
-- ③ started_at 결손 (cross-day 보호가 안 도는 잠재 케이스)
SELECT COUNT(*) AS started_null_but_closed
FROM app_task_details
WHERE completed_at IS NOT NULL AND started_at IS NULL
  AND completed_at > NOW() - INTERVAL '90 days';

-- (나) pause 이중차감 의심 — 비정상적으로 짧거나 음수인 duration
SELECT id, serial_number, task_category, duration_minutes, total_pause_minutes,
       started_at, completed_at
FROM app_task_details
WHERE completed_at IS NOT NULL
  AND COALESCE(duration_minutes, 0) <= 0
  AND completed_at > NOW() - INTERVAL '90 days'
ORDER BY duration_minutes;
```

→ 음수/0 duration이 자주 나오면 휴게·pause 차감이 겹쳤을 가능성 → auto-close 경로의 차감 로직 재검.

### 점검 우선순위

| 우려 | CT 영향 | 고치는 비용 | 권장 |
|---|---|---|---|
| ① cross-day cap | 높음 | 중 (순서 변경) | SQL로 빈도 먼저 측정 |
| ② 잔업 cap | 높음 | 중 (admin_settings) | SQL로 손실량 먼저 측정 |
| 품질 지표(분포) | — | 0 (조회만) | **지금 바로 측정 권장** |
| ⑤ 문서 불일치 | 낮음 | 0 (문서) | 바로 정정 |
| ④ backstop | 낮음 | 중 | 누적 보고 후 |
| ③/(나) | 낮음 | 소 | 이상치 모니터링 |

### 배포 후 모니터링 (FIX-DURATION v9 / interval-union — 2026-06-02 배포)

> interval-union(`compute_task_manhour`)이 v2.21.3에 들어옴. 배포 직후 며칠 아래 3개로 정합 확인. 운영 가이드: 협력사에 "내 작업완료 최대한 사용" 안내 → 완료로그 ≥1 경로(정확)로 유도 중.

**모니터링 ① — 이상치 잔존 (백필/누락 경로 점검)**
```sql
SELECT COUNT(*) FILTER (WHERE duration_minutes > 1440) AS over_24h,   -- 8일급 뻥튀기 잔존?
       COUNT(*) FILTER (WHERE COALESCE(duration_minutes, 0) <= 0) AS zero_neg
FROM app_task_details
WHERE completed_at IS NOT NULL
  AND completed_at > NOW() - INTERVAL '90 days';
```
→ `over_24h > 0` = 과거 데이터 백필 안 됐거나 새는 경로 존재 (interval-union이면 8일급 안 나와야 함).

**모니터링 ② — 재활성화/재시작 케이스 정합 (한 worker가 2번+ 시작)**
```sql
SELECT td.id, td.serial_number, td.task_category, td.duration_minutes,
       COUNT(*) AS start_events, COUNT(DISTINCT ws.worker_id) AS workers
FROM app_task_details td
JOIN work_start_log ws ON ws.task_id = td.id
WHERE td.completed_at IS NOT NULL
  AND td.completed_at > NOW() - INTERVAL '14 days'
GROUP BY td.id
HAVING COUNT(*) > COUNT(DISTINCT ws.worker_id)   -- 재시작/재활성화 존재
ORDER BY start_events DESC;
```
→ duration_minutes가 0/비정상 큰 게 없으면 LEAD capping 정상 작동(세션 합산 정확).

**모니터링 ③ — 완료로그 0건 비율 (교육 효과 + 데이터 품질 지표)**
```sql
SELECT COUNT(*) AS closed_total,
  COUNT(*) FILTER (WHERE NOT EXISTS (
    SELECT 1 FROM work_completion_log wcl WHERE wcl.task_id = td.id)) AS no_log,
  ROUND(100.0 * COUNT(*) FILTER (WHERE NOT EXISTS (
    SELECT 1 FROM work_completion_log wcl WHERE wcl.task_id = td.id)) / COUNT(*), 1) AS pct_no_log
FROM app_task_details td
WHERE td.completed_at IS NOT NULL
  AND td.completed_at > NOW() - INTERVAL '30 days';
```
→ **`pct_no_log`이 협력사 교육 후 점점 ↓ 하면 "내 작업완료" 가이드가 먹히는 것.** 이게 곧 "자동마감 적정선"이자 CT 데이터 품질 지표 (낮을수록 interval-union 정확 경로 비율 ↑).

### 배포 검증 — Before / After 비교 (백필 효과 측정)

> ✅ **2026-06-03 배포 + 백필 완료 (v2.22.0)**. 아래 baseline(배포 전)과 실제 결과를 같이 보존 — 검증 trail.
> v13 갱신: attendance를 task-level close_at이 아니라 **각 worker 세션 cap**에 직접 반영. 세션 끝 = `MIN(완료, 본인 check_out, 17시, 다음 시작, close_at)`.

**실제 결과 (배포+백필 후, 2026-06-03):**

| 지표 | baseline(배포 전) | 백필 후 | 판정 |
|---|---|---|---|
| `single_over24h` | 180 | **0** | ✅ 기대값 적중 |
| `zero_neg` 합 | 486 | **정정(1,002건 백필)** | ✅ 구 0버그 복원 |
| 전체 duration 순변화 | — | **−353,617분** | 과대계상 제거 |
| 수동강제 보존 | — | **51건** | ✅ |
| 4월 베타 | — | 미변경 | ✅ (5월~만 재계산) |

> ⚠️ 경계일(`2026-06-02`)은 백필 실행일 기준. 배포 후 신규 마감은 single>24h·zero 발생 X 여야 함(주기적 재확인).

**Baseline (배포 전 · 2026-06-03 측정, 90일):**

| 지표 | 현재(옛 로직) | 의미 |
|---|---|---|
| `over_24h` 합 | **260** | single 180 + multi 82 |
| └ `single_over24h` | **180** | 1명 24h+ = 옛 inflation 본체 |
| └ `multi_over24h` | **82** | 합산 — 일부 정상 가능 |
| `zero_neg` 합 | **486** | pre 456 + post 31 (v9 "478 0버그"와 일치) |

**기대값 (배포 + 백필 후 · 올바른 결과 유추):**

| 지표 | 기대값 | 근거 |
|---|---|---|
| `single_over24h` | **≈ 0** | 1명 man-hour는 PREV_DAY_CAP(시작일 17:00)로 묶여 24h+ 불가. 잔존 시 개별 조사 |
| `multi_over24h` | **↓ (0 아님)** | 다인원 합산은 정상적으로 24h+ 가능. 잔존분이 `worker_count × 합리적 시간`으로 설명되면 OK |
| `zero_neg` 합 | **≈ 0** | 0버그 복원 → 양수. 단 즉시 시작+종료 / 미시작 강제종료(Case 2) 등 legit-0 소수 잔존 가능 |
| 배포 후 신규(`post_fix*`) | **0 유지** | 새 마감은 interval-union → single>24h·zero 발생 X. 0 아니면 로직 점검 |

**검증 절차:**
1. (지금) baseline 기록 — 위 표 ✅
2. v2.22.0 배포 + 백필 실행 (§E9 범위: 완료로그 ≥1 → interval-union 재계산 / 0건 → 단일구간)
3. 위 모니터링 ①·A·B 쿼리 **동일 재실행** → 기대값과 대조
4. 판정: `single_over24h ≈ 0` AND `zero_neg ≈ 0` = 백필 성공 / 배포 후 신규 마감분도 0 유지 확인

**재실행용 분해 쿼리 (배포 후에도 동일 사용):**
```sql
-- A. over_24h 분해
SELECT
  COUNT(*) FILTER (WHERE worker_count = 1)             AS single_over24h,
  COUNT(*) FILTER (WHERE worker_count > 1)             AS multi_over24h,
  COUNT(*) FILTER (WHERE completed_at <  '2026-06-02') AS pre_fix,
  COUNT(*) FILTER (WHERE completed_at >= '2026-06-02') AS post_fix
FROM app_task_details
WHERE duration_minutes > 1440 AND completed_at > NOW() - INTERVAL '90 days';

-- B. zero_neg 분해
SELECT
  COUNT(*) FILTER (WHERE completed_at <  '2026-06-02') AS pre_fix_zero,
  COUNT(*) FILTER (WHERE completed_at >= '2026-06-02') AS post_fix_zero
FROM app_task_details
WHERE COALESCE(duration_minutes,0) <= 0 AND completed_at IS NOT NULL
  AND completed_at > NOW() - INTERVAL '90 days';
```
> ⚠️ `'2026-06-02'` 경계는 **백필 실행일로 갱신**할 것 (백필 후엔 "백필일 이후 신규"가 post_fix 의미).
