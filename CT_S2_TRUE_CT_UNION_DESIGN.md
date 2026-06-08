# S-2 (ⓑ) — 진짜 CT(across-worker UNION) + 동시작업자 설계서 (v1)

**Sprint ID**: FEAT-CT-TRUE-UNION (VIEW OPS_API_REQUESTS #82 ⓑ)
**범위**: BE — `migrations/061` (신규 `ct_time_minutes` 컬럼 + 백필) + `task_detail.py`(compute_task_work 확장 또는 신규) + 완료 4경로 동봉 + `statistics_service.py`(ct_*_hours/basis=ct) + `ct_analysis.py`
**연계**: S-1(v2.29.0 basis=active) 확장. Sprint 86(active_time_minutes) 패턴 정합.

---

## 1. 배경 — ① 검증 (2026-06-08, 5월+ 운영)

> **현 active_time_minutes·duration_minutes 둘 다 M/H(across-worker SUM)이지 CT 아님.** 진짜 CT = 작업자 세션 across-worker **UNION**(겹침 합산 안 함, wall-clock).

| 발견 | 수치 | 함의 |
|---|---|---|
| **union SQL 검증** | M/H 합 = 저장 active값 일치(OK) | 계산 정확, 단일/릴레이는 CT=M/H |
| 병렬 task만 갈라짐 | ELEC 다중 49% 병렬 / MECH 13% / 전체 ~9% | 다중작업자 ≠ 병렬. 세션 겹침만 CT<M/H |
| 병렬 예 | PANEL_WORK 4명 동시 → CT=M/H÷2 (1885분→944분) | 큰 task에서 2배 차 |
| 릴레이 예 | UTIL_LINE 6명 교대 → CT≈M/H (409분→410분) | 작업자 수 많아도 안 갈라짐 |

→ ⓑ 가치 = **소수(~9%)지만 큰 병렬 task에서 결정적**. ②③(CT 표준/lead time) mock→실데이터 전환의 전제.

---

## 2. 핵심 산식 (Codex M-Q1 — clip 먼저, union 나중)

```
worker_active_mr  = (session_union ∩ BH) − (manual_pause ∪ 식사휴게)   ← 작업자별 정제 multirange (S-1/Sprint86 동일)
M/H (active)      = Σ_worker FLOOR(length(worker_active_mr))           ← 현 active_time_minutes (= 공수)
CT (union)        = FLOOR(length( UNION_worker worker_active_mr ))     ← 신규 ct_time_minutes (= 경과/벽시계)
```
- ⚠️ **순서**: union을 raw 세션에 먼저 적용 ❌ → **작업자별 pause/BH/break clip 먼저 → 정제 multirange를 across-worker UNION** ✅ (작업자별 BH 경계 다름).
- **CT 캘린더 계약**: per-worker 정제구간의 합집합 길이 = "task가 (영업시간·휴게 제외) 실제 작업으로 점유한 벽시계". 단일작업자/릴레이 → CT=M/H. 병렬 → CT<M/H.
- `CT = M/H ÷ concurrency` **역산 금지**(순환) — union으로 직접 산출.
- 불변식: **CT ≤ M/H** (union ≤ sum). 저장값 = **`LEAST(FLOOR(union_exact), active_time_minutes)`** 명문화 (A-1 — 초단위 timestamp에서 `floor(union) > Σfloor(worker)` 이론상 가능 → LEAST 가드로 불변식 보장).

### 동시작업자 (ⓑ-2)
- `worker_count` 컬럼 = `COUNT(DISTINCT work_start_log.worker_id)` 신뢰 확인됨(B1-2 일치). 별도 산출 불필요 — 기존 컬럼 사용. 응답 `avg_workers` = task별 AVG(worker_count).
- **effective_concurrency (M-1 정정)**: ratio-of-medians ❌(분포 섞이면 왜곡) → **instance별 `active_time_minutes / NULLIF(ct_time_minutes, 0)` 계산 후 median** = `effective_concurrency_median`. `ct_time_minutes > 0` 필터 + NULLIF 0-division 가드 필수. 1.0=순차/릴레이, 2.0=완전병렬. (ratio-of-medians 유지 시 `median_mh_to_ct_ratio` 보조 지표로 강등.)

---

## 3. 구현

### 3-1. migration 061 (058=v2.22.0/059=Sprint86/060=식사정정 회피 → **061**)
```sql
ALTER TABLE app_task_details ADD COLUMN IF NOT EXISTS ct_time_minutes INTEGER;  -- nullable
-- 백필: 위 산식 union 길이, LEAST(ct, active_time_minutes) 가드, WHERE ct_time_minutes IS NULL (멱등)
```
- 백필 SQL = ① 검증된 dry-run CTE의 set-based 버전(per-worker cleaned multirange → across-worker range_agg union 길이).
- TANK_DOCKING(one-action) 등 active NULL → ct NULL.
- **A-2 preflight**: 백필 전 `ct_raw > active_time_minutes` 건수/샘플 출력(late checkout 유입 시 현재 재계산 CT > 과거 active 스냅샷 → LEAST 보수적 clipping 관측). 의도된 동작이나 가시화 필수.

### 3-2. compute_task_work 확장
- 기존 `compute_task_work(cur, tid, close_at) -> {manhour, active}` 에 **`ct` 추가** → `{manhour, active, ct}`.
- ct = 동일 CTE의 cleaned multirange를 worker별 SUM 대신 **across-worker range_agg union 길이**. `LEAST(ct, active)`.
- 완료 4경로(complete_task_unified·auto_close_relay_task·force_close_task·force_complete_task) UPDATE SET 에 `ct_time_minutes = %(ct)s` 동봉 (active 옆, additive).
- **A-3**: 레거시 `complete_task()`(task_detail.py L682, 호출처 0) — 제거 또는 "사용 금지" 주석/테스트 가드. ct 동봉 4경로에 미포함 확인.

### 3-3. statistics_service — basis=ct
- `basis` = duration | active | **ct** (3값). ct → `ct_time_minutes/60`, 모집단 `ct_time_minutes > 0`.
- ct_*_hours 보조필드(또는 basis=ct 전환) + 응답에 `avg_workers`(task별 AVG worker_count) + `effective_concurrency_median`(M-1: instance별 active/NULLIF(ct,0) median).
- **M-2 — basis=ct meta/coverage 명세 (S-1 상속 일반화)**:
  - `tracking_coverage_by_partner` 조건 `basis == "active"` → **`basis in ("active","ct")`** 일반화.
  - **denominator 정합 (Codex R2 M)**: `n_total` = **clean eligible completed 전체(basis 필터 전, window/TMS/TEST/model/category/dual 적용 후)** — basis 무관 동일. `n_used` = basis별 `active_time_minutes > 0`(active) / `ct_time_minutes > 0`(ct). `tracked_rate = n_used / n_total`. ⚠️ `n_used`를 분모로 쓰면 `active>0 ∧ ct=0` 행이 사라져 생존편향 방어 깨짐 → 금지.
  - meta `ct_available`(clean 모집단 중 ct NOT NULL 비율) + `basis_label`("true CT(union)" / "순수작업(M/H)" / "전체시간") + `standard_basis` 처리.
  - **provisional / Tukey(base_n,clipped_n) / window(5/1 trust) / from-to / 캐시키(basis 포함) 전부 S-1 방식 그대로 상속.**

---

## 4. 회귀 / 위험
- **additive 컬럼만** — active_time_minutes·duration_minutes·man-hour·close·audit 전부 불변. 완료경로 = SET 1줄 + 함수 반환 1키 추가.
- migration = ADD COLUMN(nullable) + 백필 UPDATE(읽기 산출, 무중단). Sprint 86/v2.28.x 패턴 정합.
- 백필 preflight: set-based = per-task dry-run 일치 검증(Sprint 86 방식).

## 5. pytest 계획 (M-3 — union 엣지 seed 구체화)
- TC-S2-01: 단일작업자 → ct = active (CT=M/H)
- TC-S2-02: 릴레이(겹침 없음) `A 13-14, B 15-16` → ct ≈ active (=120)
- TC-S2-03: 완전겹침 2명 `A 13-15, B 13-15` → ct = active/2 (active 240 → ct 120)
- **TC-S2-04: 부분겹침** `A 13:00-15:00, B 14:00-16:00` → **active 240, ct 180** (겹친 1h 1회 계산)
- **TC-S2-04b: 0분 접점** `A 13-14, B 14-15` → ct = active = 120 (경계 안 겹침)
- TC-S2-05: ct ≤ active 불변식 (전 케이스) + 저장 = LEAST(FLOOR(union), active)
- **TC-S2-05b: 멀티데이 span** (이틀 걸친 병렬)
- **TC-S2-05c: 세션상한 캡** (checkout cap / next_start cap / 17시 fallback) 후 union
- **TC-S2-05d: pause·식사 겹침 후 union** (정제 multirange union)
- TC-S2-06: basis=ct → ct_time_minutes>0 모집단 + meta ct_available/basis_label + coverage(active,ct) 일반화
- TC-S2-07: avg_workers / effective_concurrency_median (instance ratio median) + 0-division 가드
- TC-S2-08: 백필 set-based = compute_task_work per-task 일치 + A-2 preflight(ct_raw>active 카운트)
- TC-S2-09: TANK_DOCKING ct NULL
- TC-S2-10: 회귀 — active/duration/man-hour 불변
- **TC-S2-11: 운영 staging smoke** — PANEL_WORK(병렬 CT≈M/H/2) / UTIL_LINE(릴레이 CT≈M/H) SQL 재현

## 6. Codex 검증 질문
1. clip-먼저-union-나중 산식 + CT≤M/H 불변식이 모든 겹침 케이스(완전/부분/없음/멀티데이)에서 정확한가?
2. ct 백필 = active(Sprint86) 동일 CTE 재사용 + 최종 union만 차이 — 누락 경로/회귀?
3. effective_concurrency = M/H median ÷ CT median (task별) — pooled median 비율이 통계적으로 타당한가, 아니면 per-instance ratio median?
4. worker_count 컬럼 신뢰(B1-2 일치) vs work_start_log 재산출 — 어느 쪽?
5. basis=ct 추가 시 S-1 coverage/provisional/캐시키 상속 정합?
6. 누락 TC / 엣지.
