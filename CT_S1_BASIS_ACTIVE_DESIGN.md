# S-1 (ⓐ) — CT `basis=active` + 미추적 제외 + 신뢰컷오프 + 월범위 설계서 (v2)

**Sprint ID**: FEAT-CT-BASIS-ACTIVE-TRUSTCUTOFF (VIEW OPS_API_REQUESTS #82 ⓐ)
**범위**: BE only (`statistics_service.py` + `routes/ct_analysis.py`), DB/migration 0 (read-time, 기존 `active_time_minutes` 컬럼 활용)
**연계**: Sprint 85(v2.27.0 CT MVP) 확장 / Sprint 86(v2.28.0 active_time) 활용 / **S-2(ⓑ 진짜 CT union)는 별 sprint**(새 `ct_time_minutes` 컬럼+migration 필요 → 분리)
**v2 변경**: Codex 라운드 1 (M=4/A=4) 반영 + 사용자 결정 2건(5/1 단일 기준 / ⓑ 분리)

---

## 1. 배경 — 운영 데이터 14개 쿼리 검증 (2026-06-08, 전부 5월+ 기준)

> **신뢰 기준 = 2026-05-01 단일.** 5월 이전 = 베타 연습(BAT 미온보딩). 전 분석·산출 5/1+ 고정.

| 발견 | 수치 | 함의 |
|---|---|---|
| 현 CT = M/H | across-worker SUM | active_time_minutes = 공수(effort). 진짜 CT(union)는 **S-2** |
| **act=0 = 미추적** | MECH 배관 ~50%, ELEC ~10% | 작업자 시작=완료 즉시 태깅(work_completion_log d=0) → 실 timing 부재. 원본 로그 추적 확인(계산정상, 데이터부재) |
| act 분포 이봉형 | 0 vs ≥10분 (1~9분 ELEC 4·MECH 6) | **floor = `act > 0`** 충분 |
| act=0 제외 효과 | MECH WASTE_GAS_2 0.5h→**2.2h** | 최대 CT 정화 |
| **미추적율 협력사편중** | **BAT 59% vs FNI 7%** (완료율 둘다 100%) | act>0 제외 시 **FNI 편중 생존편향 위험**(M-1) → coverage 노출 |
| duration backfill 갭 | migration 058 미적용. 4월 raw 40%·5월 raw 9%·6월 raw 2% | duration 6월+만 신뢰. active는 059/060 전구간 clean → **basis=active 당위** |
| 다중작업자 | act>0 24% / 전체 28%(천장) | 추적개선 시 상승. 큰 task 집중 → ⓑ(S-2) 가치 |
| basis 모집단 | n_duration=919 / n_active(0포함)=827 / **n_active>0=683** | basis별 n 분리 필수 |
| Tukey 필요 | PANEL max 31.4h > fence 21.8h | 1-pass 유지 |
| active NULL | TANK_DOCKING(one-action) only | basis=active 실질 손실 0 |

---

## 2. API 변경

```
GET /api/ct/task-stats?basis=&from=&to=&model=&category=&dual=
```
> v3: `period`(last_90d) **완전 제거**(Codex M-6). 소비처 = CT페이지(신규)뿐 + 5/1 단일기본이라 롤링 윈도우 불필요. 기본(무파라미터)=5/1~현재월.

### 2-1. `basis` (duration|active, 기본 duration)
- `basis=active`: box plot(min/q1/median/q3/max/mean/iqr) 산출을 `active_time_minutes` 기반.
- **CT 분석 페이지(FE)는 `basis=active` 명시**(Codex M-Q4). 기본 duration = 기존 대시보드 보호.

### 2-2. 미추적 제외 `act > 0` — **active 전용**
- `basis=active`: `active_time_minutes > 0` 행만 산출. act=0(미추적)+NULL(one-action) 제외.
- ⚠️ `basis=duration`: 이 필터 **미적용**(silent 모집단 변경 금지, Codex M-Q3).

### 2-3. 신뢰 컷오프 — **단일 상수** (사용자 확정 2026-06-08)
```python
CT_TRUST_START_DATE = '2026-05-01'   # KST. 운영 정착 단일 기준. 5월 이전 = 테스트.
```
- CT 산출 endpoint 기본 윈도우 = `CT_TRUST_START_DATE` 이후 (basis 무관 동일 기준).
- ⚠️ `basis=duration`만 추가로 meta `duration_stale_before='2026-06-01'` 경고(058 미적용 → 5월 duration 9% raw 잔존). **별도 컷오프 아님**(단일 5/1 유지) — 경고만.

### 2-4. 월 범위 `from`/`to` (YYYY-MM, KST) — period 제거 (Codex M-6)
- **기본(둘 다 미지정)**: `from = 2026-05`(trust_start 월), `to = 현재 월`.
- **부분 지정 (Codex 라운드2)**: `from`만 → `to = 현재 월`. `to`만 → `from = 2026-05`.
- `from > to` → 400 `INVALID_RANGE`. `YYYY-MM` 형식 위반 → 400 `INVALID_MONTH`.
- `from < 2026-05` → 허용 + meta `immature_window=true`(FE 경고 배지).
- ⚠️ `period`(last_90d) 파라미터 **미지원**(제거). 전달돼도 무시 + meta 영향 없음.

---

## 3. 산출 규칙 + KST 월경계 SQL (Codex M-4)

```
필터 순서 (Codex Q4 PASS 확인):
  ① clean: duration_source IS NULL OR 'NORMAL_COMPLETION'
  ② TMS dirty 제외: task_id NOT IN ('TANK_MODULE','PRESSURE_TEST')
  ③ TEST 제외: serial NOT LIKE 'TEST%' AND COALESCE(customer,'') <> 'TEST CUSTOMER'
  ④ KST 월 윈도우 (아래 predicate)
  ⑤ basis=active 시 active_time_minutes > 0
  ⑥ → Tukey 1-pass: raw fence 계산 → fence 내 재집계 (base_n/clipped_n 보존)
```

KST 월경계 predicate (M-4 확정):
```sql
-- completed_kst = td.completed_at AT TIME ZONE 'Asia/Seoul'
WHERE (td.completed_at AT TIME ZONE 'Asia/Seoul') >= (%(from_month)s || '-01')::date
  AND (td.completed_at AT TIME ZONE 'Asia/Seoul') <  ((%(to_month)s || '-01')::date + interval '1 month')
```
- `from_month`/`to_month` = `'YYYY-MM'`. 경계 = `[from월 1일 00:00 KST, to월+1 1일 00:00 KST)` 반열림 → off-by-one/이중집계 차단.

basis 분기:
```
basis=active   : 값 = active_time_minutes/60, 모집단 act>0
basis=duration : 값 = duration_minutes/60,    모집단 = ⑤ 미적용 (현행)
공통: 카테고리 = pooled_median (Σmedian 폐기), Tukey 1-pass
```

---

## 4. 응답 스키마 (기존 tasks[] 불변 + meta 보강)

```
meta: {
  basis, trust_start: '2026-05-01',
  window: { from, to }, immature_window: bool,
  duration_stale_before?: '2026-06-01',          // basis=duration 시
  basis_label, trust_reason,                       // A-1: '운영정착 5월+'
  n_total, n_used,                                 // 모집단 분리 (Codex MISSING M)
  excluded_zero_active?, excluded_null_active?,    // active 전용
  tukey_clipped: bool,                             // A-3: clipped_n < base_n
  median_basis: 'pooled',
  // M-1+M-5 생존편향 방어 — 협력사별 추적 커버리지
  // ⚠️ M-5: 표시 통계와 동일 슬라이스 — model/category/dual 엔드포인트 필터 + clean/TMS/TEST/window
  //         적용 후, act>0 제외 전 + Tukey 전 에 n_total/n_used 집계 (denominator 정렬)
  tracking_coverage_by_partner: [
    { partner, n_total, n_used, tracked_rate }     // FNI 0.93 / BAT 0.41 등
  ]
}
tasks[]: { ...기존 box plot..., sample_size, standard_status: 'standard'|'provisional' }  // A-2: n<30 = provisional
```
- **캐시 키 (M-3)**: `task_stats:{basis}:{from}:{to}:{period|none}:{model}:{category}:{dual}` — 전 파라미터 포함.

---

## 5. 엣지 / 결정

| # | 사안 | 결정 |
|---|---|---|
| E1 | act floor | `> 0` (이봉형) |
| E2 | basis 기본 | `duration`(하위호환). FE CT페이지 active 명시 |
| E3 | duration mode | act 필터 미적용 + `duration_stale_before` 경고만 |
| E4 | 신뢰 기준 | **5/1 단일**(사용자 확정). duration도 5/1 윈도우 + 경고 |
| E5 | n<30 | 탈락 아님 → `standard_status='provisional'`(A-2) |
| E6 | 생존편향 | CT 모집단은 act>0 유지하되 `tracking_coverage_by_partner` 동반 노출(M-1) — FE가 커버리지 불균등 시 "추적기반 CT" 명시 |
| E7 | DAG garbage | **S-1 미포함**(S-3) |
| E8 | period 파라미터 | **제거**(M-6). 부분 from/to → 빈쪽 기본(from=5월/to=현재월) |
| E9 | ⓑ 진짜 CT | **S-2 분리**(ct_time_minutes 새 컬럼+migration) |
| E10 | coverage 슬라이스 (M-5) | tracking_coverage = 표시통계와 동일 필터(model/category/dual)+clean/TMS/TEST/window, act>0·Tukey 전 집계 |

---

## 6. pytest TC (seed 기반)

- TC-S1-01: basis=active → act>0만 (act=0/NULL 제외)
- TC-S1-02: basis=duration → 현행 불변 (act 필터 미적용)
- TC-S1-03: 기본 윈도우(무파라미터) = 2026-05~현재월 (basis 무관 단일)
- TC-S1-04: 부분 from/to — from만(to=현재월) / to만(from=2026-05) (Codex 라운드2)
- TC-S1-05: 단월 from===to / KST 경계(2026-05-01 00:00, 2026-06-01 00:00 반열림)
- TC-S1-06: immature_window (from < 2026-05)
- TC-S1-07: standard_status provisional (n<30)
- TC-S1-08: meta n_total/n_used/excluded 정합
- TC-S1-09: Tukey base_n>clipped_n → tukey_clipped (PANEL outlier)
- TC-S1-10: tracking_coverage_by_partner (FNI 고/BAT 저)
- **TC-S1-10b: coverage 슬라이스 정렬 (M-5)** — model/category 필터 시 coverage denominator도 동일 필터 적용
- TC-S1-11: 캐시 키 — 다른 basis/월 → 다른 결과(stale 미발생)
- TC-S1-12: 입력검증 — invalid basis / YYYY-MM 위반 / from>to → 400 (A-4)
- TC-S1-13: TMS dirty/TEST 제외 회귀
- **TC-S1-14: duration_stale_before (M-6 연계)** — basis=duration+5월 포함 → meta `duration_stale_before='2026-06-01'` 존재 / from>=2026-06 → 부재

---

## 7. Codex 라운드 2 검증 질문

1. M-1~M-4 + A-1~A-4 반영본 정합한가? 잔여 M?
2. 5/1 **단일** trust_start(사용자 확정) + duration `duration_stale_before` 경고 방식 — 이전 dual-date 대비 혼란 해소됐나? duration 5월 9% raw가 경고만으로 충분한가, 아니면 duration 기본은 6/1이어야 하나?
3. `tracking_coverage_by_partner`(M-1)가 생존편향 방어로 충분한가? CT median 자체는 그대로 두고 coverage만 노출 = 맞나, 아니면 CT 산출에 가중/보정 필요?
4. from/to 우선순위(from/to > period > 기본) + period_ignored 플래그 직관적인가?
5. 잔여 누락 / 엣지 / TC.
