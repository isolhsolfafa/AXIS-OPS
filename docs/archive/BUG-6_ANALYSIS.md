# BUG-6: 다중작업자 Task에서 동료 Resume 시 403 FORBIDDEN

> 분석일: 2026-04-07
> 상태: 원인 분석 완료 → 코드 수정 대기

---

## 1. 증상

- **에러 메시지**: `일시정지를 해제할 권한이 없습니다.`
- **HTTP**: 403 FORBIDDEN, error: `FORBIDDEN`
- **발생 조건**: 유저가 작업 일시정지 후 재개를 눌렀을 때 발생
- **보고 빈도**: 현재 4건 (work_pause_log id: 23, 27, 39, 40) — 전부 `resumed_at = NULL`로 미해결

---

## 2. 영향 범위

| 항목 | 내용 |
|------|------|
| 영향 테이블 | `work_pause_log` (재개 불가 → resumed_at NULL 누적) |
| 영향 사용자 | FNI, C&A 협력사 작업자 (Partner, 비관리자) |
| 영향 Task | `worker_count > 1` 다중작업자 task |
| 비영향 | 단독작업(1인), GST 사내직원(cross-worker 허용), 관리자(admin/manager) |

---

## 3. 근본 원인

### 3-1. 권한 체크 코드 (`work.py` L1045-1059)

```python
# L1045: 권한 확인: 일시정지한 작업자 본인 또는 관리자 또는 GST 동료
current_worker = get_worker_by_id(worker_id)
is_admin = current_worker and (current_worker.is_admin or current_worker.is_manager)

# Sprint 11: GST 작업자 간 cross-worker 재개 허용
gst_cross_allowed = False
if current_worker and current_worker.company == 'GST':
    pause_worker = get_worker_by_id(active_pause.worker_id)
    if pause_worker and pause_worker.company == 'GST':
        gst_cross_allowed = True

# L1055: 핵심 권한 체크
if active_pause.worker_id != worker_id and not is_admin and not gst_cross_allowed:
    return 403  # ← BUG 발생 지점
```

### 3-2. 허용 조건 3가지 (현재)

| 조건 | 설명 |
|------|------|
| `active_pause.worker_id == worker_id` | 일시정지를 건 본인 |
| `is_admin or is_manager` | 관리자 |
| `gst_cross_allowed` | GST 소속 동료 간 (Sprint 11) |

### 3-3. 누락된 조건

> **같은 task에 참여 중인 동료 작업자 (Partner 회사 다중작업자)**

task_detail_id=82 데이터:
- `work_start_log`에 5명 기록: 2192, 2190, 2186, 2277, 4441 (전부 같은 task 참여자)
- 서정원(2192, FNI)이 일시정지 → 동료(2190 등, FNI)가 재개 시도
- `active_pause.worker_id(2192) ≠ jwt_worker_id(2190)` → **403**
- FNI ≠ GST → `gst_cross_allowed = False`
- 일반 작업자 → `is_admin = False`
- **모든 조건 불통과 → FORBIDDEN**

---

## 4. 데이터 증거

### 4-1. work_pause_log (미해결 4건)

| pause_id | task_detail_id | pause_worker | 회사 | task_worker_id | resumed_at |
|----------|---------------|-------------|------|----------------|------------|
| 40 | 84 | 2198 (윤춘국) | FNI | NULL | NULL |
| 39 | 82 | 2192 (서정원) | FNI | NULL | NULL |
| 27 | 1834 | 2403 (이성훈) | C&A | NULL | NULL |
| 23 | 81 | 2224 (권민수) | FNI | NULL | NULL |

### 4-2. work_start_log vs work_pause_log 대조

