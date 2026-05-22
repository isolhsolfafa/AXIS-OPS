# CT 분석 페이지 — 아이디어 인큐베이션 (Ideas / Long-incubating)

> **목적**: 컨텍스트 영구 보존용. 결정은 시급하지 않음. 오랜 시간 아이디어 도모 후 결정.
>
> **트리거**: 2026-05-22 사용자 catch — "종료누락분석페이지는 목표가 명확하지 작업자 개선이지, 여기에 IQR 데이터가 Minitap 으로 들어가는거고 minitap detail view 가 CT 분석"
>
> **상태**: 📝 IDEAS (인큐베이션 중) — 결정 sprint 없음. Sprint 71 (종료 누락 분석) 완료 후 별도 시점 재논의.

---

## 0. 위치 정정 (중요 — 5-22 catch)

| 페이지 | 목표 | 시각 |
|---|---|---|
| **종료 누락 분석** (Sprint 71) | **작업자 개선** (단순, 명확) | dashboard / KPI / 분포 |
| **Minitap** (진입 카드 / 위젯) | CT 분석 진입 entry point | KPI 카드 + drill-down trigger |
| **CT 분석** (Minitap detail view) | M/M / APS / 계획-실적 연계의 base | 통계 모듈 + 신뢰성 지표 |

→ 본 문서는 **CT 분석 페이지** 에 대한 아이디어 인큐베이션. Sprint 71 은 영역 다름 (작업자 개선용).

---

## 0.5 자동 마감 분석 페이지 (Sprint 71) 의 4단계 사이클

> 2026-05-22 사용자 보강: "자동 마감 분석 페이지는 단순 작업자 개선이 목표지 이부분을 더관리해서 시간에 대한 정합성을 올릴수 있게 교육 및 문제점을 분석해서 편의사항 개선 (app update)"

```
[1차 — 작업자 개선]
   누락 잦은 작업자/task/협력사 식별 → 운영자 피드백 → 작업자 행동 변화
       │
       ▼
[2차 — 시간 데이터 정합성 ↑]
   누락 감소 → 자동 마감 인스턴스 감소 → duration_minutes base 데이터 정확도 상승
   → CT 분석·M/M·APS 의 input quality 자동 개선 (선행 효과)
       │
       ▼
[3차 — 교육 자료]
   "어느 task 가 자주 누락" / "어느 시간대 가장 빈번" / "어느 협력사 패턴"
   → 작업자 교육 컨텐츠 raw data
   → 협력사 미팅 자료 raw data
       │
       ▼
[4차 — App 편의사항 개선 (OPS update)]
   "왜 누락?" 근본 원인 카테고리화:
     · UI 불편 → 종료 버튼 위치 / 크기 개선
     · 알림 부족 → SHIFT_END_REMINDER 임계 조정 / TASK_REMINDER 주기 변경
     · 작업 흐름 misfit → Sprint 41-D 트리거 임계값 조정
     · 권한 / role 모호 → 안내 추가
   → 다음 OPS sprint 우선순위 입력
```

→ Sprint 71 은 단순 dashboard 가 아니라 **OPS 자체의 self-improvement 사이클 1단계** 가 됨.

### Sprint 71 산출물 ↔ 사이클 4단계 매핑

| Sprint 71 산출물 | 1차 (작업자) | 2차 (정합성) | 3차 (교육) | 4차 (app update) |
|---|---|---|---|---|
| `partner_distribution` 협력사별 누락 | 누락 1위 협력사 미팅 | — | 협력사 교육 자료 | — |
| `task_distribution` task 별 누락 | 누락 1위 task 작업자 코칭 | — | task 별 교육 모듈 | UI / 알림 / 흐름 개선 후보 |
| `hourly_distribution` 시간대 | 특정 시간대 누락 작업자 식별 | — | 시간대 교육 (퇴근 직전 catch) | 알림 시간 조정 (SHIFT_END_REMINDER) |
| `trigger_distribution` 트리거 원인 | — | — | — | Sprint 41-D 트리거 임계 조정 |
| `duration_by_category` (V4 IQR) | outlier 작업자 식별 | task 별 신뢰 IQR 확보 | 표준 작업시간 가이드 | duration_validator 임계 조정 |
| `partner_task_matrix` (V6) | 협력사 × task 약점 영역 | — | 협력사 + task 맞춤 교육 | — |
| `unstarted_task_distribution` | 미시작 task 작업자 식별 | 시작 누락 = 계획 vs 실적 갭 | 작업 시작 절차 교육 | QR 스캔 / Task 시작 UI 개선 |

