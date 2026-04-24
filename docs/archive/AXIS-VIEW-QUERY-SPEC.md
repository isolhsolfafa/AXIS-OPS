# AXIS-VIEW Dashboard Query Specification

> CT / MH 계산 기준 및 React 대시보드 쿼리 설계
> 작성일: 2026-03-02
> 상태: **확정 — 방식 B 메인 + 라인 밸런싱 효율 지표**

---

## 1. 용어 정의

| 용어 | 정의 | 단위 |
|------|------|------|
| **CT (Cycle Time)** | 작업의 첫 시작 ~ 마지막 완료, 휴게시간 차감 | hours (h) |
| **MH (Man-Hour)** | 개인별 실작업시간(break 차감) 합산 | man-hours (MH) |
| **이론 MH** | CT × 투입 인원수 (1명이 했을 경우의 시간) | man-hours (MH) |
| **라인 효율** | 실측 MH / 이론 MH × 100 (인력 활용도) | % |
| **Worker Count** | 해당 작업에 투입된 고유 작업자 수 | 명 |

### 공수 계산 공식
$$MH = \sum_{i=1}^{n} (완료시각_i - 시작시각_i - 휴게시간_i)$$

### 대시보드 표시 예시
```
GAIA 모델 > SN-2026-001 > MECH(기구)
┌──────────────────────────────────────────────────────────────┐
│ Task A (CABINET_ASSY)  CT: 2h40m  공수: 4h20m  2명  효율 81% │
│ Task B (HARNESS)       CT: 3h00m  공수: 3h00m  1명  효율100% │
│ Task C (COVER_ASSY)    CT: 2h00m  공수: 3h40m  2명  효율 92% │
│ Task D (FINAL_CHECK)   CT: 1h00m  공수: 1h00m  1명  효율100% │
│──────────────────────────────────────────────────────────────│
│ MECH 합계              CT: 8h40m  공수: 12h00m       효율 91% │
└──────────────────────────────────────────────────────────────┘
```

### 라인 효율 해석 가이드
```
95~100% : 최적 — 모든 작업자가 CT 전체에 균등 투입
80~95%  : 양호 — 소폭 유휴 시간 존재
60~80%  : 개선 필요 — 인원 배치 불균형
60% 미만 : 문제 — 대기/유휴 시간 과다, 인원 재조정 필요
```

---

## 2. 공수(MH) 계산 기준 — 확정

### 결론: 방식 B(개인별 SUM)를 메인 지표로 사용

> Gemini, GPT, 내부 검토 결과 일치:
> **방식 B가 제조 MES 표준**이며, A/B 비율(라인 효율)이 관리 핵심 지표

### 방식 A: CT × 인원수 (이론 MH)
```
이론MH = (elapsed_minutes - break_overlap) × worker_count
```
- 용도: **라인 효율 계산의 분모** (1명이 했으면 걸렸을 시간)
- 의미: "이 작업에 최대로 투입 가능했던 인력 시간"

### 방식 B: 개인별 실작업시간 SUM (실측 MH) ← **메인 지표**
```
실측MH = SUM(각 작업자의 (completed_at - started_at - break_overlap))
```
- 용도: **공수의 메인 표시값**
- 의미: "실제 투입된 인력 시간"
- DB 매핑: `duration_minutes` (이미 구현됨)

### 라인 밸런싱 효율 (신규 지표)
```
라인효율(%) = 실측MH / 이론MH × 100
            = duration_minutes / (elapsed_minutes × worker_count) × 100
```
- 100%: 모든 작업자가 CT 전체에 참여 (이상적)
- 낮을수록: 유휴/대기 시간 많음 → 인원 배치 개선 필요

### 현재 시스템(AXIS-OPS)의 실제 저장값

| 필드 | 계산 방식 | 대시보드 용도 |
|------|-----------|--------------|
| `duration_minutes` | SUM(개인 duration) - manual_pause | **공수 MH (메인)** |
| `elapsed_minutes` | MAX(completed_at) - MIN(started_at) | **CT** |
| `worker_count` | COUNT(DISTINCT worker_id) | **투입 인원** |
| *(계산)* | `elapsed × worker_count` | **이론 MH** |
| *(계산)* | `duration / (elapsed × worker_count) × 100` | **라인 효율 %** |

