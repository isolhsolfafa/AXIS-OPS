# #83 — CT 협력사×모델×task×구분(dual) 분해 집계 (partner-breakdown) 설계서 (v1)

**Sprint ID**: FEAT-CT-PARTNER-BREAKDOWN (VIEW OPS_API_REQUESTS #83)
**범위**: BE only — 신규 `GET /api/ct/partner-breakdown` (read-only). `statistics_service.py` 신규 함수 + `ct_analysis.py` route. DB/migration 0 (기존 ct_time_minutes/active_time_minutes read-time).
**연계**: #82 ⓐ(S-1 basis)·ⓑ(S-2 ct union) 완료 위에 partner 차원 추가. #81 dual 로직 재사용.

---

## 1. 배경 — CT 분석의 본질 = 협력사 평가

CT 최종 목적 = "어느 협력사가 어느 모델/공정에서 빠르고 일관적인가". 현 `task-stats` = task별 pooled(partner 차원 전무) → VIEW `CtPartnerModelMatrix`·CT 표준 후보표·협력사 평가 페이지 전부 mock. partner 분해가 빈 축.

## 2. 검증 결과 (6개, 2026-06-08 운영 5월+, basis=ct)

| 검증 | 결과 | 설계 함의 |
|---|---|---|
| **M1 표본 파편화** | 4축 119셀 중 **57% n<5**(n중앙 3) / rollup partner×task 72% 쓸만(n중앙 25) | **rows(4축, 게이트) + rollups(평가용) 병행 필수** |
| 즉시완료율 by partner | **BAT 61%** vs FNI 11%·P&S 2% (one-click 제외) | 태깅 KPI 작동. rollup에서 평가 반영 |
| vs_std (PANEL_WORK) | TMS 0.68 / P&S 1.28 | task 표준 대비 비율 = 공정 비교 |
| **생존편향** | BAT 61% 미추적 → 39%만으로 CT 산출 | **속도 + tracking coverage 짝 노출 필수** |
| 모델 편중 | 협력사 DUAL 비중 45~56% 분산 | dual 정규화 필요 |
| **dual 왜곡** | 같은 협력사·task에서 DUAL +17~19%(현업: ~1.5배, 병렬제작) | **vs_std 기준 = (task, dual) 표준** |

## 3. API — 신규 endpoint (Codex M3: task-stats 불변)

```
GET /api/ct/partner-breakdown?from=&to=&category=&model=
```
- 윈도우/basis 상속: 트러스트 [2026-05~](S-1 `_resolve_window`/`_WINDOW_WHERE`), clean 모집단, basis=ct(+active 병기).
- 응답 = `{ rows, rollups, meta }` (별 타입, 기존 CtTaskStatsResponse 불변).

### 3-1. partner 정규화 (Codex M2) — `_COMPANY_SQL`(v2.20.11) 재사용
```
partner_raw     = category별 raw (mech→mech_partner / elec→elec_partner / TMS→module_outsourcing / PI·QI·SI→'GST')
partner_display = TMS → TMS(M)(mech/module)·TMS(E)(elec) 분기 (_COMPANY_SQL CASE)
partner_scope   = category (해석 컨텍스트)
NULL 구분: '미해당(자연 제외)' vs '품질 누락(applicable인데 미입력)' — meta 카운트 분리(무결성 ≠ CT 관측)
```

### 3-2. rows (4축 raw, Codex M1 게이트)
행 = `(partner_raw, partner_display, partner_scope, model, task_id, dual)`:
```
ct: median/q1/q3/iqr/var_ratio(iqr÷median)  +  active(M/H) median 병기
n_raw / n_after_tukey / tukey_clipped_count / tukey_applied(n>=30만 true)
standard_status: n<5='reject' / 5≤n<30='provisional'(Tukey 미적용) / n>=30='standard'
instant_n / instant_completion_applicable(bool) / instant_excluded_reason  ← 보조값만(A4)
side_applicable: TMS/TANK_MODULE 한정 true, 그 외 false (A5 — L/R 무의미 분리 방지)
```

### 3-3. rollups (평가용 — 표본 충분)
> ⚠️ **M-1 (Codex)**: rollup median 은 **raw rows median 의 합산이 아니라 독립 GROUP BY `percentile_cont`** (median = non-additive). 산출 = **3벌 독립 쿼리**(또는 단일 GROUPING SETS): `rows`(4축) / `partner_task_rollups`(partner_display×task) / `partner_model_rollups`(partner_display×model). FE 재집계·raw 합산 **금지**(TC-PB-04 강제). 기존 `statistics_service.py` 카테고리 pooled median 패턴 정합.

`partner_task_rollups`, `partner_model_rollups` 2종 (둘 다 **GROUP BY `partner_display`** — M-3: category 정규화된 키라 TMS(M)/TMS(E) 자동 분리):
```
ct median/iqr/var_ratio + active median + n
vs_task_standard_ratio: 해당 (task, dual) pooled 표준 대비 비율  ← dual별 표준(검증D +18%)
  · <1 = 빠름 / >1 = 느림. 모델/dual 난이도 보정(raw median 직접비교 교란 방지, M6)
  · ⚠️ M-2: 표준 자체 n<5 → vs_task_standard_ratio=null + vs_task_standard_status='insufficient_standard' + standard_n 동봉
    (n>=5 → 'ok'). partner×model rollup 은 task 무관이라 vs_std 미산출(null, 'not_applicable')
instant_completion_rate: 즉시완료율(태깅 이해도) — 평가 반영은 여기(A4)
  · substantive task만: one-click 화이트리스트 제외
tracking_coverage(tracked_rate): n_used(active>0 또는 ct>0) / n_total(clean eligible)  ← 생존편향 방어(검증: BAT)
  · ⚠️ 속도(vs_std)는 tracking_coverage 와 반드시 짝 노출(BAT 61% 미추적 → 39%로 판정 금지)
category_mix: 이 rollup 행에 포함된 category 목록  ← M-3: partner_display='GST'(PI+QI+SI) 등 다중 category 가시화. 협력사(FNI/BAT/C&A/P&S/TMS(M)/TMS(E))는 단일 category 자연 보장
standard_status: 동일 게이트
```
> ⚠️ **M-3 (Codex)**: rollup GROUP BY = **`partner_display`**(=(partner_raw, category) 파생). 협력사 partner_display 는 category-coherent(FNI=MECH only / TMS(E)=ELEC only) → 혼재 불가. 단 `GST`(PI/QI/SI 내부검사)만 다중 category → `category_mix` 노출 + 협력사 평가는 협력사 partner_display 우선(GST=내부, 평가 대상 아님). BE 는 score 합성 안 함(A-3, 가중은 VIEW).

### 3-4. one-click 화이트리스트 (즉시완료율 정상 task — A4)
`TANK_DOCKING`(트리거 마커) / `SI_SHIPMENT`(출하 단일액션) / `SELF_INSPECTION` / `INSPECTION` (자주검사 짧음). → 이들은 `instant_completion_applicable=false`(즉시완료가 정상). BE가 task 메타로 관리(`_INSTANT_WHITELIST`).

### 3-5. meta (Codex M6 진단 + 재현성)
```
window{from,to} / trust_start / basis='ct' / as_of
excluded_partner_missing(자연 제외) / excluded_quality_missing(품질 누락, applicable인데 미입력)
excluded_null_ct / excluded_zero_ct
exclusion_ver / dag_ver(현 'none', S-3 후 갱신) / calendar_ver  ← 재현성(#82 연장)
garbage_excluded: false  ← S-3 ⓒ 미적용 명시(현 partner CT는 TMS-dirty 제외 + MECH 소수라 대체로 clean)
```

## 4. 산출 규칙 (S-1/S-2 상속)
- 모집단: clean(`duration_source IS NULL OR 'NORMAL_COMPLETION'`) + TMS dirty(TANK_MODULE/PRESSURE_TEST) 제외 + TEST 제외 + 트러스트 윈도우.
- basis=ct(`ct_time_minutes > 0`) box plot + active median 병기.
- Tukey 1-pass = **n≥30 셀만**(M1 — n<30은 fence 무의미, tukey_applied=false).
- dual = model ILIKE '%DUAL%'(#81). vs_std 표준 = (task, dual) pooled median(검증D).
- read-only. mutation 0(VIEW 원칙 M-e). TTL 캐시 1h.

## 5. 회귀 / 위험
- **신규 endpoint + 신규 함수만** — `get_task_ct_stats`/`get_data_quality`/task-stats 응답 불변. DB/migration 0.
- 회귀 표면 = 0 (additive). partner 매핑은 `_COMPANY_SQL` 검증된 패턴.

## 6. pytest 계획 (`test_partner_breakdown.py`)
- TC-PB-01: rows 4축 키 + standard_status 게이트(n<5 reject / 5~29 prov tukey_applied=false / 30+ std)
- TC-PB-02: partner 정규화 — TMS → mech:TMS(M)/elec:TMS(E), partner_raw/display/scope
- TC-PB-03: partner NULL — 자연제외 vs 품질누락 meta 분리
- **TC-PB-04: rollup 독립 median (M-1)** — partner_task/partner_model rollup median = 독립 GROUP BY percentile_cont. **raw rows median 합산 ≠ rollup median** 검증(다른 값 나오는 seed로 합산 금지 입증)
- **TC-PB-05: vs_task_standard_ratio (M-2)** — (task,dual) 표준 기준(SINGLE은 SINGLE표준/DUAL은 DUAL표준) + **표준 n<5 → ratio=null + status='insufficient_standard' + standard_n**
- TC-PB-06: instant_completion — one-click 화이트리스트 제외(TANK_DOCKING 등 applicable=false)
- TC-PB-07: tracking_coverage(tracked_rate) rollup 동봉 + 속도 짝
- TC-PB-08: side_applicable — TMS만 true
- TC-PB-09: dual 분리 — SINGLE/DUAL 셀 분리(섞임 없음)
- **TC-PB-09b: partner_display rollup 키 (M-3)** — TMS raw → mech:TMS(M)/elec:TMS(E) 분리 rollup + GST 다중 category → category_mix 노출
- TC-PB-10: 회귀 — task-stats/data-quality 응답 불변
- **TC-PB-10b: BE composite 미합성 (A-3)** — 응답에 즉시완료율·coverage 단독 노출만, 통합 score 키 부재(가중=VIEW)
- TC-PB-11: meta 진단(excluded_partner_missing/excluded_quality_missing/excluded_null_ct) + 재현성(exclusion_ver/garbage_excluded=false)
- TC-PB-12: 입력검증 — from/to YYYY-MM/from>to → 400(S-1 _resolve_window 재사용)

## 7. Codex 검증 질문 (BE 구현 관점)
1. rows+rollups 이중 산출 = 쿼리 2벌(또는 raw에서 FE 재집계 금지하고 BE rollup) — 성능/정합? rollup이 raw와 독립 GROUP BY여야 표본 충분(raw 합산 ≠ rollup median)?
2. vs_task_standard_ratio = (task,dual) pooled median 기준 — 표준 자체도 n<5면? (표준 미산출 시 ratio NULL + 사유)
3. tracking_coverage denominator = clean eligible(basis 필터 전) — S-2 coverage와 동일 정합?
4. partner_display 분기(_COMPANY_SQL)가 category 의존인데 rollup(partner×task)에서 partner 일관?
5. one-click 화이트리스트 하드코딩 vs task 메타 — 유지보수?
6. 누락 TC / 엣지(garbage 미제외 영향 / DUAL L/R side_applicable).