### 4차 → 다음 sprint 진입 사례 (가설)

- "PANEL_WORK 종료 누락 50%↑ 평균 대비" → UI catch → `task_management_screen` 의 완료 버튼 크기/위치 개선 → 별 sprint
- "17:00~18:00 종료 누락 집중" → 알림 catch → `SHIFT_END_REMINDER` 임계 변경 (admin_settings) → 별 sprint
- "BAT 협력사 IF_2 트리거 자동 마감 ↑" → 흐름 catch → Sprint 41-D `_trigger_first_close` 임계 조정 → 별 sprint
- "미시작 자동 마감 다수" → QR 스캔 → Task 시작 절차 catch → BUG-42 영역 또는 신규 sprint

→ Sprint 71 자체가 **OPS update 후보 sprint 생성 엔진**. 4차 결과물 BACKLOG 등록 패턴 가능.

---

## 1. 배경

Sprint 71 (종료 누락 분석) 이 산출하는 IQR / duration / 자동 마감 데이터가 그대로 끝나는 게 아니라 **Minitap → CT 분석 페이지** 로 흘러가는 구조. 즉:

```
[Sprint 71 종료 누락 분석 — 작업자 개선용]
       │
       │ IQR / duration / 자동 마감 raw data
       ▼
[Minitap — 진입 카드 / KPI 위젯]
       │
       │ drill-down click
       ▼
[CT 분석 페이지 — Minitap detail view] ◄── 본 문서 메인 주제
       │
       ├─→ M/M 신뢰성 지표 (장기)
       ├─→ APS 진입 데이터 (장기)
       └─→ 계획-실적 연계 추이 (장기)
```

CT 분석 = `docs/concepts/G-AXIS VIEW(CT분석).html` mockup 존재 (이미 AXIS-VIEW repo 에 컨셉 html 보유).

---

## 2. 데이터 흐름 — Sprint 71 산출물이 어떻게 CT 분석으로 가는가

| Sprint 71 산출물 (raw) | Minitap 표시 (요약) | CT 분석 상세 활용 |
|---|---|---|
| task_id 별 IQR (Q1/Q3) | task 별 정상/경고/위험 분포 | task 별 박스플롯 + sample_size + confidence |
| 자동 마감 비율 (V6 매트릭스) | 협력사 × task 누락률 카드 | 협력사 평가지수 base + APS 리스크 계수 |
| 시간대별 분포 (V1) | 휴게/근무시간 시각 | shift 모델 + 야간/주말 패턴 분석 |
| started vs unstarted | 모집단 분리 KPI | M/M base 산출 (미시작 = 계획 vs 실적 갭) |
| duration_source 5종 (NATURAL / RELAY / MANUAL / PREV_DAY_CAP / SECOND) | 단순 카운트 | M/M 가중치 적용 base (RELAY 자동 마감 = 의심) |

---

## 3. CT 분석 페이지 — M/M / APS / 계획-실적 매핑

```
[CT 분석 페이지]
       │
       ├─→ M/M 신뢰성 지표
       │     · task_id 별 정상 IQR 알아야 "이 작업 실제 4h ± 1h" 신뢰
       │     · auto-close 인스턴스 제외해야 깨끗한 통계
       │     · duration_source 별 가중치 다름
       │
       ├─→ APS 진입 데이터
       │     · 표준 작업시간 (task_id 별 median) ← APS scheduler 입력
       │     · 협력사 capacity (company × task_id 매트릭스) ← APS 자원 배분
       │     · 종료 누락 비율 ← APS 리스크 계수
       │
       └─→ 계획-실적 연계 추이
             · plan.product_info 변경이력 (ETL _FIELD_LABELS 8필드) ↔ duration 변화
             · ship_plan_date 변경 시 실제 ship 패턴
             · mech/elec_start 변경 시 협력사 부하 패턴
```

→ CT 분석 페이지가 **장기 3개 페이지의 공통 base**.

---