---

## 3. 현재 DB 스키마 매핑

### app_task_details (작업 단위)
```sql
-- 핵심 필드
serial_number     VARCHAR(255)   -- 제품 SN
task_category     VARCHAR(50)    -- MECH, ELEC, TM, PI, QI, SI
task_id           VARCHAR(100)   -- CABINET_ASSY 등
task_name         VARCHAR(255)   -- 표시명

-- CT / MH 관련
started_at        TIMESTAMPTZ    -- 첫 작업자 시작시각
completed_at      TIMESTAMPTZ    -- 마지막 작업자 완료시각
duration_minutes  INTEGER        -- 공수 MH (개인별 SUM - pause - break)
elapsed_minutes   INTEGER        -- CT (실경과시간, 분)
worker_count      INTEGER        -- 투입 인원수

-- UNIQUE(serial_number, task_category, task_id)
```

### work_start_log (작업자별 시작 기록)
```sql
task_id       INTEGER   -- FK → app_task_details.id
worker_id     INTEGER   -- FK → workers.id
started_at    TIMESTAMPTZ
-- 인덱스: serial_number
```

### work_completion_log (작업자별 완료 기록)
```sql
task_id           INTEGER
worker_id         INTEGER
completed_at      TIMESTAMPTZ
duration_minutes  INTEGER   -- 개인 duration (break 차감 후)
```

### completion_status (카테고리 완료 추적)
```sql
serial_number     VARCHAR(255) PRIMARY KEY
mech_completed    BOOLEAN
elec_completed    BOOLEAN
tm_completed      BOOLEAN
pi_completed      BOOLEAN
qi_completed      BOOLEAN
si_completed      BOOLEAN
all_completed     BOOLEAN
all_completed_at  TIMESTAMPTZ
```

### 모델 연결 경로
```
plan.product_info.model → model_config.model_prefix (GAIA, DRAGON 등)
plan.product_info.serial_number → app_task_details.serial_number
```

---

## 4. AXIS-VIEW React 대시보드 쿼리

### Q1: 특정 SN의 카테고리별 작업 목록 (Task Level)
```sql
SELECT
    t.task_id,
    t.task_name,
    t.worker_count,
    t.started_at,
    t.completed_at,
    -- CT (시간 단위)
    ROUND(t.elapsed_minutes / 60.0, 1) AS ct_hours,
    -- 공수: 방식 B (메인)
    ROUND(t.duration_minutes / 60.0, 1) AS mh_actual,
    -- 이론 MH: 방식 A (참고)
    ROUND(t.elapsed_minutes * t.worker_count / 60.0, 1) AS mh_theoretical,
    -- 라인 효율
    CASE
        WHEN t.elapsed_minutes * t.worker_count > 0
        THEN ROUND(t.duration_minutes * 100.0
                    / (t.elapsed_minutes * t.worker_count), 0)
        ELSE 100
    END AS line_efficiency_pct
FROM app_task_details t
WHERE t.serial_number = :serial_number
  AND t.task_category = :task_category
  AND t.completed_at IS NOT NULL
  AND t.is_applicable = TRUE
ORDER BY t.started_at;
```

