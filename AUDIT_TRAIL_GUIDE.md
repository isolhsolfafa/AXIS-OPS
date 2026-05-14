# AUDIT_TRAIL_GUIDE.md — DB 추적 가이드

> **목적**: `app_task_details` 테이블 close 영역 누가/언제/왜/어떻게 4W 추적 가이드. 운영 분석 + 디버깅 + 정합성 검증 + 통계용.
>
> **도입**: v2.15.14 (2026-05-15) — BUG-SECOND-CLOSE-FORCE-CLOSED-FALSE-POSITIVE 후 audit trail 4 trigger 함수 통일.

---

## 1. 추적 4W 매트릭스

| 4W | 컬럼 | 의미 |
|----|------|------|
| **언제** | `completed_at` | task 정확히 close된 시각 |
| **누가** | `closed_by` | trigger 발동시킨 worker_id (마지막 본인 완료 worker) |
| **왜** | `close_reason` | First/Second Final trigger 영역 어느 경로 + 어느 task |
| **어떻게** | `force_closed` + `duration_minutes` | 자연 close 영역 vs 강제종료 영역 + 작업 시간 |

---

## 2. close_reason 라벨 정의

| 라벨 | 발동 시점 | 영향 task | trigger 함수 |
|------|---------|---------|------|
| `AUTO_CLOSED_BY_FIRST_FINAL_TRIGGER:TANK_DOCKING` | TANK_DOCKING 시작 시점 | gas1/util1/HEATING_JACKET | `_trigger_first_close()` |
| `AUTO_CLOSED_BY_FIRST_FINAL_TRIGGER:IF_2` | IF_2 시작 시점 | panel/cabinet/wiring/IF_1 | `_trigger_first_close()` |
| `AUTO_CLOSED_BY_SECOND_FINAL_TRIGGER:SELF_INSPECTION` | SELF_INSPECTION 완료 시점 또는 체크리스트 100% PUT 시점 | gas2/util2 + SELF_INSPECTION 본인 | `_trigger_second_close()` / `_try_mech_close()` |
| `AUTO_CLOSED_BY_SECOND_FINAL_TRIGGER:IF_2` | INSPECTION 완료 시점 또는 체크리스트 100% PUT 시점 | IF_2 본인 | `_trigger_second_close()` / `_try_elec_close()` |
| `MANUAL_FORCE_CLOSE` | 관리자 수동 강제종료 | 임의 task | `/api/admin/tasks/{id}/force-close` |
| `AUTO_CLOSED_LEGACY` | ⚠️ v2.15.13 이전 영역 fallback (LEGACY trail) | ⚠️ 정보 손실 | (이전 코드, 추적 어려움) |

### 사용 안 하는 라벨

- `AUTO_CLOSED_LEGACY` = v2.15.14 이후 = 0건 발생되어야 함. 1건+ 발견 시 = 어디서 LEGACY 분기 새고 있는지 추적 필요.

---

## 3. force_closed 의미

| 값 | 의미 | 판정 기준 |
|----|------|---------|
| `FALSE` (자연 close) | 모든 worker 본인 "내 작업 완료" 누른 후 trigger 발동 | `unfinished_workers_count = 0` (work_start_log workers 모두 work_completion_log 보유) |
| `TRUE` (강제종료) | 일부 worker 미종료 상태에서 trigger 발동 (manager 권한) | `unfinished_workers_count > 0` |

### 판정 SQL (참조)

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
| **v2.15.14** | 2026-05-15 | 4 trigger 함수 영역 audit trail 통일 (close_reason + closed_by) — `_trigger_first_close`, `_trigger_second_close`, `_try_mech_close`, `_try_elec_close` 모두 동일 trail 형식. Codex 라운드 1 옵션 b 채택 |
| v2.15.13 이전 | ~2026-05-14 | checklist 경로 = `AUTO_CLOSED_LEGACY` + closed_by NULL (정보 손실) / task_service 경로 = `AUTO_CLOSED_BY_*_TRIGGER:...` + closed_by worker_id |

---

## 8. 관련 BACKLOG 영역

- `POST-REVIEW-AUDIT-TRAIL-CONSISTENCY-20260515` — Advisory 6건 잔존 (pytest TC + 추가 정밀화)
- `BUG-SECOND-CLOSE-FORCE-CLOSED-FALSE-POSITIVE-20260514` — v2.15.14 완료

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