## 4. 임계치 결정사항 5건 (T1 ~ T5) — CT 분석에서 결정 필요

> Sprint 71 BE 측에서는 V4 IQR 산출 시 BE 고정값으로 일단 출발 가능. CT 분석 페이지 설계 시점에 admin_settings 등록 여부 결정.

| # | 항목 | Sprint 71 측 (단기) | CT 분석 측 (장기 결정) |
|---|---|---|---|
| **T1** | IQR 산출 기간 | BE 고정 30일 | admin_settings `iqr_lookback_days` (30/60/90 동적) |
| **T2** | `sample_size` confidence 임계 | 30/100 (VIEW v3) | 운영 1개월 누적 후 재조정 (50/200?) |
| **T3** | Tukey 계수 | 1.5/3.0 표준 | GST 운영 데이터 분포 보고 (예: 2.0/4.0) |
| **T4** | task_id 단위 IQR vs 카테고리 | task_id 단위 (Q4 폐기) | 사전 캐싱 vs 매 호출 산출 — 데이터 양 늘면 캐싱 |
| **T5** | outlier 라벨 비대칭 | 양쪽 동일 critical | "너무 빠른 작업 = 누락 의심" 별도 분류 검토 |

---

## 5. 별 sprint 후보 3건 (CT 분석 영역)

### Sprint 72 (가칭) — 계획-실적 연계 추이

- **트리거**: `plan.product_info` 변경이력 (`_FIELD_LABELS` 8필드)
- **데이터 흐름**: ETL 변경 → 변경 전후 duration 비교 → "계획 변경 시 실적 변화 패턴"
- **활용**: APS 자동 일정 조정 시 "과거 비슷한 변경 패턴에서 실제 얼마나 영향 받았나" reference

### Sprint 73 (가칭) — M/M 신뢰성 지표 페이지

- task_id 별 IQR / median / 표준편차 + sample_size + confidence
- 협력사별 capacity (worker_count × duration)
- duration_source 별 가중치 (NATURAL: 1.0, RELAY: 0.7, MANUAL: 0.3)
- APS 진입 직전 데이터 검증 페이지

### Sprint 74 (가칭) — 통계 공통 모듈 (`statistics_service.py`)

- Sprint 71 V4 IQR 산출 로직을 services 분리
- `/ct` CT 분석 / `/partner/evaluation` / `/dashboard/auto-close` / 추후 APS 모두 재사용
- DRY 정합 (CLAUDE.md L516~538 재활용 원칙)

→ CT 분석 페이지 = Sprint 72/73/74 모두의 공통 base.

---

## 6. 아이디어 5건 (CT 분석 페이지 영역)

### ① V4 IQR 산출을 별 service 로 분리 (DRY 선행)

- `services/statistics_service.py` 신규 — task_id 별 IQR / median / confidence 산출 단일 함수
- Sprint 71 `dashboard_service.py` 는 이 service 호출만 (산출 로직 미포함)
- 장점: CT 분석 / 협력사 평가지수 / APS 모두 동일 함수 호출 → 통계 일관성
- 단점: 사전 설계 비용 +30분

### ② T1~T5 임계치를 admin_settings 등록 (CT 분석 시점에 결정)

- `iqr_lookback_days` (default 30), `iqr_confidence_low_threshold` (default 30), `iqr_tukey_warning` (default 1.5) 등 6~8 keys
- 운영자가 데이터 누적되면 직접 조정 가능
- 단점: admin_settings SETTING_KEYS 28+8 = 36개로 증가

### ③ CT 분석 응답에 `data_quality` meta 필드 추가

- 응답 매 호출에 `{lookback_days, sample_size_total, confidence_overall, last_etl_change_at, ...}` 명시
- FE 에서 "샘플 데이터 부족 — 7일 더 누적 후 신뢰 가능" 자동 hint
- 장기 M/M / APS 활용 시 신뢰도 명시 정합

### ④ 계획 변경 추이를 CT 분석 V7 시각화로 추가

- `plan.product_info` 변경이력 4 필드 (`mech_end` / `elec_end` / `module_start` / `ship_plan_date`) ↔ 실제 duration 변화
- "계획 변경 시 자동 마감 증가" hypothesis 검증
- Sprint 72 (계획-실적 연계) 와 분리 vs 통합?