### Q2: 특정 SN의 카테고리별 합계 (Process Level)
```sql
SELECT
    t.task_category,
    COUNT(*) AS task_count,
    SUM(t.worker_count) AS total_workers,
    -- CT 합계
    ROUND(SUM(t.elapsed_minutes) / 60.0, 1) AS total_ct_hours,
    -- 공수 (메인: 방식 B)
    ROUND(SUM(t.duration_minutes) / 60.0, 1) AS total_mh_actual,
    -- 이론 MH (방식 A)
    ROUND(SUM(t.elapsed_minutes * t.worker_count) / 60.0, 1) AS total_mh_theoretical,
    -- 카테고리 라인 효율
    CASE
        WHEN SUM(t.elapsed_minutes * t.worker_count) > 0
        THEN ROUND(SUM(t.duration_minutes) * 100.0
                    / SUM(t.elapsed_minutes * t.worker_count), 0)
        ELSE 100
    END AS line_efficiency_pct,
    -- 완료 여부
    cs.mech_completed, cs.elec_completed, cs.tm_completed,
    cs.pi_completed, cs.qi_completed, cs.si_completed
FROM app_task_details t
LEFT JOIN completion_status cs ON cs.serial_number = t.serial_number
WHERE t.serial_number = :serial_number
  AND t.completed_at IS NOT NULL
  AND t.is_applicable = TRUE
GROUP BY t.task_category,
         cs.mech_completed, cs.elec_completed, cs.tm_completed,
         cs.pi_completed, cs.qi_completed, cs.si_completed
ORDER BY t.task_category;
```

### Q3: 모델별 평균 CT/MH (Model Level — GAIA, DRAGON 등)
```sql
SELECT
    p.model,
    t.task_category,
    t.task_id,
    t.task_name,
    COUNT(DISTINCT t.serial_number) AS sn_count,
    -- 평균 CT
    ROUND(AVG(t.elapsed_minutes) / 60.0, 1) AS avg_ct_hours,
    -- 평균 공수 (방식 B)
    ROUND(AVG(t.duration_minutes) / 60.0, 1) AS avg_mh_actual,
    -- 평균 이론 MH (방식 A)
    ROUND(AVG(t.elapsed_minutes * t.worker_count) / 60.0, 1) AS avg_mh_theoretical,
    -- 평균 라인 효율
    CASE
        WHEN SUM(t.elapsed_minutes * t.worker_count) > 0
        THEN ROUND(SUM(t.duration_minutes) * 100.0
                    / SUM(t.elapsed_minutes * t.worker_count), 0)
        ELSE 100
    END AS avg_line_efficiency_pct,
    -- 평균 투입 인원
    ROUND(AVG(t.worker_count), 1) AS avg_workers
FROM app_task_details t
JOIN plan p ON p.product_info->>'serial_number' = t.serial_number
WHERE p.model = :model_prefix
  AND t.completed_at IS NOT NULL
  AND t.is_applicable = TRUE
GROUP BY p.model, t.task_category, t.task_id, t.task_name
ORDER BY t.task_category, t.task_id;
```

### Q4: 특정 작업의 작업자별 상세 (Worker Detail)
```sql
SELECT
    w.name AS worker_name,
    wsl.started_at,
    wcl.completed_at,
    wcl.duration_minutes,
    ROUND(wcl.duration_minutes / 60.0, 1) AS hours,
    -- 개인 CT 대비 비율
    CASE
        WHEN t.elapsed_minutes > 0
        THEN ROUND(wcl.duration_minutes * 100.0 / t.elapsed_minutes, 0)
        ELSE 100
    END AS participation_pct
FROM work_start_log wsl
JOIN work_completion_log wcl
    ON wcl.task_id = wsl.task_id AND wcl.worker_id = wsl.worker_id
JOIN workers w ON w.id = wsl.worker_id
JOIN app_task_details t ON t.id = wsl.task_id
WHERE wsl.task_id = :task_detail_id
ORDER BY wsl.started_at;
```

### Q5: 일자별 작업 타임라인 (Gantt Chart 용)
```sql
SELECT
    t.task_category,
    t.task_id,
    t.task_name,
    t.started_at,
    t.completed_at,
    t.elapsed_minutes,
    t.worker_count,
    t.duration_minutes
FROM app_task_details t
WHERE t.serial_number = :serial_number
  AND t.started_at IS NOT NULL
  AND t.is_applicable = TRUE
ORDER BY t.task_category, t.started_at;
```

### Q6: 진행중 작업 실시간 모니터링
```sql
SELECT
    t.serial_number,
    t.task_category,
    t.task_name,
    t.started_at,
    t.is_paused,
    t.worker_count,
    EXTRACT(EPOCH FROM (NOW() - t.started_at)) / 60 AS current_elapsed_min,
    (SELECT STRING_AGG(w.name, ', ')
     FROM work_start_log wsl
     JOIN workers w ON w.id = wsl.worker_id
     WHERE wsl.task_id = t.id) AS worker_names
FROM app_task_details t
WHERE t.completed_at IS NULL
  AND t.started_at IS NOT NULL
  AND t.is_applicable = TRUE
ORDER BY t.started_at;
```