| pause_id | task_detail_id | pause_worker | start_workers (전체) | 다중작업 |
|----------|---------------|-------------|---------------------|---------|
| 23 | 81 | 2224 | 2198, **2224** | ✅ 2명 |
| 27 | 1834 | 2403 | **2403** | ❌ 1명 |
| 39 | 82 | 2192 | 2190, **2192**, 2186, 2277, 4441 | ✅ 5명 |
| 40 | 84 | 2198 | **2198** | ❌ 1명 |

- **굵은 글씨**: pause_worker == start_worker (본인 확인 ✅)
- task 81, 82: 다중작업자 → 동료가 resume 시도 시 403 발생 가능
- task 1834, 84: 단독작업자 → **본인이 resume해도 성공해야 함**

### 4-3. 단독작업자 케이스 (pause_id 27, 40) 추가 분석 필요

pause_id 27(이성훈, 단독)과 40(윤춘국, 단독)은 본인이 resume하면 통과해야 합니다.
이 2건이 실제로 403을 받았는지, 아니면 아직 resume을 시도하지 않았을 뿐인지 구분이 필요합니다.

**확인 방법:**
```sql
-- Railway 로그에서 해당 task의 resume 시도 기록 확인
-- 또는 app_access_log에서 /work/resume + status_code=403 조회
SELECT worker_id, endpoint, status_code, created_at
FROM app_access_log
WHERE endpoint LIKE '%/work/resume%'
  AND status_code = 403
  AND created_at >= '2026-03-30'
ORDER BY created_at DESC;
```

---

## 5. 수정 방향

### 5-1. 코드 변경 (`work.py` L1050 부근)

**Before** (현재):
```python
if active_pause.worker_id != worker_id and not is_admin and not gst_cross_allowed:
    return 403
```

**After** (수정안):
```python
# 같은 task에 참여 중인 동료 작업자 허용 (BUG-6)
task_coworker_allowed = False
if active_pause.worker_id != worker_id and not is_admin and not gst_cross_allowed:
    task_coworker_allowed = _worker_has_started_task(task_detail_id, worker_id)

if (active_pause.worker_id != worker_id
    and not is_admin
    and not gst_cross_allowed
    and not task_coworker_allowed):
    return 403
```

### 5-2. 보안 범위

- `_worker_has_started_task`는 `work_start_log`에 해당 worker의 start 기록이 있는지 확인
- 즉, **해당 task에 실제 참여한 작업자만** resume 허용
- 무관한 제3자는 여전히 403 → 보안 유지

### 5-3. 디버그 로깅 추가 (권장)

```python
logger.warning(
    f"Resume permission check: pause_worker={active_pause.worker_id}, "
    f"jwt_worker={worker_id}, is_admin={is_admin}, "
    f"gst_cross={gst_cross_allowed}, task_coworker={task_coworker_allowed}"
)
```

---

## 6. 테스트 케이스 (추가 필요)

기존 `test_pause_resume.py`에 아래 TC 추가:

| TC ID | 시나리오 | 기대 결과 |
|-------|---------|-----------|
| TC-PR-19 | 다중작업자 task — 동료(start_log 있음)가 resume | **200** 성공 |
| TC-PR-20 | 다중작업자 task — 무관한 제3자(start_log 없음)가 resume | **403** 거부 |
| TC-PR-21 | Partner 다중작업자 — pause한 본인이 resume | **200** 성공 |
| TC-PR-22 | Partner 단독작업자 — pause한 본인이 resume | **200** 성공 (기존 TC-PR-02와 동일하나 company='FNI' 확인) |

---

## 7. 미해결 데이터 정리 (수정 배포 후)

수정 배포 후, 4건의 stuck pause를 수동 해제:
```sql
UPDATE work_pause_log
SET resumed_at = NOW(),
    pause_duration_minutes = EXTRACT(EPOCH FROM (NOW() - paused_at))::int / 60
WHERE id IN (23, 27, 39, 40)
  AND resumed_at IS NULL;

UPDATE app_task_details
SET is_paused = false
WHERE id IN (81, 82, 84, 1834)
  AND is_paused = true;
```