### ⑤ duration_source 별 가중치 도입 (M/M base)

- v2.15.x 도입한 `duration_source` (NATURAL / RELAY / MANUAL / PREV_DAY_CAP / SECOND) 5종
- M/M 산출 시 "RELAY 자동 마감 duration = 의심" → 가중치 0.7
- CT 분석 응답에 `duration_source_breakdown` 추가 (sample_size 별 분류)

---

## 7. 발산용 추가 질문 (결정 X, 의논 토대)

> 결정 시점이 아니라 아이디어 incubation 단계. 컨텍스트 보존용.

### 페이지 구조

- CT 분석 페이지 단일 vs M/M / APS / 계획-실적 3 별도 페이지?
- Minitap = KPI 카드 위젯 vs 별도 페이지?
- CT 분석 진입 = Minitap drill-down 만? 사이드바 직접 진입도?

### 데이터 산출 시점

- 매 호출 산출 vs 사전 산출 (cron 1h) + 캐싱?
- task_id 별 IQR 산출 비용 — 운영 데이터 누적 시 query 시간 측정 필요
- 데이터 stale 허용 시간 (5분 / 1시간 / 1일)?

### 신뢰도 표현

- confidence low/medium/high 만? 또는 sample_size 직접 노출?
- ETL 변경 후 N 일 데이터는 oblique (덜 신뢰)?
- 시즌성 (월말 vs 월초) 반영?

### M/M 정의

- M/M = Man-Hours / Man-Months 중 어느 단위?
- task_id 별 M/M vs 카테고리 별 M/M?
- 협력사 capacity = worker_count × 평균 duration vs 다른 산출법?

### APS 진입 timing

- APS Lite (~2026 Q3 CLAUDE.md L520) 진입 시점 = CT 분석 페이지 운영 안정화 후?
- APS Full = 어떤 외부 시스템 (SAP / 사내 WAS)?
- APS 인풋 = task_id 별 median + 협력사 capacity 면 충분?

### 계획-실적 연계

- ETL 변경이력 → 자동 마감 증가 hypothesis = 통계적으로 유의한가?
- 변경 시점 ± 며칠 영향 측정?
- 변경 패턴 (mech_end 단축 vs ship_plan 단축) 별 영향 차이?

---

## 8. 연관 mockup / 자료

- AXIS-VIEW `docs/concepts/G-AXIS VIEW(CT분석).html` — CT 분석 페이지 컨셉 mockup (이미 존재)
- AXIS-VIEW `docs/concepts/G-AXIS VIEW(분석).html` — 분석 그룹 전체 컨셉
- AXIS-VIEW `docs/concepts/G-AXIS VIEW(헙력사대시보드).html` — 협력사 평가지수 컨셉 (별 sprint 진입)
- AXIS-OPS `AGENT_TEAM_LAUNCH.md` L44203~L44561 — Sprint 71 BE 설계서
- AXIS-VIEW `OPS_API_REQUESTS.md` #71 L6621~L6966 — Sprint 71 VIEW v3 명세

---

## 9. 컨텍스트 보존 — 다음 의논 재진입 시

```
1. 본 파일 (CT_ANALYSIS_ROADMAP.md) 읽기
2. AXIS-VIEW docs/concepts/G-AXIS VIEW(CT분석).html mockup 같이 보기
3. Sprint 71 운영 데이터 1주~1개월 누적 결과 검토
4. T1~T5 임계치 + 의견 5건 + 발산 질문 5영역 → 결정 단계 진입
5. Sprint 72/73/74 분리/통합 결정
```

---

## 10. 변경 이력

| 날짜 | 내용 |
|---|---|
| 2026-05-22 | 초안 작성 — Sprint 71 (작업자 개선) ↔ Minitap (진입 카드) ↔ CT 분석 (M/M/APS/계획-실적 base) 위치 정정 후 인큐베이션 시작 |
| 2026-05-22 | § 0.5 보강 — Sprint 71 자동 마감 분석 페이지의 4단계 사이클 (작업자 개선 → 시간 정합성 → 교육 → app update). 사용자 catch: "이부분을 더관리해서 시간에 대한 정합성을 올릴수 있게 교육 및 문제점을 분석해서 편의사항 개선 (app update)" |