### Q7: 라인 효율 경고 목록 (효율 80% 미만 작업)
```sql
SELECT
    t.serial_number,
    t.task_category,
    t.task_name,
    t.worker_count,
    ROUND(t.elapsed_minutes / 60.0, 1) AS ct_hours,
    ROUND(t.duration_minutes / 60.0, 1) AS mh_actual,
    ROUND(t.elapsed_minutes * t.worker_count / 60.0, 1) AS mh_theoretical,
    ROUND(t.duration_minutes * 100.0
          / NULLIF(t.elapsed_minutes * t.worker_count, 0), 0) AS efficiency_pct
FROM app_task_details t
WHERE t.completed_at IS NOT NULL
  AND t.is_applicable = TRUE
  AND t.worker_count >= 2
  AND t.duration_minutes * 100.0
      / NULLIF(t.elapsed_minutes * t.worker_count, 0) < 80
ORDER BY t.duration_minutes * 100.0
         / NULLIF(t.elapsed_minutes * t.worker_count, 0) ASC;
```

---

## 5. React 컴포넌트 구조 (참고)

```
axis-view/
├── pages/
│   ├── ModelDashboard.jsx      -- Q3: 모델별 평균 CT/MH/효율
│   ├── SerialDetail.jsx        -- Q1+Q2: SN별 작업 목록 + 카테고리 합계
│   ├── TaskTimeline.jsx        -- Q5: 간트 차트
│   ├── LiveMonitor.jsx         -- Q6: 실시간 모니터링
│   └── EfficiencyReport.jsx    -- Q7: 라인 효율 경고/분석
├── components/
│   ├── ProcessSummaryCard.jsx  -- 카테고리별 CT/MH/효율 카드
│   ├── TaskTable.jsx           -- 작업 목록 테이블
│   ├── WorkerDetailModal.jsx   -- Q4: 작업자별 상세 모달
│   ├── GanttChart.jsx          -- 타임라인 시각화
│   └── EfficiencyBadge.jsx     -- 효율 % 색상 배지 (초록/노랑/빨강)
└── hooks/
    ├── useTaskMetrics.js       -- Q1~Q3 데이터 fetching
    ├── useLiveMonitor.js       -- Q6 WebSocket/polling
    └── useEfficiencyAlerts.js  -- Q7 효율 경고 데이터
```

---

## 6. 미결 사항 (협력사 미팅 후 확정)

### 6-1. 반복 작업 세션 지원
- [ ] 같은 작업이 여러 날에 걸쳐 반복 발생하는 경우 처리 방안
- [ ] 현재: 1 Task = 1 Start + 1 Complete per Worker (재시작 불가)
- [ ] 필요시: Work Session 테이블 신규 or `_worker_has_started_task()` 로직 수정

### 6-2. CT 정의 세부 (반복 작업 시)
- [ ] CT = 첫시작~마지막완료 (wall-clock) — 현재 `elapsed_minutes`
- [ ] CT = 일별 활성시간 합산 (비작업일 제외) — 별도 계산 필요
- [ ] 반복 작업 시 CT는 각 세션 CT의 SUM인지, 전체 기간인지

### ~~6-3. 공수 기준~~ → 확정
- [x] **방식 B (개인별 SUM) = 메인 공수 지표**
- [x] **방식 A (CT × 인원) = 이론 MH (라인 효율 계산용)**
- [x] **라인 효율(%) = B / A × 100 = 인력 활용도 지표**

---

## 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-03-02 | 초안 작성 — CT/MH 정의, 쿼리 Q1~Q6, 미결사항 정리 |
| 2026-03-02 | **확정** — 방식 B 메인, 라인 효율 지표 추가, Q7 추가, Gemini/GPT 검증 반영 |
