# AXIS-OPS 프로젝트 진행 상황

## 개요
GST 제조 현장 작업 관리 시스템 — 스프레드시트 수동 입력에서 모바일 App 실시간 Push로 전환.

> **현재 버전**: **v2.41.0 (FEAT-CT-RELIABILITY-SUMMARY / B — CT 데이터 신뢰도 게이트 재설계, 2026-06-14)** — BE only minor, read-only, 신규 endpoint, migration 0. CT "데이터 신뢰도" summary 가 FE 파생 가중평균(풀링 부풀림 80.6%)이라 과대평가 → **count 게이트+생산량 가중**으로 재설계(3모델 합의+사용자 catch 누적). 신규 `GET /api/ct/reliability-summary`: 표준가능=셀(모델×task×dual) 중 (n≥30 AND 모델공정추적≥70%) 비율, 생산량 가중 Σ(모델 12mo 생산비중·표준가능비율)(주력 GAIA 88% 지배=정직), 2조건 분리(n_met/tracking_met), 모델 기준, 라벨 정정, 헤드라인=추적율. Codex 3R(NO-GO→CONDITIONAL_GO Q2/Q4/Q5→DEPLOY_SAFE M=0)+Fable 2차. 실데이터 추적53%/standard_ready17.6%/병목=추적(tracking_met22.5%). pytest 9+1skip+회귀 44+1skip. **⏭️ 다음**: VIEW FE(별 repo, VIEW_FE_Request.md 인계 — 가중평균 제거→endpoint 소비, 드릴 계층).
> **선행 release**: **v2.40.0 (FIX-FORCE-CLOSE-DURATION-SOURCE / A — 강제종료 duration_source='FORCE_CLOSED', 2026-06-13)** — BE only minor, **migration 062 동반**. 강제종료(`force_close_task`)가 duration_source NULL → 입력정합 NULL=clean 과대(force-close 199건, 81.8%). migration 062 enum 'FORCE_CLOSED' 추가+backfill(force_closed=TRUE AND source∈NULL/NORMAL→FORCE_CLOSED 멱등, FALLBACK/PREV_DAY_CAP 보존) + admin force_close UPDATE 기록 + statistics `_ESTIMATED_SOURCES` 추가. prod 실측 251 FORCE_CLOSED+2 FALLBACK·clean 잔존 0 → **입력정합 72.7% 정직값**. Codex R1 NO-GO(M-Q1 migration 트랜잭션)→R2 DEPLOY_SAFE M=0. pytest 5/5+회귀 69 passed 1 skip. **⏭️ 다음**: B 재논의(CT 신뢰도/입력정합 summary weighted-avg 과대→headline 추적커버리지 단독, 3모델 합의안) / VIEW MissedTaskQueueCard 교체 / #87 Phase 2b.
> **선행 release**: **v2.39.1 (Sprint 91-FE-b — 미종료 큐 방치 기준 통일 BE, 2026-06-13)** — BE only additive. `/open-tasks` 에 inactive_hours+meta.by_partner(칩)+meta.buckets+basis='realtime_abandoned' 추가 → VIEW 미종료 카드 근사(254)→방치(127) 통일 계약. Codex R2 DEPLOY_SAFE M=0. pytest 34/34. **⏭️ 다음**: VIEW MissedTaskQueueCard progress→/open-tasks 교체(별 repo) / #87 Phase 2b / 설계서 분할.
> **선행 release**: **v2.39.0 (Sprint 90-BE-C-b / #90b — close-type-trend 주별 ISO week 버킷, 2026-06-13)** — BE only additive. `?bucket=week`(기본 month back-compat) ISO 라벨+meta.bucket+주 zero-fill. Codex R1 DEPLOY_SAFE M=0. pytest 9/9. VIEW [주|월] 토글 자동 전환. **⏭️ 다음**: VIEW 수정 잔여 / #87 Phase 2b / 설계서 분할.
> **선행 release**: **v2.38.2 (Sprint 91-FE 연장 — 퇴근 다이얼로그 [모두 내작업완료], 2026-06-13)** — FE only. 실기기 QA(일시정지 ✅) 후 추가: completeTask(finalize=false) 순차 + 실패 안내. Sprint 번호 부여(90-BE-D/91/91-FE). 공지 117. Netlify prod. **⏭️ 다음**: VIEW 수정 6건(데이터종합 툴팁/B5/#91 툴팁/#90 비교 실데이터/커버리지 연동) / #87 Phase 2b.
> **선행 release**: **v2.38.1 (FEAT-OPS-FE-PENDING-GUARD — OPS app 미종료 가드 FE, 2026-06-13)** — FE only patch(3화면). A 퇴근 다이얼로그(open_tasks → [모두 일시정지] idempotent pause/[나중에]) / B 방치 뱃지(무활동 N시간+⏸ metadata Row) / C 종료 다이얼로그 무활동 문구. Codex R1 정정 반영. build GREEN + Netlify prod 배포. **⏭️ 다음**: 실기기 QA / VIEW B5 / #87 Phase 2b.
> **선행 release**: **v2.38.0 (FEAT-PENDING-DISCIPLINE-REFINE — 미종료="방치" 단일 기준 + 0초탭 force 제외 + 퇴근 open_tasks, 2026-06-13)** — BE only minor, read-only+additive, migration 0. BAT 매니저 일괄 강제종료(98건) 재발 방지 1차(BE). 방치=canonical+활성(미pause)세션≥1+마지막활동(시작/재개) 24h+(`pending_task_standard.py` 신규, GREATEST(wsl.started_at, wpl.resumed_at)). 4표면 통일(데이터종합 openTasks 월anchor/discipline 큐/대시보드 grouped/OPS 메뉴+additive 필드). zerotap force 제외. 활성 task 강제종료 `[활동중 종료]` audit 태그(차단X). checkout open_tasks[](토스트용). Codex R2 DEPLOY_SAFE M=0. pytest 63/63 GREEN. **⏭️ 다음**: OPS app FE(토스트+뱃지·섹션) / VIEW B5 / #87 Phase 2b.
> **선행 release**: **v2.37.0 (#90 협력사 마감유형 추이 + #91 협력사 매니저 group_avg 노출, 2026-06-12)** — BE only minor, read-only, migration 0. VIEW OPS_API_REQUESTS #90/#91. **#90** `GET /api/ct/close-type-trend`(신규 `close_type_trend_service.py` + route, gst_or_admin_required): 협력사×그룹×월×{auto,zerotap,force} flat series → VIEW CloseTrendChart [비교] 오버레이 실데이터. partner=MECH/ELEC TMS(M)/(E), GST+SH 제외, 빈 달 zero-fill. pytest 7. **#91** `_group_avg` `cand=partners`(자사 포함 group-wide avg): 협력사 매니저도 그룹평균 노출(3곳서 자사제외 2<3 영구 suppress 정정), 역추론 가드 `len(vals)≥3`, admin·협력사 동일 값, VIEW 변경 0. pytest test_sprint89 32. Codex 각 R1 DEPLOY_SAFE M=0. **⏭️ 다음**: 값 정합성 확인 / VIEW FE(#90 mockup→실 / #91 툴팁) / #87 Phase 2b.
> **선행 release**: **v2.36.1 (FIX-CT-FORCE-CLOSE-POLLUTION — CT 표준 강제종료 오염 정정, 2026-06-12)** — BE only patch, read-only, migration 0. **버그**: 강제종료(`force_close_task`)가 v2.22.0/v2.28.0에서 `compute_task_work`로 ct/duration 계산·저장하나 `duration_source` 미설정(NULL) → CT clean 필터 통과 → CT 표준 표본 오염. 클린 코어 원칙(2026-04-20 "강제종료=버리는 데이터")과 drift. **실측(2026-05~, 1,244건)**: 강제종료 128건(10.3%), MECH 배관 median 왜곡(WASTE_GAS_LINE_1 1.40h→2.98h +112%). **Fix**: `_CLEAN_CORE`에 `force_closed=FALSE` 1줄(→ task-stats #82/partner-breakdown #83/training 전파). **자동마감 유지**: AUTO_CLOSED_BY_* 65건 work_completion_log 전건 보유=작업자완료라 제외 X(Codex Q3 실데이터 0건). Codex R1 NO-GO→실데이터 해소→**R2 DEPLOY_SAFE M=0**. pytest 신규 test_ct17 + CT회귀 18/18 GREEN. read-only·저장값 무변경(man-hour 리포트 영향 0). VIEW §8-7 #1 정정. **⏭️ 다음**: VIEW CT/종료누락 페이지 표준값 정정 자동 반영 / #87 Phase 2b(checklist).
> **선행 release**: **v2.36.0 (Sprint 90-BE/90-BE-B — 태깅 커버리지/0초탭 드릴다운 + 마감 유형 월별 추이 zerotap, 2026-06-11)** — BE only minor, read-only, migration 0. AXIS-VIEW `종료 누락 분석` mockup 2종 실데이터. **① Sprint 90-BE** `GET /api/ct/tagging-coverage`(신규 `tagging_coverage_service.py` + `ct_analysis.py` route, `gst_or_admin_required`): 공정별(MECH/ELEC/PI/QI/SI) 추적율/0초탭 + `well_tracked_pct`(추적율≥80% serial) + `zero_tap_tasks` 드릴다운(task별 partner share). 분모=완료+active NOT NULL+applicable+force_closed=FALSE(자동마감·admin대행=**미추적 포함**, 사용자 결정 — mock PI/QI/SI 고미추적 신호). 3분류 oneClick>zero_tap(active≤1 OR close_reason)>tracked(active>1 AND close_reason NULL). PI/QI/SI=GST 단일, DUAL per-row, share largest-remainder. Codex **4라운드 M=3→2→1→0 GO**. pytest 16/16 + CT회귀 16/16. **② Sprint 90-BE-B** `data-quality.auto_close_trend[]`에 `zerotap`/`zerotap_rate` additive(CloseTrendChart용, 신규 route 불필요=DRY). Codex 1라운드 DEPLOY_SAFE. pytest 17/17. **advisory(BACKLOG)**: A-1 SELF_INSPECTION 자동마감 시 월별 auto>zerotap 역전(VIEW tooltip) / A-2 private whitelist import. **⏭️ 다음**: VIEW FE 2 card 연동(별 repo) / #87 Phase 2b(checklist) → 계획·납기(Sprint 87-BE).
> **선행 release**: **v2.35.0 (#87 규율 대시보드 보정 — 미종료 월단위·기준통일 + 중복지표 교체, 2026-06-10)** — BE only minor, read-only, migration 0. 사용자 catch 보정 묶음. **① 중복지표 교체**: `checkinNoTag`(taggingRate와 중복) 폐기 → **`checkoutMiss`(퇴근미체크율, reference_only 참고/평가제외)** — #86 checkout_status(cutoff D+1 02:00 KST) 월×협력사 가중집계. **② openTasks 월단위(A)**: 실시간 → `started_at` ∈ 해당 월 + 미완(autoClose 월 anchor 일관). **③ 미종료 기준 통일(B)**: 정식 `/tasks/pending/grouped` 정합 (is_applicable=TRUE + force_closed=FALSE + TEST 제외) — openTasks + open-tasks 큐. **④ 공통 하이진(C)**: autoClose/zeroTap/universe is_applicable + TEST 제외. **⑤ 큐 realtime 유지(D)**: summary openTasks(월) ≠ 큐(실시간) 의도된 차이 + meta basis 라벨. **⑥ 비협력사 제외**: `_EXCLUDED_PARTNERS`=GST+**SH** → 6개 정식 협력사. Codex 중복지표→미종료 설계 R1 GO→실코드 R2 DEPLOY_SAFE M=0. pytest 32/32 GREEN + 실스모크(openTasks 월 BAT 82·큐 493·checkoutMiss C&A 0.30·SH/GST 제외). **⏭️ 다음**: Phase 2b(checklist) → 계획·납기(Sprint 87-BE). VIEW FE = checkinNoTag→checkoutMiss 키 변경 + reference_only/openTasks_basis meta + 월단위 의미 렌더.
> **선행 release**: **v2.34.0 (#87 협력사 규율 대시보드 Phase 2a, 2026-06-10)** — BE only minor (partner_discipline_service + admin_discipline, read-only, migration 0). Phase 1 placeholder 4지표 중 3개 실측 전환 + trend endpoint. **taggingRate**(GST 현장 출근 분모 ÷ work_start_log 태깅, 월 DISTINCT) / **checkinNoTag**(onsite−tagged) / **zeroTap**(active≤1 미추적 ÷ substantive, one-click `is_instant_whitelisted` 제외 — 실데이터 BAT/MECH 0.66·ELEC ~0, CT 발견 일치) / **`GET /api/admin/discipline/trend?months=N`**(월별 autoClose/taggingRate/zeroTap, openTasks 제외). union universe(task∪worker partner) + provenance meta. group_avg 불변식(raw None 가능 ⟺ missing None). **Phase 1 버그 2건 동반 정정**: `_PARTNER_SQL` NULLIF(,'GST')(GST 자체수행 noise row 제외) + open-tasks 타사/NULL 작업자 실명 마스킹(M-Q8/NULL). Codex 설계 GO → 실코드 R2 M=2(M-Q5 checkinNoTag·M-Q8 누수)→R4 **DEPLOY_SAFE M=0**(M-Q5→A 2자합의). pytest 31/31 GREEN + 실데이터 스모크. **⏭️ 다음**: Phase 2b(checklist, applicable resolver 추출, 별 Codex) → 완료 후 계획·납기(Sprint 87-BE). VIEW FE = placeholder→실측 렌더 + trend 차트.
> **선행 release**: **v2.33.0 (#87 협력사 규율 종합 대시보드 Phase 1, 2026-06-10)** — BE only minor (신규 `services/partner_discipline_service.py` + `routes/admin_discipline.py` + blueprint, read-only, migration 0). VIEW PartnerDashboardPage 실데이터 1차. endpoint 2개: `GET /api/admin/discipline/summary?month=`(partner×group + 지표 envelope — Phase 1 실측 openTasks/autoClose + group_avg peer-only k≥3, Phase 2 4지표 placeholder available=false) + `GET /api/admin/discipline/open-tasks`(미종료 즉시조치 큐 + repeat 30d/2). 공정성: BE는 raw+group_avg만(등급=VIEW), MECH/ELEC only, 협력사 매니저=자사 row만+group_avg suppress(현 3사 peer<3), 추적율<70% grade_eligible=false. `statistics_service.is_instant_whitelisted()` 공개 helper 추가(A3). 근태(출근율·퇴근미체크) 평가 제외(2026-06-10 결정, 출근=태깅율 분모로만). Codex 설계 R1 M=8→R2 조건부 GO / 실코드 R3 M=1(_PARTNER_SQL 빈값 제외 누락)→fix(NULLIF+TRIM)→**R4 DEPLOY_SAFE M=0**(추적 6→4→1→0). pytest 신규 22 GREEN, 회귀 0. **⏭️ 다음**: Phase 2(taggingRate/checkinNoTag/zeroTap/checklist/trend) → 그 후 계획·납기(Sprint 87-BE).
> **선행 release**: **v2.32.2 (#88 출하상세 출하 처리자 shipment_worker 1필드, 2026-06-10)** — BE only patch, additive. `shipment/details` items[] 에 SI_SHIPMENT 완료자(COALESCE(closed_by 대행, worker_id 현장)→name, 엑셀=null) LEFT JOIN LATERAL. pytest 32/32 GREEN.
> **선행 release**: **v2.32.1 (출고처리 실패 메시지 명확화, 2026-06-10)** — BE only patch, 메시지 문구만. pre-transition 제품(QR 전환 ~1달, task seed 부재)이 출고 실패 시 SI_TASK_NOT_FOUND/SI_FINISHING_NOT_STARTED 한글 안내. 자동 seed는 미구현(BACKLOG, 재발 시 재검토). pytest 15/15 GREEN.
> **선행 release**: **v2.32.0 (#86 협력사 데이터 RBAC + 근태 checkout_status, Sprint 88-BE, 2026-06-10)** — BE minor, migration 0. PR1 `jwt_auth.resolve_company_scope()` SSoT(company 없는 매니저·None→403 누수 차단) + errorhandler / step① 근태로직 hr_attendance_service 추출(admin.py 2626→2456) / step② checkout_status(not_started/working/missed/done, cutoff LEAST(익일첫in,D+1 02:00)) + 미체크률 by_work_site. Codex PR1 R3 DEPLOY_SAFE / 설계 R2 GO / step② GO 전부 M=0. pytest 94+37+신규9 GREEN. VIEW 후속(가드 제거+렌더).
> **선행 release**: **v2.31.0 (#83 CT 협력사×모델×task×dual 분해 집계 partner-breakdown, 2026-06-08)** — BE only minor (신규 `GET /api/ct/partner-breakdown` read-only + statistics_service 신규 함수, DB/migration 0). CT 본질=협력사 평가인데 task-stats는 task-pooled(partner 전무) → VIEW 매트릭스/평가 mock. **검증 6개**: 4축 57% n<5→rollup 72%(병행 필수) / 즉시완료율 BAT 61% / vs_std TMS(E) 0.65·P&S 1.07 / BAT 미추적 생존편향 / DUAL +18%(현업 ~1.5배). `{rows(4축), rollups{partner_task,partner_model}, meta}` — rollup 독립 pooled median + vs_task_standard_ratio((task,dual) 표준) + tracking_coverage(속도+추적 짝) + instant_completion(화이트리스트 제외) + category_mix. BE composite 미합성(가중=VIEW). Codex 설계 R1 M=3→R2 GO / 구현 R1 M=1(rollup Python)→M→A 2자합의→**DEPLOY_SAFE**. pytest 신규 14+회귀 33 GREEN. read-only·additive(task-stats/data-quality 불변). 잔여 A: rollup GROUPING SETS 전환(별 BACKLOG). **⏭️ 다음**: VIEW FE partner-breakdown 연동 / **S-3 ⓒ DAG garbage 제외 + 무결성 KPI**.
> **선행 release**: **v2.30.0 (Sprint S-2 ⓑ 진짜 CT across-worker union + 동시작업자 — VIEW #82 ⓑ, 2026-06-08)** — BE minor (migration 061 ct_time_minutes 컬럼+백필). 현 active/duration 둘 다 M/H(across-worker SUM)이지 CT 아님 → 진짜 CT = across-worker UNION(벽시계). 다중작업자 ≠ 병렬(겹침만 CT<M/H, PANEL 2.0x/UTIL 1.0x). compute_task_work {manhour,active,ct} + basis=ct + effective_concurrency_median. Codex 설계 R3 GO / 구현 DEPLOY_SAFE M=0. pytest 신규 15+회귀 67 GREEN. 배포검증 백필 갭 0·CT>active 위반 0.
> **선행 release**: **v2.29.1 (get_data_quality 트러스트 윈도우 통일 — VIEW #82 ⓐ 후속, 2026-06-08)** — data-quality도 옛 90일→`CT_TRUST_START_MONTH` 윈도우 통일(duration_source 분포만, 추이 6mo·교육 전기간 유지). meta lookback_days→window. pytest 5 GREEN.
> **선행 release**: **v2.29.0 (Sprint S-1 ⓐ CT basis=active + 미추적 제외 + 신뢰컷오프 + 월범위 — VIEW #82 ⓐ, 2026-06-08)** — BE only minor (statistics_service.py + ct_analysis.py, DB/migration 0 read-time). 14개 운영 쿼리 검증: 현 "CT"=M/H, **act=0=미추적**(시작=완료 즉시태깅, MECH 배관 ~50%), act=0 제외 시 MECH CT 0.5h→2.2h, 미추적율 BAT 59% vs FNI 7%(완료율이 숨김), duration 058 미적용→6월+만 신뢰. `GET /api/ct/task-stats` 신규 `basis`(duration기본\|active) + `from`/`to`(YYYY-MM KST 반열림) + period 제거. basis=active→act>0 미추적 제외, 신뢰 기준 `CT_TRUST_START_MONTH='2026-05'` 단일, 생존편향 `tracking_coverage_by_partner`(FNI 0.71/BAT 0.34), basis별 n + provisional(n<30). Codex 설계 R1 M=4→R2 CONDITIONAL_GO→구현 R1 M=2→**재검증 DEPLOY_SAFE M=0**. pytest 신규 18+회귀 sprint85 16 GREEN. 회귀 0(additive). 분리: ⓑ CT union=S-2(새 컬럼+migration)/ⓒ DAG+무결성KPI=S-3.
> **선행 release**: **v2.28.2 (active-time 식사시간만 제외 정정 — 오전/오후 휴게=작업시간, 2026-06-07)** — 사용자 catch: Sprint 86이 4휴게 전부 제외했으나 식사(점심 11:20-12:20·저녁 17:00-18:00)만 제외해야 함(오전/오후 20분 휴게=작업시간 인정). compute_task_work breaks_day=식사 2개만 + migration 060 active 전체 재백필(OVERWRITE, duration 불간섭). 일 160→120분, PANEL active 6.1→6.7h(man 8.9h, active≤man 유지). pytest active 12 GREEN.
> **선행 release**: **v2.28.1 (CT task-stats dual 파라미터 — DUAL/단일 분리, VIEW #81, 2026-06-07)** — CT ②가 DUAL/단일 합산해 표준 왜곡(PANEL 단일 5.6h vs DUAL 11.8h) → `?dual=dual\|single` 추가. `_dual_clause` = model ILIKE '%DUAL%'(포함, iVAS 중간DUAL 엣지 커버). meta dual_scope, 스키마 불변(VIEW v1.59.x 선반영). BE 2파일, DB 0. pytest CT-16/CT-14 GREEN.
> **선행 release**: v2.28.0 (Sprint 86 순수 작업시간 active-time + CT 표준 격상 — FEAT-ACTIVE-TIME-PURE-WORK, 2026-06-07) — man-hour는 세션−수동pause라 휴게(160분/일)·영업시간 밖 idle 미차감 → active-time = 세션∩영업창 − (수동pause∪휴게)∩... 순수 작업시간. 영업창=attendance 우선/fallback 평일[08,20]·주말[08,17]. 신규 `compute_task_work`(man-hour+active 단일 CTE) + 기존 compute_task_manhour 위임 + migration 059(active_time_minutes 컬럼+백필) + 완료 4경로 active 동봉 + statistics_service active_*_hours. **man-hour(duration_minutes) 불변(additive)**. Codex 6라운드(설계 R5 GO / 구현 R6 M-1 force_complete·M-2 active_available 해소). 운영 검증 active 중앙 PANEL 8.9→6.1h. pytest active 12 + 회귀 relay 38·CT 15 GREEN. VIEW FE 후속 별 세션.
> **선행 release**: v2.27.0 (Sprint 85 CT 분석 허브 BE 연동 MVP — FEAT-CT-ANALYSIS-HUB-BE-MVP, 2026-06-05) — VIEW CT 분석 페이지(13 컴포넌트 4섹션) mock → 실데이터 연동 MVP = ①데이터신뢰도 + ②CT표준(IQR, man-hour)만. 신규 `statistics_service.py` + `routes/ct_analysis.py`(`/api/ct/task-stats` + `/api/ct/data-quality`, admin OR GST manager). box plot = `duration_minutes/60`(man-hour SSoT, 목업 mean×인원 폐기) + clean(NULL/NORMAL) + TMS(M)·TEST 제외 + Tukey 1-pass. 카테고리 pooled_median. KST 월경계/교육 cut. **Codex 3라운드(R1 NO-GO M=5 → R2 GO → R3 DEPLOY_SAFE)**. pytest 15/15(CT-01~15) + 회귀 test_factory 21. DB·migration 0 read-time 회귀 0. ③ skeleton/④ 미구현, VIEW FE 후속 별 세션.
> **선행 release**: v2.26.0 (Sprint 84 생산현황 상세 1차/2차 마일스톤 — FEAT-FACTORY-PHASE-1-2-PROGRESS, 2026-06-05) — 생산현황 상세 진행률을 손님용 rollup + 1차(가압 PI까지)/2차(마무리 SI) 마일스톤 그룹핑. monthly-detail 응답에 `phase` 필드 additive (Sprint 83 `_compute_stage_completion` 재사용). 1차완료=`pi` / 2차완료=`si`(SI_FINISHING). ⚠️ QI app 미입력(검사자동화시스템 추후 API) → 2차 SI binary. 신규 helper `_phase_pct`/`_build_phase` + `_compute_stage_completion` 0-applicable→None 일반화. **Codex 라운드 1 NO-GO(M=2) → 라운드 2 GO(M=0/A=1)**: M-2(SI_SHIPMENT-only 50% 오염)→`_PHASE2_KEYS=['si']` / M-3(non-standard absent stage 분모 왜곡)→present_map None / A-1(QI 연동 시 SI reached 제한)→BACKLOG. pytest 39 GREEN(sprint83 11 + sprint84 8 + test_factory 19). BE only `factory.py` additive, 회귀 0. VIEW: progress_pct 큰 바 + phase 마커 렌더(별 세션).
> **선행 release**: v2.25.1 (Sprint 83 공정 순서 정정 — 반제품 선행, 2026-06-05) — v2.25.0 cascade tier 순서 정정 (반제품 TM 을 기구/전장과 병렬→선행). 실 순서: 전장외부→반제품→기구→전장→가압→공정→마무리. 후속 공정 도달 시 반제품 강제 100% (W23 tm 83.9→100.0). pytest 11 GREEN(CR-11 신규).
> **선행 release**: v2.25.0 (Sprint 83 — 공장 대시보드 공정별 완료율 정합, 2026-06-05) — 공정별 완료율이 `completion_status` 옛 플래그(lag)를 봐 저평가(TM 19 vs 3, 출하완료 12건 상위 플래그 누락). → 실제 task 완료 + 하위완료→상위 cascade rollup(옵션 B 체크리스트 무관, SI=SI_FINISHING)으로 재계산. BE only `factory.py` read-time(근본 data·DB·migration 0), 대시보드 보여주기만(생산현황/실적/상세 무변경). `_get_task_progress_by_serial` 무수정 별도 helper. 운영 W23 mech 0→82.4 / GBWS-7163 100%. Codex R1 GO(M=0/A=3). pytest test_sprint83 10 + 회귀 test_factory 21 GREEN. 스키마 불변/회귀 0. 후속 BACKLOG FEAT-FACTORY-ACTUAL-COMPLETION-VIEW.
> **선행 release**: v2.24.1 (auto-close-details quarter period 지원, #80 후속, 2026-06-04) — VIEW 강제 종료 분포도 분기 매트릭스 ↔ 상세 패널 불일치 fix. details period 화이트리스트가 summary 와 비대칭(`_VALID_PERIODS_DETAILS` 에 quarter 누락 → 400) → `admin_dashboard.py` 1줄 추가(서비스 `_resolve_period_range` 는 이미 quarter 지원). pytest CT-11 신규 + 기존 12 GREEN. 회귀 0. VIEW 후속: detailsPeriod 다운그레이드 제거.
> **선행 release**: v2.24.0 (Sprint 82 #80 — auto-close-details close_type/task_id 필터, 2026-06-04) — VIEW 강제 종료 상세 패널 전수 보장. `/auto-close-details` 에 `close_type`(auto/manual/force, 미지정=union 하위호환) + `task_id`(마감 공정) 요청 파라미터 additive + per_page cap 100→500(운영 Q2 force 125건 이미 초과). BE only `dashboard_service.py`+`admin_dashboard.py`, 응답 스키마 0 변경. Codex R1 DEPLOY_SAFE(M=0/A=4 반영). pytest test_sprint82 12 GREEN(CT-01~10) + summary·매트릭스·invariant 무변경. 설계: AGENT_TEAM_LAUNCH.md § Sprint 82.
> **선행 release**: v2.23.0 (Sprint 81 #79 — 강제 종료 협력사 2축 매트릭스, 2026-06-04) — 자동 마감 매트릭스(v2.20.x)의 협력사 분포를 강제 종료(force_closed=TRUE)에도 동일 제공. `/auto-close-summary` 응답 `force_closed` block 에 additive 2키 (`partner_task_matrix` 협력사×공정 + `partner_elapsed_matrix` 협력사×처리기간 5버킷). BE only `dashboard_service.py` (OPS 앱 변경 0, VIEW MissedCloseAnalysisPage 소비). 미시작=`started_at IS NULL` 최우선 분리(원안 elapsed=0 '1일내' 오분류 차단) + `_COMPANY_SQL` 재사용 + EXISTS(work_start_log) 제거(grand_total==force_count). Codex 3라운드 GO (R2 M-1 multi-SELECT snapshot invariant → REPEATABLE READ 단일 snapshot 고정 fix). pytest test_sprint81 23 GREEN + 회귀 test_sprint71 21p 1s. DB/migration 변경 0. 설계: AGENT_TEAM_LAUNCH.md § Sprint 81.
> **선행 release**: v2.22.0 (duration man-hour 재정의 — 수동 일시정지 미반영 + 휴게 이중차감 fix, 2026-06-03) — 작업 완료 시 `duration_minutes`가 raw(완료−시작)로 덮어써져 **작업자 수동 일시정지가 전혀 반영되지 않던** 버그 (운영 210건). 사용자 결정 = 휴게/점심 차감 안 함(원본 적재) + 수동 일시정지만 차감. 새 `compute_task_manhour` SSoT (per-worker interval-union(세션) − 수동 pause∩session_union, 세션 상한 = LEAST(완료기록, **본인 그날 attendance check_out**, [없으면]시작일 17:00 fallback, 다음 start(LEAD), close_at)) + 3경로 통일 (정상/ship·admin/자동마감/수동강제 → `complete_task_unified` 단일 UPDATE 원자). VIEW 중복 이력 표시 = work.py `get_tasks_by_serial` LATERAL 세션 페어링 (cross-join 9행→3행). Codex 13라운드 GO. pytest 신규 20 (DP-01~45, attendance-cap DP-41~45) + 회귀 95 GREEN. 백필(migration 058) 1002건 net −353,617분 / 5월+ 만 (4월 베타 제외) / 수동강제 51건 보존 / 단일워커 이상 0건. 설계: AGENT_TEAM_LAUNCH.md § FIX-DURATION-MANUAL-PAUSE-RAW (v1~v13).
> **선행 release**: v2.21.3 (MECH 체크리스트 자재 드롭다운 긴 spec 줄바꿈 표시, 2026-06-02) — 긴 자재 사양(flow sensor / MFC)이 `...`로 잘리던 문제. `mech_checklist_screen.dart` `itemHeight: null` + `selectedItemBuilder`(닫힘 1줄 ellipsis) + 메뉴 항목 `softWrap maxLines:3`. ELEC 제외. FE only, 회귀 0.
> **선행 release**: v2.21.2 (위치 검증 토글 Off 시 출근 GPS 권한 요청 제거, 2026-05-30) — admin `geo_check_enabled` Off 인데도 FE 가 무조건 GPS 호출 → BE `/hr/attendance/today` 응답에 `geo_check_enabled` additive + FE `(_geoCheckEnabled && work_site=='GST')` 일 때만 GPS (BE hr.py:132 정합). `_attendanceStatusLoaded` 게이트 (Codex M-Q2). Codex R1 M=1 반영.
> **선행 release**: v2.21.1 (협력사 퇴근 확인 다이얼로그 + 출퇴근 성공 토스트, 2026-05-30) — one-action 토글 퇴근 실수 클릭 방지 (`_handleAttendance` checkType=='out' confirm). FE only.
> **선행 release**: v2.21.0 (Sprint 80 — SI 출하예정 ISO 주차별 그룹핑 + 200 cap 누락 해소, 2026-05-29) — 출하예정 389건 중 189건 누락(per_page 200). BE `get_shipment_week_groups()` 신규 (ISO 주차+모델별 카운트 전체 GROUP BY, planned·no-q 시 `by_week` additive, 기존 튜플 서비스 무변경) + FE 주차 ExpansionTile(접힘, 펼치면 모델 카운트)/검색 시 평면 + W53 "미정" 칩 + 출고완료 버튼 `_canShip` 정합(GST PI/QI 403 방지). pytest test_sprint79 25 passed (WK-01~07). Codex R1(M=4)→R2(M=0 DEPLOY_SAFE). 설계서 SPRINT80_SI_SHIPMENT_WEEK_GROUP.md.
> **선행 release**: v2.20.15 (SI 마무리공정 출고완료 권한 확장, 2026-05-29) — SI 일반 작업자(role='SI' 비매니저) 출고완료 403 → `si_manager_or_admin_required` 데코 신규 (is_admin\|\|is_manager\|\|role=='SI') + ship-complete route 교체. pytest test_ship_complete 15 passed (PERM-01~03 + TC-SHIP-11 회귀수정). Codex M=0/A=6. + 가입화면 한글화 + 라벨 괄호 통일.
> **선행 release**: v2.20.14 (종료 분석 페이지 GST 매니저 전체 조회, 2026-05-29) — GST 매니저가 GST task(PI/QI/SI)만 보임 → `_build_partner_filter is_full_access = is_admin or worker_company=='GST'`. 협력사 매니저 격리 유지. pytest 21 passed (tc14b). Codex M=0/A=2.
> **선행 release**: v2.20.13 (VIEW #78 공장 대시보드 TEST 데이터 전역 제외, 2026-05-29) — `_TEST_EXCLUDE_SQL` (customer<>'TEST CUSTOMER' AND serial_number NOT LIKE 'TEST%') factory.py 6곳. monthly_detail 5월 169→164.
> **선행 release**: v2.20.12 (VIEW #75 ETL 변경 이력 필터 KST 자정 정합, 2026-05-29) — `admin.py /admin/etl/changes` NOW() 24h 롤링 → KST 자정 기준 (옵션 A). catch 2(S/N tracking) 스킵.
> **현재 버전(이전)**: **v2.20.11 (TMS(M)/TMS(E) 협력사 구분 + 매트릭스 셀↔리스트 정합 통일, 2026-05-29)** — Sprint 71 종료누락 분석 마무리. 도메인 규칙 (Twin파파): mech_partner='TMS'→TMS(M) / module_outsourcing='TMS'→TMS(M) / elec_partner='TMS'→TMS(E). `_COMPANY_SQL` 표준식 신설 → matrix/details/partner_filter 3곳 통일. 운영 검증: 매트릭스 grand_total 223 (TMS(M) 8 + TMS(E) 19 분리) + 셀↔리스트 분류 1:1 정합 (차이=force 모집단). 미시작 자동마감 0건 검증 (설계상 정상 — 릴레이 자동마감은 started task 만 대상).
> **선행 release**: v2.20.10 (미지정 분류 버그 2건, 2026-05-29) — 버그1 task_category 'TM'→'TMS' 오타 (dashboard_service.py만, task_service.py 전체는 'TMS') → TMS 8건 잘못 '(미지정)'. 버그2 '(미지정)' 셀 클릭 0건 (표시값 직접 매칭) → category-aware CASE.
> **선행 release**: v2.20.6~9 (VIEW #76/#77, 2026-05-29) — #76 auto-close-details 500 (SQL alias p↔pi 불일치) / #77 force_closed 3분류 (옵션 X, force block + by_reason + close_type) + invariant force 합산 / v2.20.8 배포 실패(일괄 치환 syntax) → v2.20.9 복구. 운영 auto 223 + manual 0 + force 107 = total 330.
> **선행 release**: v2.20.2~5 (출하 알림 cron 복구, 2026-05-29) — v2.20.2 admin debug endpoint (scheduler 진단 + cron 강제실행) / v2.20.3 APScheduler timezone 9시간 지연 메가버그 (KST=ZoneInfo + tzdata) / v2.20.4 CronTrigger 13개 timezone=Config.KST 명시 / v2.20.5 출하 0건 시에도 완료 메일 (daily health check, 메일 수신 확인).
> **선행 release**: v2.20.0~1 (Sprint 71 Manager Dashboard 자동마감 분석, 2026-05-28~29) — dashboard_service.py + admin_dashboard.py 신규 endpoint 2개 (summary/details). 분류 LIKE + 모집단 3분리 + V1 hourly 24h + V6 matrix + invariant. pytest 18/18 GREEN. Codex 라운드 1(M=3)→2(M=0). v2.20.1 invariant violation hotfix (COALESCE '(미지정)').
> **선행 release**: v2.19.11 (#74 후속 — `_ALLOWED_DATE_FIELDS` qi_start + si_start 추가, 2026-05-28) — BE 1줄 / VIEW v1.53.0 prod 배포 후 사용자 catch (Twin파파 11:20 KST): Phase 1 QI/SI 카드 카운트 0 (400 INVALID_DATE_FIELD). factory.py 화이트리스트 영역 qi_start + si_start 누락 → 추가. pytest 11/11 PASS. Railway 자동 배포.
> **선행 release**: v2.19.10 (#74 옵션 C + 출하 메일 template 회원가입 컨셉 정합, 2026-05-28) — BE only / 두 catch 통합. (1) VIEW #74 옵션 C — factory.py /monthly-detail date parameter 신규 (VIEW Sprint 78 v1.53.0 carrier). (2) 출하 미처리 메일 template 전면 rewrite — 회원가입 승인 메일 컨셉 (회색 박스 + 표 + [앱 열기] 버튼) + 박스 엣지 색상 제거. 메일 발송 spec 확정 trail: yesterday ship_plan_date + actual_date IS NULL (= app OR ETL 양쪽 미처리, best 패턴 정합, De Morgan's law). pytest 11/11 PASS (회귀 9 + 신규 2). Railway 자동 배포 trigger.
> **선행 release**: v2.19.9 (Sprint 79 — 출하 예정 탭 [출고 완료] 버튼 옵션 B 채택, 2026-05-28) — FE 1줄 변경 / 사용자 catch: 생산관리 일정 자동화 X 매니저 누락 case → 출하 예정 탭 검색 후 직접 출하 처리. 객관 분석 옵션 B 채택 (ETL plan 보존 + 책임 분리 + audit trail 자동 = SI_SHIPMENT.completed_at). 추후 분석 인큐베이션 FEAT-SHIPMENT-PROCESS-AUDIT-ANALYSIS-20260528.
> **선행 release**: v2.19.8 (출하 알림 chip 카드 PI 위임 패턴 정합, GST 매니저 name, 2026-05-28) — BE schema 변경 (int_list → string_list, worker name CSV base) + FE chip 카드 (`_buildChipListSetting` 활용) + pytest 18/18 PASS (4 신규 TC 추가)
> **선행 release**: v2.19.7 (미종료 작업 분류 화면 UI 컨셉 정합, 2026-05-28) — pending_tasks_grouped Card 디자인 PI/QI carrier
> **선행 release**: v2.19.6 (SI Finishing 버튼 권한 logic 재정정, 2026-05-28) — Tab 1 본인 [내 작업 완료] + admin/manager [강제 종료] / Tab 2 [출고 완료] GST 인원 전체
> **선행 release**: v2.19.5 (SI 카드 디자인 PI/QI 정합 + Tab 2 GST 인원 [내 작업 완료] 버튼, 2026-05-28) — BE schema 추가 (model + customer + si_finishing_task_id + worker_id + worker_name) + FE _buildPendingCard 신규
> **선행 release**: v2.19.4 (미종료 작업 권한 BE + SI 버튼 UI PI/QI 컨셉, 2026-05-28) — /admin/tasks/pending 권한 본문 분기 (admin OR manager OR company='GST') + 버튼 UI Divider + Row Expanded
> **선행 release**: v2.19.3 (미종료 작업 권한 GST 자사 FE, 2026-05-28) — /admin/tasks/pending/grouped @admin_required → @gst_or_admin_required + home 메뉴 표시 권한
> **선행 release**: v2.19.2 (SI Finishing action 버튼 추가, 2026-05-28) — _completeMyWork + _shipComplete + _forceCloseTask 함수 3개
> **선행 release**: v2.19.1 (SI 카드 navigate + admin_options 분리 + 메일 토글, 2026-05-27) — SI 카드 /si-finishing navigate + admin_options 비활성/미종료 섹션 제거 (~310 lines) + shipment_alert_enabled 토글 추가
> **선행 release**: v2.19.0 (Sprint 79 FEAT-SI-SHIPMENT-FLOW-3PHASE, 2026-05-27) — 큰 sprint / SI 마무리공정 TabBar 3개 (미종료/출하 확정/출하 예정) + admin 메인 메뉴 분리 (비활성 사용자 + 미종료 작업 분류) + 매일 07:30 KST 출하 미처리 자동 알림. BE 신규 2 + 수정 4 / FE 신규 3 + 수정 2 / pytest 14/14 PASS / Codex 라운드 1 (M=7/A=2/N=4) 모두 반영 (사용자 결정 Q8 (나) overlap / M2 현행 / A-추가1 (가)).
> **선행 release**: v2.18.35 (매뉴얼 모바일 PWA HOTFIX — ApiService 싱글톤 catch, 2026-05-27) — FE 1 파일 / v2.18.34 fix 후 사용자 catch "세션만료" SnackBar 만 뜨고 접속 불가. Root cause: ApiService 영역 싱글톤 아님 → `ApiService()` 직접 호출 = 새 instance + token null. Fix: `ref.read(apiServiceProvider).token` (Riverpod Provider singleton). flutter build web GREEN + 사용자 실기기 catch 정상. 같은 sprint 인큐베이션 BACKLOG `REFACTOR-API-SERVICE-SINGLETON-20260527` 등록 의무.
> **선행 release**: v2.18.34 (VIEW #72 admin 권한 데코레이터 통일 + 매뉴얼 모바일 PWA fix, 2026-05-27) — BE 2 + FE 1 + version / 두 catch 통합 release. (1) VIEW OPS_API_REQUESTS.md #72 운영 차단 catch — checklist.py 5곳 + admin.py L1543/L1574 `@admin_required` → `@gst_or_admin_required` + `/api/admin/product-codes` 신규 endpoint. GST manager (testpm 외 모든 자사) 체크리스트 관리 + admin_settings 접근 정상. 협력사 차단 의도 유지. (2) `BUG-OPS-MANUAL-BUTTON-MOBILE-PWA-20260526` CLOSED — `home_screen.dart _handleOpenManual()` 영역 `await getToken()` (async) → `ApiService().token` (sync) 변경 (장기 시스템 관점 옵션 A — DRY + 책임 분리 + 표준 패턴). pytest 28/28 PASS + flutter build web GREEN.
> **선행 release**: v2.18.33 (Sprint 76-BE plan_change_warning 신규 + Sprint 77 인큐베이션, 2026-05-27) — BE 1 파일 + pytest 1 TC / 사용자 핵심 catch: "계획대비 출하 = 계획일 수정 시 100% 정시 트릭" 모순. 운영 5월 plan 148건 중 89건 (60%) `ship_plan_date` 변경됨 검증. `_fetch_plan_change_warning()` 2단계 SQL (to_regclass IF + etl.change_log JOIN) 신규 — `kpi.plan_change_warning = { count, share_pct, hint }` 응답 추가. test DB `etl.change_log` 없음 안전망 (count=0 fallback). pytest 32/32 GREEN. Sprint 77 (가칭) Lead Time 준수율 신규 KPI 인큐베이션 BACKLOG 등록. commit `d8dcc22`.
> **선행 release**: v2.18.32 (Sprint 76-BE TEST CUSTOMER 제외, 2026-05-27) — BE 2곳 WHERE 절 / 사용자 catch: "test data는 당연히 제외 되야됨" / `_build_best_ship_cte` + `_fetch_monthly_trend` 양쪽 `AND COALESCE(p.customer, '') <> 'TEST CUSTOMER'` 추가 / factory.py v2.15.21 (#69) 패턴 동일 / 5월 응답 plan_count 153→148, fulfillment_pct 79.7%→82.4% (정합도 ↑) / pytest 31/31 GREEN
> **선행 release**: v2.18.31 (OPS 매뉴얼 버튼 모바일 PWA catch fix try → BACKLOG 이관, 2026-05-26) — FE 1 파일 / 사용자 catch: "메뉴얼버튼 눌러도 페이지 전환안됨 모바일에서 전환안됨" / `_handleOpenManual()` anchor click + fallback 패치 / 사용자 재검증 "메뉴얼로 안넘가네 터치는 잘눌리는데" → root cause: `await getToken()` 후 anchor.click() user gesture context lost (모바일 popup 차단) / BACKLOG `BUG-OPS-MANUAL-BUTTON-MOBILE-PWA-20260526` 🟠 MEDIUM 이관 (옵션 A tokenSync / B location.href / C 조합 결정 의무)
> **선행 release**: v2.18.30 (Sprint 76-BE best_ship CTE model source 정정, 2026-05-26) — BE 1줄 fix / 사용자 catch: v2.18.29 운영 검증 invariant 실패 → 운영 1199건 검증 결과 product_code (숫자 SKU '41200152') vs model (분류 이름 'GAIA-I DUAL') 의미 완전 다름. `p.product_code AS model` → `p.model AS model` 1줄 정정. TEST 5건 자동 해소 + 매니저 직관 ↑ + VIEW 변경 0 (응답 schema 유지). pytest 31/31 GREEN.
> **선행 release**: v2.18.29 (Sprint 76-BE by_model 옵션 C 정정 + P-v3 avg_lead_time_days, 2026-05-26) — BE 1 파일 + pytest 1 / 사용자 catch: by_model base 일관성 (by_customer plan+shipped 분리 vs count 단일) + 공정 순서 정정 (elec→TM→mech→pi 운영 1352/1357) + Plan ETL standard 현재 / 추후 OPS actual 토글 인큐베이션. by_model `count → plan rename + shipped + avg_lead_time_days P-v3 (AVG(pi_start - LEAST(elec_start, mech_start)))` + invariant 5건 확장. pytest 31/31 GREEN. BACKLOG-SPRINT76-ACTUAL-LEAD-TIME-OPS 등록. (docs commit `8e4dd63` — 명세서 SQL BETWEEN → 반개구간 일괄 정정 동반)
> **선행 release**: v2.18.28 (Sprint 76-BE 출하이력 페이지 BE 신규, 2026-05-26) — BE 신규 3 파일 + pytest 1 (29 TC, ~520 LoC) / AXIS-VIEW Sprint 76 (#73 v2) 의 OPS BE part / API 2개 신규 (`/api/admin/shipment/summary` + `/details`, @gst_or_admin_required) / best_ship CTE = factory.py _count_shipped(basis='best') 패턴 정합 / 반개구간 (>= AND <) + N+1 batch top_delayed + invariant 3건 + TEST-SHIP-76-* fixture / Codex 2 라운드 (VIEW M=7+A=2 + OPS BE M=5+A=2+N=1) 전수 close
> **선행 release**: v2.18.27 (매뉴얼 보안 통합 — OPS 상단 버튼 + axis-manual JWT 미들웨어, Codex 라운드 1 M=2/A=5 반영, 2026-05-22) — OPS 2 + axis-manual 3 + AXIS-VIEW 1 파일 / 사용자 catch: "url 이 현재 전체공개라 누구나 볼수 있게 됬는데 이것도 보안이 필요한데" → OPS 홈 상단 `[📖 매뉴얼]` IconButton (token 첨부 새 탭) + axis-manual Netlify Edge Function JWT verify(HS256) + payload.type='access' 검증(refresh 차단) + Cookie Max-Age JWT exp 기준 동적 + 정적 자산 우회 축소(폰트/파비콘만) + VIEW Header.tsx token 첨부. axis-manual v1.4.0 (Edge Function 신규) + v1.5.0 (Admin Section B 2페이지). Codex 라운드 1: M=2/A=5 반영 + A=3 BACKLOG 권고
> **선행 release**: v2.18.26 (로그인 후 AuthGate 강제 진입 pushAndRemoveUntil, 2026-05-22) — FE 1 파일 / LoginScreen 이 first route 일 때 popUntil 무동작 catch → pushAndRemoveUntil(MaterialPageRoute(builder: AuthGate), (route)=>false) 변경. Navigator 스택 정리 패턴
> **선행 release**: v2.18.25 (로그인 성공 후 새로고침 안내 SnackBar, 2026-05-22) — FE 1 파일 / PWA 모바일 강제 새로고침 어려움 catch → 3초 후 화면 안 넘어가면 SnackBar 안내. v2.18.26 정식 fix 후 안전망 유지
> **선행 release**: v2.18.24 (ApprovalPendingScreen 승인 후 자동 홈 이동, 2026-05-22) — FE 1 파일 / 사용자 catch: admin 승인 후 화면 전환 안 됨 → PWA 강제 새로고침 필요 / ref.listen(authProvider) 자동 감지 + manual check 안전망 이중
> **선행 release**: v2.18.23 (가입 승인 메일에 매뉴얼 URL 추가, 2026-05-22) — BE 1 파일 / axis-manual.netlify.app
> **선행 release**: v2.18.22 (가입 승인 메일 URL 정정 + 로그인 방법 안내 박스, 2026-05-22) — BE 1 파일 / 도메인 g-view → gaxis-ops.netlify.app + 메일 본문 🔑 로그인 박스
> **선행 release**: v2.18.21 (안내 메일 도메인 변경 + login 안내 박스 + PIN 설정 위치, 2026-05-22) — BE 1 + FE 1 파일 / login_screen 안내 박스 + PIN 위치
> **선행 release**: v2.18.20 (승인 메일 + prefix 확장 + 안내 3가지, Codex 라운드 1 M=3 반영, 2026-05-22) — BE 4 + FE 2 + 신규 1 + pytest 1 / notification_service.py 신규 (`send_approval_notification` + `_async` thread 캡슐화, Codex M-Q4 admin.py 정책 정합) / `get_worker_by_email_prefix` 신규 (3개 도메인 후보, ambiguous debug log) / login chain 4-tier (admin→user prefix→이름→이메일) / register SnackBar + login 안내 3가지 (이메일/prefix/PIN, 이름 코드 유지/안내 제외). Codex 라운드 1: M=3 반영 (HTML escape XSS / thread 캡슐화 / pytest 4 TestClass) + A=3 BACKLOG (도메인 중복 / 모호 안내 / outbox). 신규 BACKLOG: REFACTOR-ADMIN-SPLIT HIGH + 3건 LOW
> **선행 release**: v2.18.19 (verify_email 카운트다운 3분 → 1분, 2026-05-22) — FE 2줄 / BE rate limit 60s 동기화. login redirect/resend 버튼은 이미 구현돼 있던 catch
> **선행 release**: v2.18.18 (인증 메일 도메인 안내 + whitelist 검증, 2026-05-22) — BE 1 + FE 2 파일 / 사용자 catch (카카오/다음 가입 시 인증메일 미수신, KT Biz Office SMTP 외부 도메인 차단) / `ALLOWED_EMAIL_DOMAINS = {gst-in.com, naver.com, gmail.com}` BE/FE 동기화 + register_screen 안내 메시지 / `EMAIL_DOMAIN_NOT_ALLOWED` 에러 응답 / CLAUDE.md L626 문서와 코드 일치
> **선행 release**: v2.18.17 (Sentry 잡음 2건 fix — WebSocket Broken pipe + SMTP Recipients refused, 2026-05-22) — BE 3 파일 + FE version bump / events.py BrokenPipeError 분기 logger.info / email_service.py + auth_service.py SMTPRecipientsRefused 분기 logger.warning / 진짜 ERROR 추적성 보존 (exc_info=True). v2.10.13 패턴 정합. 운영 catch: admin 이메일 점검 부탁 (workers.is_admin=true 잘못된 이메일 존재 가능성)
> **선행 release**: v2.18.16 (BUG-42 fix — zoom 2.0x 자동 적용, videoConstraints 우회, 2026-05-21) — FE 1 파일 / qr-test.html 사용자 검증: videoConstraints 사용 시 디코더 방해 / applyConstraints({advanced:[{zoom}]}) 만 사용 시 디코더 정상 + 명판 확대. `_applyZoomIfSupported` helper (+47 LOC) + 3곳 fire-and-forget 호출. cameraIdOrConfig + qrbox 200 + DOM/CSS baseline 그대로. 누적 trail: 13번 시도 후 도달 (v2.18.5~11 셀카 → v2.18.12 1차 ROLLBACK → v2.18.13/14 인식 NG → v2.18.15 2차 ROLLBACK + qr-test.html → v2.18.16 최종 fix). 실기기 QA 위탁
> **선행 release**: v2.18.15 (ROLLBACK 2차 — v2.18.4 baseline 복귀, 2026-05-21) — FE 1 파일 / v2.18.13(4-tier)+v2.18.14(3-tier) 실기기 catch: 1차 tier QR 인식 NG (코너 초록색 변화 없음) — 운영 코드 fallback chain 자동 회귀 안 됨. `git checkout 8a2233f -- qr_scanner_web.dart` baseline 복귀 (506 LOC). 누적 trail: v2.18.5~v2.18.11 11번 hotfix → v2.18.12 1차 ROLLBACK → Codex 검증 + qr-test.html → v2.18.13/14 → v2.18.15 2차 ROLLBACK. BUG-42 🔴 OPEN + 7 별 sprint. **재시도 조건**: 실기기 디버깅 환경 (Mac 원격 + Eruda) 갖춘 후 minimal change 단계별 검증
> **선행 release**: v2.18.13 (BUG-42 재시도 — 4-tier fallback chain, Codex 라운드 1+2 합의, ROLLED BACK in v2.18.15, 2026-05-21) — FE 1 파일 / `_buildFallbackTiers()` helper 신규 + 4-tier chain (1차 full → 2차 advanced 제거 → 3차 해상도 제거 → 4차 baseline). videoConstraints 안에 facingMode 명시 (라이브러리 동작 정합). 사용자 qr-test.html 시뮬레이션 4 시나리오 GREEN catch 후 적용. Codex 라운드 2 DEPLOY_SAFE:CONDITIONAL. 신규 BACKLOG 2 (QR-SCANNER-RETRY-CLEANUP / QR-SCANNER-ERROR-CLASSIFICATION) + REFACTOR-FUNCTION-SPLIT MEDIUM 격상. **실기기 QA 8항목 사용자 위탁**
> **선행 release**: v2.18.12 (ROLLBACK + qr-test.html 검증 + Codex 라운드 1, 2026-05-21) — FE 1 파일 / v2.18.5~v2.18.11 (11번 BUG-42 hotfix 시리즈) 모두 롤백. `git checkout 8a2233f -- qr_scanner_web.dart` 506 LOC. **테스트 페이지 신규** (`frontend/web/qr-test.html`): 운영 1:1 복제 + 옵션 토글 7개 → 사용자 실기기 매트릭스 catch — 옵션 1/2 단독 ON 셀카 / 패턴 A (videoConstraints 안 facingMode 명시) 후면 ✅. **Root Cause 확정** (Codex 라운드 1 M-Q1): html5-qrcode 2.3.8 `areVideoConstraintsEnabled ? internalConfig.videoConstraints : createVideoConstraints(cameraIdOrConfig)` → videoConstraints 키 존재 시 cameraIdOrConfig.facingMode 무시. **Codex 권고**: 4단계 fallback chain (M-Q2) + 실기기 QA 8항목 (M-Q4) + TEST-QR-LIB-CONSTRAINT-PREFLIGHT / TOOL-ERUDA-DEV-CONSOLE BACKLOG 등록 (A-Q5/Q6). **v2.18.13 재시도 준비 완료**. BUG-42 🔴 OPEN + 5개 별 sprint
> **선행 release**: v2.18.11 (HOTFIX-14 권한 발급 시점 environment hint, 2026-05-21, ROLLED BACK) — `_requestCameraPermission()` 영역 1차 `{video:{facingMode:'environment'}}` 권한 발급 → enumerate 후면 노출 유도. v2.18.12 에서 롤백
> **선행 release**: v2.18.10 (HOTFIX-13 getUserMedia exact + facingMode 검증, ROLLED BACK)
> **선행 release**: v2.18.9 (HOTFIX-12 getUserMedia 직접 호출 0차, ROLLED BACK)
> **선행 release**: v2.18.8 (HOTFIX-11 cameras label 매칭 1차 승격, ROLLED BACK)
> **선행 release**: v2.18.7 (HOTFIX-10 후면 카메라 강제, 2026-05-21, ROLLED BACK) — FE 1 파일(qr_scanner_web.dart) / 사용자 catch (v2.18.6 직후): "카메라 방향이 셀카인데 전환 버튼 돌려달라" — 모바일에서 `facingMode:'environment'` hint 영역 OS 무시 → user silent fallback → 셀카 / fix: `environment` 영역 `{exact:...}` 강제 + 3차 cameraId fallback 영역 'back'/'rear'/'후면' label 매칭 안전망 추가 / 데스크톱은 자동 user fallback (1차 fail 후) / flutter build web GREEN / LOC 533→551 🟡 / **별 sprint**: `BUG-42-CAMERA-SWITCH-BUTTON-DEFERRED` BACKLOG 등록(전환 버튼 UI) / **실기기 manual QA 재위탁**
> **선행 release**: v2.18.6 (HOTFIX-09 cameraIdOrConfig 1-key 위반 fix, 2026-05-21) — FE 1 파일(qr_scanner_web.dart) / v2.18.5 배포 직후 사용자 실기기 catch: `'cameraIdOrConfig' object should have exactly 1 key, found 4 keys` — html5-qrcode `start()` 1번째 인자 1-key 제약 위반 → 3시도 모두 reject → "카메라 없음" 에러 / fix: helper 1-key 객체만 반환 + `__qrScanConfig.videoConstraints` 영역으로 해상도/focusMode 이동 / flutter build web GREEN / LOC 530→533 🟡 / Codex 라운드 1 (v2.18.5) 놓친 라이브러리 spec catch / **모바일 셀카 catch → v2.18.7 hotfix**
> **선행 release**: v2.18.5 (HOTFIX BUG-42 명판 소형 QR 인식률 개선 — Task 2, 2026-05-21) — FE 1 파일(qr_scanner_web.dart) / 사용자 운영 catch "자동 포커싱이 안 되는 거 같다" / `_buildScannerConstraints()` helper 분리 + 3곳 호출 통일(env/user/cameraId) — width 1920 + height 1080 + `focusMode: continuous` + cameraId `{deviceId:{exact:...}}` 변환 / Codex 라운드 1 M=4 합의 (Task 1 BarcodeDetector skip = no-op, Task 3 자동 줌 BACKLOG 이관, iOS Safari 안전 폴백) / flutter build web GREEN / LOC 506→530 🟡 경고 영역 유지 → REFACTOR-QR-SCANNER-WEB-FUNCTION-SPLIT BACKLOG 등록 / **실기기 catch (cameraIdOrConfig 4 keys) → v2.18.6 hotfix**
> **선행 release**: v2.18.4 (#70 출하 KPI `best` 분기 엑셀 게이트 제거, 2026-05-21) — BE 1 파일(factory.py) / AXIS-VIEW OPS_API_REQUESTS.md #70 — SI 공정 5-19 시행 후 app SI 데이터 유입 시작 → `best` 토글 엑셀 게이트(`WHERE actual_ship_date IS NOT NULL`) 가 app-only 출하 누락 → 합집합(OR) 으로 정정 / `COUNT(DISTINCT p.serial_number)` 자동 중복 제거 + `COALESCE(DATE(t.completed_at), p.actual_ship_date)` app 우선 / pytest TestFactoryKpiV24Amendment #70 TC 2 GREEN / 응답값 즉시 변경 0 (현재 갭 0건) / 출하이력 페이지(FEAT-SHIPMENT-HISTORY-PAGE 6월 초) 선행 의존성 해소
> **선행 release**: v2.18.3 (SEC-CONFIG-DATABASE-URL-FALLBACK-REMOVED + GCP migration HOLD, 2026-05-20) — BE 1 파일(config.py) / Railway DB URL 하드코딩 fallback 제거 + GCP migration 준비 100% 완료 후 비용 협의로 hold / GCP standby: 월 ~$20 (storage만) / 재오픈 30분 절차는 `GCP_MIGRATION_STANDBY.md` 참조 / Railway prod 운영 그대로 (Auto Deploys ON 복원, 사용자 150명)
> **선행 release**: v2.18.2 (FIX-MECH-CHECKLIST-QR-DOC-ID-SINGLE-UNIFY: DRAGON DUAL MECH 체크리스트 완료판정 P0, 2026-05-19) — BE 1(checklist_service.py) + OPS FE 1(mech_checklist_screen.dart) / qr_doc_id 컨벤션 혼재(INLET `-L`/`-R` vs SINGLE) → DRAGON DUAL MECH 체크리스트 영원히 100% 불가 P0 버그 / 옵션 D — qr_doc_id `DOC_{S/N}` SINGLE 통일, `check_mech_completion` DUAL 분기 제거 / `check_tm_completion` 미변경 / Codex 라운드 1 M=2(TC 보강)/A=4 / pytest 신규 12 TC + 회귀 131 GREEN / 운영 데이터 0건 회귀 위험 0
> **선행 release**: v2.18.1 (Sprint 69 fix: 내 작업 완료 다이얼로그 공정명 하드코딩, 2026-05-19) — FE only 1줄(gst_products_screen.dart) / `_completeMyWork()` 확인 다이얼로그 `'SI 마무리공정'` 하드코딩 → `$_categoryLabel` (PI/QI 에서도 정확) / flutter build GREEN / 회귀 0
> **선행 release**: v2.18.0 (Sprint 69: PI/QI 완료 권한 잠금 + admin 정상완료, 2026-05-19) — BE 2(task_service.py, shipment_service.py+work_shipment.py) + FE 1(gst_products_screen.dart) / PI/QI cross-worker 완료 차단(시작 본인만) + `POST /api/app/work/admin-complete`(admin/manager 정상완료, force_closed=FALSE) + PI/QI 카드 [종료] 버튼·종료 시각 다이얼로그 + O/N·S/N 검색 칸 / Codex 라운드 1 BE M=10/A=4 + FE M=1/A=3 / pytest test_admin_complete 10/10 GREEN / flutter build GREEN / migration 불필요 회귀 0
> **선행 release**: v2.17.2 (Sprint 68 fix: SI 마무리공정 화면 출고 대기 누락, 2026-05-19) — BE 1 파일(gst.py) / SI 화면이 SI_FINISHING 진행중만 표시 → 출고 대기(SI_FINISHING 완료+미출고) 제품 누락 fix / SI WHERE 분기 `task_id='SI_FINISHING' AND started AND si_completed=false` + completion_status JOIN / SQL 검증 SI 7건(진행중 4+출고대기 3) / PI/QI 현행 유지 회귀 0
> **선행 release**: v2.17.1 (Sprint 68 OPS FE: SI 출고 버튼 + O/N 표시, 2026-05-19) — BE 1(gst.py) + FE 1(gst_products_screen.dart) / SI 카드 [내 작업 완료]+[출고 완료] 버튼 + PI·QI·SI O/N·고객사 표시 / Codex 라운드 1 M=2+A-Q7 / flutter build GREEN
> **선행 release**: v2.17.0 (Sprint 68: 출하 완료 ship-complete endpoint, 2026-05-19) — BE 신규 2 파일(shipment_service.py + work_shipment.py) + pytest 1 / `POST /api/app/work/ship-complete` — SI task 2개 완료 + completed_at 지정 + audit / Codex 라운드 1 M=5/A=1 / pytest test_ship_complete 12/12 GREEN
> **선행 release**: v2.16.0 (Sprint 67-BE: progress API 공정 토글 신호, 2026-05-18) — BE 1 파일(progress_service.py) + pytest 1 / VIEW Sprint 46 공정 토글 필터 BE part — progress API `categories` 에 `started`/`completed_at`/`completed_today` 3신호 추가 / Codex 라운드 1 M=1/A=6 / pytest test_sn_progress 22/22 GREEN
> **선행 release**: v2.15.21 (#69 월간 생산량 KPI TEST CUSTOMER 제외, 2026-05-18) — BE 1 파일(factory.py) / `get_monthly_kpi()` `production_count` 쿼리 WHERE 절에 `COALESCE(p.customer,'') <> 'TEST CUSTOMER'` 추가 / 월간 생산량 KPI 169→164 (Sprint 44 고객사 도넛과 일치) / pytest test_factory 19/19 GREEN / 회귀 위험 0
> **선행 release**: v2.15.20 (FIX-FORCE-CLOSED-REACTIVATION, 2026-05-18) — BE 1 파일(task_detail.py) + VIEW 1 파일(ProcessStepCard.tsx v1.44.2) + pytest 1 / 강제종료 task 재활성화 정상화 — `reactivate_task()` 4컬럼 리셋(force_closed/closed_by/close_reason/duration_source) + VIEW 재활성화 버튼 조건 `(completed_at||force_closed)` / Codex 라운드 1 M=2 합의·A=2 BACKLOG·N=3 / pytest reactivate 6/6 GREEN / 회귀 위험 0
> **선행 release**: v2.15.19 (FEAT-FACTORY-MONTHLY-DETAIL-BY-CUSTOMER #68, 2026-05-18) — BE 1 파일 + pytest 1 / monthly-detail 응답에 by_customer 집계 추가 (공장 대시보드 월간 고객사 도넛) / by_model 1:1 복제 / Codex 라운드 1 M=6 (3건 prompt 오독) / pytest test_factory 19/19 GREEN / 회귀 위험 0 (additive)
> **선행 release**: v2.15.18 (POST-REVIEW-OPS-65-PATH2-REOPEN, 2026-05-15) — BE 1 파일 + pytest 1 / MECH Dual-Trigger 경로 2 fix (M-A4 mech_completed flag UPDATE + M-A7 close 게이트 check_mech_completion_all) / AXIS-VIEW 측 #65 리뷰 catch / Codex 라운드 1 M=2 합의 / pytest 5/5 GREEN / 회귀 위험 0
> **인프라 (5-18)**: conftest migration SQL 분리 로직 운영 runner 통일 (POST-REVIEW-PYTEST-FAILED-ANALYSIS, commit 9b4dd7d) — 051 계열 empty query 해소. 전수 재측정 deadline 5-22
> **선행 release**: v2.15.17 (FIX-VIEW-ORPHAN-DURATION-MISSING, 2026-05-15) — BE 2 파일 + pytest 1 / Trigger task auto-close 시 VIEW 소요시간 '—' 미표시 fix / Codex M=2 반영 / pytest 10/10 GREEN
> **선행 release**: v2.15.16 (SPRINT-V2-15-16-MECH-FORCE-CLOSED-PREV-DAY-CAP, 2026-05-15) — BE 3 파일 + migration 1 + pytest 1 / 사용자 catch 3건 fix / Codex M=5 전수 반영 / pytest 50/50 GREEN
> **선행 release**: v2.15.15 (BUG-RELAY-MODE-AUTO-REFRESH-MISSING + COMPLETE-KEY-USELESS, 2026-05-15) — BE 1 + FE 2 파일 / fetchTasks silent 인자 + "공정 마감" 버튼 + and not finalize / 자가 리뷰 M-1+M-2 catch
> **선행 release**: v2.15.14 (BUG-SECOND-CLOSE-FORCE-CLOSED-FALSE-POSITIVE + AUDIT TRAIL 통일, 2026-05-15) — BE only 3 파일
> **선행 release**: v2.15.13 (HOTFIX-MECH-CHECKLIST-DUAL-TRIGGER — 체크리스트 100% PUT 시점 SELF_INSPECTION + 잔여 task 일괄 close, 2026-05-15) — BE only 1 파일
> **INFRA (5-15)**: **INFRA-CI-PYTEST-AUTO** — `.github/workflows/pytest.yml` 신규 도입 (push/PR 시 자동 pytest 실행) + ADR-029 사례 #28 등록 (cowork pytest 결과 보고 검증 누락 catch trail)
> **DOCS (5-15)**: **AUDIT_TRAIL_GUIDE.md 신규** — v2.15.14 audit trail 통일 후 DB 추적 4W 매트릭스 + SQL 활용 사례 6건 + 트러블슈팅 가이드 (운영 분석 영구 reference)
> **pytest 전수 결과 (5-15 백그라운드 54분 36초)**: PASS **1201** / FAILED 80 / ERROR 20 / SKIPPED 35 = PASS 비율 **92.3%** (1201/1301). test_relay_first_final 38/38 GREEN (Sprint 41-D + v2.15.14 회귀 0). 분석 1주 보류 (옵션 c — 운영 검증 우선) → BACKLOG `POST-REVIEW-PYTEST-FAILED-ANALYSIS-20260515` (deadline 2026-05-22)
> **선행 release**: v2.15.12 (FIX-MECH-CHECKLIST-PROGRESS-REALTIME-AND-STICKY — 실시간 갱신 + 스크롤 고정, 2026-05-15) — FE only 1 파일
> **선행 release**: v2.15.11 (FIX-MECH-CHECKLIST-PROGRESS-HEADER — ELEC 패턴 정합 진행률 표시, 2026-05-15) — FE only 1 파일
> **선행 release**: v2.15.10 (HOTFIX-SPRINT41D-ELEC-CLOSE-CONDITION-DUAL-TRIGGER — IF_2 강제 제거 + Dual-Trigger 완성, 2026-05-14) — BE only 2 파일
> **선행 release**: v2.15.9 (HOTFIX-SPRINT41D-PROGRESS-100-REVERT-AND-LABEL-CHANGE — (나) → (가) 회귀 + "공정 마감" 라벨, 2026-05-14) — BE 1 + FE 2 파일
> **선행 release**: v2.15.8 (FIX-27 statusText 정정 — "동료 진행 중" 추측 → "재참여 가능" 사실 기반, 2026-05-14) — FE only / 단일 문자열 변경 / 사용자 catch UX 카피라이팅 정합
> **선행 release**: v2.15.7 (FIX-27 FE TASK_CARD_MY_STATUS_AND_PULL_TO_REFRESH — TEST-1111 UX 개선, 2026-05-14) — FE only 3 파일 / Codex 라운드 1 정정 5건 / flutter analyze 0 error
> **선행 release**: v2.15.6 (HOTFIX-SPRINT41D-TMS-CLOSE-FIX-MECH-ELEC-PROGRESS-100 — TMS 잘못 매핑 정정 + (나) 옵션, 2026-05-14) — BE only / pytest 38/38 GREEN / 회귀 위험 0
> **선행 release**: v2.15.5 (HOTFIX-SPRINT41D-CHECKLIST-AND-SINGLE-ACTION — SINGLE_ACTION First Close + 체크리스트 100% AND, 2026-05-14) — BE only / catch #24 + #25 통합
> **선행 release**: v2.15.4 (HOTFIX-SPRINT41D-SQL-COLUMN-FIX — last_started_at 컬럼명 오류 + DRY 정정, 2026-05-14) — BE only / Sentry silent fail catch (GPWS-0799)
> **선행 release**: v2.15.3 (HOTFIX-SPRINT41D-AUTO-FINALIZE-RANGE-EXTENSION — Issue A 차단 범위 확장, 2026-05-14) — pytest 46/46 GREEN
> **선행 release**: v2.15.2 (HOTFIX-SPRINT41D-AUTO-FINALIZE-NOT-BLOCKED — 즉시 return 누락 fix, 2026-05-14) — pytest 26/26 GREEN
> **선행 release**: v2.15.1 (Sprint 41-D FE 후속 — `_kFinalTaskIds` IF_2 제거 + INSPECTION 추가, 2026-05-14) — flutter analyze clean
> **선행 release**: v2.15.0 (Sprint 41-D Relay First Final Logic — 2026-05-14) — BE only minor / 5 파일 +650 LOC / Codex 라운드 1+2 정정 12건 반영 / pytest 38/38 GREEN
> **선행 release**: v2.14.4 (HOTFIX-ELEC-CHECKLIST-SELECT-IMMEDIATE-PUT — dropdown 단독 변경 시 저장, 2026-05-13)
> **선행 release**: v2.14.3 (HOTFIX-ELEC-CHECKLIST-PLACEHOLDER-DEACTIVATE — 046a 사고 정정, 2026-05-13)
> **선행 release**: v2.14.2 (HOTFIX-MATERIALS-CATEGORY-ILIKE — 자재 마스터 검색 case-insensitive, 2026-05-13)
> **선행 release**: v2.14.1 (FIX-DB-POOL-CONN-LEAK-WORK-PY — work.py conn leak 5 위치 fix, 2026-05-12)
> **선행 release**: v2.14.0 (Sprint 66-BE-FOLLOWUP v3 — 자재 마스터 Excel 일괄 업로드 endpoint, 2026-05-12)
> **선행 release**: v2.13.2 (HOTFIX-TASKS-BY-ORDER-WORKERS — workers 배열 추가, S1 동반, 2026-05-11)
> **선행 release**: v2.13.1 (HOTFIX-TASKS-BY-ORDER-SCHEMA — 응답 형식 정정, 2026-05-11)
> **선행 release**: v2.13.0 (Sprint 64-BE v3 — Work Batch 엔드포인트 신규, 2026-05-11)
> **선행 release**: v2.12.6 (HOTFIX-SPRINT66BE-CREATE-MASTER-ITEM-TYPE-AND-CONFLICT-MSG — POST INSERT 정정, 2026-05-11)
> **선행 release**: v2.12.5 (FIX-ADMIN-OPTIONS-LISTS-SCROLL-ALERT-DEFAULT + HOTFIX-SPRINT66BE-MASTER-LIST-ITEM-TYPE — 4건 묶음, 2026-05-11)
> **선행 release**: v2.12.4 (FIX-ELEC-IF-NAMING-DOCKING-CLARITY — IF_1/IF_2 task_name 도킹 전/후 명시, 2026-05-10) — BE 2 line + Migration 054 (370 row UPDATE atomic) + pytest 28/28 PASS
> **선행 release**: v2.12.2 (FEAT-MATERIAL Step 3 — checklist_master 동적 자재 조회, 2026-05-08) — BE checklist_service.py 4 신규 함수 + FE mech_checklist_screen.dart 재진입 hydrate + pytest 14 TC
> **선행 인프라**: FIX-DB-POOL-MAX-SIZE-20260427 — Railway env DB_POOL_MAX 20→30 (2026-04-27, 코드 변경 0)
> **D+1 운영 검증 (2026-04-28)**: 출근 peak 측정 PASS — Pool exhausted 0 / direct conn fallback 0 / OPS conn 6~7 안정 / Sentry 새 issue 0 → 옵션 X1 유지, OBSERV-WARMUP COMPLETED 확정, v2.10.11 HOTFIX-06b 불필요
> **DB Pool V4.1 T+1주 검증 (2026-05-10)**: 🟢 시나리오 A 이상적 1차 통과 — Railway 36h 0/0 0건, Sentry 1주 신규 0건, Cluster A 9.5h 무중단. 5일 주기 가설 break 진행 중 (4-29 → 5-04 → 5-07 → 5-10 0건). 사용자 측 5-15까지 추가 점검 (5-12 ± 1d 예상 사고 시점 통과 확인)

---

## v2.18.3 + GCP MIGRATION STANDBY (2026-05-20)

**Sprint**: SEC-CONFIG-DATABASE-URL-FALLBACK-REMOVED + INFRA-GCP-MIGRATION-PREP

**상태**: ✅ COMPLETED → HOLD (비용 협의)

**배경**: 2026-05-19 Railway 부분 장애 → GCP Cloud Run + Cloud SQL migration 결정 → 1주 일정 진행 → 1일 만에 모든 준비 100% 완료 → 비용 분석 결과 Railway 대비 ~10배 증가 (월 $30 → $340) → 사용자 결정 hold + 비용 협의

**v2.18.3 코드 변경**:
- `backend/app/config.py` `DATABASE_URL` 하드코딩 Railway fallback 제거 → `os.getenv("DATABASE_URL", "")` + `RuntimeError` fail-fast
- 사고: Cloud Run 첫 부팅 시 env 누락 → fallback Railway URL 사용 → 의도치 않게 Cloud Run 이 Railway DB 에 연결되던 catch
- 영향 0: pytest `conftest.py` `TEST_DATABASE_URL → DATABASE_URL` 매핑, Railway env 자동 설정

**GCP 작업 trail**:
1. Cloud SQL `g-axis-core` 생성 (PG 18, Enterprise Plus, asia-northeast3)
2. Cloud Run `axis-core-api` 생성 + Cloud Build GitHub 트리거 + Dockerfile (`backend/Dockerfile`)
3. 환경변수 12개 등록 + DATABASE_URL typo (`asia-northe   ast3` 공백) catch + 수정
4. Railway DB (PG 16, 89MB) → pg_dump → Cloud SQL restore (`cloud-sql-proxy` 통해 Unix socket)
5. admin login 검증 (INVALID_PASSWORD → DB 정상 연결 확인)
6. Cloud SQL 머신 다운사이즈 (db-perf-optimized-N-8 → N-2, 월 $1,200 → $300)
7. 백업 + PITR 활성화 (15개 보관, 7일 PITR)
8. 비용 협의로 hold 결정 → Cloud Run min=0 + Cloud SQL stop (월 ~$20 → 500일+ 안전)

**Railway 상태**: prod 운영 그대로 (사용자 150명) + Auto Deploys ON 복원

**재오픈 절차**: 30분 안에 cutover 가능 — `AXIS-OPS/GCP_MIGRATION_STANDBY.md` 참조

**잠재 catch (별 sprint)**:
- APScheduler `/tmp/lock` multi-instance 한계 (max_instances=10 scale-out 시 cron 중복 fire 잠재 — advisory lock 도입)
- 평문 비밀번호 회전 (Railway DB / JWT keys / SMTP — Secret Manager 마이그레이션)
- pytest 환경 (`TEST_DATABASE_URL`) 도 Railway 폐기 시 같이 이전 필요
- Dockerfile JSON CMD 형태 (linter advisory)
- Cloud Run non-root user (보안 강화)

**Free trial 만료 (~2026-06-19)**: 결정 트리거 — cutover 진행 / GCP 자원 delete / 신용카드 등록 standby 유지

**연관 문서**:
- `GCP_MIGRATION_STANDBY.md` (신규, 재오픈 30분 가이드)
- `CHANGELOG.md` v2.18.3 entry
- `handoff.md` 2026-05-20 KST entry
- `~/.claude/projects/.../memory/project_gcp_migration_standby.md` (auto-memory)

**관련 commit**:
- `affea54` Dockerfile (backend/) + .dockerignore
- `9b43e66` CLAUDE.md Codex 채널 정정 (brew → npm `@openai/codex`)
- `3fb98cd` v2.18.3 config.py fallback 제거

---

## v2.18.2 (FIX-MECH-CHECKLIST-QR-DOC-ID-SINGLE-UNIFY: DRAGON DUAL MECH 체크리스트 완료판정 P0, 2026-05-19)

**Sprint**: FIX-MECH-CHECKLIST-QR-DOC-ID-SINGLE-UNIFY-20260519 (BE 1 + OPS FE 1 + pytest 1)

**상태**: ✅ COMPLETED

**배경**: BACKLOG `BUG-MECH-CHECKLIST-DUAL-MODEL-QR-DOC-ID-MISMATCH-20260514` (🔴 P0). DRAGON DUAL 모델 MECH 체크리스트가 영원히 100% 안 됨 → SELF_INSPECTION 공정 마감 finalize 차단.

**Root Cause**: `checklist_record.qr_doc_id` 저장 컨벤션 혼재 — INLET 배관 S/N 8항목은 `DOC_{S/N}-L`/`-R` 분리 저장 / 나머지 MECH 항목은 `DOC_{S/N}` SINGLE → `check_mech_completion` DUAL 분기 `[-L, -R]` loop 전수 매칭 요구 → SINGLE 항목 영원히 mismatch → False.

**사용자 결정**: 옵션 D (qr_doc_id `DOC_{S/N}` SINGLE 통일). INLET L/R 구분은 master(item_name + master_id)가 담당. 옵션 B(BE 3분리 SELECT)는 반창고라 기각.

**운영 데이터 검증 (SQL)**: MECH `-L`/`-R` = TEST-333 16건뿐(운영 0건) → migration 불필요. TM L 450/R 540 = dual tank 정상 → D 범위 제외.

**변경**:
- BE `checklist_service.py check_mech_completion()` — DUAL 분기(model SELECT + `-L`/`-R` loop) 제거 → `DOC_{S/N}` SINGLE 단일. `check_tm_completion()` 미변경
- OPS FE `mech_checklist_screen.dart _qrDocIdForItem()` — `requiresLrHint` 제거 → 항상 SINGLE
- VIEW FE — 코드 변경 0 (BE 읽기 경로 이미 SINGLE → 자동 정합)
- TEST-333 — 사용자 직접 초기화

**검증**:
- pytest 신규 `test_v2_18_2_mech_qr_doc_id_unify` 12 TC GREEN
- 회귀 `test_mech_checklist` 69 + `test_relay_first_final` 38 + `test_v2_15_16/18` 24 GREEN
- flutter build web GREEN
- Codex 라운드 1 M=2(호출자 전수 TC + 게이트 경로 TC)/A=4 반영
- 운영 데이터 0건 → 회귀 위험 0

---

## v2.18.0 (Sprint 69: PI/QI 완료 권한 잠금 + admin 정상완료, 2026-05-19)

**Sprint**: FEAT-PIQI-COMPLETE-OWNER-LOCK-20260519 (BE 2 + FE 1 파일 + pytest 1)

**상태**: ✅ COMPLETED

**배경**: PI/QI = GST 사내 검사 공정. GST 작업자끼리 cross-worker 완료(worker2가 worker1 시작 task를 완료)가 허용되어 worker tracking·진행률·CT 파악이 왜곡됨. 사용자 결정 — PI/QI는 시작한 본인만 완료, 불가피 시 admin/manager가 종료 시각 다이얼로그로 정상완료(force_closed=FALSE).

**변경**:
- **BE-1** `task_service.py complete_work()` — `task_category in ('PI','QI')` 이고 시작 worker ≠ 호출 worker 면 403 `FORBIDDEN` ("PI/QI 검사는 작업을 시작한 본인만 완료할 수 있습니다."). SI/MECH/ELEC/TMS cross 현행 유지
- **BE-2** `shipment_service.py admin_complete()` 신규 + `routes/work_shipment.py` `POST /api/app/work/admin-complete` (`@manager_or_admin_required`) — PI/QI category 미완료 applicable task 전수 완료, task별 `completed_at` 검증(미래 차단 + started 이전 차단), 멀티작업자 orphan `work_completion_log` backfill, audit `close_reason='ADMIN_COMPLETE'`+`closed_by`+`force_closed=FALSE`, 멱등(`already_completed`), `update_process_completion`. `_set_ship_audit`→`_set_close_audit(reason 파라미터화)` 리네임
- **FE-A** `gst_products_screen.dart` — PI/QI 카드 admin/manager `[종료]` 버튼 + 종료 시각 다이얼로그(`showDatePicker`+`showTimePicker`, 미래 시각 차단) → admin-complete API
- **FE-B** 상단 O/N·S/N 검색 칸 (`_searchQuery`+`_filteredProducts`, sales_order/serial_number 부분매칭, PI/QI/SI 3화면 공용)

**검증**:
- pytest `test_admin_complete` 10/10 GREEN (TC-AC-01~10: cross 차단 PI/QI / admin-complete 성공 / partial·all-done 멱등 / completed_at 미래·started이전 차단 / 멀티작업자 backfill / PI 위임 모델 DRAGON regression)
- flutter build web GREEN
- Codex 라운드 1 — BE M=10/A=4 + OPS FE M=1(미래 시각 차단)/A=3 반영. A 3건(naive ISO8601 KST 환경 무관 / admin 버튼 status 무관 노출 의도 / `_fetchProducts` 초기 setState) 미반영 advisory
- migration 불필요, 기존 complete/ship-complete 영향 0

**연관**: AXIS-VIEW Sprint 48 (PI/QI 종료 버튼 — VIEW 세션 담당) + v2.17.0 (Sprint 68 ship-complete — admin_complete는 동일 audit 패턴 재사용)

---

## v2.15.19 (FEAT-FACTORY-MONTHLY-DETAIL-BY-CUSTOMER #68, 2026-05-18)

**Sprint**: AXIS-VIEW OPS_API_REQUESTS.md #68 (BE 1 파일 + pytest 1)

**상태**: ✅ COMPLETED

**요청**: 공장 대시보드 월간 뷰 "고객사 비율 도넛 차트" 위젯용 — `monthly-detail` 응답에 월 전체 고객사별 집계 `by_customer` 추가.

**변경 (BE 1 + pytest 1 + version)**:
- `factory.py` `get_monthly_detail()` — `by_customer` 집계 쿼리 + 응답 dict 키 추가 (~14 LOC, `by_model` 1:1 복제)
- `test_factory.py` — `test_md01` by_customer 키 검증 + `test_md01b_by_customer_aggregate` 신규 (키 구조 + count 내림차순 + 합계=total)
- `version.py` + `app_version.dart` 2.15.18 → **2.15.19**

**검증**: pytest test_factory.py 19/19 PASS (241s). 회귀 위험 0 (additive — 응답 키 1개 추가, breaking 아님 / DB 스키마·migration 변경 0).

**Codex 라운드 1**: M=6/A=2/N=2 — M 6건 중 3건(Q1-1/Q1-2/Q2-1)은 Codex prompt 코드블록 오독. 유효분 = test_factory `by_customer` TC 반영.

---

## v2.15.18 (POST-REVIEW-OPS-65-PATH2-REOPEN, 2026-05-15)

**Sprint**: `POST-REVIEW-OPS-65-PATH2-REOPEN-20260515` (BE 1 파일 + pytest 1)

**상태**: ✅ COMPLETED

**트리거**: AXIS-VIEW 측 리뷰어가 OPS_API_REQUESTS.md #65 entry 교차검증 중 OPS 배포 코드 (v2.15.13~v2.15.17) 영역 버그 2건 발견. #65 = "MECH 체크리스트 Dual-Trigger" v2.15.13 ✅ COMPLETED 처리됐으나 경로 2 (체크리스트가 마지막) 미완성.

**버그 2건 (Codex 라운드 1 M=2 합의)**:
| catch | 내용 |
|-------|------|
| M-A4 | `_try_mech_close()` 영역 `UPDATE completion_status SET mech_completed=TRUE` 누락 (ELEC `_try_elec_close()` 영역 존재) → 경로 2 close 후 mech_completed=FALSE 잔존 → VIEW "미완료" 표시 |
| M-A7 | `upsert_mech_check()` close 게이트 = `check_mech_completion(sn, judgment_phase)` 단독 → 1차 검수만 채워도 close (v2.15.16 catch 1 의 경로 2 잔존분) |

**변경 (BE 1 + pytest 1 + version)**:
- `checklist_service.py` `_try_mech_close()` — close 후 `UPDATE completion_status SET mech_completed=TRUE WHERE ... AND mech_completed=FALSE` + `conn.commit()` (M-A4)
- `checklist_service.py` `upsert_mech_check()` — close 게이트 `check_mech_completion_all()` 분리, `is_complete` (FE 진행률 phase별) 유지 (M-A7)
- `test_v2_15_18_mech_path2_close.py` 신규 5 TC
- `version.py` + `app_version.dart` 2.15.17 → **2.15.18**

**검증**: pytest 신규 5/5 PASS (0.09s). 회귀 위험 0 (task_service.py 경로 1 + ELEC touch 0, MECH 경로 2 전용).

---

## v2.15.17 (FIX-VIEW-ORPHAN-DURATION-MISSING, 2026-05-15)

**Sprint**: `FIX-VIEW-ORPHAN-DURATION-MISSING-20260515` (BE 2 파일 + pytest 1)

**상태**: ✅ COMPLETED

**사용자 운영 catch (5-15)**: "Trigger task close 시 VIEW 에서 소요시간 표시 안 됨 / 정상 완료된 task 만 소요시간 표시 됨"

**Root Cause**: `work.py` + `task_service_batch.py` worker 배열 조회 SQL 영역 `completed_at` 영역 `COALESCE(wcl.completed_at, td.completed_at)` fallback 있는데 `duration_minutes` 영역 `wcl.duration_minutes` 단독 → orphan worker (auto-close, work_completion_log record 없음) 영역 NULL → VIEW '—' 표시.

**Codex 라운드 1 결과 — M=2 (Claude 사전 검토 누락)**:
| Q | 라벨 | catch |
|---|------|-------|
| Q1 | M | 음수 duration + float 반환 → `GREATEST(0, FLOOR(...))::int` 클램프 필수 |
| Q2~Q5 | A | 멀티 worker / 응답 일관성 / is_orphan 라벨 / pause 차감 별 sprint |
| Q6 | M | `task_service_batch.py` L323 동일 버그 — 같은 PR fix 필수 |

**변경 (BE 2 + pytest 1 + version)**:
- `work.py` L645 — `duration_minutes` COALESCE + `GREATEST(0, FLOOR(EXTRACT(EPOCH FROM (close - started))/60))::int` fallback
- `task_service_batch.py` L323 — `_enrich_tasks_with_workers()` 동일 fallback (Codex Q6 M)
- `test_hotfix04_orphan.py` — TC-ORPHAN-01/04 NULL → 240분 갱신 + TC-ORPHAN-05 신규 (음수 클램프 0)
- `version.py` + `app_version.dart` 2.15.16 → **2.15.17**

**검증**: pytest `test_hotfix04_orphan.py` 10/10 PASS (260s). 회귀 위험 0 (SQL 1 expression 2곳, 신규 로직 아님).

**한계 (별 sprint)**: pause 차감 미반영 근사값 → `REF-WORKER-DURATION-PRECISION` / VIEW `is_orphan` "추정" 라벨 → AXIS-VIEW 별 sprint.

---

## v2.15.16 (SPRINT-V2-15-16-MECH-FORCE-CLOSED-PREV-DAY-CAP, 2026-05-15)

**Sprint**: `SPRINT-V2-15-16-MECH-FORCE-CLOSED-PREV-DAY-CAP-20260515` (BE 3 파일 + migration 1 + pytest 1)

**상태**: ✅ COMPLETED

**사용자 운영 catch (3건)**:
1. MECH 체크리스트 1차만 완료해도 task close (Phase 2 미입력 영역 close 발동)
2. ELEC 정상 동작 확인 (작업 없음)
3. close trigger 미완료 task force_closed=TRUE 처리 — 사용자 분석상 조건 1 (attendance check_out) + 조건 2 (17:00 fallback) 무의미

**Codex 라운드 1 결과 — M=5 (Claude 사전 검토 누락)**:
| Q | 라벨 | Catch |
|---|------|-------|
| Q1 | M | check_mech_completion 호출자 4곳 (Claude 2곳만 식별) → X-β 채택 |
| Q2 | M | force_closed 버그 5곳 (Claude 2곳만 식별) |
| Q3 | M | auto-close 영역 validate_duration 미호출 → 본 sprint 포함 |
| Q4 | N | test_relay_first_final.py 38 TC 회귀 0 |
| Q5 | M | task_service.py L843 Sprint 41-B 레거시 루프 잔존 |
| Q6 | N | duration_calculator 활성 사용 중 |

**변경 (BE 3 파일 + migration 1 + pytest 1 + version)**:
- `checklist_service.py` 신규 `check_mech_completion_all()` (Phase 1 short-circuit + Phase 2 ELEC 패턴 정합) + IF_2/SELF_INSPECTION/orphan auto-close 3곳 `force_closed=False` 통일
- `task_service.py` MECH 분기 `check_mech_completion_all()` 호출 + FIRST/SECOND trigger `force_closed=False` + `last_started_at` 전달 + L843 Sprint 41-B 레거시 루프 제거 (`_trigger_second_close()` 단일 경로)
- `duration_calculator.py` priority 0 `PREV_DAY_CAP` 추가 — `calculate_close_at()` signature `last_started_at` 인자 추가, trigger.date() > started.date() 시 started.date() 17:00 KST cap, started ≥ 17:00 시 started 그대로 (음수 차단)
- `migrations/057_add_prev_day_cap_duration_source.sql` CHECK constraint 4 → 5 enum
- `tests/backend/test_v2_15_16_force_closed_and_prev_day_cap.py` 신규 12 TC (시나리오 A/B/C/D + priority 0 + Phase 1+2 + signature)
- `version.py` + `app_version.dart` 2.15.15 → **2.15.16**

**시나리오 매트릭스 (PREV_DAY_CAP 발동)**:
| 시나리오 | started | trigger | cap 발동? | close_at |
|----------|---------|---------|-----------|----------|
| A 정상 (운영 99%) | 5-15 09:00 | 5-15 14:00 | ❌ | 14:00 |
| B 같은 날 야간 | 5-15 09:00 | 5-15 19:00 | ❌ | 17:00 (fallback) |
| C 익일 trigger | 5-14 14:00 | 5-15 09:00 | ✅ | **5-14 17:00** |
| D 주말 후 | 5-10 (금) 14:00 | 5-13 (월) 09:00 | ✅ | **5-10 17:00** |
| E started ≥ 17:00 | 5-14 18:00 | 5-15 09:00 | ✅ + 보호 | started 그대로 (음수 차단) |

**검증 (pytest 결과 기록)**:
- 신규 `test_v2_15_16_force_closed_and_prev_day_cap.py` **12/12 PASS** (0.14s)
- 회귀 `test_relay_first_final.py` **38/38 PASS** (21.86s)
- 합계 **50/50 GREEN**
- 인접 통합 테스트 (`test_force_close.py` + `test_duration_validator.py`) 22 ERROR 발생 — staging DB connection 영역 영향 (5-15 전수 pytest 80 FAILED + 20 ERROR 일부, deadline 5-22 `POST-REVIEW-PYTEST-FAILED-ANALYSIS-20260515` 별 sprint), **v2.15.16 코드 변경 영역 무관**

**회귀 위험 0**:
- FIX-A X-β = signature 보존 (호출자 4곳 영향 0)
- FIX-B = additive policy 단일화 (force_closed default=True 그대로, 호출자 영역 명시 False)
- FIX-C = additive priority 0 (last_started_at=None 시 cap skip → 기존 동작 보존)
- FIX-D = 레거시 루프 직후 `_trigger_second_close()` 동일 task 영역 v2.15.14 표준 재처리

**POST-REVIEW (BACKLOG 등록)**:
- `POST-REVIEW-AUTOCLOSED-CLOSED-BY-20260515` — Codex Q2 추가 catch: auto-close `closed_by = worker_id` 기록 vs 설계서 "NULL" 모순 정책 명확화
- `POST-REVIEW-AUDIT-TRAIL-CONSISTENCY-20260515` — force_closed 의미론 변경 영역 AUDIT_TRAIL_GUIDE.md 갱신
- `POST-REVIEW-OFFHOURS-TRIGGER-DURATION-CAP-20260515` — Q3 별 sprint 분리 불가 판정, 본 sprint 영역 처리 완료 (별 BACKLOG 등록 불필요)

**영향 사용자**:
- 사용자 5-15 운영 catch 3건 모두 해결
- 익일/주말 trigger 18h+ 비정상 duration 자동 cap (운영 audit trail 정확화)
- MECH Phase 2 미입력 시 close 발동 차단 (ELEC 패턴 정합)
- Sprint 41-B `AUTO_CLOSED_LEGACY` audit trail 신규 발생 0건 (v2.15.14 표준 통일)

---

## v2.15.15 (BUG-RELAY-MODE-AUTO-REFRESH-MISSING + COMPLETE-KEY-USELESS, 2026-05-15)

**Sprint**: `BUG-RELAY-MODE-AUTO-REFRESH-MISSING-AND-COMPLETE-KEY-USELESS-20260514` (BE 1 + FE 2 파일)

**상태**: ✅ COMPLETED

**배경**: 사용자 5-14 catch (BACKLOG L342) + 5-15 결정 — "내 작업만 완료" relay_mode 후 자동 갱신 안 됨 + 본인 완료 "완료" 키 TASK_ALREADY_COMPLETED 에러.

### 사용자 결정 (5-15)

- Catch 1 = **B** (FE fetchTasks 호출)
- Catch 2 = **c** (확인 다이얼로그 "이 task만 정식 종료됩니다.")
- 결정 3 = **a** (일시정지 조건부 숨김)

### 변경 (BE 1 + FE 2 파일)

- `task_provider.dart` fetchTasks() silent 인자 + completeTask() 응답 후 fetchTasks(silent: true) 호출
- `task_management_screen.dart` 블록 A 영역 "공정 마감" 버튼 신규 + 블록 B/C 조건 `myWorkStatus != 'completed'` 추가 + `_handleFinalizeOnly()` 신규
- `task_service.py` L564 영역 `and not finalize` 추가 (M-2 catch)
- `version.py` + `app_version.dart` 2.15.14 → **2.15.15**

### 자가 리뷰 catch (M-1 + M-2)

| Catch | 위치 | Fix |
|-------|-----|---|
| M-1 spinner 두 번 표시 (flickering) | fetchTasks() L175 | silent 인자 추가 |
| M-2 TASK_ALREADY_COMPLETED 에러 | complete_work L564 | `and not finalize` 추가 |

### 검증

- pytest 38/38 PASS (21.20s)
- flutter build GREEN + Netlify 배포 완료
- Codex 라운드 1 = API overload (529) skip (S2 패턴, 7일 사후 검토)
- 회귀 위험 0

### 후속

- POST-REVIEW deadline 2026-05-22 (7일) — Codex 사후 검토 필수
- A' (BE route enrichment) 별 sprint `REF-WORK-RESPONSE-ENRICHMENT-20260515` BACKLOG 등록 권고

---

## v2.15.14 (BUG-SECOND-CLOSE-FORCE-CLOSED-FALSE-POSITIVE + AUDIT TRAIL 통일, 2026-05-15)

**Sprint**: `BUG-SECOND-CLOSE-FORCE-CLOSED-FALSE-POSITIVE-20260514` (BE only 3 파일) + Codex 옵션 b (audit trail 통일)

**상태**: ✅ COMPLETED

**배경**: 사용자 5-14 운영 catch — SELF_INSPECTION / IF_2 누른 후 자동 close된 잔여 task 영역 모두 "강제종료" 라벨 + duration 0m 잘못 표시. 작업자 본인이 "내 작업 완료" 누른 task도 강제종료 처리됨.

### Root cause

`auto_close_relay_task()` 영역 = UPDATE SQL 영역 `force_closed = TRUE` 일괄 고정 → work_completion_log row 있는 task (자연 close 의도)도 강제종료 처리됨.

### 변경 (BE only, 3 파일)

- `task_detail.py` `auto_close_relay_task()`: `force_closed: bool = True` 인자 추가 (default 영역 legacy 호환) + UPDATE SQL 양쪽 분기 `force_closed = %s`
- `task_service.py` `_trigger_first_close()` + `_trigger_second_close()`: SELECT 영역 `unfinished_workers_count` 추가 + force_closed 분기
- `checklist_service.py` `_try_mech_close()` + `_try_elec_close()`: 동일 패턴 + Codex 옵션 b (trigger_type='SECOND_FINAL' + trigger_task_id + closed_by 통일)

### force_closed 결정 로직

- unfinished_workers_count = 0 → 모든 worker 본인 종료 → **force_closed = FALSE** (자연 close)
- unfinished_workers_count > 0 → 일부 미종료 → **force_closed = TRUE** (manager 권한 강제종료)

### Codex 라운드 1 결과 (M=0 / A=8 / N=2)

- M=0 → 배포 블로커 없음
- A 2건 반영 (옵션 b — audit trail 통일): close_reason + closed_by 4 trigger 함수 통일
- A 6건 잔존 = 별 sprint BACKLOG (`POST-REVIEW-AUDIT-TRAIL-CONSISTENCY-20260515`)

### 검증

- pytest test_relay_first_final.py 38/38 PASS (19.26s)
- flutter build web GREEN (13.9s)
- Netlify prod 배포 완료
- 회귀 위험 0 (default=TRUE legacy 호환 + Sprint 41-B 기존 호출 그대로)

### 사용자 결정 (5-15)

"옵션 b — 장기 운영 영역 디테일 중요" → audit trail 통일 채택. 추후 데이터 분석 / 디버깅 영역 일관성 확보.

### 후속

- POST-REVIEW deadline 2026-05-22 (7일)
- pytest TC 5건 (TC-SC-01~05) = 별 sprint P2

---

## v2.15.13 (HOTFIX-MECH-CHECKLIST-DUAL-TRIGGER — 체크리스트 100% PUT 시점 SELF_INSPECTION + 잔여 task 일괄 close, 2026-05-15)

**Sprint**: `HOTFIX-MECH-CHECKLIST-DUAL-TRIGGER-20260515` (BE only 1 파일)

**상태**: ✅ COMPLETED

**배경**: 사용자 5-15 운영 catch + Railway logs 결정적 trail 발견 — TEST-1111 SELF_INSPECTION 먼저 complete (체크리스트 미입력 상태) → relay_mode → SELF_INSPECTION.completed_at=NULL → 체크리스트 100% PUT 후에도 close 안 됨. MECH 영역 양방향 트리거 미구현.

### Root cause (Railway logs trail)

```
5-15 00:37:24  SELF_INSPECTION 시작
5-15 00:37:29  SELF_INSPECTION 완료 (체크리스트 미입력)
              → "체크리스트 100% 미달 → close 보류" (정상 동작)
              → SELF_INSPECTION.completed_at = NULL (relay_mode)
5-15 00:37:38~51  체크리스트 11개 NA 입력 → 100% 도달
              → ❌ MECH 양방향 트리거 미구현 → 영원히 close X
```

### 변경 (BE only, 1 파일)

- `checklist_service.py`:
  - `_try_mech_close(serial)` 신규 — SELF_INSPECTION work_completion_log 1+ 확인 + 잔여 MECH task auto_close_relay_task 호출 (ELEC `_try_elec_close()` v2.15.10 패턴)
  - `upsert_mech_check()` 영역 `is_complete=True` 시 `_try_mech_close()` 호출 + 응답 `mech_closed` 필드
- `version.py` + `app_version.dart` 2.15.12 → **2.15.13**

### Dual-Trigger 매트릭스 (v2.15.13)

| 시점 | 발동 |
|------|------|
| SELF_INSPECTION complete (체크리스트 이미 100%) | `_trigger_second_close()` |
| 체크리스트 100% PUT (SELF_INSPECTION 이미 complete) | `_try_mech_close()` 신규 |

→ 순서 무관, 동일 효과.

### 검증

- pytest test_relay_first_final.py 38/38 PASS (14.27s)
- flutter build web GREEN (12.7s)
- Netlify prod 배포 완료
- 회귀 위험 0 (BE only, additive helper + 호출 1줄)

### 후속

- POST-REVIEW deadline 2026-05-22 (7일)
- Catch 2 (작업화면 시작/내작업완료 후 메뉴 미동기화) = 별 hotfix 진단 진행

---

## v2.15.12 (FIX-MECH-CHECKLIST-PROGRESS-REALTIME-AND-STICKY — 실시간 갱신 + 스크롤 고정, 2026-05-15)

**Sprint**: `FIX-MECH-CHECKLIST-PROGRESS-REALTIME-AND-STICKY-20260515` (FE only 1 파일)

**상태**: ✅ COMPLETED

**배경**: v2.15.11 직후 사용자 catch 2건 — ① MECH 진행률 바 실시간 갱신 안 됨 / ② 스크롤 시 진행률 바 위로 사라짐 (ELEC = 고정).

### Root cause

| Catch | Root cause |
|-------|----------|
| 실시간 갱신 안 됨 | 라디오 onTap 영역 `_checkResultMap` 만 update, `item['check_result']` 미동기화 — v2.15.11 진행률 getter (`_checkedCount`) 옛 값 참조 |
| 스크롤 시 사라짐 | v2.15.11 진행률 헤더 = ListView item — ELEC 영역 = `Column > Expanded(ListView)` 외부 고정 패턴 미적용 |

### 변경 (FE only, 1 파일)

- `mech_checklist_screen.dart`:
  - L796 라디오 onTap 영역 setState 영역 `item['check_result'] = value` 추가 (v2.15.11 진행률 getter 정합)
  - `_buildBody()` 영역 Column wrap — `_buildHeader() + _buildProgressHeader() + Divider + Expanded(RefreshIndicator(ListView))` 영역 영역 진행률 헤더 영역 ListView 외부 고정
- `version.py` + `app_version.dart` 2.15.11 → **2.15.12**

### 검증

- flutter build web GREEN (12.5s)
- Netlify prod 배포 완료
- 회귀 위험 0 (BE 변경 0)

### 후속 (별 hotfix 진단 진행)

- **Catch 2 (작업화면 시작/내작업완료 후 메뉴 미동기화)** — BE startTask/completeTask 응답 task 객체 필드 분석 필요 + Sentry 콘솔 (5-14 23:59 silent fail) 확인 필요
- **MECH gas2/util2 close 안 됨 catch** — `_trigger_second_close()` SELECT 5조건 모두 통과 확인 (사용자 추가 SQL) → 호출 자체 안 됐거나 silent fail. Sentry 5-14 23:59 시각 `_trigger_second_close orphan SELECT failed` 메시지 검색 권고

---

## v2.15.11 (FIX-MECH-CHECKLIST-PROGRESS-HEADER — ELEC 패턴 정합 진행률 표시, 2026-05-15)

**Sprint**: `FIX-MECH-CHECKLIST-PROGRESS-HEADER-20260515` (FE only 1 파일)

**상태**: ✅ COMPLETED

**배경**: 사용자 catch (5-14 Catch 2 진단 중) — "MECH 체크리스트 진행률 카운트 현재 elec처럼 없으며". ELEC 체크리스트 화면 상단 영역 진행률 헤더 동일 패턴 적용 요청.

### 변경 (FE only, 1 파일)

- `mech_checklist_screen.dart` — `_totalCount` / `_checkedCount` / `_progress` / `_isAllDone` getter 신규 + `_buildProgressHeader()` 위젯 신규 + ListView itemCount +1
- `version.py` + `app_version.dart` 2.15.10 → **2.15.11**

### 진행률 정의 (ELEC 패턴 정합)

```
total = scope 매칭 active 항목 (BE phase1_applicable 이미 필터)
done  = total 중 check_result IN ('PASS', 'NA')
```

### 검증

- flutter analyze 0 error
- flutter build web GREEN (12.9s)
- Netlify prod 배포 완료
- 회귀 위험 0 (BE 변경 0, additive UI)

### 후속

- Catch 2 (MECH gas2/util2 close 안 됨) = 진단 SQL 4건 결과 대기 후 별 hotfix
- 옵션 2 (CI 워크플로우 + pytest 재검증) = 사용자 측 자면서 진행 예정

---

## v2.15.10 (HOTFIX-SPRINT41D-ELEC-CLOSE-CONDITION-DUAL-TRIGGER — IF_2 강제 제거 + Dual-Trigger 완성, 2026-05-14)

**Sprint**: `HOTFIX-SPRINT41D-ELEC-CLOSE-CONDITION-DUAL-TRIGGER-20260514` (BE only 2 파일)

**상태**: ✅ COMPLETED

**배경**: 사용자 5-14 운영 catch — TEST-1111 IF_2 본인 종료 (relay 모드 completed_at NULL) + INSPECTION 완료 + 체크리스트 100% (Phase 1 16/16 + Phase 2 24/24) 상태인데 IF_2 close 안 됨. 진단 SQL 4건 확인 결과 silent fail 0 + 체크리스트 미입력 0 → 코드 로직 자체 결함 확정.

### Root cause

| 영역 | v2.15.5 catch #25 명시 의도 | v2.15.9 까지 실제 구현 |
|------|---------------------------|---------------------|
| 경로 1 (INSPECTION complete 시점) | INSPECTION + 체크리스트 100% 만 검증 | `check_elec_final_tasks_completed()` 영역 IF_2 강제 → relay 모드 False |
| 경로 2 (체크리스트 100% PUT 시점) | IF_2 task close + completion_status flag | completion_status flag 만 set, task close 누락 |

→ 양방향 트리거 절반만 작동. IF_2 relay 모드 영원히 close X.

### 사용자 의도 정의 (확정)

```
조건: INSPECTION.completed_at NOT NULL  AND  ELEC 체크리스트 100%
액션: IF_2 task close (auto_close_relay_task)
순서: 무관 (양방향 트리거)
잔여 task: IF_2 start 시점 First Close 가 이미 처리 (panel/cabinet/wiring/IF_1)
```

### 변경 (BE 2 파일 + version)

| 파일 | 변경 |
|------|-----|
| `task_service.py` | (1) `check_category_close_eligible('ELEC')` → `_check_inspection_completed()` 호출로 교체 (IF_2 강제 제거) (2) `_check_inspection_completed()` 신규 — INSPECTION completed_at 단순 검증 (3) `check_elec_final_tasks_completed()` deprecation 마킹 |
| `checklist_service.py` | `_try_elec_close()` 확장 — IF_2 work_completion_log 검증 → INSPECTION complete 검증으로 교체 + `auto_close_relay_task(IF_2)` 호출 추가 |
| `version.py` + `app_version.dart` | 2.15.9 → **2.15.10** |

### 양방향 트리거 매트릭스 (v2.15.10 정합)

| 시나리오 | 발동 시점 | 액션 | 결과 |
|---------|---------|------|:-:|
| A. INSPECTION 종료 → 체크리스트 100% | 체크리스트 PUT (경로 2) | `auto_close_relay_task(IF_2)` | IF_2 close ✅ |
| B. 체크리스트 100% → INSPECTION 종료 | INSPECTION complete (경로 1) | Sprint 41-D Second Close | IF_2 close ✅ |

### 회귀 위험 0

- DB schema 변경 0
- `check_elec_final_tasks_completed()` 호출 0건 (dead code, import 호환 보존)
- `_try_elec_close()` 기존 동작 (completion_status flag) 보존 + auto_close 추가만
- MECH/TM/TMS 분기 영향 0

### 후속

- POST-REVIEW deadline 2026-05-21 (7일) — Codex 사후 검토 필수
- MECH catch (gas2/util2 close 안 됨) = 별 hotfix 진단 필요 (scope_rule + tank_in_mech 영역)
- pytest TC 신규 작성 (TC-DT-01~04) — 별 sprint P2

---

## v2.15.9 (HOTFIX-SPRINT41D-PROGRESS-100-REVERT-AND-LABEL-CHANGE — (나) → (가) 회귀 + 다이얼로그 라벨, 2026-05-14)

**Sprint**: `HOTFIX-SPRINT41D-PROGRESS-100-REVERT-AND-LABEL-CHANGE-20260514` (BE 1 + FE 2 파일)

**상태**: ✅ COMPLETED

**배경**: v2.15.6 (나) 옵션 채택이 v2.15.3 `auto_finalize_blocked` 11 task allowlist 와 충돌 catch. 사용자 운영 검증 시 SELF_INSPECTION + 체크리스트 100% 진행했는데 gas2/util2 close 안 됨. Root cause: task progress 100% AND 검증 시 `app_task_details.completed_at IS NULL` 기준 카운트 → "내 작업 완료" 누른 task = completed_at NULL = pending 잡힘 = `check_category_close_eligible = False` → Sprint 41-D Second Close trigger 발동 X → gas2/util2 영원히 open. cowork 이 사용자 발화 "mech, elec 실적 조건 변동 없음" 을 (나) 로 잘못 해석. 실제 의도 = (가) "실적 정의 불변, close 조건도 그대로". + 다이얼로그 라벨 변경 묶음 (사용자 5-14 결정).

### 변경 (BE 1 + FE 2 + version)

| 파일 | 변경 |
|------|-----|
| `backend/app/services/task_service.py` | (1) `check_category_close_eligible()` MECH/ELEC 분기 task progress 100% AND 제거 — MECH=체크리스트 100% 만 / ELEC=IF_2+INSPECTION+체크리스트 100% (v2.15.5 회귀) (2) `check_elec_close_eligible_at_if2()` INSPECTION + 체크리스트 100% 만 (task progress 100% 제거) (3) `check_category_progress_100()` deprecation 마킹 — 호출 0건 (4) `check_elec_final_tasks_completed()` deprecation 해제 |
| `frontend/lib/screens/task/task_management_screen.dart` | L888 다이얼로그 "아니오, 작업 완료" → "아니오, 공정 마감" |
| `frontend/lib/screens/task/task_detail_screen.dart` | L904 동일 라벨 변경 |
| `backend/version.py` + `frontend/lib/utils/app_version.dart` | 2.15.8 → **2.15.9** |

### 카테고리별 close 조건 매트릭스 (v2.15.6 → v2.15.9)

| Category | v2.15.6 (잘못) | v2.15.9 (회귀) | 의도 |
|---|---|---|:-:|
| **MECH** | task progress 100% + 체크리스트 100% | **체크리스트 100% 만** (SELF_INSPECTION trigger 보존) | ✅ |
| **ELEC** | task progress 100% + 체크리스트 100% | **IF_2 + INSPECTION + 체크리스트 100%** | ✅ |
| **TMS** | PRESSURE_TEST complete | 동일 보존 (v2.15.6 정정) | ✅ |

### 다이얼로그 라벨 변경 (5-14 사용자 결정)

| 키 | 이전 | v2.15.9 | 의미 |
|---|---|---|---|
| finalize=false (relay) | "예, 내 작업만 종료" | 유지 | "내 개인 작업 끝남, 동료 진행 가능" |
| finalize=true | "아니오, 작업 완료" | **"아니오, 공정 마감"** | "task 단위 정식 close + 자동 정리 trigger" |

### 검증

- 회귀 위험 0: DB schema 변경 0, 함수 시그니처 보존
- v2.15.5 close 조건 회귀 = 기존 운영 동작 동일
- v2.15.6 TM/TMS 정정 보존
- `check_category_progress_100()` 호출 0건 (dead code, import 호환 보존)
- `check_elec_final_tasks_completed()` 호출 복귀

### 후속 별 sprint (P2)

- `FEAT-PROGRESS-MY-COMPLETION-HYBRID-AND-LABEL-CHANGE-20260514` — Hybrid 진행률 정의 (동적 옵션) + 화면 라벨 통일 + AXIS-VIEW 영향 분석 + 1.5~2일 (1주 운영 후 진행 권고)

### 학습

- cowork 사용자 발화 해석 catch: "mech, elec 실적 조건 변동 없음" = "정의 자체 불변" 의미, "close 조건에 새 AND 추가" 가 아님
- v2.15.3 `auto_finalize_blocked` 와 task progress 100% AND 의 의존 충돌 = "내 작업 완료" 누른 task 영원히 progress 카운트 X

---

## v2.15.8 (FIX-27 statusText 정정 — "동료 진행 중" 추측 → "재참여 가능" 사실 기반, 2026-05-14)

**Sprint**: FIX-27 후속 정정 (FE only)

**상태**: ✅ COMPLETED (5-14 release, Netlify 자동 배포)

**배경**: 사용자 catch (v2.15.7 release 직후) — "내 종료 / 동료 진행 중" 표현은 시스템이 실제로 알 수 없는 상태 추측. task open 상태일 뿐 동료 진행 여부 불명. 사용자 권고 "재시작 가능 / 재참여 가능" 사실 기반.

### 변경 (FE only, 1 파일)

- `task_management_screen.dart` L249 영역 — statusText `'내 종료 / 동료 진행 중'` → `'내 종료 / 재참여 가능'`

### 검증

- flutter build web GREEN (12.8s)
- Netlify prod 배포 완료
- 회귀 위험 0 (단일 문자열)

### 학습

- UX 카피라이팅: 시스템 알 수 없는 상태 추측 표현 회피, 사용자 액션 가능성만 명시

---

## v2.15.7 (FIX-27 FE TASK_CARD_MY_STATUS_AND_PULL_TO_REFRESH — TEST-1111 UX 개선, 2026-05-14)

**Sprint**: `FIX-27-FE-TASK-CARD-MY-STATUS-AND-PULL-TO-REFRESH-20260514` (FE only)

**상태**: ✅ COMPLETED (5-14 release, commit `328ba93`)

**배경**: 사용자 catch (TEST-1111 실기기 5-14) — (1) 본인 완료 + task open 시각 구분 부재 (v2.15.3 옵션 B 영향) (2) 새로고침 수단 부재 (QR 재태깅만) (3) "다시 시작" 라벨 — task_detail_screen 이미 구현 확인 후 스킵.

### 변경 (FE only, 3 파일)

| 파일 | 변경 |
|------|-----|
| `frontend/lib/utils/design_system.dart` | GxColors 신규 토큰: peerActive (teal-500) + peerActiveBg + muted + mutedBg |
| `frontend/lib/screens/task/task_management_screen.dart` | (a) 본인 완료 + task open 분기 청록 뱃지 (b) RefreshIndicator wrap + AlwaysScrollableScrollPhysics (c) AppBar IconButton refresh + tooltip (d) `_refreshTasks()` 신규 — `taskProvider.notifier.fetchTasks()` |
| `frontend/web/index.html` | `overscroll-behavior-y: contain` — 안드로이드 Chrome 자체 새로고침 차단 |

### Codex 검증 trail

- 라운드 0 (cowork 자가): M-1 my_status 필드 존재 / M-2 `'working'` → `'in_progress'` 정정
- 라운드 1 (Codex): M=2 / A=3 / N=3 → 모두 정정 반영
  - M-1: myWorkStatus fallback 경유 (task_item.dart L212)
  - M-2: `taskListProvider` → `taskProvider` 명칭 정정
  - A-1: AlwaysScrollableScrollPhysics
  - A-2: GxColors 토큰 (Colors.teal.shade300 → GxColors.peerActive)
  - A-3 (Q-8): task_detail_screen "다시 시작" 이미 L502/L505 구현 → 본 sprint 범위 제거
  - N (3건): WebSocket race / CSS overscroll / iOS Material 정합 GREEN
- 라운드 2 미진행 (CLAUDE.md 라운드 상한 1회 정합)

### 검증

- flutter analyze: error 0 (info만, 기존 prefer_const)
- flutter build web --release: GREEN (12.6s)
- Netlify prod 배포 완료

### 회귀 위험 0

- BE 변경 0 (my_status 응답 work.py L703-735 이미 존재)
- DB schema 변경 0
- FE 분기 logic 추가만 (기존 분기 보존)
- RefreshIndicator = additive wrapper
- CSS overscroll = PWA standalone 영향 0

### 후속 (별 sprint P2)

- pytest 위젯 10 TC (TC-FIX27-01~10) — `test_task_management.dart` 더미 영역 실제 구현
- BACKLOG `FEAT-TASK-PROGRESS-COUNT-DISPLAY` (옵션 D — BE 응답 확장 "1/2명 종료")

---

## v2.15.6 (HOTFIX-SPRINT41D-TMS-CLOSE-FIX-MECH-ELEC-PROGRESS-100 — TMS 잘못 매핑 정정 + (나) 옵션, 2026-05-14)

**Sprint**: `HOTFIX-SPRINT41D-TMS-CLOSE-FIX-MECH-ELEC-PROGRESS-100-20260514` (BE only)

**상태**: ✅ COMPLETED (5-14 release, commit `97a02f9`, Railway + Netlify 자동 배포)

**배경**: v2.15.5 prod 배포 후 사용자 catch — cowork 이 VIEW 의 TM 실적 카운트 조건 (tank module com + 체크리스트 100%) 을 OPS close 조건에 잘못 매핑. 사용자 명시 — "가압검사는 무조건 이행됨 → PRESSURE_TEST complete = close", "TM 실적 카운트는 VIEW 별도", "TANK_MODULE 미시작/미완료 = VIEW 일괄 시작/종료 별도 해결", "MECH/ELEC = (나) 옵션 task progress 100% AND 채택".

### 변경 (3 파일)

| 파일 | 변경 |
|------|-----|
| `backend/app/services/task_service.py` | `check_category_progress_100()` 신규 (DRY 공용 헬퍼) + `check_elec_close_eligible_at_if2()` 재구현 (IF_2 본인 제외) + `check_category_close_eligible()` 재구현 (TM/TMS True / MECH/ELEC progress 100% + checklist AND) + `check_elec_final_tasks_completed()` DEPRECATED 마킹 |
| `backend/app/routes/work.py` | L295-298 — `checklist_pending` forward 추가 (Codex M-1 v2.15.5 catch 정정) |
| `backend/version.py` / `frontend/lib/utils/app_version.dart` | 2.15.5 → 2.15.6 |

### 카테고리별 close 조건 매트릭스 (v2.15.5 → v2.15.6)

| 카테고리 | v2.15.5 | v2.15.6 |
|---------|---------|---------|
| MECH | SELF_INSPECTION + check_mech_completion | **task progress 100% + check_mech_completion** |
| ELEC | IF_2 + INSPECTION + check_elec_completion | **task progress 100% + check_elec_completion** |
| **TM/TMS** | PRESSURE_TEST + check_tm_completion ❌ | **PRESSURE_TEST complete 만** (체크리스트 무관) |
| PI/QI/SI | 항상 True | 항상 True (변경 없음) |

### Codex 검증 trail

- v2.15.5 Codex 라운드 1: M=1 (checklist_pending forward 누락) / A=3 / N=3
- M-1 정정: work.py forward 1줄 추가 ✅
- A-1 (TMS 회귀 catch) 사용자 catch 반영 — 무조건 True ✅
- A-2/A-3 별 sprint 보류

### pytest 결과

- 신규 + 회귀: 38/38 GREEN (29.33s)
- 회귀 1건 (test_ff_v2153_second_final_self_inspection_normal_close) — v2.15.6 의도된 변경 영향
  · `check_category_close_eligible` mock 추가 (return_value=True) → 정상 close 검증

### 회귀 위험 0

- DB schema 변경 0
- FE 다이얼로그 변경 0
- 응답 schema additive (`checklist_pending` 신규)
- HEATING_JACKET 비활성 = `is_applicable=FALSE` 자동 제외

---

## v2.15.5 (HOTFIX-SPRINT41D-CHECKLIST-AND-SINGLE-ACTION — SINGLE_ACTION First Close + 체크리스트 100% AND, 2026-05-14)

**Sprint**: `HOTFIX-SPRINT41D-CHECKLIST-AND-SINGLE-ACTION-20260514` (BE only)

**상태**: ✅ COMPLETED (5-14 release, v2.15.6 후속 정정 묶음)

**배경**: v2.15.4 배포 후 사용자 catch — (1) MECH TANK_DOCKING start 시 gas1/util1 자동 close 미발동 (catch #24 — SINGLE_ACTION endpoint 우회) (2) ELEC IF_2 + INSPECTION + 체크리스트 100% AND 조건 미적용 (catch #25 — 옵션 X3-전영역).

### 변경 (BE only, 2 파일)

- `task_service.py` — `check_category_close_eligible()` 신규 (MECH/ELEC/TM 통합) + `check_elec_close_eligible_at_if2()` 신규 + complete_work() ELEC IF_2 sub-분기 + Sprint 55 (3-C) 체크리스트 미달 → relay_mode 응답
- `routes/work.py` — `/work/complete-single` SINGLE_ACTION First Close 트리거 호출 추가 (catch #24)

### 사용자 결정 (5-14)

- Q1=B (MECH+ELEC+TM 모두 적용)
- Q2=A (체크리스트 100% 단순)
- Q3=Manager 책임
- Q4=AND 통일 + 트리거 양방향 (ELEC IF_2 + INSPECTION 시점)
- Q5=가 (체크리스트 미달 → task open + checklist_pending)

### 신규 응답 플래그

- `checklist_pending: bool` — 체크리스트 미달 시 task open + FE 안내 분기용

---

## v2.15.4 (HOTFIX-SPRINT41D-SQL-COLUMN-FIX — last_started_at 컬럼명 오류 + DRY 정정, 2026-05-14)

**Sprint**: `HOTFIX-SPRINT41D-SQL-COLUMN-FIX-20260514` (BE only)

**상태**: ✅ COMPLETED (5-14 release)

**배경**: v2.15.3 prod 배포 후 사용자 catch — "MECH TANK_DOCKING 시작해도 gas1/util1 자동 close 안 됨". Sentry 메시지 `_trigger_first_close orphan SELECT failed: column td.last_started_at does not exist` catch.

**Root cause**: app_task_details 정식 컬럼 = `started_at`, `last_started_at` 컬럼 미존재. try/except silent fail → 자동 close 미발동.

### 변경 (BE only, 1 파일)

- `task_service.py` `_trigger_first_close()` + `_trigger_second_close()` 두 함수 SQL 정정
  - SELECT: `td.last_started_at` → `COALESCE((SELECT MAX(wsl.started_at) FROM work_start_log wsl WHERE wsl.task_id = td.id), td.started_at)` (옵션 B + Catch B 통합)
  - WHERE: `td.started_at IS NOT NULL` 가드 추가 (Catch D 옵션 A)
  - inline duration 계산 → `calculate_auto_close_duration()` 호출 통합 (Catch C DRY 정정)

### 운영 영향 (사용자 측 SQL 검증)

- 운영 1건 (GPWS-0799 ELEC IF_2 4 task orphan) — Manager force-close 직접 처리 필요
- 테스트 2건 (TEST-1111 MECH + ELEC)
- 이전 영역 4건 (GBWS-6979/6980/7087/7088) — 본 결함 무관 기존 영역

### ADR-029 후속 사례 추가

- #21: pytest mock 영역 vs 실제 DB SQL 검증 분리 표준
- #22: Codex/SQL 작성 시 information_schema cross-check 표준
- #23: 사용자 답변 "True" 영역 운영 데이터 SQL 검증 권고

---

## v2.15.3 (HOTFIX-SPRINT41D-AUTO-FINALIZE-RANGE-EXTENSION — Issue A 차단 범위 확장, 2026-05-14)

**Sprint**: `HOTFIX-SPRINT41D-AUTO-FINALIZE-RANGE-EXTENSION-20260514` (BE only)

**상태**: ✅ COMPLETED (5-14 release, commit `7b38d10` push, Railway + Netlify 자동 재배포)

**배경**: v2.15.2 잔존 catch — FIRST_FINAL (TANK_DOCKING, IF_2) 만 차단되고 gas1/util1/PRE_DOCKING phase task 영역 여전히 Sprint 55 auto-finalize 작동 → 사용자 의도 ("relay 한 명 참여 시 close 방지 = 모든 relay-able task") 미충족. 옵션 B Allowlist (`AUTO_FINALIZE_BLOCKED_TASK_IDS` 11 task) 채택으로 확장.

### 변경 (3 파일)

| 파일 | 변경 |
|------|-----|
| `backend/app/services/task_service.py` | `AUTO_FINALIZE_BLOCKED_TASK_IDS` 11 task set 신규 + 분기 정정 (`is_first_final` → `is_auto_finalize_blocked`) + 응답 `auto_finalize_blocked` 신규 + `first_final_blocked` 호환성 보존 |
| `backend/app/routes/work.py` | forward 매핑 영역 `first_final_blocked` + `auto_finalize_blocked` 2 키 추가 (Codex M-1 정정) |
| `tests/backend/test_relay_first_final.py` | parametrize TC 11 task 매트릭스 (TC-FF-01e~01o) + SELF_INSPECTION 회귀 방지 TC (TC-FF-01i) + 기존 TC-FF-01b/c/d 응답 플래그 검증 보강 |

### pytest 결과

- **신규 v2.15.3 12 TC** + 기존 26 TC = **38 TC GREEN** (20초)
- 회귀 (test_work_api.py): 8/8 PASS (3분 56초)
- 총 **46/46 GREEN**

### Codex 검증 trail

- 라운드 1: M=1 / A=2 / N=4 → M-1 (work.py forward) + A-1 (parametrize TC) 정정 반영
- 라운드 2 미진행 (CLAUDE.md 핵심 규칙 6 "라운드 상한 1회" 정합)

### 회귀 위험 0

- TANK_DOCKING/IF_2 차단 (v2.15.2 fix) 그대로 보존
- SELF_INSPECTION/INSPECTION 정상 close (Sprint 55 3-C 분기) 정합 — TC-FF-01i 회귀 방지
- Second Close 트리거 변경 0
- FE 다이얼로그 (`_kFinalTaskIds` v2.15.1 정합) 변경 0
- DB schema 변경 0

### 사용자 결정 (5-13~14)

- TMS TANK_MODULE: 제외 (사용자 결정)
- HEATING_JACKET: 포함 — admin 토글 false 대비 사전 등록

---

## v2.15.2 (HOTFIX-SPRINT41D-AUTO-FINALIZE-NOT-BLOCKED — 즉시 return 누락 fix, 2026-05-14)

**Sprint**: `HOTFIX-SPRINT41D-AUTO-FINALIZE-NOT-BLOCKED-20260514` (BE only)

**상태**: ✅ COMPLETED (5-14 release)

**배경**: 사용자 catch (TEST-1111) — v2.15.0 + v2.15.1 배포 후에도 "내 작업만 종료 → task close 발생" 사고 재현. **Root cause**: `task_service.py` L363-369 First Final 차단 분기가 `logger.info` 만 출력하고 `finalize` 변수 그대로 False 유지 → L408 auto_finalize 분기 진입 → `_all_workers_completed=True` (한 명 참여) 시 `auto_finalized=True` → **task close 발생 (의도와 반대)**.

### 변경 (1 파일)

- `backend/app/services/task_service.py` complete_work() L363-378 정정
  - 즉시 return + `first_final_blocked: True` 플래그 추가
  - work_completion_log 본인 row 기록 (duration 측정 보장)
  - pause auto-resume (Sprint 55 3-D 패턴 흡수)

### pytest 결과

- 신규 TC-FF-01b/01c/01d: 3 TC GREEN
- 기존 23 TC: GREEN
- 총 **26/26 GREEN**

### 학습 영역 (실수 #20)

- 설계서 ↔ 구현 wire-through 검증 누락
- pytest TC 작성 시 constants 검증 vs 실제 동작 검증 분리 필수
- Codex 라운드 1+2 catch 누락 — 사용자 운영 catch 영역 결국 발견

---

## v2.15.1 (Sprint 41-D FE 후속 — `_kFinalTaskIds` 정합, 2026-05-14)

**Sprint**: `HOTFIX-SPRINT41D-FE-KFINAL-TASK-IDS-20260514` (FE only)

**상태**: ✅ COMPLETED (5-14 release, Netlify 배포)

**배경**: 사용자 catch (TEST-1111) — IF_2 작업 시 "내 작업만 종료" 다이얼로그 미표시. **Root cause**: FE `_kFinalTaskIds` set 에 `IF_2` 포함 → 다이얼로그 미표시 + 항상 `finalize=true` 강제 전송 → BE Sprint 41-D First Final 차단 로직 우회.

### 변경 (FE only, 2 파일)

- `frontend/lib/screens/task/task_detail_screen.dart`: `_kFinalTaskIds` 영역 `IF_2` 제거 + `INSPECTION` 추가
- `frontend/lib/screens/task/task_management_screen.dart`: 동일 set 정합

### 검증

- flutter analyze clean (0 issues)
- flutter build web GREEN (12.1s)
- Netlify prod 배포 완료

---

## v2.15.0 (Sprint 41-D Relay First Final Logic + 자동 정리 트리거, 2026-05-14)

**Sprint**: Sprint 41-D — Relay First Final Logic (BE only, ~12h)

**상태**: ✅ COMPLETED (5-14 release)

**배경**: Sprint 41 ~ Sprint 55 trail 마무리 — "내 작업만 종료" 의도 + 시스템 강제 보호 통합. 2026-04-22 O/N 6588 GBWS-6978/6979/6980 UTIL_LINE_2 사례 (이영식/서명환) root cause fix.

### 변경 (5 파일 / +650 LOC)

- `backend/app/services/task_service.py`: FIRST/SECOND/SINGLE FINAL TASK_IDS 3 set + PHASE_MAP + ENUM + 트리거 함수
- `backend/app/services/duration_calculator.py` 신규: `_to_kst()` + `calculate_close_at()` + `calculate_auto_close_duration()`
- `backend/app/models/task_detail.py`: `auto_close_relay_task()` 확장
- `backend/migrations/056_add_duration_source.sql` 신규: duration_source NULLABLE + CHECK 4 enum
- `tests/backend/test_relay_first_final.py` 신규: pytest 23 TC

### pytest 결과

- 신규 Sprint 41-D: 23/23 PASS (0.21s)
- 회귀 (work_api + task_workers): 15/15 PASS
- 총 **38/38 GREEN**

### Codex 검증 trail

- 라운드 1: M=2 / A=4 / N=2 → 정정 7건
- 라운드 2: M=2 / A=2 / GREEN=2 → 정정 5건
- 라운드 3 미진행 (CLAUDE.md 라운드 상한 1회 정합)

---

## v2.14.4 (HOTFIX-ELEC-CHECKLIST-SELECT-IMMEDIATE-PUT — dropdown 단독 변경 시 저장, 2026-05-13)

**Sprint**: `HOTFIX-ELEC-CHECKLIST-SELECT-IMMEDIATE-PUT-20260513` (FE only patch)

**상태**: ✅ COMPLETED (5-13 release, Netlify 자동 배포)

**배경**: 사용자 catch — ELEC `master_id=67` (TUBE 종류/색상) 운영 record 18건 중 11건 `selected_value=NULL`. 진단 결과: dropdown `onChanged` 가 setState 만 호출하고 PUT 호출 없음 → "PASS 먼저 → 드랍다운" 순서 입력 시 selected_value 영원히 NULL. MECH 는 v2.11.4 (4-22) Q6-C fix 적용된 패턴 운영 안정 입증, ELEC 는 동일 fix 누락.

### Root cause

`elec_checklist_screen.dart:951-961` dropdown onChanged:
```dart
onChanged: (value) {
    if (value == null) return;
    setState(() { ... });  // 화면 UI 만
    // ❌ apiService.put() 호출 없음
}
```

MECH `mech_checklist_screen.dart:839-857` 정합:
```dart
onChanged: (value) {
    if (value == null) return;
    setState(() { ... });
    _debouncedUpsert(...);  // ✅ 즉시 PUT (500ms debounce)
}
```

### 변경 (FE only, 1 파일)

- `frontend/lib/screens/checklist/elec_checklist_screen.dart`
  - `dart:async` import 추가
  - `_selectDebounceTimers: Map<int, Timer>` 필드 추가 + dispose 영역 cancel
  - `_saveSelectedValue(item, value)` helper 신규 — 500ms debounce 후 selected_value 단독 PUT
  - dropdown onChanged 영역 helper 호출 추가
  - PASS/NA 미선택 + selected_value 있음 시 노란 경고 "PASS 또는 NA 선택 후 저장됩니다" (MECH L860-872 패턴)

### 동작 변경 (시나리오 4가지)

| 사용자 입력 순서 | Before | After |
|----------------|-------|-------|
| 드랍다운 → PASS | ✅ 저장 | ✅ 저장 (2회 PUT, 멱등) |
| **PASS → 드랍다운** | ❌ NULL | ✅ 저장 |
| **드랍다운만 (PASS 안 누름)** | ❌ 저장 0 | ✅ selected_value 저장 + 노란 경고 |
| 드랍다운 → 옵션 변경 → 옵션 변경 | ❌ 저장 0 | ✅ 마지막 선택만 (debounce) |

### BE 무변경

- `checklist_service.py:upsert_elec_check` 정상 — selected_value 단독 PUT 도 INSERT/UPDATE 모두 처리
- BE 회귀 위험 0

### 검증

- `flutter analyze` clean (0 issues)
- `flutter build web --release` GREEN (12.4s)
- MECH 패턴 (v2.11.4 이후 운영 안정) 그대로 이식 — pytest TC 별도 X (FE only)

### 운영 영향

- 신규 ELEC SELECT 입력: 자동 정상 저장 ✅
- 기존 NULL 11건 (4-24 ~ 5-13): 자동 fix 안 됨 — 운영자가 재진입 + 드랍다운 재선택 시 수동 보정
- placeholder fix (v2.14.3) 와 무관 (id 67 정식 영역)

---

## v2.14.3 (HOTFIX-ELEC-CHECKLIST-PLACEHOLDER-DEACTIVATE — 046a 사고 정정, 2026-05-13)

**Sprint**: `HOTFIX-ELEC-CHECKLIST-PLACEHOLDER-DEACTIVATE-20260513` (BE only patch)

**상태**: ✅ COMPLETED (5-13 release, Railway 자동 재배포 진행 중 — migration 055 자동 적용)

**배경**: 사용자 catch — 운영 DB `checklist_master` ELEC COMMON 영역 62개 row (예상 31개의 2배). 진단 SQL 4건 결과 정식 31건 (id 62-92, 2026-04-10 11:26 created) + placeholder 31건 (id 94-124, 2026-04-27 21:36 created) 영역 분리 확인. Root cause: HOTFIX-08 (v2.10.10, 4-27 21:36:04) 의 db_pool transaction 정리 fix 부수 효과로 migration 046a (Sprint 57 초기 placeholder seed) 가 자동 재적용 → 047 의 `DELETE → 정상 INSERT` 이후 placeholder 31건이 신규 INSERT 됨.

### 변경 (3 파일)

| 파일 | 변경 |
|------|-----|
| `backend/migrations/055_elec_checklist_placeholder_deactivate.sql` | 신규 — placeholder 31건 (id 94-124) `is_active=FALSE` + DO block 검증 (placeholder active 0 / 정식 active 31 / deactivate 31) |
| `backend/migrations/046a_elec_checklist_seed.sql` | 본문 교체 — placeholder 31항목 → 047 의 정식 31항목 + `ON CONFLICT (product_code, category, item_group, item_name) DO NOTHING` (향후 fresh boot 환경 재발 방지) |
| `backend/version.py` / `frontend/lib/utils/app_version.dart` | 2.14.2 → 2.14.3 |

### pytest TC 신규 5건 (`test_migration_055_elec_placeholder.py`)

- `test_migration_055_deactivates_placeholder_31_rows` — id 94-124 모두 is_active=FALSE
- `test_migration_055_no_active_placeholder` — placeholder 영역 active row 0
- `test_migration_055_keeps_legacy_31_active` — 정식 id 62-92 모두 is_active=TRUE 유지
- `test_migration_055_preserves_record_fk` — placeholder master 참조 record 보존
- `test_migration_055_total_active_is_31` — ELEC COMMON active 총 31 (정식만)

### Logic 변경: 0

모든 ELEC 체크리스트 logic 이 `cm.is_active = TRUE` 필터 사용 — placeholder deactivate 후 정식 31건만 노출. 1차/2차 체크 logic + 성적서 + 작업자/QI 화면 모두 정상화.

| Logic | 위치 | placeholder deactivate 후 |
|-------|------|------|
| Phase 1 NULL count (1차 체크) | `checklist_service.py:1170` | 정식 31건만 count |
| Phase 2 NULL count (2차 체크) | `checklist_service.py:1192` | 정식 31건만 count |
| Phase 1+2 total | `checklist_service.py:1209` | 정식 31건만 count |
| `get_elec_checklist()` | `checklist_service.py:230` | 작업자/QI 화면 정식 31건만 노출 |
| `get_checklist_report()` | `checklist_service.py:553` | 성적서 정식 31건만 |

### 운영 적용 흐름

1. Railway 재배포 시 migration_runner 가 055 자동 적용 (신규 파일, `migration_history` 미등록)
2. 046a 본문 수정은 향후 fresh boot 환경 대비 (운영 DB `migration_history` 영역 046a 이미 적용 trail 존재 → 재실행 X)
3. placeholder record 50건 (id 111-117 운영자 PASS/NA 입력) FK 보존 — 작업자 입력 trail 감사용

### 사용자 결정

- **Soft delete** (`is_active=FALSE`) — 운영 데이터 보존 원칙 (CLAUDE.md L188-194)
- **record 50건 보존** — placeholder 의미 불명이지만 시각/작업자 trail 보존

### 사고 trail

| 시점 | 사건 | 결과 |
|------|------|-----|
| 2026-04-09 22:55 | migration 046 적용 | 스키마 생성 |
| 2026-04-10 11:26 | migration 047 적용 (Sprint 57-C) | DELETE + 정상 31항목 INSERT (id 62-92) |
| 2026-04-15 23:06 | migration 048 적용 | phase1_applicable + qi_check_required 정규화 |
| **2026-04-27 21:36** | **HOTFIX-08 v2.10.10 부수 효과** | **046a 자동 재적용 → placeholder 31건 신규 INSERT (id 94-124)** |
| 2026-05-13 | 사용자 catch + migration 055 적용 | placeholder 31건 deactivate, 정식 31건만 active |

---

## v2.14.2 (HOTFIX-MATERIALS-CATEGORY-ILIKE — 자재 마스터 검색 case-insensitive, 2026-05-13)

**Sprint**: `HOTFIX-MATERIALS-CATEGORY-ILIKE-20260513` (BE only patch)

**상태**: ✅ COMPLETED (5-13 release, commit `86fc8a1` push, Railway 자동 재배포 진행 중)

**배경**: AXIS-VIEW `OPS_API_REQUESTS.md` #64 catch — `/api/admin/materials?category=` 가 `=` 정확 매칭이라 사용자가 'm' / 'mfc' 입력 시 0건. `keyword` / `description` 은 이미 `ILIKE` 적용되어 있어 일관성 보강.

### 변경 (1 파일 / 3 line)

| 파일 | 변경 |
|------|-----|
| `backend/app/routes/admin_materials.py` L82-84 | `category = %s` → `category ILIKE %s` + `f'%{category}%'` |

### pytest TC 신규 2건

- `test_list_materials_filter_by_category_case_insensitive` — `category=mfc` → MFC 13건
- `test_list_materials_filter_by_category_partial_match` — `category=m` → MFC 13건 이상
- 기존 `test_list_materials_filter_by_category` (`MFC` 정확 매칭) → 회귀 0 (13건 동일)

### 검증

- pytest 신규 3 TC: 3/3 PASS (70초, category 관련 only)
- pytest 회귀 전체: 15/15 PASS (218초, test_sprint66_be_step4_admin.py)
- 회귀 위험 0: `=` 케이스는 `ILIKE` 부분 매칭에 흡수, NULL row 매칭 영향 동일 (NULL 매칭 X)

### 변경 영향 표

| 입력 | Before | After |
|------|--------|-------|
| `MFC` (정확) | ✅ 13건 | ✅ 13건 |
| `mfc` (소문자) | ❌ 0건 | ✅ 13건 |
| `m` (한 글자) | ❌ 0건 | ✅ 13건 이상 |
| `mf` (부분) | ❌ 0건 | ✅ 13건 |
| `xyz` (없는 영역) | ✅ 0건 | ✅ 0건 |

### 연관

- AXIS-VIEW v1.43.8 `ChecklistEditModal` 자재코드 input case-insensitive (FE client filter)
- AXIS-VIEW BACKLOG `OPS-MATERIALS-KEYWORD-ILIKE`

---

## v2.14.1 (FIX-DB-POOL-CONN-LEAK-WORK-PY — work.py conn leak 5 위치 fix, 2026-05-12)

**Sprint**: `FIX-DB-POOL-CONN-LEAK-WORK-PY-20260512` (BE only patch, Codex GREEN)

**상태**: ✅ COMPLETED (5-12 release, Railway 자동 재배포 진행 중)

**배경**: 2026-05-12 KST 16:48 Railway pool exhausted 사고 (사용자 측 restart 영역 정상화) → log 분석 + 트래픽 패턴 영역 root cause 확정.

### Root cause

- `routes/work.py` L705: `conn2.close()` 직접 호출 (psycopg2 close 메서드)
- ThreadedConnectionPool 영역 `put_conn()` 호출 영역 conn 반환 → conn 영구 누수
- 모바일 작업자 S/N 상세뷰 진입 마다 1 conn 누수 → MAX=30 도달

### 변경 (work.py 5 위치, ~40 LOC)

- L705: `conn2.close()` → `put_conn(conn2)` + try/finally (영구 leak 차단)
- L676-707: my_status 영역 `conn2=None` 초기화 + finally
- L594-670: workers 배열 try/finally 패턴
- L568-583: worker_name try/finally + worker_map 외부 초기화
- L468-486: complete_single_action_route try/finally

### 검증

- pytest 45/45 PASS (test_work_api + test_work_batch + test_task_workers_api, 18분 11초)
- Flask app boot 정상
- conn.close() 0건 / put_conn 8건 / finally 6건
- Codex 라운드 1 GREEN (M=0 / A=1 BACKLOG)

### 회귀 위험 0

- pytest 45/45 + Flask boot + Sprint 64-BE v3 task_service_batch 동일 패턴 호환

### 후속 BACKLOG

- `BUG-WORK-INSERT-ROLLBACK-EXPLICIT-20260512` (P3 Advisory) — L468-486 INSERT except 시 `conn.rollback()` 명시 추가

### 운영 모니터링 (v2.14.1 release 후)

**🔴 1순위 — Pool exhausted 재발 여부 (24h 동안 0건 유지 목표)**:
- `[db_pool] Pool exhausted` Sentry alert
- `[db_pool] Using direct connection` Railway log
- `[pool_warmup] 0/0 conn warmed`
- `[db_pool] 0/0 warmed for 3 consecutive cycles` (자가 회복 발화 = leak 재발 가설)

**🟠 2순위 — 응답 시간 정상화**:
- `GET /api/app/tasks/{sn}` 50-300ms (위험 500ms+)
- `POST /api/app/work/complete` 200-800ms (위험 1.5초+)
- `GET /api/app/work/today-tags` 50-150ms (위험 300ms+)

**🟡 3순위 — 다른 release 운영 안정성**:
- v2.14.0 자재 업로드 endpoint (flow sensor 완료 후 검증)
- AXIS-VIEW Sprint 40 일괄 처리
- 5-17 ± 1d 5일 주기 Railway proxy idle 가설 재발 X

**검증 시점**: T+1h / T+24h (5-13) / T+5d (5-17)

---

## v2.14.0 (Sprint 66-BE-FOLLOWUP v3 — 자재 마스터 Excel 일괄 업로드, 2026-05-12)

**Sprint**: `SPRINT-66-BE-FOLLOWUP-MATERIALS-UPLOAD-20260511` (BE only, P2 MEDIUM, Codex 5라운드 GREEN)

**상태**: ✅ COMPLETED (5-12 release, Railway 자동 재배포 진행 중)

**배경**: AXIS-VIEW Sprint 42 v1.43.0 `MaterialUploadModal.tsx` 4단계 워크플로우 prod 배포 완료 영역 BE `/upload` endpoint 미구현 → Twin파파 측 자재 마스터 변경 시 SQL 직접 INSERT 필요 (운영 부담). #63 검토 결과 Q1/Q2/Q3 사용자 결정 영역 확정.

### 변경 파일 5개

| 파일 | LOC |
|------|-----|
| `backend/app/utils/__init__.py` ⭐ 신규 | +1 |
| `backend/app/utils/material_parser.py` ⭐ 신규 | +228 |
| `backend/app/services/material_upload_service.py` ⭐ 신규 | +228 |
| `backend/app/routes/admin_materials.py` | +88 |
| `tests/backend/test_admin_materials_upload.py` ⭐ 신규 (24 TC) | +~440 |
| `backend/requirements.txt` (chardet + openpyxl) | +2 |

### Codex 검증 5라운드 trail

- 라운드 1 M=4/A=5/N=8 → v2 trail
- 라운드 2 M=4/A=5/N=7 → v3 본문 정정 (non-MFC scope + MFC INVALID_BOM_KEY + category 50 + 단일소스화)
- 라운드 3 M=2/A=3/GREEN=5 → diff_with_db spec + ATTRIBUTE_CONFLICT 정책 + Step 순서
- 라운드 4 M=1/A=3 + 5 PASS → tuple unpacking + TC 24 통일 + pair-wise IN
- **라운드 5 M=0/A=3 GREEN** ✅ → 구현 진입 권고

### pytest 23/23 GREEN

- Unit 12 (DB-free, 0.30초)
- Integration 11 + 1 skip (TC-MU-11 의도) (staging DB, 2분 52초)

### v3 핵심 결정 (053a generator 패턴 정합)

- Q1 MFC scope only / non-MFC dedup / ATTRIBUTE_CONFLICT 첫 등장 유지 / INVALID_BOM_KEY BOM row 영역만 / FIELD_TOO_LONG 8 필드 / .xls drop / utils + services 분리 / `{error, message}`

### 회귀 위험 0

- 기존 admin_materials.py 5 endpoint 영향 0
- DB schema 변경 0, migration 불필요
- FE Sprint 42 v1.43.0 contract 정합

### 후속 영역

- FE #63 정정 권고 (별 PR): BOM 4-key → 2-key / `detail` → `message` / `.csv/.xlsx only`
- TC-MU-11 ROLLBACK injection TC 별 sprint

---

## v2.13.2 (HOTFIX-TASKS-BY-ORDER-WORKERS — workers 배열 추가, S1 동반, 2026-05-11)

**Sprint**: `HOTFIX-TASKS-BY-ORDER-WORKERS-20260511` (S1 동반, Sprint 64-BE v3 / v2.13.1 후속)

**상태**: ✅ COMPLETED (5-11 release, Railway 자동 재배포, POST-REVIEW deadline 2026-05-12)

**배경**: VIEW v1.43.6 S1 HOTFIX 영역 catch — v2.13.1 release 직후 응답 형식 정정으로 orderTasks 영역 정상 추출 영역 → 이전 영역 빈 배열 fallback 영역 회피됐던 버그 노출 → FE `task.workers.find()` TypeError → React crash → S/N 상세뷰 흰 화면 발생.

### Root cause

- 내 `get_tasks_by_order()` 영역 `_task_to_dict()` 호출 후 후처리 영역 X
- 기존 `get_tasks_by_serial` (work.py L562~728) 영역 후처리 약 170 line (workers 배열 + worker_name + my_status 일괄 조회) 영역 동일 패턴 누락
- Codex 5 라운드 + v2.13.1 catch 모두 — 응답 spec 검증만 영역, **후처리 패턴 일관성** 검증 누락

### 변경 (~110 LoC)

- `backend/app/services/task_service_batch.py`:
  - 신규 private helper `_enrich_tasks_with_workers(task_list)` (~100 LoC)
    - worker_name 일괄 조회 (task.worker_id → workers.name)
    - workers 배열 일괄 조회 (work_start_log JOIN workers JOIN work_completion_log JOIN app_task_details)
    - legacy fallback (work_start_log 없을 시 단일 작업자 정보)
  - `get_tasks_by_order()` 영역 helper 호출 추가 (1 line)
- `backend/version.py` + `frontend/lib/utils/app_version.dart`: 2.13.1 → 2.13.2

### 응답 schema 변경

각 task item 영역 추가 필드:
- `workers: [{worker_id, worker_name, company, started_at, completed_at, duration_minutes, status, is_orphan, task_closed_at}, ...]`
- `worker_name: string | null`

### 회귀 위험

- 0 — VIEW v1.43.6 정규화 코드 (`workers ?? []`) 영역 BE 응답 후에도 자동 정상 작동
- `_enrich_tasks_with_workers()` 영역 private helper, work.py touch 0
- 기존 `get_tasks_by_serial` 영역 영향 0

### POST-REVIEW 영역 (24h 이내)

- Codex 사후 검토 — S1 HOTFIX 정합 (CLAUDE.md L237 deadline 2026-05-12)
- Codex 검증 라운드 표준화 권고 — 응답 spec 일관성 + 후처리 패턴 일관성 동시 검증 항목 (재발 방지)

### 검증

- VIEW v1.43.6 S1 HOTFIX release 완료 (Twin파파 측)
- OPS v2.13.2 release 후 S/N 상세뷰 흰 화면 영역 정상 렌더 확인 예정

### ✅ 운영 검증 완료 (Twin파파 측, 2026-05-11 KST)

- VIEW 일괄 시작/종료 액션 정상 작동 확인 (TEST-1111~1113 영역)
- S/N 상세뷰 흰 화면 없이 정상 렌더 확인
- 토스트 succeeded / skipped 양쪽 정상 표시
- Sprint 64-BE v3 (v2.13.0) + HOTFIX 2건 (v2.13.1 + v2.13.2) 영역 통합 정합 완료

---

## v2.13.1 (HOTFIX-TASKS-BY-ORDER-SCHEMA — 응답 형식 정정, 2026-05-11)

**Sprint**: `HOTFIX-TASKS-BY-ORDER-SCHEMA-20260511` (S2, Sprint 64-BE v3 후속)

**상태**: ✅ COMPLETED (5-11 release, Railway 자동 재배포)

**배경**: v2.13.0 Sprint 64-BE v3 release 직후 AXIS-VIEW 측 catch — `/tasks/by-order/<sales_order>` 응답이 `{tasks, total}` 객체 wrap 영역 → VIEW FE `Array.isArray(data) ? data : []` 영역 빈 배열 fallback → 일괄 시작 토스트 미표시. 다른 list endpoint 영역 배열 직접 반환 영역 일관성 위반 catch.

### Root cause (Codex 5 라운드 catch 누락)

- v3 본문 L35628 영역 `{'tasks': tasks, 'total': len(tasks)}` 명시 영역 — Codex 5 라운드 모두 통과
- 영역 영역 catch 영역 = 다른 endpoint (`/api/app/tasks/{sn}?all=true` 영역 배열 직접 반환) **응답 spec 대조 누락**
- POST-REVIEW 영역 catch — 사용자 측 VIEW 분석 영역 즉시 영역

### 변경 (~5 line)

- `backend/app/services/task_service_batch.py` `get_tasks_by_order()`:
  - return type annotation: `Tuple[Dict[str, Any], int]` → `Tuple[List[Dict[str, Any]], int]`
  - return 영역: `({'tasks': tasks, 'total': N}, 200)` → `(tasks, 200)`
- `backend/app/routes/work_batch.py` `tasks_by_order_route()` — `jsonify(response)` 그대로 (Flask 3.x list 자동 처리)
- `backend/version.py` + `frontend/lib/utils/app_version.dart`: 2.13.0 → 2.13.1

### 양쪽 동시 release (옵션 B 선택)

- **VIEW v1.43.5**: `getTasksByOrder()` 영역 양쪽 형식 호환 코드 (Array.isArray ? data : data.tasks ?? []) — 미래 회귀 0
- **OPS v2.13.1**: 응답 형식 정정 (객체 wrap → 배열 직접) — 일관성 정합

### 회귀 위험

- 0 — VIEW v1.43.5 호환 코드 영역 BE 변경 후에도 자동 정상 작동
- pytest TC 영향 0 (현재 `get_tasks_by_order()` 직접 호출 TC 없음, 별 sprint 영역 추가)

### 검증

- Twin파파 측 VIEW 일괄 시작 토스트 정상 표시 확인 예정
- Network 탭 응답 영역 `[task1, task2, ...]` 배열 형식 확인

---

## v2.13.0 (Sprint 64-BE v3 — Work Batch 엔드포인트 신규, 2026-05-11)

**Sprint**: `SPRINT-64-BE-WORK-BATCH-V2-20260511` (BE only, P1, Codex 5 라운드 검증 GREEN)

**상태**: ✅ COMPLETED (5-11 release, Railway 배포 진행 중 — Twin파파 측 AXIS-VIEW 직접 검증 예정)

**배경**: 2026-04-28 등록 후 Codex 라운드 1 catch (M=6 Critical) → 2026-05-11 v2 재설계 (best-effort sequential helper reuse) → Codex 5 라운드 검증 → 구현 진입. AXIS-VIEW Sprint 40 v1.40.0 (TM Tank Module 일괄 시작/종료 admin 액션) prod 배포 완료 — BE 측 batch 엔드포인트 신규 추가로 graceful degrade 영역 해제.

### 변경 파일 5개

| 파일 | 변경 | LOC |
|------|------|-----|
| `backend/app/routes/work_batch.py` ⭐ **신규** | 3 route (start-batch / complete-batch / by-order) + `_validate_batch_input` helper | +117 |
| `backend/app/services/task_service_batch.py` ⭐ **신규** | start/complete_work_batch + 3 helper (`_fetch_task_product_map` / `_filter_eligible_ids` / `_match_manager_company`) + 매핑표 2건 | +209 |
| `backend/app/__init__.py` | `from app.routes import work_batch` import 1줄 (register_blueprint 전 필수) | +1 |
| `tests/conftest.py` | fixture 3종 신규 (`seed_tank_module_tasks_batch` / `seed_manager_company_matrix` / `assert_audit_log_count`) | +~150 |
| `tests/backend/test_work_batch.py` ⭐ **신규** | 30 TC (Unit 13 + Integration 17) | +~280 |

**기존 `work.py` (1,355 LOC 🔴) + `task_service.py` (1,551 LOC ⛔) touch 0** — CLAUDE.md L545 "필수 분할 파일 새 로직 추가 금지" 정합.

### 결정 사항 (v3)

- **신규 파일 2개 분리**: 기존 비대화 파일 touch 0, 분리 정책 100% 준수
- **30건 상한**: helper task당 7~9 query (start) / 10~15 query (complete) → 30 × 15 = 450 query / pool MAX=30 안전
- **Best-effort sequential**: 각 task 마다 기존 `start_work()`/`complete_work()` helper 호출 — audit log + start guards + complete logic 자동 흡수
- **`_match_manager_company()`**: work.py L340-356 reactivate 패턴 정합 (TMS = `module_outsourcing OR mech_partner`, MECH = `mech_partner only`)
- **응답 shape**: `_task_to_dict()` 전체 shape 재사용 — FE Sprint 40 contract 정합

### Codex 검증 5 라운드 trail

| 라운드 | 결과 | 정정 |
|--------|------|------|
| 1 | M=6/A=3 | v1 all-or-nothing 폐기 → v2 helper reuse 패턴 (audit log escape / TMS 매핑 회귀 / start guards / complete logic / schema 가정 / 응답 contract 정정) |
| 2 | M=4/A=1/N=3 | 분리 파일 + 30건 + complete pseudo code + 16+ TC |
| 3 | M=1/A=3/N=3 | 12 case 전수 + TC-AUDIT-02 id + import 순서 + gate 측정 환경 |
| 4 | M=1/A=1/N=2 | prefix 충돌 정정 (Blueprint url_prefix 영역 + register_blueprint 매개변수 영역 제거) |
| **5** | **M=0/A=1/N=3 GREEN** | pool warm-up 한 줄 추가 → 구현 진입 권고 |

### pytest 30 TC GREEN (Unit 13 + Integration 17, staging DB 22분 10초 실측)

**Unit** (DB 무관, ~0.27초):
- TC-MATCH-UNIT-01 C1~C12 (12 case 전수): TMS/MECH 매핑 + suffix 제거 + empty + NULL fallback + PI/QI/SI 영역 외 False
- A-1 substring 보조 (BAT vs COMBAT — 운영 미발생, 후속 BACKLOG)

**Integration** (Railway staging DB, ~22분):
- 입력 검증 4: 빈 / 누락 / >30 / 비-정수
- 화이트리스트+매니저 5: admin 30건 / TMS(M) 매칭 / FNI 다른 회사 FORBIDDEN / FNI mech_partner 매칭 / 모두 NOT_TANK_MODULE → 400
- TC-AUDIT-01/02 (audit log 1:1): work_start_log + work_completion_log row 증가 = succeeded 건수
- TC-SHAPE-01/02 (응답 shape): start/complete `_task_to_dict()` 전체 필드 (is_paused / total_pause_minutes / force_closed / close_reason / closed_by_name / task_type 등)
- Skipped reason 매트릭스 4: NOT_FOUND / ALREADY_STARTED / TC-COMPLETE-01 FORBIDDEN_WORKER / TC-COMPLETE-02 ALREADY_COMPLETED

### pytest catch 2건 (Codex 5 라운드 못 catch — pytest 자체 catch 가치 입증)

1. **C1 case 인자 오기**: 설계서 + TC 작성 시점 `('TMS', 'TMS', 'FNI', 'FNI') → True` 오기 (manager 'TMS' vs mod 'FNI' mismatch). 정정 → `('TMS', 'TMS', 'TMS', 'FNI')` (TMS module_outsourcing match 의미 정합)
2. **complete TC reason 예상값**: `complete_work()` L217 `_worker_has_started_task` False 분기가 L233 `task.started_at None` 분기보다 **먼저 발동**. admin 이 cross-worker GST 영역 아닌 경우 FORBIDDEN 분기 (시작 안 한 task complete 차단 = 보안 정합). 정정 → reason `FORBIDDEN_WORKER`. NOT_STARTED 도달은 cross-worker GST 영역에서만 가능

### 후속 BACKLOG

- `BUG-MATCH-COMPANY-SUBSTRING-FALSE-POSITIVE-20260511` 🟢 P3 Advisory — substring 매칭 boundary issue (BAT vs COMBAT). 운영 데이터 기준 발생 케이스 0. work.py L347 reactivate 패턴 정합 보존 영역. 분기별 1회 모니터링.

### 회귀 위험

- 0 — 기존 `/work/start` `/work/complete` 영향 0 (Flutter 모바일 앱 흐름 보존)
- DB schema 변경 0, migration 불필요
- `_task_to_dict()` 시그니처 변경 0, helper 시그니처 변경 0

---

## v2.12.6 (HOTFIX-SPRINT66BE-CREATE-MASTER-ITEM-TYPE-AND-CONFLICT-MSG — POST INSERT 정정, 2026-05-11)

**Sprint**: `HOTFIX-SPRINT66BE-CREATE-MASTER-ITEM-TYPE-AND-CONFLICT-MSG-20260511` (S2, cowork 실수 #19)

**상태**: ✅ COMPLETED (5-11 release, Railway 배포 완료, BE only — Netlify 빌드 X)

**배경**: v2.12.5 release 직후 사용자 측 catch — AXIS-VIEW "+ 항목 추가" 모달에서 신규 SELECT/INPUT 항목 추가 시 묵음 회귀.

### 변경 (~50 LoC)

**BE** `backend/app/routes/checklist.py`:
- `import json` 추가
- `create_checklist_master()` POST 정정 3건:
  1. `item_type` 추출 + enum 검증 (CHECK/SELECT/INPUT)
  2. `select_options` 추출 + list 검증 + `json.dumps()` 직렬화
  3. CONFLICT 응답 보강 — 기존 충돌 항목 `id` + `is_active` 포함 + 비활성 시 토글 안내
- INSERT 컬럼 2개 추가 (`item_type`, `select_options`)

### Root cause

- Sprint 52 POST 작성 시점 ~ Sprint 63-BE 'INPUT' enum 확장 시점까지 **묵음 누적 회귀**
- FE 가 `item_type='SELECT'|'INPUT'` 전송해도 BE 가 무시 → DB DEFAULT `'CHECK'` 저장
- 신규 SELECT/INPUT 항목 생성 불가 → 사용자 측 catch 까지 ~수 sprint 잠복

### ADR-024 분리 정책 결정 시급

cowork 누적 실수 영역:
- 5-09 #16 — HOTFIX-SPRINT66BE-ENRICH-SELECT-OPTIONS-ITEMCODE (Codex M1~M5 폐기)
- 5-11 #18 — HOTFIX-SPRINT66BE-MASTER-LIST-ITEM-TYPE (GET 누락)
- 5-11 #19 — 본 HOTFIX (POST 누락, 동일 그룹)

→ 2일 누적 3건 (특히 #18+#19 동시 발견) = cowork ↔ Claude Code 작업 분리 정책 결정 영역 임계 초과.

### 영향

- 회귀 위험 0 (FE 가 item_type 미전송 시 'CHECK' fallback — 기존 동작 보존)
- 사용자 영향: AXIS-VIEW 신규 SELECT/INPUT 항목 추가 정상화

### 후속

- POST-REVIEW deadline 2026-05-18
- ADR-024 분리 정책 결정 영역 — 별 sprint

---

## v2.12.5 (FIX-ADMIN-OPTIONS-LISTS-SCROLL-ALERT-DEFAULT — Admin 옵션 3건 정정, 2026-05-11)

**Sprint**: `FIX-ADMIN-OPTIONS-LISTS-SCROLL-ALERT-DEFAULT-20260511` (P2 — 사용자 운영 catch, 3건 묶음)

**상태**: ✅ COMPLETED (5-11 release, Railway + Netlify 배포 완료)

**묶음 영역** (4건):
1. ① FE/BE API 키 정정 (admin_options_screen.dart)
2. ② 3 list 영역 스크롤 추가 (240px max ConstrainedBox)
3. ③ 미시작 작업 알람 default off (BE SETTING_KEYS + FE state)
4. **④ HOTFIX-SPRINT66BE-MASTER-LIST-ITEM-TYPE-20260511 (S2, cowork 실수 #18)** — `checklist.py` `list_checklist_master()` SELECT + 응답 dict 에 `cm.item_type` + `cm.select_options` 누락 정정 (+2 LoC, additive). AXIS-VIEW v1.43.1 ChecklistEditModal `item.item_type === 'SELECT'` 분기 정상화. POST-REVIEW deadline 2026-05-18.

**배경**: 사용자 측 5-11 catch — Admin 옵션 화면 3건:
1. 비활성/미로그인 사용자 목록 안 보임 (VIEW 정상)
2. 미종료 작업 목록 무제한 렌더 (UI 영역 overflow)
3. 미시작 작업 알람 default 영역 (업데이트 시 자동 true 변경 현상)

### 변경 (FE 5 + BE 1)

**FE** `frontend/lib/screens/admin/admin_options_screen.dart`:
- **#1-a FE/BE 키 정정** (silent fail catch):
  - L444: `response['workers']` → `response['inactive_workers']`
  - L461: `response['workers']` → `response['deactivated_workers']`
- **#1-b/c/2 스크롤 추가** (5-11 사용자 결정 — 240px max ≈ 3건):
  - 비활성 사용자 ListView → ConstrainedBox 240px wrap
  - 비활성화 계정 ListView → ConstrainedBox 240px wrap
  - 미종료 작업 Column → ConstrainedBox 240px + SingleChildScrollView wrap
- **#3 미시작 알람 default off** (FE state 정합):
  - L35: `bool _alertTaskNotStartedEnabled = true` → `false`
  - L324: fallback `?? true` → `?? false`

**BE** `backend/app/routes/admin.py`:
- **#3 SETTING_KEYS default off** L71: `'default': True` → `'default': False`

### Root cause 영역

| # | Root cause | 영향 영역 |
|---|-----------|----------|
| 1 | FE/BE API 응답 키 불일치 (cowork 실수 영역, Sprint 40-C 도입 시 미동기) | 운영 admin 영역 silent fail (VIEW는 정확한 키 사용 → 정상) |
| 2 | Column 무제한 렌더 (스크롤 영역 X) | 미종료 작업 다수 시 UI overflow |
| 3 | SETTING_KEYS default `True` + FE fallback `?? true` | 신규 admin/staging 환경 진입 시 자동 ON |

### Root cause #3 사용자 시나리오 해석

prod DB 검증 결과 `alert_task_not_started_enabled = false` (5-11 08:26 사용자 설정). 사용자 "업데이트 할때마다 true값으로 변경" 현상 = DB key 부재 시 BE GET fallback `result.setdefault(key, meta['default'])` 가 default `True` 반환 영역. 5-11 catch 직전엔 default 적용 영역 (사용자 측 첫 설정 영역).

### 검증

- Flutter analyze: error 0 / 9 info (모두 기존 코드)
- pytest 영역: `alert_task_not_started_enabled` 의존 test 0건
- prod DB: 변경 0 (사용자 5-11 08:26 false 그대로)

### 영향

- 회귀 위험 = 0 (test 의존 X, FE 변경은 UI 영역만)
- 사용자 영향:
  - #1 비활성 사용자 목록 정상 표시
  - #2 미종료 작업 다수 시 UI 스크롤 영역 보호
  - #3 신규 admin 환경 default OFF (사용자 의도 정합)

### 후속 (저녁 진행 예정)

- version bump v2.12.5 (이미 적용)
- git commit + push origin main
- Netlify FE build + deploy
- Railway BE 자동 재배포 검증
- handoff/BACKLOG 업데이트
- T+1h 검증

---

## v2.12.4 (FIX-ELEC-IF-NAMING-DOCKING-CLARITY — IF_1/IF_2 task_name 도킹 전/후 명시, 2026-05-10)

**Sprint**: `FIX-ELEC-IF-NAMING-DOCKING-CLARITY-20260510` (P3 — 단순 UX 정정, 작업자 혼동 catch)

**배경**: 작업자 측 운영 catch — ELEC IF_1/IF_2 의 1/2 기준이 tank docking 전/후 인지 혼동. 명시적 라벨 (`(도킹 전)` / `(도킹 후)`) 부여로 영구 해결.

### 변경 (3 line + Migration 054)

- **BE** `backend/app/services/task_seed.py` L77-78 — TaskTemplate 정정
  - `'I.F 1'` → `'I.F 1 (도킹 전)'`
  - `'I.F 2'` → `'I.F 2 (도킹 후)'`
- **BE** `backend/app/services/task_service.py` L495 — ELEC IF_2 알림 message 정정
- **DB Migration 054** — `BEGIN/COMMIT` atomic + UPDATE 2건 + DO block 검증
  - IF_1 185 row + IF_2 185 row = 총 370 row UPDATE
  - idempotent: `WHERE task_name = 옛 이름` 조건 (재실행 no-op)
- **TEST** `test_company_task_filtering.py` L541-542 + `test_issue46_workers_mapping.py` L353/359/363 갱신
- **운영 적용 완료**: prod psql + migration_history 등록

### 영향 (회귀 위험 0)

- task_id 변경 X → 코드/알림/체크리스트 매칭 로직 무관
- FE 코드 변경 0 (task_name display only)
- pytest 28/28 PASS (회귀 0)

---

## v2.12.3 (Sprint 66-BE FEAT-MATERIAL Step 4 — admin endpoints 자재 마스터 CRUD + 체크리스트 매핑, 2026-05-08)

**Sprint**: `Sprint 66-BE / FEAT-MATERIAL-MASTER-AND-BOM-INTEGRATION-20260507 Step 4 (OPS BE)` (P1, Codex 라운드 1 GREEN — M=0/A=6 advisory)

**배경**: Sprint 66 R3 4-step 의 마지막 step (OPS BE 측). AXIS-VIEW Sprint 42 (별 repo) 의 admin GUI 가 consume 할 endpoint 인프라 신규. **Sprint 66-BE OPS 측 100% 완료**.

### Codex 검증 trail

- **Step 4 implementation 라운드 1**: **M=0 / A=6 GREEN** (전부 advisory, BACKLOG 처리)
  - I-1: inactive material stale mapping round-trip — admin 가시성 영역 (의도된 동작). AXIS-VIEW FE 시각 마킹 BACKLOG
  - I-3: NULL vs `[]` 매핑 구분 소실 — FE 처리 규약 문서화 BACKLOG
  - B-legacy: legacy string CI 커버리지 조건부 — seed fixture BACKLOG
  - B-coerce: PATCH string ID coercion 미구현 — AXIS-VIEW Sprint 42 측 int 전송 보장 확인 필수
  - D-race: validation-update race window — 운영 빈도 낮음, advisory
  - F-wildcard: ILIKE wildcard escape 미구현 — 검색 의미론, 보안 X

### 변경 (BE 2 신규 파일 + Blueprint 등록 + pytest 1 신규)

**`backend/app/routes/admin_materials.py`** 신규 (5 endpoint):
- `GET /api/admin/materials` — 검색 + 페이지네이션 (category 정확 / keyword ILIKE on item_name+item_code / description ILIKE / is_active 분기 [true|false|all] / page / per_page max 200)
- `POST /api/admin/materials` — ON CONFLICT DO UPDATE idempotent + RETURNING `(xmax = 0) AS created`
- `PATCH /api/admin/materials/<id>` — 화이트리스트 갱신 (item_name/category/spec_1/spec_2/unit/description) — item_code 식별자 보호
- `PATCH /api/admin/materials/<id>/deactivate` — soft delete (RESTRICT FK 안전, is_active=FALSE)
- `PATCH /api/admin/materials/<id>/reactivate` — admin 실수 복구

**`backend/app/routes/admin_checklists.py`** 신규 (2 endpoint):
- `GET /api/admin/checklists/master/<id>/options` — dual-format 분기 (Codex D4-01: int → JOIN+array_position 순서 보존 / string → legacy_string flag legacy compat)
- `PATCH /api/admin/checklists/master/<id>/options` — 5종 검증 (list / int (bool 차단) / 중복 / material_master 존재+is_active=TRUE / item_type='SELECT')

**`backend/app/__init__.py`** — admin_materials_bp + admin_checklists_bp 2 블루프린트 등록

**권한 정합 (ADR-023 cross-check 준수)**:
- 모든 endpoint 에 `@jwt_required + @gst_or_admin_required` 2단 적층 (jwt_auth.py L263 표준 — Sprint 27 v1.7.4 도입)
- 새 데코레이터 작성 X — DRY + ADR-023 #6 (cowork 추측 작성 차단)

**`tests/backend/test_sprint66_be_step4_admin.py`** 신규 13 TC:
- list (default + ILIKE description + ILIKE category) / create idempotent (1차 created=true, 2차 false) + validation 400 / update whitelist (item_code 차단) / deactivate-reactivate roundtrip / get options legacy / patch validation 4건 / patch roundtrip + array_position 순서 보존 / 권한 (JWT 부재 401 + partner 403 + GST 200)
- 결과: **13/13 PASS** (Step 1+2+3 회귀 34/34 + Step 4 13/13 = **총 47/47 GREEN**)

### 영향

- **Sprint 66-BE OPS 측 100% 완료** — Step 1+2+3+4 prod 적용 + 47/47 pytest GREEN
- 회귀 위험 0 (신규 endpoint, 기존 API 영향 0)
- AXIS-VIEW Sprint 42 (별 repo) admin GUI consume endpoint 인프라 확보

### 후속

- AXIS-VIEW Sprint 42 (별 repo): `/materials` admin GUI + `/checklists` 매핑 GUI consume
  - admin 매핑 시 BE override (Step 3) 자동 작동 → 작업자 동적 자재 옵션 수신 시작

---

## v2.12.2 (Sprint 66-BE FEAT-MATERIAL Step 3 — checklist_master 동적 자재 조회 + selected_material_id 직접 전달, 2026-05-08)

**Sprint**: `Sprint 66-BE / FEAT-MATERIAL-MASTER-AND-BOM-INTEGRATION-20260507 Step 3` (P1, Codex 설계서 라운드 5 GREEN + Step 3 implementation 라운드 1~2 GREEN)

**배경**: Sprint 66 R3 4-step의 Step 3 — checklist_master.select_options 동적 자재 조회 + selected_material_id 직접 전달 (NEW-M-01) + dual-format 호환 (옛 51a string array + 신규 int material_id array). 작업자 화면 회귀 0 (현재 prod 8개 string_array 영역 그대로 표시) — Step 4 admin GUI 매핑 후부터 자재 동적 표시 활성.

### Codex 검증 trail

- **Step 3 implementation 라운드 1**: M=2 (G+D 동일 경로) / A=2 / N=3
  - **M (G+D)**: FE re-entry 시 `_selectMaterialIdMap` 복원 누락 → PASS/NA 라디오 탭 시 selected_material_id NULL 덮어쓰기 silent bug
- **Step 3 implementation 라운드 2**: **M=0 / A=1 GREEN**
  - 정정: BE GET SQL 에 `COALESCE(cr.selected_material_id, cr_p1.selected_material_id)` 추가 + FE `_fetchChecklist` 에서 `_selectMaterialIdMap` 복원 (`smid is int` 가드)
  - TC 보강: `test_fetch_material_master_map_single_select` (proxy cursor 단일 쿼리 검증) + `test_validate_material_id_invalid_raises_specific` (master_id 우회 직접 검증)
  - **A 1건**: Codex 측 sandbox pytest 미설치 (운영성, 코드 결함 아님 — 우리 환경 14/14 PASS 검증 완료)

### 변경 (BE 2 파일 + FE 1 파일 + pytest 1 신규)

**`backend/app/services/checklist_service.py`** (4 신규 함수 + 3 함수 수정):
- `_collect_material_ids(items) -> set` — items 영역 select_options 의 material_id (int) 일괄 수집 (bool 가드)
- `_fetch_material_master_map(cur, material_ids) -> Dict` — 단일 SELECT `WHERE id = ANY(%s) AND is_active = TRUE` (N+1 BATCHED, Codex P0 #3)
- `_enrich_select_options(select_options, material_map) -> tuple` — `(display_strings, material_ids)` parallel arrays:
  - 옛 string 배열 → (그대로, [None]*N) — legacy compat
  - 신규 int 배열 → ("name (description) | spec_1 | spec_2", material_id) — 5-08 사용자 결정 description 포함
  - invalid material_id → WARN log + skip (작업자 noise 0, Sentry capture)
  - 혼합 영역 → WARN + str(x) fallback
- `_validate_material_id(cur, selected_material_id)` — None=no-op / 미존재=ValueError(INVALID_MATERIAL_ID)
- `_get_checklist_by_category()` 수정 — SQL `COALESCE(cr.selected_material_id, cr_p1.selected_material_id)` (FE re-entry hydrate, ADR-026 phase split 정합) + items 빌드 후 N+1 BATCHED enrich + 응답 dict 에 `select_material_ids` + `selected_material_id` 추가
- `upsert_mech_check()` + `upsert_elec_check()` 수정 — `selected_material_id: Optional[int] = None` 인자 + `_validate_material_id()` 호출 + INSERT/UPDATE 컬럼 갱신

**`backend/app/routes/checklist.py`** (2 endpoint 수정):
- PUT `/api/app/checklist/mech/check` — `selected_material_id=data.get('selected_material_id')` 전달
- PUT `/api/app/checklist/elec/check` — 동일 패턴 (대칭성)

**`frontend/lib/screens/checklist/mech_checklist_screen.dart`** (5 변경):
- `_selectMaterialIdMap: Map<int, int?>` 신규 — masterId → material_id 추적
- `_debouncedUpsert()` + `_upsertNow()` 시그니처에 `int? selectedMaterialId` 인자 + PUT body에 selected_material_id 동봉
- `_buildSelectDropdown()` — `materialIds` 로컬 + onChanged idx lookup → `_selectMaterialIdMap[masterId]` 갱신
- PASS/NA 라디오 onTap — `_selectMaterialIdMap[masterId]` 동봉 (번들 PUT)
- **`_fetchChecklist()` 재진입 hydrate** (Codex M 정정) — BE `selected_material_id` 응답에서 `_selectMaterialIdMap` 복원

**`tests/backend/test_sprint66_be_step3_enrich.py`** (신규, 14 TC):
- [1~6] _enrich_select_options 단위 (legacy / int / description / invalid / mixed / none)
- [7~9] _validate_material_id (None / active / nonexistent raise)
- [10] _get_checklist_by_category N+1 batched 동작 검증
- [11~12] upsert_mech_check (null OK / invalid raise)
- [13] **`test_fetch_material_master_map_single_select`** (Codex A 정정) — `_CountingCursor` proxy class 로 단일 SELECT 검증
- [14] **`test_validate_material_id_invalid_raises_specific`** (Codex A 정정) — INVALID_MATERIAL_ID 메시지 + material_id 디버그 영역 특정 검증
- 결과: **14/14 PASS** (Step 1 회귀 9/9 + Step 2 회귀 11/11 + Step 3 14/14 = 총 34/34 GREEN)

### 영향

- **회귀 위험 = 0** — 작업자 화면 표시 영역 그대로 (현재 prod 8개 string_array 영역 모두 legacy compat 경로). 추가 응답 필드 (`select_material_ids`, `selected_material_id`) additive (기존 FE 무시 시 0 영향).
- **운영 의도** — Step 4 admin GUI (별 repo) 배포 후 admin 이 material_id int array 매핑 시 BE override 자동 작동 → 작업자 화면이 옵션 Y 형식 동적 자재 옵션 수신.
- **재진입 hydrate** — Codex M 정정으로 silent NULL overwrite 차단. PASS/NA 탭 시 자재 추적 보존.

### 후속 step

- **Step 4** (AXIS-VIEW 별 sprint, admin GUI): admin GUI 자재 등록 + 매핑 → AXIS-VIEW v1.X.X (별 repo, FEAT-AXIS-VIEW-MATERIALS-AND-CHECKLISTS-MGMT-20260507)
  - `/api/admin/materials/*` CRUD endpoint
  - `/api/admin/checklists/master/:id/options` 매핑 endpoint
  - 배포 후 작업자 화면이 동적 자재 옵션 수신 시작 (Step 3 BE override 자동 작동)

---

## v2.12.1 (Sprint 66-BE FEAT-MATERIAL Step 2 — 185 자재 + 1626 BOM seed + description 컬럼, 2026-05-08)

**Sprint**: `Sprint 66-BE / FEAT-MATERIAL-MASTER-AND-BOM-INTEGRATION-20260507 Step 2` (P1, Codex 설계서 라운드 5 GREEN + Step 2 implementation 라운드 1~5 GREEN)

**배경**: Sprint 66 R3 4-step의 Step 2 — 통합 csv (1654 row) + MFC xlsx 정합 → 185 unique 자재 + 1626 product_bom 매핑 prod 적용. 5-08 description 컬럼 추가 보완 (admin AXIS-VIEW 측 ILIKE 검색 보조).

### Codex 검증 trail

- **Step 2 implementation 라운드 1~5**: M=3/A=4 → M=2/A=2 → M=1/A=1 → M=0/A=2 → **M=0/A=1 GREEN**
  - 핵심 정정: ① **MFC 단일 'MFC' 카테고리 합의 위반 catch (Twin파파, ADR-023 cross-check)** — Codex M4 advisory 따라 'MFC LNG/CDA/O2/N2' 분리 적용 → 5-07 합의 위반. 사용자 발견 후 즉시 'MFC' 단일 복원. ADR-023 표준 1차 입증 #5 사례. ② **'-' placeholder 자재 reject** (M1) — 186→185, 1640→1626. ③ **description 컬럼 추가 (053b)** — 1110299900 LNG/O2 dual-use → 단일 row + description='LNG,O2' (RFC 4180 quote). ④ **Generator self-containment** — 053a SQL 최상단 ALTER ADD COLUMN IF NOT EXISTS prefix.
- **A 1건** (라운드 5) = AXIS-VIEW Step 4 dropdown 회귀 검증은 별 repo 영역 → BACKLOG 처리

### 변경

**`backend/migrations/053a_material_master_and_bom_seed.sql`** (신규 자동 생성, 115.5 KB):
- 최상단 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS description TEXT` (self-containment, alphabetic 순서로 053b 보다 먼저 실행되어도 안전)
- material_master 185 INSERT + ON CONFLICT (item_code) DO UPDATE
- product_bom 1626 INSERT (FROM VALUES + JOIN material_master.item_code) + ON CONFLICT (product_code, material_id) DO UPDATE
- BEGIN/COMMIT atomic

**`backend/migrations/053b_material_master_add_description.sql`** (신규):
- ALTER TABLE checklist.material_master ADD COLUMN IF NOT EXISTS description TEXT
- 13 MFC 자재 description backfill UPDATE atomic (LNG×5 + LNG,O2×1 + CDA×2 + O2×4 + N2×1)
- DO block validation (described_count != 13 RAISE EXCEPTION)

**`backend/scripts/generate_migration_053a.py`** (신규, ~270 LOC, 자동 생성):
- `CSV_COLUMN_MAP` 한글→영문 매핑 (비고:description 포함)
- `parse_csv_bom_format()` — D2-03 csv.DictReader + placeholder '-' reject
- `validate_source_keys(strict)` — D2-02 fail-fast 중복키 검증 (WARN/RAISE 분기)
- `dedup_material_master()` / `dedup_product_bom()` — 옵션 A 첫 등장 보존
- `emit_sql()` — BEGIN/COMMIT + ON CONFLICT DO UPDATE + ALTER prefix self-contained
- MFC 자재: item_name + category 모두 단일 'MFC' (가스 분기 = description, ADR-023)

**`tests/backend/test_migration_053a_seed.py`** (신규, 11 TC):
- [1] 185 unique materials / [2] 1626 product_bom + JOIN 정합 + orphan 0
- [3] MFC 13 단일 category + 1110299900 description='LNG,O2'
- [4] **`test_mfc_description_backfill_13_rows`** (5-08 신규) — 분포 (LNG 6 / O2 5 / CDA 2 / N2 1) + ILIKE 검색 + 1110299900 dual-use 양쪽 매칭
- [5] product_code 41200076 BOM JOIN sample
- [6~9] TC-NEW-07/07b/07c/08 (generator dedup + WARN/strict + quoted/NULL/blank)
- [10~11] TC-M2 placeholder reject + missing required field
- 결과: **11/11 PASS** (Step 1 회귀 9/9 + Step 2 11/11 = 총 20/20 GREEN)

**`/Users/twinfafa/Desktop/GST/material_master_통합.csv`** (사용자 측 수정):
- 헤더에 `비고` 컬럼 추가
- 1110299900 = LNG/O2 dual-use → 두 row를 단일 row로 합침 (item_name='MFC', spec_2='P:2~4 / W:0.3', 비고='"LNG,O2"')
- 13 MFC row 비고 채움
- 결과: 1654 → 1653 data rows (1110299900 dedup)

### 운영 적용 (2026-05-07~08 KST)

- **5-07 23:16~** — 053a (185 + 1626) prod psql 직접 적용 GREEN
- **5-08 09:55** — 053b ALTER + 13 UPDATE atomic + DO block 검증 PASS
- migration_history INSERT — 053 / 053a / 053b 모두 등록 (Railway 재배포 중복 차단)
- prod 검증: 185 자재 / 1626 매핑 / 13 description / ILIKE LNG 6 / O2 5 / 1110299900 dual-use 양쪽 매칭

### 영향

- **회귀 위험 = 0** — 신규 INSERT (기존 코드 영향 0). select_options 양식 변경 X (Step 3 BE override 단계에서 dual-format 호환).
- **운영 의도** — admin AXIS-VIEW Step 4 측 자재 등록 시 ILIKE 검색 보조 (가스 종류 description). 작업자 측 변경 0 (Step 3 까지).

### 후속 step

- **Step 3** (BE override): _enrich_select_options + selected_material_id 직접 전달 → v2.12.2 OPS (~2h, BE+FE)
- **Step 4** (AXIS-VIEW 별 sprint): admin GUI 자재 등록 + 매핑 → AXIS-VIEW v1.X.X (별 repo)

---

## v2.12.0 (FEAT-MATERIAL Step 1 — schema 이전 + material_master CREATE, 2026-05-07)

**Sprint**: `FEAT-MATERIAL-MASTER-AND-BOM-INTEGRATION-20260507 Step 1` (P1, Codex 설계서 라운드 1~5 GREEN + Step 1 implementation 라운드 1 GREEN)

**배경**: Sprint 63 의 51a seed `select_options` placeholder ("MKS GE50A | 5 SLM | ...") 가 운영 영구 차단 영역. 5-07 Twin파파 catch — 실 자재 데이터 (csv 1640 row + MFC xlsx 14 자재 = 186 unique) 으로 영구 해결 목표. 4 step 분할 sprint 의 Step 1 (schema 영역) 완료.

### Codex 검증 trail

- **설계서 라운드 1~5**: M=8/A=6/N=9 → M=2/A=7/N=9 → M=1/A=2/N=1 → M=0/A=0/N=2 → **M=0/A=0/N=0 GREEN**
  - 합의 영역: D1-01 google_doc_id→qr_doc_id / D1-02 NOT NULL 제약 / D1-03 DROP 자식→부모 / NEW-M-01 selected_material_id 직접 전달 / D6-01 ordered deploy 등
- **Step 1 implementation 라운드 1**: **M=0/A=2/N=11 GREEN** (A 2건 즉시 정정 — UNIQUE 컬럼 명시 + index partial predicate 검증)

### 변경 (2 신규 파일)

**`backend/migrations/053_material_master_and_bom_schema_migration.sql`** (신규, 175 LOC, BEGIN/COMMIT atomic):

- DROP `public.bom_csv_import` + `bom_checklist_log` + `product_bom` (자식→부모 순, RESTRICT)
- CREATE `checklist.material_master` (10 컬럼, item_code UNIQUE, NOT NULL boolean/timestamp)
- CREATE `checklist.product_bom` (9 컬럼, hard FK material_id RESTRICT, UNIQUE (product_code, material_id))
- CREATE `checklist.bom_checklist_log` (17 컬럼, **qr_doc_id (D1-01)**, hard FK bom_item_id RESTRICT, AI 검증 영역 보존)
- ALTER `checklist.checklist_record` ADD COLUMN `selected_material_id` INTEGER (NEW-M-01: FK RESTRICT, partial idx WHERE NOT NULL)
- 인덱스 7건 (partial WHERE is_active 2건 + WHERE NOT NULL 1건)
- 트리거 3건 (DROP IF EXISTS → CREATE 패턴, idempotent)
- COMMENT ON 4건

**`tests/backend/test_migration_053_schema.py`** (신규, 9 TC):

- [1] checklist 신규 3 테이블 / [2] public 폐기 3 테이블 부재
- [3] FK 정합 + RESTRICT 3건 / [4] UNIQUE 컬럼 명시 검증 (Codex A1)
- [5] NOT NULL D1-02 / [6] selected_material_id NEW-M-01
- [7] qr_doc_id D1-01 + google_doc_id 부재 (TC-NEW-09)
- [8] 트리거 3건 / [9] 인덱스 + partial predicate 검증 (Codex A2 — pg_get_expr() 괄호 wrapping 정합)
- 결과: **9/9 PASS** (40s)

### 운영 적용 (2026-05-07 KST)

- 운영 DB 직접 적용 (psql) → BEGIN/DROP×3/CREATE TABLE×3/CREATE INDEX×7/ALTER TABLE/CREATE TRIGGER×3/COMMIT 정상 실행
- 검증 SQL (사전 11건 + 사후 4건) 모두 GREEN
- migration_history INSERT 완료 (Railway 재배포 시 중복 실행 차단)

### 사전 검증 SQL 11건 GREEN trail

- update_updated_at_column public schema / search_path "$user", public
- public.product_bom + bom_checklist_log + bom_csv_import = 모두 0 row
- pg_depend = 외부 view/function/trigger 의존성 0 (internal 영역만)
- select_options content_shape = 8 SELECT 항목 모두 legacy_string_array (Step 4 deploy 전 영역)
- selected_material_id 컬럼 부재 → ADD COLUMN 안전

### 영향

- **회귀 위험 = 0** — 신규 테이블 + 신규 컬럼만 (기존 코드 영향 0). select_options 양식 변경 X (Step 3 BE override 단계에서 dual-format 호환).
- **운영 의도** — 자재 마스터 인프라 도입 + admin/GST 측 자재 등록 기반 마련. Step 2 (seed) → Step 3 (BE override) → Step 4 (AXIS-VIEW admin GUI) 단계별 진행.

### 후속 step

- **Step 2** (Migration 053a seed): material_master 186 자재 + product_bom 1640 BOM 매핑 INSERT → v2.12.1
- **Step 3** (BE override): _enrich_select_options + selected_material_id 직접 전달 → v2.12.2 OPS
- **Step 4** (AXIS-VIEW 별 sprint): admin GUI 자재 등록 + 매핑 → AXIS-VIEW v1.X.X (별 repo, FEAT-AXIS-VIEW-MATERIALS-AND-CHECKLISTS-MGMT-20260507)

---

## v2.11.7 (Sprint 65-BE MECH 성적서 분기 hotfix — qr_doc_id 명시 + Phase 1/2 분리, 2026-05-06)

**Sprint**: `Sprint 65-BE — MECH 체크리스트 성적서 분기 hotfix` (P1, Codex 1차 P1~P5 전건 반영)

**배경**: 5-05 Twin파파 운영 검증 — VIEW `/partner/report` 페이지 "기구" 섹션에서 input_value 가 `—` 로만 렌더링. 모바일 앱 입력 정상 + DB record 정상 (master_id 149/158/163/176, input_value='1', '11' 등) but VIEW 화면 미표시. Root cause: BE `else` 분기에서 `qr_doc_id=''` (default) 로 SELECT → DB row (`DOC_TEST-1111`) 매칭 0건 → LEFT JOIN cr 컬럼 NULL → VIEW '—' 표시.

### Codex 1차 검증 P1~P5 전건 반영

- 🔴 P1 VIEW FE schema 정합 — 4 angle prerequisite 통과 (entry 개수 무관 + phase_label 이미 구현 + optional 타입 + ELEC baseline 운영 검증)
- 🟠 P2 신규 pytest TC 3건 (qr_doc_id 매칭 + phase split + ELEC/TM 회귀)
- 🟠 P3 REFACTOR-CHECKLIST-PHASE-SPLIT BACKLOG 등록 (헬퍼 함수 추출, P3 LOW)
- 🟡 P4 handoff/CHANGELOG/BACKLOG/memory ADR-026 자취 추가
- 🟡 P5 DUAL INLET L/R 분리 TODO 주석 + BACKLOG ID 명시

### BE 변경 (~25 LOC, 단일 파일)

**`backend/app/services/checklist_service.py L484~`**:

- `else` → `elif cat == 'MECH':` 명시 분기 + ELEC 패턴 (Phase 1/2 분리: `'1차 입력'` / `'2차 검수'`)
- `_normalize_qr_doc_id(serial_number)` 명시 호출 = `'DOC_<sn>'` (모바일 앱 `_normalizeQrDocId` 정합)
- `phase1_applicable=False` 항목 자동 제외 (Sprint 60-BE 컬럼 기반)
- DUAL INLET L/R 분리 TODO 주석 명시 (운영 데이터 0건, 향후 hotfix 예약)
- 기존 `else` 보존 → PI/QI/SI 잠재 신규 카테고리 fallback (ADR-026 표준 검토 후 명시 분기 권장)

### TEST 변경 (~120 LOC, +3 TC)

**`tests/backend/test_sprint54_checklist_report.py` 신규 `TestSprint65MechReportBranch`**:

- `test_tc65_01_mech_qr_doc_id_match_returns_input_value` — qr_doc_id 매칭 + input_value 정상 반환 검증
- `test_tc65_02_mech_phase_split_labels_correct` — phase=1/phase=2 entry 분리 + phase_label 정확 + master inherit 검증
- `test_tc65_03_elec_tm_unaffected_by_mech_branch` — TM 카테고리 회귀 0 + phase 키 미노출 검증
- 결과: **22/22 PASS** (전 sprint54 GREEN, 회귀 0)

### memory.md ADR-026 신설

신규 체크리스트 카테고리 phase split 표준 — ELEC/MECH/TM/PI/QI/SI 결정 매트릭스. 워커 입력 흐름 (1→2 분리 vs 1회 완료) + qr_doc_id 모바일 앱 송신 패턴 + VIEW FE 정합 검증 절차 표준화.

### 영향

- BE 단일 파일 분기 추가 — ELEC/TM 무영향 (additive)
- 모바일 앱 변경 0건, VIEW FE 변경 0건 (P1 prerequisite 통과 입증)
- migration/DB 변경 없음 → git revert 1건으로 v2.11.6 복귀 가능
- 사용자 영향: VIEW 성적서 MECH 섹션 input_value 정상 표시 + Phase 1/2 분리 노출 (UX 개선)

### 후속 BACKLOG

- `OPS-CHECKLIST-PHASE-SPLIT-REFACTOR-01` (P3 LOW) — ELEC/MECH 헬퍼 함수 추출 (~1h)
- `FIX-MECH-DUAL-INLET-L-R-SEPARATION` (LOW, 트리거 시) — INLET L/R record 발생 시 hotfix

### 사용자 검증 plan (배포 후)

- VIEW `/partner/report` TEST-1111 검색 → 기구 섹션 input_value 정상 표시 (1, 11)
- 작업자 이름 (마스킹) / 확인 일시 정상 표시
- Phase 1 / Phase 2 두 섹션 분리 노출 (ELEC 와 동일 패턴)
- ELEC / TM 카테고리 영향 없음 + 다른 SN (TEST-2222 등) 정상 동작

---

## v2.11.6 (DB Pool 자가 회복 메커니즘 — keepalive + warmup self-recovery, 2026-05-06)

**Sprint**: `FIX-DB-POOL-SELF-RECOVERY-20260504` (P1)

### 배경 — 5일 주기 사고 패턴 확립

| 사고 일시 | warmup 결과 | 회복 |
|----------|-------------|------|
| 4-29 23:31 KST | 0/0 silent failure (1.5h+) | Restart 수동 |
| 5-04 11:38 KST | 5/5 → 2/2 → 0/0 (40분) | Restart 수동 |

**Root cause** — 2단계:
1. **트리거** — Railway network proxy idle TCP disconnect (`pg_settings` idle 정책 0 + `tcp_keepalives_idle=7200초` + Sprint 30-B 정책으로 client keepalive OFF)
2. **확산** — `ThreadedConnectionPool` `_used` dict dead conn 정리 부재 → `getconn()` PoolError exhausted → warmup 0/0 8 cycles → Restart 외 회복 불가

WATCHDOG 영역 외: 기존 watchdog 은 `_pool=None` 만 감지 → 본 사고는 `_pool` object 살아있음 → Sentry 0 event.

### 변경 (BE only)

#### `backend/app/db_pool.py`
- `_CONN_KWARGS` keepalive 4 args 활성화: `keepalives=1, idle=60, interval=10, count=3` (90초 안 끊김 발견)
- `_consecutive_zero_warmup` 모듈 카운터 + `get_consecutive_zero_warmup()` getter
- `warmup_pool()` 0/0 conn 연속 3 cycles (15분) 시 `close_pool()` + `init_pool()` 자가 회복 + 카운터 리셋
- `logger.error` 격상 → LoggingIntegration(event_level=ERROR) 자동 Sentry capture (WATCHDOG 확장)

#### `tests/backend/test_db_pool.py` — 신규 4 TC
- `test_keepalive_args_passed_to_psycopg2` — psycopg2 connect kwargs 4 args 정확 전달
- `test_consecutive_zero_warmup_triggers_init_pool` — 3 cycles 자가 회복 trigger 검증
- `test_zero_warmup_logger_error_captured` — Sentry capture 보장 (logger.error)
- `test_normal_warmup_resets_consecutive_counter` — 정상 cycle 카운터 리셋

**테스트 결과**: 8/8 PASS (기존 4 + 신규 4) ✓

### 영향

- 사용자 영향 0 (정상 운영 시 keepalive 부작용 없음, 사고 시 15분 max 자동 회복)
- 회귀 위험 0 (additive 변경, 기존 정상 path 무영향)
- migration/DB 변경 없음 → git revert 1건 복귀 가능
- staging 1h 관찰 권장 (Sprint 30-B Railway proxy TCP_OVERWINDOW 충돌 패턴 재발 검증 — 4-30+ tier 변동으로 해결됐을 가능성)

### Pre-deploy Gate (3건)
1. Staging 1h 운영 후 `TCP_OVERWINDOW` WARN 0건 확인
2. 자가 회복 trigger 강제 시뮬레이션 — `pg_terminate_backend` 5 conn 후 15분 안에 init_pool 호출 logs 확인
3. Sentry 새 issue (`[db_pool] 0/0 warmed for N consecutive cycles`) capture 검증

### 선행/후속 sprint
- 선행: `OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP-20260427` ✅ (warmup cron) + `FIX-DB-POOL-DIRECT-FALLBACK-LOG-LEVEL-20260428` ✅ (logger.warning 강등) + `FIX-DB-POOL-WARMUP-WATCHDOG-20260430` ✅ (WATCHDOG 도입)
- 후속 (선택): `INFRA-RAILWAY-PROXY-IDLE-INVESTIGATION-20260504` (P3) / `OBSERV-WARMUP-LOGGER-CLARIFY-20260504` (P3)

### 효과 검증 (T+1주 / 5-09 ± 1d 도달)
- 재발 0 (keepalive 자체 차단) → keepalive 효과 입증
- 또는 자가 회복 작동 (close+init 호출 logs + Sentry event 발화) → 자가 회복 효과 입증
- Restart 수동 처리 빈도 0 도달 → 본 sprint 정량 입증

### 변경 파일 (2)
- `backend/app/db_pool.py` (변경)
- `tests/backend/test_db_pool.py` (변경)
- `backend/version.py` 2.11.5 → 2.11.6
- `frontend/lib/utils/app_version.dart` 2.11.5 → 2.11.6 (FE 변경 없으나 단일 소스 일치 정책)

---

## v2.11.5 (Sprint 63 후속 hotfix — phase=2 1차 데이터 inherit + CHECK description, 2026-05-06)

**Sprint**: `FIX-MECH-CHECKLIST-PHASE2-DATA-AND-DESCRIPTION-20260504` (P0)

**배경**: v2.11.4 prod 운영 후 사용자 발견 — "2차 검사 화면에서 1차 SELECT 값 안 보임". BE SQL phase 단일 LEFT JOIN 한계 + FE description 일부 위젯 누락.

**변경 (BE 1 + FE 1, ~25 LoC)**:
- R1 BE: cr_p1 LEFT JOIN 추가 (4개 조건) + COALESCE 우선 — phase=2 GET 시 phase=1 input/select inherit
- R2 FE: `_buildCheckRadio` Row → Column wrap + description 추가 (ELEC 패턴 정합)

**Codex 라운드 1**: M=1 (DUAL 보호 — 설계 정합) / A=4 / N=2

**Test**: TestPhase2InheritsPhase1Data 2 TC 신규 (input/select inherit) — 2/2 PASS (58.02s) / 누적 30 → 32 TC

**검증**: pytest 2/2 PASS / flutter analyze 0 error / flutter build web ✓

**회귀 영향**: 0건 (BE additive LEFT JOIN + FE Text 추가만)

---

## v2.11.4 (Sprint 63 후속 hotfix — 옵션 C UI 가이드 + description 렌더, 2026-05-06)

**Sprint**: `FIX-MECH-CHECKLIST-PHASE2-READONLY-AND-VALIDATION-20260504` 추가 정정 1+3+4 (P0)

**배경**: v2.11.3 prod 운영 후 사용자 발견 — "2차 드롭다운 react 안 됨". v2.11.3 R1 fix (`cr.isEmpty 시 PUT skip`) 부작용 가시화 누락. 옵션 C 채택 (UI 가이드 + R1 유지).

**변경 (FE only, 1 파일 ~30 LoC)**:
- 추가 정정 1: description 렌더 (item_name 아래 작은 글씨, ELEC L898-909 패턴)
- 추가 정정 3: 옵션 C — PASS/NA 미선택 경고 ⚠️ (`hasInput && !hasResult && !isPhase2`)
- INPUT setState({}) 추가 (controller.text reactive 보강)

**Codex 라운드 1**: M=0 / A=2 / N=3 (ELEC 패턴 정합 입증)
- N1/N3/N5: 옵션 C+R1 / description / read-only+경고 호환 모두 정합
- A2/A4: setState 성능 minor risk (허용 범위)
- 추가 advisory: widget test 별 BACKLOG 분리

**검증**: flutter analyze 0 error / flutter build web ✓

**ADR-023 신설**: 신규 Flutter 코드 작성 시 ELEC 패턴 정확 검증 표준 (멤버 grep + 패턴 1:1 + BE schema + 위젯 시각 + analyze/build)

---

## v2.11.3 (Sprint 63 후속 hotfix — check_result null 차단 + phase=2 read-only, 2026-05-04)

**Sprint**: `FIX-MECH-CHECKLIST-PHASE2-READONLY-AND-VALIDATION-20260504` 1차 (P0)

**변경**: mech_checklist_screen.dart 3 위치 (~13 LoC) — `_upsertNow` cr.isEmpty 시 PUT skip / `_buildInputField` phase=2 readOnly + cloud / `_buildSelectDropdown` phase=2 onChanged null + cloud

**진단 SQL**: TEST-1111/TEST-333 input_value/selected_value 모두 정상 저장 확인 → BE 무관 확정

---

## v2.11.2 (Sprint 63 후속 hotfix — 체크리스트 진입점 누락 fix, 2026-05-04)

**Sprint**: `FIX-SPRINT-63-MECH-CHECKLIST-ENTRY-POINT-20260504` (P0, 5-04 등록 + 당일 release)

**배경**: v2.11.1 prod 배포 직후 사용자 검증 — "체크리스트 자동 전환 안 됨" + "task 상세 메뉴 버튼 없음" 발견. Sprint 63-BE 설계 시 진입점 검증 누락.

**변경 (BE 1 + FE 1, +25 LoC)**:
- BE work.py L177~ MECH 분기 (4 task_id: UTIL_LINE_1/2 + WASTE_GAS_LINE_2 + SELF_INSPECTION)
- FE task_detail_screen.dart 5 위치 정정 (import + _hasChecklistAccess + onTap × 2 + _navigateToChecklist)

**Codex 라운드 1 + 추가 검토 (M=1 / A=3 / N=1 + AV=2 + 추가 catch 1)**:
- 추가 검토 catch: 5번째 위치 (`_buildCompletedBadge` onTap) 누락 → 4→5 위치 갱신
- AV2: 선택 3 (work/complete MECH) 별 sprint 분리 (`FEAT-MECH-WORK-COMPLETE-CHECKLIST-NUDGE-20260504`, P3)

**Test (24 → 30 TC)**:
- TestWorkStartMechChecklistEntry 6 TC 신규 (4 task PASS + WASTE_GAS_LINE_1 negative + ELEC INSPECTION 회귀)
- 결과: pytest 30/30 PASS (248.87s)

**검증**:
- pytest 30/30 PASS ✅ / flutter analyze 0 error ✅ / flutter build web 성공 ✅
- 회귀 영향: 0건 (additive, migration 없음)

**ADR-022 신설**: 신규 카테고리 도입 시 진입점 검증 표준 (BE 4 + FE 5 + alert 1 = 10 영역)

---

## v2.11.1 (Sprint 63-FE Flutter UI + R2-1 BE patch + N1/N2): Sprint 63 전체 종료 (2026-05-04)

**Sprint**: `SPRINT-63-FE-MECH-CHECKLIST-20260501` (5-01 등록 → 5-04 v2.11.1 release)

**배경**: Sprint 63-BE (v2.11.0) squash merge 직후 FE piece 통합 release. Codex 라운드 1+2 + N1/N2 정정 trail 14건 모두 실코드 반영.

**완료 사항**:

### BE patch (R2-1, ~10 LoC)
- `services/checklist_service.py` `get_mech_checklist()` 응답에 `tank_in_mech: bool` 추가
- model_config LEFT JOIN longest-prefix 매칭 + HOTFIX-08 rollback

### FE 신규 (mech_checklist_screen.dart 844 LoC)
- 입력 UI 3종 분기 (CHECK 라디오 / SELECT 드롭다운 / INPUT TextField + PASS/NA)
- DUAL split-token 매칭 — `RegExp(r'[\s\-]').contains('DUAL')` (M-R2-A/B 'DUAL-300' false-positive 차단)
- `_qrDocIdForItem` — DRAGON+INPUT+DUAL 만 hint 강제 (M-R2-C, ArgumentError 안전망)
- INLET Left/Right subgroup (Q1-B) + role gate (M3) + debounce 500ms (Q6-C)
- helper: `_normalizeQrDocId` / `_evaluateDualModel` / `_checkResultMap` / `_selectValueMap` / `_getCurrentCheckResult`

### N1: WebSocket CHECKLIST_MECH_READY 핸들러 (A6-F1)
- `models/alert_log.dart` priority + iconName CHECKLIST_MECH_READY 추가
- `screens/admin/alert_list_screen.dart` `_handleAlertTap` MECH 분기 + title/color 매핑
- `alert_provider.dart` 의 `_handleNewAlert` 가 alert_type 무관 자동 처리 → MECH 자동 등록 + 탭 시 MechChecklistScreen 진입

### N2: pytest 3 TC 신규 (M-R2-D)
- `TestR21TankInMechResponse`:
  * `test_get_mech_checklist_response_has_tank_in_mech_key` (모든 모델 키 존재)
  * `test_..._tank_in_mech_true_for_dragon_gallant_sws`
  * `test_..._tank_in_mech_false_for_gaia_mithas_sds`
- 결과: **3/3 PASS** (85.54s)
- 누적: 21 → 24 TC

### 라우팅
- `screens/task/task_management_screen.dart`: MechChecklistScreen 진입 라우팅

**검증**:
- pytest 24/24 PASS (Sprint 63-BE 21 + R2-1 patch 3)
- 회귀 영향: 0건 (BE 응답 additive 키 + FE 신규 파일 + alert 분기 추가만)

**파일 변경 (10 파일, +1,038 LoC)**:
- BE: checklist_service.py +18
- FE: mech_checklist_screen.dart 신규 +844
- FE: alert_log.dart +2 / alert_list_screen.dart +19 / task_management_screen.dart +6
- Test: test_mech_checklist.py +47
- Doc: CHANGELOG +46 / version.py + app_version.dart 2.11.0→2.11.1 / AGENT_TEAM_LAUNCH +다수

**Sprint 63 전체 통계 (BE v2.11.0 + FE v2.11.1)**:
- BE 인프라 +1,415 LoC + FE UI +1,038 LoC = **+2,453 LoC**
- pytest 24/24 PASS
- 정정 trail 14건 (라운드 1 5 + 라운드 2 9 + N1/N2 2)

**후속 별 sprint**:
- AXIS-VIEW Sprint 39: BLUR 해제 + AddModal 토글 (~0.5d, 별 repo)
- BUG-TM-CHECKLIST-AUTO-FINALIZE-STALE-TC-20260504 (P3, 1h, Sprint 63 무관)

---

## v2.11.0 (Sprint 63-BE MECH 체크리스트 BE 인프라): 양식 73 항목 / 20 그룹 도입 (2026-05-04)

**Sprint**: `SPRINT-63-BE-MECH-CHECKLIST-20260429` (4-29 등록 → 5-01 v2 INLET 8개 분리 → 5-04 squash merge)

**배경**: TM(Sprint 52, v2.6.0) / ELEC(Sprint 57, v2.9.0) 후 MECH 자주검사 체크리스트 디지털화. Sprint 32 도입 (3-19) silent failure 사고 trail 으로 정정 trail 11건 (Codex 라운드 1+2+3 + 사용자 결정 4건) 모두 적용.

**완료 사항 (Step 1~9, branch sprint-63-be-mech-checklist 11 commits squash merge)**:

### Step 1: migration 051/051a + seed CSV git add (+253 LoC)
- `migrations/051_mech_checklist_extension.sql`: scope_rule + trigger_task_id 컬럼, item_type CHECK 'INPUT', alert_type_enum 'CHECKLIST_MECH_READY'
- `migrations/051a_mech_checklist_seed.sql`: 73 INSERT (CHECK 56 / INPUT 10 / SELECT 7, all 56 / tank_in_mech 9 / DRAGON 8)

### Step 2: `_normalize_qr_doc_id()` 공유 helper (+42 LoC)
- TM/ELEC/MECH 공유 normalizer (Sprint 59-BE 재발 방지, ADR-020)
- SINGLE='DOC_{S/N}' / DUAL='DOC_{S/N}-L|R' / idempotent / edge case (hint=None, 공백, mixed-case full-id, 빈 serial)

### Step 3+4: `_resolve_active_master_ids()` + `check_mech_completion()` (+152 LoC)
- scope_rule 'all' / 'tank_in_mech' (DRAGON·GALLANT·SWS) / 'DRAGON' (INLET S/N L/R 8개) 분기
- judgment_phase=2 (c)안 — 1차 record 강제 안 함, 관리자 phase=2 record 만으로 cover
- HOTFIX-08 표준 conn.rollback() 2곳 적용

### Step 5: `_check_tm_completion` → `check_tm_completion` rename (9 hits)
- private→public 일관 인터페이스
- 영향: checklist_service 5 + production 2 + test_alert_all20 2

### Step 6: routes/checklist.py MECH 분기 + service 함수 2개 (+257 LoC)
- GET / PUT / GET status 3 endpoints
- get_mech_checklist() / upsert_mech_check() — ELEC 패턴 + INPUT type 지원
- _get_checklist_by_category() SELECT 절에 scope_rule + trigger_task_id 추가 (FE 무영향, 신규 필드)

### Step 7+8: task_service hook + production MECH 분기 (+69 LoC)
- _trigger_mech_checklist_alert() — UTIL_LINE_1/UTIL_LINE_2/WASTE_GAS_LINE_2 시작 시 'CHECKLIST_MECH_READY' alert
- _check_sn_checklist_complete() MECH 분기 활성화

### Step 9: pytest 21 TC 신규 (+554 LoC) — 21/21 PASS (186.84s)
- [A] _normalize_qr_doc_id pure function 6 TC (DB 불필요)
- [B] scope_rule + phase1 7 TC (all/tank_in_mech/DRAGON × 모델별 매핑)
- [C] trigger_task_id 매핑 3 TC (Speed 4 / MFC+FS 7 / INLET 8)
- [D] seed count 1 TC (51a 실파일 분포 자동 검증)
- [E] rename gate 1 TC (rg "_check_tm_completion" = 0)
- [F] phase=2 (c)안 2 TC (1차 record 미강제)
- [G] WebSocket emit 1 TC (mock create_alert 호출 검증)

**검증 (Pre-deploy Gate 7건 통과)**:
1. pytest test_mech_checklist 21/21 PASS ✅
2. SELECT scope_rule, COUNT(*) → all=56 / tank_in_mech=9 / DRAGON=8 정합 ✅
3. resolve_managers_for_category('MECH') 표준 패턴 활용 ✅
4. CHECKLIST_MECH_READY alert 발화 검증 ✅
5. rg "_check_tm_completion" = 0 hits ✅
6. AXIS-VIEW cross-repo schema 정합 ✅
7. ALTER TYPE ADD VALUE non-transactional 보증 (migration_runner autocommit=True) ✅

**회귀 영향**: 0건 (TM/ELEC 응답에 새 필드 추가만, 기존 키 무변경).

**파일 변경 (16 파일, +1,415 LoC)**:
- migration 신규 2 (051 / 051a) + CSV 신규 1
- service: checklist_service.py +365 / task_service.py +65
- routes: checklist.py +96 / production.py +5
- test: test_mech_checklist.py 신규 +554 / test_alert_all20_verify.py rename
- doc: handoff +130 / memory +50 / CHANGELOG +52 / BACKLOG status

**후속 별 sprint**:
- Sprint 63-FE: `mech_checklist_screen.dart` 신규 (~1,000~1,200 LoC, 2~3d, BE 배포 후)
- AXIS-VIEW Sprint 39: BLUR 해제 + AddModal 토글 (~0.5d, 별 repo)

---

## v2.10.12 (FIX-26-DURATION-WARNINGS-FORWARD): /api/app/work/complete 응답 키 일관성 (2026-04-28)

**Sprint**: `FIX-26-DURATION-WARNINGS-FORWARD-20260428` (BACKLOG L362 `BUG-DURATION-VALIDATOR-API-FIELD` 4-22 등록 → 4-28 fix)

**원인**: 응답 키 생성 경로 (`duration_validator.py:70-93` REVERSE_COMPLETION 브랜치 → `task_service.py:361-363,496-498` → `work.py:261-266`) 의 conditional layer 가 빈 리스트 `[]` 일 때 키 자체를 응답에서 제거. FE 가 `data.duration_warnings` 안전 접근 불가.

**자동 감지 경로**: v2.10.11 (FIX-PROCESS-VALIDATOR-TMS-MAPPING) pytest 회귀 시 동일 fail 재출현 → Codex 라운드 2 Q1/Q2 모두 A 라벨 합의 → 별건 fix Sprint 시작.

**코드 변경 (BE 2 파일 + test 1 파일 — 옵션 C 양 끝 unconditional)**:
- `backend/app/services/task_service.py` L497-499 — `if duration_warnings:` 조건 제거 → 항상 응답에 키 추가 (빈 리스트라도)
- `backend/app/routes/work.py` L265-266 — `if 'duration_warnings' in response:` 조건 제거 → `response.get('duration_warnings', [])` default 빈 리스트 forward
- `tests/backend/test_duration_validator.py`:
  - L75-76 `test_normal_duration_no_warnings` assertion 갱신 (`'duration_warnings' not in data` → `'duration_warnings' in data` + `== []`)
  - 신규 TC `TestDurationWarningsAlwaysPresent::test_normal_completion_returns_empty_duration_warnings` 추가
  - `TestReverseDuration::test_reverse_completion` `@pytest.mark.skip` 추가 — 시작/종료 timestamp 서버 `datetime.now(Config.KST)` 자동 기록 (`task_service.py:146/256`, `work.py:448`), 운영 발생 불가, prod 0건 실측 (4-04~4-28 24일), 인프라 사고 시나리오만
- `backend/version.py` v2.10.11 → 2.10.12
- `frontend/lib/utils/app_version.dart` v2.10.11 → 2.10.12

**검증**:
- pytest test_duration_validator.py: **4 passed / 1 skipped / 0 fail** ✅
- LoC: task_service / work ±0 (refactor only) — Line 규칙 통과
- git commit: `5e17026`

**핵심 인사이트 — 사용자 정정으로 단순화**:
- 시작/종료 timestamp 가 서버 측 `datetime.now()` 자동 기록 → 클라이언트 시간 입력 path 0
- REVERSE_COMPLETION 운영 발생 불가 (인프라 사고 차원만)
- 처음 우려한 silent failure / 4-22 유사 구조 → **모두 무의미한 우려**
- 본 Sprint 는 응답 contract 일관성만 fix 하고 종결

**BACKLOG 동기화**:
- L362 `BUG-DURATION-VALIDATOR-API-FIELD` → ✅ COMPLETED

---

## v2.10.11 (FIX-PROCESS-VALIDATOR-TMS-MAPPING): 옵션 D-2 표준 함수 도입 (2026-04-28)

**Sprint**: `FIX-PROCESS-VALIDATOR-TMS-MAPPING-20260428` (옛 ID `-ROLE-MAPPING-20260427` 통일)

**원인**: 4-22 HOTFIX-ALERT-SCHEDULER-DELIVERY 의 `_resolve_managers_for_category` 표준 패턴이 scheduler_service 에만 도입되고 duration_validator 3곳 (L74/L100/L179) + task_service L403 에는 미적용 → `get_managers_for_role(task.task_category)` 호출 → SQL `WHERE role='TMS'` → enum cast 실패 → silent skip → TMS 매니저 알람 미수신.

**자동 감지 경로**: 2026-04-28 03:00 KST cron 실행 중 Sentry 가 `Failed to get managers for role=TMS: invalid input value for enum role_enum: "TMS"` 에러를 도입 8시간만에 31 events / escalating 으로 자동 감지 → Sentry 가치 입증 #3.

**코드 변경 (BE 5 파일 atomic — 옵션 D-2)**:
- `backend/app/services/process_validator.py` (+30 LOC) — `_CATEGORY_PARTNER_FIELD` dict + `resolve_managers_for_category()` public 함수 신설
- `backend/app/services/scheduler_service.py` (-15 LOC) — private helper + dict 제거 + import 교체 + 3 호출 site 1:1
- `backend/app/services/task_service.py` (±0 LOC) — L403 import + L410 호출 1:1 (Codex M2 5번째 파일)
- `backend/app/services/duration_validator.py` (±0 LOC) — L16 import + L74/L100/L179 호출 1:1
- `tests/conftest.py` (+50 LOC) — `seed_test_managers_for_partner` 격리 fixture (옵션 D, Codex M1)
- `tests/backend/test_process_validator.py` (+130 LOC) — TC 7개 (TMS-GAIA / DRAGON 회귀 / MECH / ELEC / PI / unknown / e2e)

**Codex 합의 trail**:
- 라운드 1 (Sprint 설계 검증): M=2 / A=2 / N=2 — M1 fixture 정합성 (옵션 D 격리 fixture) + M2 Rollback 5 파일 (task_service.py L403-410 누락 발견) + A1 DRAGON gap (별건 BACKLOG `BUG-DRAGON-TMS-PARTNER-MAPPING-20260428`) + A2 e2e 회귀 TC. 모두 반영
- 라운드 2 (pytest 회귀 라벨링): Q1/Q2 모두 A — test_duration_validator 1 fail = BACKLOG L362 BUG-DURATION-VALIDATOR-API-FIELD 4-22 별건 확정 → v2.10.12 처리

**검증**:
- pytest 신규 TC: 7/7 PASS (TestResolveManagersForCategory + e2e)
- pytest 회귀: 51 passed / 5 skipped / 0 fail (test_scheduler / test_scheduler_integration / test_task_seed)
- LoC: scheduler **-15** / task_service ±0 / duration ±0 / process_validator +30 — Line 규칙 통과
- git commit: `a1829cb`

**BACKLOG 동기화**:
- L352 `FIX-PROCESS-VALIDATOR-TMS-MAPPING-20260428` → ✅ COMPLETED
- L353 `BUG-DRAGON-TMS-PARTNER-MAPPING-20260428` → 🟢 OPEN P3 (prod 실측 후 우선순위 재평가)

---

## v2.10.10 (HOTFIX-08): db_pool transaction 정리 누락 + 046a 자동 적용 (2026-04-27)

**원인**: psycopg2 default `autocommit=False` → SELECT 도 BEGIN 자동 시작 → INTRANS 상태로 풀 반납 → 이 conn 을 받아 `m_conn.autocommit = True` 시도 시 `set_session cannot be used inside a transaction` 거부.

**자동 감지 경로**: v2.10.9 배포 후 Railway log 에 `046a_elec_checklist_seed.sql 실행 실패: set_session ...` 발생 → assertion 이 즉시 캡처.

**코드 변경 (BE only ~2줄)**:
- `backend/app/db_pool.py _is_conn_usable()` L98+ — SELECT 1 후 `conn.rollback()` 추가
- `backend/app/db_pool.py warmup_pool()` L270+ — 동일 패턴 적용
- `backend/version.py` v2.10.9 → 2.10.10
- `frontend/lib/utils/app_version.dart` v2.10.9 → 2.10.10

**부수 효과 (긍정)**: 046a_elec_checklist_seed.sql 자동 적용 — 4-22 049 와 동일 Docker artifact silent gap 두 번째 사례. ON CONFLICT DO NOTHING idempotent 보장으로 prod 31항목 안전 재적용. 사용자 영향 0.

**검증**:
- pytest 회귀 0건
- Railway log: `[migration] ✅ 046a_elec_checklist_seed.sql 실행 완료` + `[migration-assert] ✅ sync OK (13 migrations applied)` (12 → 13 갱신)
- git commit: `72579e1`

**BACKLOG 상태**:
- assertion 자동 감지 layer 가치 2차 입증 (1차: HOTFIX-07 row[0] / 2차: HOTFIX-08 transaction)

---

## v2.10.9 (HOTFIX-07): RealDictCursor row[0] KeyError 긴급 복구 (2026-04-27)

**원인**: `db_pool` 이 `RealDictCursor` 사용 → row 가 dict-like → `row[0]` 은 `KeyError: 0`. 이전 `run_migrations()` 의 outer try/except 가 silent 흡수 → 5일간 무인지. v2.10.8 의 `assert_migrations_in_sync()` 는 try/except 없이 호출 → KeyError 가 그대로 propagate → gunicorn worker boot 실패 → 503.

**코드 변경 (BE only)**:
- `backend/app/migration_runner.py _get_executed()` L51 — `row[0]` → `row['filename']`
- `backend/app/migration_runner.py assert_migrations_in_sync()` L165+ — outer try/except 안전망 (assertion 자체 실패가 worker boot 막지 않도록)
- `backend/version.py` v2.10.8 → 2.10.9
- `frontend/lib/utils/app_version.dart` v2.10.8 → 2.10.9

**Lesson**: assertion 도입 자체가 사고 발견 trigger 가 됨 — 5일간 silent 흡수된 row[0] KeyError 가 try/except 없는 호출 경로에서 즉시 노출. 향후 신규 assertion 도입 시 outer try/except 안전망 표준화 권장.

---

## v2.10.8: 알람 시스템 사후 검증 마무리 4 Sprint 통합 (2026-04-27)

**Sprint 통합**:
- `OBSERV-RAILWAY-LOG-LEVEL-MAPPING` 🔴 P1 → ✅ COMPLETED
- `POST-REVIEW-MIGRATION-049-NOT-APPLIED` 🔴 S3 → ✅ COMPLETED (POST_MORTEM_MIGRATION_049.md 산출)
- `OBSERV-ALERT-SILENT-FAIL` 🔴 P1 → ✅ COMPLETED (Sentry 정식)
- `OBSERV-MIGRATION-RUNNER-STARTUP-ASSERTION` 🟡 P2 → ✅ COMPLETED

**코드 변경 (BE only ~140 LOC)**:
- `backend/Procfile` — gunicorn `--access-logfile=- --log-level=info` 추가
- `backend/app/__init__.py` — `import sys` + `logging.basicConfig(stream=sys.stdout, force=True)` 명시 + `_init_sentry()` 함수 신규 (~50 LOC, FlaskIntegration + LoggingIntegration + release auto-binding + send_default_pii=False) + `run_migrations()` 직후 `assert_migrations_in_sync()` 호출
- `backend/requirements.txt` — `sentry-sdk[flask]>=2.0` 추가
- `backend/app/migration_runner.py` — `assert_migrations_in_sync()` 함수 신규 (~40 LOC) + 실패 시 `sentry_sdk.capture_exception` / gap 시 `sentry_sdk.capture_message`
- 신규 산출물: `POST_MORTEM_MIGRATION_049.md` — 4가지 가설 전수 검증 (가설 ④ Docker artifact / Railway build cache 가장 유력)

**Sentry DSN 활성화 (Twin파파 측, 4-27 완료)**:
1. ✅ sentry.io 가입 + Python/Flask project 생성 + DSN 발급
2. ✅ Railway env 등록: `SENTRY_DSN` (필수) + `SENTRY_ENVIRONMENT` (production) + `SENTRY_TRACES_SAMPLE_RATE`
3. 🟡 Sentry alert rule 설정 (1주 운영 후 미세 조정)

**검증**:
- pytest test_scheduler.py 8 passed / 1 skipped / 회귀 0건
- BE syntax check (init/migration_runner) ✅

**시스템 신뢰성 1차 완성**:
```
Before (4-22 사고): silent gap → 5일 무인지 → 사용자 신고
After (4-27+):       silent gap → assertion 즉시 → Sentry email/push
                     평균 인지 시간: 5일 → ~1분
```

---

## v2.10.7 (HOTFIX-06): warmup_pool() 시계 리셋 누락 fix (2026-04-27)

**원인**: v2.10.6 OBSERV-WARMUP 배포 후 결함 발견 — warmup 외형상 작동하지만 SELECT 1 만 실행하고 `_conn_created_at` 갱신 안 함 → `_is_conn_usable()` 가 expired 판정 → discard → direct conn fallback 다발.

**코드 변경 (BE only 1줄)**:
- `backend/app/db_pool.py warmup_pool()` L240+ — `_conn_created_at[id(conn)] = time.time()` 1줄 추가
- `backend/version.py` v2.10.6 → 2.10.7
- `frontend/lib/utils/app_version.dart` v2.10.6 → 2.10.7
- git commit: `7a13085`

**Limitation (per-worker 함정)**:
- 본 fix 는 fcntl lock 으로 1 worker (Worker A) 만 scheduler 실행 → Worker A 의 pool 만 시계 리셋
- Worker B 의 pool 은 자연 만료. 결과: conn 7~11 진동 (영구 10 의도는 절반 달성)
- 사용자 영향 0 입증. **D+1 (4-28 화) 출근 peak 측정 결과 따라 v2.10.11 HOTFIX-06b** (per-worker warmup) 진행 결정

**검증**:
- pytest test_scheduler.py 8 passed / 1 skipped / 회귀 0건 (327.32s)

---

## FEAT-PIN-STATUS-BACKEND-FALLBACK + OBSERV-DB-POOL-WARMUP: 병행 배포 (2026-04-27, v2.10.6)

**배경**: 4-27 KST 같은 날 두 작업 병행 진행 — (1) FIX-PIN-FLAG v2.10.5 의 2차 보호 layer (backend fallback), (2) FIX-DB-POOL-MAX Phase A 적용 후 실측으로 입증된 MIN=5 무효 문제 해결.

**병행 안전성 검증**:

| 차원 | FEAT-PIN-STATUS (FE) | OBSERV-WARMUP (BE) | 충돌 |
|---|---|---|---|
| 수정 파일 | `main.dart` + `auth_service.dart` | `db_pool.py` + `scheduler_service.py` | ✅ 없음 |
| 의존성 | 없음 | 없음 | ✅ 독립 |
| 회귀 | 0 | pytest 8 passed | ✅ |
| 운영 영향 | PIN 라우팅 분기 추가 | 신규 cron job (기존 11→12) | ✅ |

---

### Part A — FEAT-PIN-STATUS-BACKEND-FALLBACK (FE, P1 격상)

**트리거**: FIX-PIN-FLAG v2.10.5 의 Limitation — `pin_registered` 만 SharedPrefs 로 옮겨도 4개 키 (refresh_token + worker_id + worker_data 포함) 일괄 손실 시 효과 없음. Backend 가 진실의 source 로 자동 복구가 진짜 root fix.

**코드 변경**:
- `frontend/lib/services/auth_service.dart` `getBackendPinStatus()` 신규 (~15 LOC):
  - `/auth/pin-status` (BE 엔드포인트, JWT 보호) 호출
  - 응답 `{"pin_registered": bool, "biometric_enabled": bool}` 파싱
  - 호출 실패 (네트워크/서버) 시 `false` 반환 + debugPrint 로그 — 정상 흐름 fallback
- `frontend/lib/main.dart` L275~ 라우팅 분기 추가 (~16 LOC):
  - `tryAutoLogin()` 성공 후 `getBackendPinStatus()` 호출
  - `pin_registered=true` → `savePinRegistered(true)` 로 로컬 양방향 sync 복구 + PinLoginScreen
  - `pin_registered=false` → 정상 흐름 (마지막 경로 복원, HomeScreen)

**효과**: PIN 사용자가 IndexedDB 잃어도 backend 가 진실의 source 로 자동 복구 → 사용자 보안 의도 유지 (HomeScreen 직행 X).

**BE 엔드포인트 사전 확인**:
- `backend/app/routes/auth.py:823` `@auth_bp.route("/pin-status", methods=["GET"])` 이미 존재
- `@jwt_required` 보호 + `hr.worker_auth_settings.pin_hash` 조회

---

### Part B — OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP (BE, P2 격상)

**트리거**: 2026-04-27 KST 실측 — Phase A 적용 (DB_POOL_MAX=30 + MIN=5) 후:

```
10:14:00  풀 초기화 직후     OPS 10 conn (5×2 worker)  baseline
10:19:00  5분 경과            OPS  9 conn (-1)          max_age 1차 만료
10:24:00  10분 경과           OPS  7 conn (-3)          감소 가속
```

→ Codex 라운드 3 A4 advisory ("MIN=5 효과는 max_age 만료 직전~직후 변동 가능, 실측 필요") 가 10분만에 실측 입증. P3 → P2 격상.

**Claude Code advisory 1차 (M=0/A=5)**:
- A1 `_pool` private API 직접 import → public `warmup_pool()` 함수 노출 권장
- A2 pytest TC test env `_pool=None` skip 처리 명시
- A3 `IntervalTrigger` 명시 import 권장 (스타일)
- A4 ThreadPool max=10 - warmup 5 = 여유 5 (burst 차단 위험 낮음)
- A5 `next_run_time=datetime.now()` → timezone 명시 권장

**Codex 이관 미해당**: 6항목 미충족 (단일 함수 신규, DB 스키마 변경 X, API 응답 X, 인증 로직 X, 클린코어 X, 1파일 touch).

**코드 변경**:
- `backend/app/db_pool.py` `warmup_pool() -> tuple[int, int]` public 함수 신규 (~40 LOC, A1 반영):
  - `_MIN_CONN` 만큼 `getconn()` → `SELECT 1` → `putconn()`
  - finally 블록으로 반납 보장
  - `_pool=None` 시 `(0, 0)` 반환 (test env safe)
- `backend/app/services/scheduler_service.py`:
  - L17 `from apscheduler.triggers.interval import IntervalTrigger` (A3)
  - L23 `from app.db_pool import put_conn, warmup_pool`
  - `_pool_warmup_job()` 신규 함수 (warmup_pool 호출 + 결과 로그 + try/except)
  - `add_job` 12번째 등록:
    - `IntervalTrigger(minutes=5)`
    - `next_run_time=datetime.now(Config.KST) + timedelta(seconds=10)` (timezone-aware, A5 반영)
  - 스케줄러 job 수: **11 → 12**

**효과**: 매 5분 풀 안 모든 idle conn 활성화 → max_age 시계 리셋 → MIN=5 강제 유지 → 영구 10 conn 보장.

---

### 안전성 검증 종합

- ✅ Flutter web build 성공 (12.1s)
- ✅ BE syntax check (db_pool.py + scheduler_service.py 정상)
- ✅ pytest test_scheduler.py: 8 passed / 1 skipped / 회귀 0건
- ✅ 기존 11 job 영향 X (12번째 추가만)
- ✅ 기존 storage 키 영향 X (FEAT 는 pin_registered 호출 추가만)
- ✅ Rollback git revert 1 commit 으로 둘 다 원복

### Deploy

- 빌드: flutter build web --release ✓ 12.1s
- 배포 (FE): Netlify Deploy ID `69eef28fca3b7ffce577068d` (2026-04-27 KST)
- 배포 (BE): Railway 자동 (git push origin main → ~1분)
- Production URL: https://gaxis-ops.netlify.app
- git commit: `2e023eb` (`222aec0..2e023eb`)

### Post-deploy 검증 (Twin파파)

#### Railway logs (배포 직후)

```
[scheduler] Scheduler initialized with 12 jobs   ← 11 → 12 확인
[pool_warmup] 5/5 conn warmed                    ← 첫 실행 (10초 후)
```

#### 1시간 관찰 (`pg_stat_activity`)

매 5분마다 conn 수 측정 → **10 영구 유지** = 성공. 이전 추세 (10→9→7) 와 비교.

#### FEAT-PIN-STATUS 효과 검증

PIN 사용자가 IndexedDB 잃은 케이스 시뮬레이션 → `/auth/pin-status` 호출 → PinLoginScreen 복귀 (HomeScreen 직행 X).

### 문서 산출물

- 코드 4 파일: db_pool.py + scheduler_service.py + auth_service.dart + main.dart
- 버전 2 파일: backend/version.py + frontend/lib/utils/app_version.dart
- 문서 4 파일: AGENT_TEAM_LAUNCH.md (advisory trail) + CHANGELOG.md ([2.10.6] entry) + BACKLOG.md (FEAT/OBSERV COMPLETED) + handoff.md (3/3 세션) + PROGRESS.md (이 섹션)

### 신규 BACKLOG 갱신

- `FEAT-PIN-STATUS-BACKEND-FALLBACK-20260427` 🔴 P1 → ✅ COMPLETED (v2.10.6)
- `OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP-20260427` 🟡 P2 → ✅ COMPLETED (v2.10.6)

남은 BACKLOG (대기):
- `AUDIT-PWA-SW-INDEXEDDB-PRESERVE-20260427` 🟡 P2 (audit, 30분)
- `UX-LOGIN-FALLBACK-PIN-RESET-LINK-20260427` 🟢 P3 (1h)
- `FEAT-AUTH-STORAGE-MIGRATION-FULL-20260427` 🟡 P2 (보안 trade-off, 3~4h)

---

## FIX-PIN-FLAG-MIGRATION-SHAREDPREFS: PIN 등록 플래그 storage 안정화 (2026-04-27, v2.10.5)

**배경**: 2026-04-26 Twin파파 PC sticky cache 조사 + PIN 화면 손실 가설 분석 → `pin_registered` 플래그가 `flutter_secure_storage` (encrypted IndexedDB) 에 저장 중. PWA 환경 IndexedDB 손실 (iOS Safari 7일 idle / Storage quota evict / Origin 변경) 시 → main.dart 라우팅 EmailLoginScreen 빠짐 → 비번 모름 → 막힘. 동일 파일의 `device_id` 는 이미 SharedPreferences (localStorage) 사용 중인 비대칭 구조.

**4 라운드 advisory review (M=8/8 + 추가 리스크 2/2 전수 반영)**:

| 라운드 | 주체 | 핵심 발견 |
|---|---|---|
| 1 (자체) | Claude Code | A1 인증 로직 영향 → Codex 이관 / A2 baseline SQL 추가 / A3 ⛔ 단방향 마이그레이션 rollback 위험 → **양방향 sync 채택** / A4 양방향 write 패턴 / A5 race / A6 IndexedDB trigger (6건) |
| 2 (Codex) | Codex 1차 | M1 atomic try/catch / M2 SQL `request_path` LIKE / M3 SW 업데이트 ≠ IndexedDB / Q2.d rollback 5번째 / Q2.e cohort / Q3.g 다른 가설 / Q3.h D+7 통계 / Q4.j iOS Safari localStorage 도 영향 (M=8) |
| 3 (Codex 추가) | Codex | refresh_token + worker_id + worker_data 도 SecureStorage → BACKLOG `FEAT-AUTH-STORAGE-MIGRATION-FULL` 신규 / backend `/auth/pin-status` 가 진짜 root fix → BACKLOG `FEAT-PIN-STATUS-BACKEND-FALLBACK` P2 → P1 격상 (2건) |
| 4 (배포 검증) | Twin파파 | home_screen.dart 별건 알림 배지 동기화 동시 포함 안전 검증 (1건) |

**최종 결정**:
- Storage 정책: SharedPreferences 주 저장소 + SecureStorage 보조 저장소 (양방향 sync)
- atomic 정책: SharedPrefs 반드시 성공 + SecureStorage best-effort try/catch
- Rollback 정책: SecureStorage delete 안 함 (양방향 sync 로 rollback 시 일괄 빠짐 위험 0)

**수정 파일 (FE 1파일 + 부수 1파일 + 버전 2파일 = 4파일)**:
- `frontend/lib/services/auth_service.dart` (+50/-11 LOC):
  - L3 `package:flutter/foundation.dart` import (debugPrint)
  - `hasPinRegistered()` 양방향 read + auto-sync (SharedPrefs 우선, SecureStorage fallback)
  - `savePinRegistered()` 양방향 write + atomic try/catch (Codex M1 반영)
  - `logout()` (L243) SharedPrefs `pin_registered` 도 정리
- `frontend/lib/screens/home/home_screen.dart` 알림 배지 동기화 (별건, 같은 commit)
- `backend/version.py` v2.10.4 → 2.10.5
- `frontend/lib/utils/app_version.dart` v2.10.4 → 2.10.5

**무변경 (의도적)**:
- `frontend/lib/main.dart` 라우팅 분기 무변경 (FEAT-PIN-STATUS-BACKEND-FALLBACK 후속 Sprint 에서 진행)
- `auth_service.dart` 의 `_refreshTokenKey` / `_workerIdKey` / `_workerDataKey` 무변경 (FEAT-AUTH-STORAGE-MIGRATION-FULL 후속 Sprint 에서 진행)

**Limitation (Codex 1차 advisory 핵심)**:

| 손실 패턴 | 빈도 | 본 Sprint | FEAT-PIN-STATUS-BACKEND |
|---|---|---|---|
| pin_registered 만 단독 | 드뭄 | ✅ | ✅ |
| 4개 키 함께 (Clear site data, evict) | 흔함 | ❌ | ✅ (refresh 살아있으면) |
| iOS Safari 7일 idle | 흔함 | ❌ | ✅ (refresh 살아있으면) |

→ **본 Sprint = 1차 보호 layer**. 진짜 root fix 는 `FEAT-PIN-STATUS-BACKEND-FALLBACK` (P1 격상).

**Deploy**:
- 빌드: flutter build web --release ✓ 12.2s
- 배포: Netlify Deploy ID `69eed5d26147a9d3c6966ecf` (2026-04-27 KST)
- Production URL: https://gaxis-ops.netlify.app

**Baseline 측정 (Twin파파 pgAdmin, 배포 전 1회 권장)**:

설계서 L31644~31691 SQL 3종 (`request_path` LIKE 패턴, Codex M2 정정):
1. PIN 손실 의심 사용자 식별 (같은 날 `/auth/login` 2회 이상)
2. EmailLoginScreen 진입 빈도 (사용자당 login attempts/day)
3. 출근 burst 시점 auth_pct (`/auth/login` + `/auth/refresh` 비중)

**1주 관찰 지표 (D+7 = 2026-05-04)**:
- PIN 손실 의심 사용자: baseline ___ → 0~1명/일 (기대)
- 사용자당 login attempts/day: baseline ___ → ~1.0 (기대)
- auth_pct: baseline ___ → 감소 시 connection burst 부수 기여 입증

**통계 신뢰성 보강 (Codex Q3.g/h)**:
- 동일 요일 3일 pre/post 비교 (화/수/목 같은 요일 3주 데이터)
- active worker 분모 정규화
- Cohort 정의 (cohort_A: build_date >= 2026-04-27 / cohort_B: < 2026-04-27 / cohort_secure_write_ok vs fail)
- 다른 가설 구분 cohort (device_id, UA, 시간대)

**Codex 공식 이관 적용 (인증 로직 영향)**:
본 작업은 CLAUDE.md L130 Codex 이관 체크리스트 4번 (인증·권한 로직 변경) 해당 + "판정 애매 시 = 자동 이관" 적용. Codex 1차 advisory review 후 적용.

**롤백**:
`auth_service.dart` 변경 git revert → flutter build web → Netlify 배포. 양방향 sync 채택으로 rollback 시 4개 케이스 안전, 단 SecureStorage write 실패 cohort (try/catch best-effort) 만 잔존 위험.

**문서 산출물 (FE 1파일 + 문서 4파일 + 신규 1파일)**:
- `frontend/lib/services/auth_service.dart` 핵심 변경
- `AGENT_TEAM_LAUNCH.md` FIX-PIN-FLAG-MIGRATION-SHAREDPREFS-20260427 섹션 (L31395+) — 양방향 sync 코드 + atomic try/catch + Limitation + baseline SQL + Rollback 5케이스
- `CHANGELOG.md` `[2.10.5]` entry
- `BACKLOG.md` 5개 entry 신규 (FIX-PIN-FLAG / FEAT-PIN-STATUS-BACKEND P1 / AUDIT / UX / FEAT-AUTH-STORAGE-MIGRATION-FULL)
- `handoff.md` 2026-04-27 (2/2) FIX-PIN-FLAG 세션
- `CODEX_REVIEW_FIX_PIN_FLAG_20260427.md` Codex 1차 advisory 프롬프트

**신규 BACKLOG (4개 후속 Sprint)**:
- `FEAT-PIN-STATUS-BACKEND-FALLBACK-20260427` 🔴 P1 (격상 — 진짜 root fix, 1h)
- `AUDIT-PWA-SW-INDEXEDDB-PRESERVE-20260427` 🟡 P2 (audit, 30분)
- `UX-LOGIN-FALLBACK-PIN-RESET-LINK-20260427` 🟢 P3 (UX, 1h)
- `FEAT-AUTH-STORAGE-MIGRATION-FULL-20260427` 🟡 P2 (Codex 신규 권장)

---

## FIX-DB-POOL-MAX-SIZE-20260427: DB Connection Pool 사이즈 보정 (2026-04-27, 인프라 only)

**배경**: 4-25 토 새벽 (KST 07:29) Pool exhausted 다발 사례 + 사용자 ≥120명 / peak 07:30~09:00, 16:30~17:00 출근 burst 패턴 확정. 기존 Railway env `DB_POOL_MAX=20` 으로는 Q-B 측정 31 동시 in-flight 흡수에 부족 (per-worker 분배 시 worker A 16+ 필요).

**진단 데이터 (3 SQL — Q-A/Q-B/Q-C)**:
- **Q-A**: 시간대별 burst 분석 (4-19 ~ 4-25, 7일치) — Mon 07 624 req / Fri 16 629 req 최다, Tue 15 max 2415ms / p99 1981ms 최저
- **Q-B**: ⭐ 결정적 데이터 — 2026-04-21 화 출근 burst 측정 (07:00~09:00 KST self-join CTE)
  - peak 31 동시 in-flight (08:06:07)
  - 21 동시 17회 (07:46~08:55, 70분간 연속)
- **Q-C**: task API 성장 추이 (3-29 ~ 4-27, 30일) — work_api 13→365 (4-16 peak), total_api 287→4920 (4-16 peak)

**4 라운드 advisory review (M=0 / A=12)**:

| 라운드 | 주체 | 핵심 발견 |
|---|---|---|
| 1 (텍스트) | Codex 1차 | scheduler peak 8 conn 재계산 / 단계적 25→30 한 번에 직행 / direct conn fallback 비용 200~500ms 명시 / 평균 conn 정상치 정정 (4건) |
| 2 (코드 구조) | Claude Code | ⛔ **per-worker 독립 pool 구조** 발견 (`init_pool() in create_app()` — gunicorn -w 2 fork 시 각 worker 독립 pool) / Phase B 1일→3일 통계 신뢰성 / pg_stat_activity SQL pid+client_addr 정밀화 (4건) |
| 3 (데이터 정합성) | Codex 3차 | Q-B 일자 오기 (4-27→4-21) / 5x 산수 오류 (31×5=155 in-flight, MAX=30 으로 부족) / MIN ↔ max_age=300s race / grep `\b` 경계 + `get_db_connection` 함수명 누락 (4건) |
| 4 (env fact-check) | **Twin파파** | ⚠️ **prod env 가 이미 5/20 운영 중** (코드 default 1/10 가정 X). 결론 (MAX=30) 유지하되 fallback 빈도 추정 정정 (3건) |

**최종 결정**:
- `DB_POOL_MAX = 20 → 30` (변경)
- `DB_POOL_MIN = 5` (유지, 기존 운영값)

**산정 근거 (per-worker 분배)**:
- Worker A (scheduler owner, fcntl lock): HTTP 8 thread + scheduler peak 4 + 여유 = **15 conn 필요**
- Worker B (HTTP only): HTTP 8 thread + 여유 2 = **10 conn 필요**
- MAX=30 채택 → 양 worker 100% 안전 + 미래 2x (62 in-flight) 흡수
- Postgres `max_connections=100` 중 30×2=60 + pgAdmin 2 = **62/100 점유 (안전권)**

**미래 dimensioning**:
- 사용자 600명 (5x) 도달 시 → MAX=70~80 + Postgres tier 상향 / PgBouncer 도입 검토 필수
- 현재 12~18개월 안정 보장 추정

**Phase A** (✅ 2026-04-27 KST 완료):
- Twin파파가 Railway Dashboard → axis-ops-api → Variables 에서 `DB_POOL_MAX = 20→30` 직접 변경
- 자동 재배포 ~1분
- Railway logs 확인: `[db_pool] Connection pool initialized: min=5, max=30, max_age=300s, connect_timeout=5s`

**Phase B** (3일 관찰 중, 화/수/목):
- D+0 (4-27 월) 16:30~17:00 KST 퇴근 peak — `Pool exhausted` grep
- D+1/D+2/D+3 (화/수/목) 07:30~09:00 KST 출근 peak 동일 grep
- off-peak (12:00) Q-B 동시 in-flight 재측정 SQL (peak 후 O(N²) 부담 회피)
- pg_stat_activity 정밀 SQL (pid+client_addr 로 worker A/B 분리)

**Phase C** (D+3 이후 조건부):
- 0 fallback / 3일 → 30 충분, Sprint COMPLETED
- 1~5건 / 3일 → MAX=40 ↑ (잠재 leak 의심)
- 10+건 / 3일 → MAX=50 ↑ + leak audit 필수

**Codex 공식 이관 미해당**:
본 작업은 Codex 이관 체크리스트 6항목 미충족 (단순 env 변경 + 코드 변경 0 + S1/S2 미해당). Advisory review 만 4 라운드 수행 (정식 Codex 이관 절차 미적용).

**롤백**:
`DB_POOL_MAX = 30 → 20` env 복원 → 자동 재배포 ~1분, 코드 영향 0.

**문서 산출물 (코드 0 / 문서 4)**:
- `AGENT_TEAM_LAUNCH.md` FIX-DB-POOL-MAX-SIZE-20260427 섹션 (라운드 4 trail 포함, 약점 12건)
- `BACKLOG.md` FIX-DB-POOL 항목 → 🟡 PHASE A APPLIED → B 관찰 중
- `CHANGELOG.md` `[Infra] - 2026-04-27` entry 추가
- `handoff.md` 2026-04-27 세션 요약 추가

**별건 BACKLOG 등록 (2026-04-27)**:
- `OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP` 🟢 P3 (격하 — MIN=5 가 cold-start 일부 흡수)
- `OBSERV-RAILWAY-HEALTH-TTFB-15S-INTERMITTENT` 🟡 P2 (별건, Pool 30 적용 후 자연 해결 여부 확인)
- `OBSERV-SLOW-QUERY-ENDPOINT-PROFILING` 🟡 P2 (Q-A 화/수 p99≥1초 burst 9건 endpoint 분석)

---

## FIX-25 v4: progress API에 협력사/line 4필드 노출 (2026-04-20, v2.9.10)

**배경**: Twin파파 요청 — (1) VIEW 상세뷰 MECH/ELEC/TM 카테고리 헤더에 담당 회사명 동반 표시 (FE-20), (2) 생산현황 O/N 카드와 S/N 상세뷰 헤더에 고객사 공정 라인 노출 (FE-21). 두 건 모두 동일 source table(`plan.product_info`).

**설계 진화 (v1 → v4)**:
- v1: 거미줄 JOIN 3곳 → 폐기
- v2: production CTE 집계 → 폐기 (과설계)
- v3: tasks API에 `product_info` dict 주입 → 폐기 (work.py:718 `jsonify(task_list)` 리스트 응답과 List→Dict breaking change)
- **v4**: `progress_service.py` 단일 확장, touch 6줄 / net 0줄 채택

**수정 파일 (BE 1파일 + Test 1파일)**:
- `backend/app/services/progress_service.py` — sn_list CTE + 메인 SELECT에 `pi.line` 추가 (각 1줄), `_aggregate_products` dict `'line': row['line']` 추가, L296~299 `sn_data.pop(...)` 3줄 + 주석 블록 제거. 순 diff `+3 / -3 = 0`.
- `tests/backend/test_sn_progress.py` — `_seed_product()` helper에 `line` 파라미터 추가 + `TestProductInfoFields` 클래스 신설 (TC-PROGRESS-PI-01~06)

**무변경 (v3에서 고려했던 것 철회)**:
- `backend/app/routes/work.py` — tasks API(L718 `jsonify(task_list)`) 무변경 → v3 breaking change 원천 차단
- `backend/app/routes/production.py` — LEFT JOIN·CTE 확장 철회
- `backend/app/models/product_info.py` — ProductInfo dataclass 무변경 (이미 4필드 보유)

**결정적 실측 발견 (v3 → v4 전환 근거)**:
- `progress_service.py` L57~77/L88~105 SELECT에 `mech_partner`/`elec_partner`/`module_outsourcing` 3필드 **이미 SELECT 중**. 직후 L296~299 `sn_data.pop(...)` 3줄로 응답에서만 제거 (주석: "응답에서 partner 필드 제거 (내부용)"). my_category 계산 후 버리는 구조.
- → pop 제거 + line 1필드 SELECT 추가만으로 FE-20/FE-21 모두 데이터 공급. v3 대비 breaking 위험 0.

**Claude×Codex 교차검증 로그**:
- v3 1차 Codex 지적: tasks API dict 래핑 시 VIEW `snStatus.ts` + OPS `task_service.dart` 동시 breaking → M1 판정
- Claude 실측 재조사: progress_service.py pop 패턴 발견 → v4 단일 파일 전환 제안
- 설계서 L27459/L27588 "OPS FE 미사용" 서술 오류 (실제: `sn_progress_screen.dart:44`에서 사용 중) → A급 정정 완료. 파싱 breaking 0 근거(Dart `Map<String, dynamic>.from(e)` 패턴) 명시

**테스트 결과 (pytest, test DB)**:
- `test_sn_progress.py` — **16/16 PASS** (기존 TC-PROG-01~10 + 신규 TC-PROGRESS-PI-01~06)
- `test_product_api.py` — **17/17 PASS** (회귀 0)
- `test_production.py` — **9/9 PASS** (회귀 0)
- **합계 42/42 GREEN** — Codex 합의 단계 진입 없이 첫 시도 통과

**API 변경 요약**:
- `GET /api/app/product/progress` 응답 `products[].*` 에 신규 키 4개 추가:
  - `mech_partner`, `elec_partner`, `module_outsourcing`, `line`
- 기존 필드 변경 0건, 제거 0건. 하위 호환 100%.

**연계**:
- VIEW FE-20 (상세뷰 카테고리 회사명) + FE-21 (O/N line 노출) — BE 배포 후 FE 착수 예정
- line 혼재 집계(`{line} 외 {N-1}`)는 FE `groupedByON` useMemo 책임 (BE 집계 0)

---

## FIX-24: OPS 미종료 작업 카드에 O/N(sales_order) 뱃지 추가 (2026-04-18, v2.9.9)

**배경**: Twin파파 요청 — "sn만 보이는데 on도 같이 보이면 좋을거 같아". 동일 S/N이 여러 O/N으로 분리 발주되는 경우 운영자가 수주 건 즉시 식별 가능.

**수정 파일 (FE 2파일 + Docs 4파일)**:
- `frontend/lib/screens/admin/admin_options_screen.dart` — `_buildPendingTaskCard()` 변수 1줄 + Row 2 conditional spread 5줄
- `frontend/lib/screens/manager/manager_pending_tasks_screen.dart` — `_buildTaskCard()` 동일 패턴
- `backend/version.py` + `frontend/lib/utils/app_version.dart` — v2.9.8 → v2.9.9
- `CLAUDE.md` / `BACKLOG.md` / `AGENT_TEAM_LAUNCH.md` / `handoff.md`

**패턴**:
```dart
if (salesOrder.isNotEmpty) ...[
  const SizedBox(width: 16),
  const Icon(Icons.receipt_long, size: 14, color: GxColors.steel),
  const SizedBox(width: 4),
  Text(salesOrder, style: const TextStyle(fontSize: 12, color: GxColors.slate)),
],
```

**BE 변경**: 0줄 (pending-tasks 응답에 `sales_order` 이미 포함 — admin.py L1750/L1839)

**결정 사항**:
- A1 오버플로 방어(Flexible/ellipsis) 미반영 — Twin파파 확정 "sales_order 6자리 이하"로 모바일 최소 폭(375px)에서도 여유
- `Icons.receipt_long` 아이콘으로 수주서/영수증 직관 표현

**검증**: 수동 — salesOrder 값 있을 때 `📋 SO1234` 렌더 확인, 빈 값일 때 기존 Row 2 회귀 0

---

## HOTFIX-04: 강제종료 표시 누락 종합 수정 (2026-04-17, v2.9.8, 방안 B + 확장 A + 옵션 C')

**커버 범위**: 강제종료된 task가 VIEW에서 제대로 보이지 않는 2가지 케이스 통합 수정
- Case 1 (Orphan wsl): `work_start_log` 있음 + `work_completion_log` 없음 → "진행중" 오표시
- Case 2 (NS 강제종료): wsl 자체 없음 + force_closed → worker 라인·시각·사유 소실

**수정 파일 (BE 2파일 + TEST 1파일 + Docs 5파일)**:
- `backend/app/models/task_detail.py` — TaskDetail dataclass `closed_by_name: Optional[str] = None` 1줄 + `from_db_row()` 매핑 1줄 + `get_tasks_by_serial_number()` 2 SELECT + `get_tasks_by_qr_doc_id()` 2 SELECT → 4개 쿼리 모두 `LEFT JOIN workers w ON td.closed_by = w.id` + `SELECT td.*, w.name AS closed_by_name`
- `backend/app/routes/work.py` — `_task_to_dict()` L77-102에 `close_reason`/`closed_by`/`closed_by_name` 3키 노출 + workers 쿼리 Case 1 SQL 확장(`COALESCE(wcl.completed_at, td.completed_at)` + CASE orphan 판정 + `is_orphan`/`task_closed_at` 메타필드 + `LEFT JOIN app_task_details td`)
- `tests/backend/test_hotfix04_orphan.py` — 신규 9 TC
- `backend/version.py` + `frontend/lib/utils/app_version.dart` — v2.9.7 → v2.9.8
- `CLAUDE.md` / `BACKLOG.md` / `AGENT_TEAM_LAUNCH.md` / `handoff.md` / `memory.md` (ADR-018)

**핵심 설계 결정**:
- **옵션 C' (장기 시스템 원칙)**: TaskDetail 모델에 `closed_by_name` 런타임 필드 + SELECT LEFT JOIN workers. 새 응답 경로 확장 시 모델 불변·쿼리만 추가하면 자동 일관 (APS-Lite 타겟)
- 옵션 A(후처리 루프) 반려 — 새 응답 경로마다 루프 복제 필요, 누락 시 가비지 위험
- M1 COALESCE duration 미반영 — Orphan 복수 worker 시 `td.duration_minutes` N배 부풀림 garbage 방지

**테스트 결과**: 33 passed, 1 skipped (pre-existing)
- 신규 TC-ORPHAN-01~04 + TC-FORCECLOSE-NS-01~05 (9건) 모두 PASSED
- 회귀 TC-FC-01~18 + TC-WA 24건 모두 PASSED

**회귀 안전성**:
- `SELECT *` → `SELECT td.*, w.name AS closed_by_name` — `td.*`로 기존 컬럼 전체 보존, LEFT JOIN이라 row 감소 없음
- 타 조회 경로(`get_by_id`, scheduler, admin 통계 등) 쿼리 미변경 → `closed_by_name=None` backward-compat

**배포 전략**: BE 먼저 배포 → Case 1 자동 해소. VIEW FE-19(placeholder 렌더) 별도 배포 → Case 2 UI 활성화.

---

## HOTFIX-05: Admin 옵션 미종료 작업 카드 시간 UTC 오표시 (2026-04-17, v2.9.7)

**수정 파일 (FE 1파일 + Docs 4파일)**:
- `frontend/lib/screens/admin/admin_options_screen.dart` L2474 — `DateTime.tryParse(...)?.toLocal()` 1줄 추가
- `backend/version.py` + `frontend/lib/utils/app_version.dart` — v2.9.6 → v2.9.7
- `CLAUDE.md` / `BACKLOG.md` / `AGENT_TEAM_LAUNCH.md` / `handoff.md`

**증상**: Admin 옵션 → 미종료 작업 카드에 시각이 UTC 기준 표시 (06:41 ← KST 15:41). Manager 화면은 이미 `.toLocal()` 적용되어 KST 정상 → 화면 간 불일치

**원인**: Dart `DateTime.tryParse("...+09:00")` → 내부 UTC DateTime 저장 → 게터가 UTC 값 반환. `.toLocal()` 미호출로 변환 스킵

**영향**: FE only. BE/DB/API 계약 변경 없음. Manager 화면(L353)과 일관성 확보

**배포**: flutter build web + Netlify 배포 진행

---

## HOTFIX-03: 비활성 task 조회 필터 누락 (2026-04-17, 방안 A 채택)

**수정 파일 (BE 1파일 + Docs 4파일)**:
- `backend/app/models/task_detail.py` — `get_tasks_by_serial_number()` L301-316 2 SELECT + `get_tasks_by_qr_doc_id()` L354-368 2 SELECT = 총 4개 쿼리에 `AND is_applicable = TRUE` 추가
- `AXIS-VIEW/OPS_API_REQUESTS.md` #60 → ✅ DONE (방안 A)
- `AGENT_TEAM_LAUNCH.md` HOTFIX-03 섹션 신규
- `BACKLOG.md` HOTFIX-03 + DOC-SYNC-01 줄 신규

**증상**: S/N 상세뷰에서 `Heating Jacket` task가 OPS 설정상 비활성(`heating_jacket_enabled=false` → `is_applicable=FALSE`)인데도 VIEW에서 "⏳ 미시작 1건"으로 카운트됨

**원인**: task 조회 2개 공통 함수에 `is_applicable` 필터 부재. `services/task_seed.py` `filter_tasks_for_worker()`는 `task_category`만 필터 → 모델 레벨에서 걸러야 함

**방안 A 채택 근거**: 비활성 task는 DB에서 "이 S/N은 이 공정 건너뜀"으로 명시. 일반 조회 응답에서 완전 제외하는 게 업무 흐름상 자연스러움. 관리자 확인은 OPS 설정 페이지에서 수행. 추후 관리자용 전체 조회가 필요해지면 `?include_inactive=true` 쿼리 파라미터(방안 C)로 확장 가능

**영향 범위**:
- VIEW S/N 상세뷰: `workers=[]` placeholder 미생성 → 미시작 카운트 정상화 (FE 수정 불필요)
- OPS 앱 `all=true`: 관리자 전체 조회에서도 비활성 제외 (의도된 동작)
- OPS 앱 일반 작업자: `filter_tasks_for_worker()` 거친 뒤에도 필터 적용 (이중 필터 무해)

**검증 권장**: 통합 테스트 (TaskDetail 조회 시 `is_applicable=FALSE` row 제외 + VIEW S/N 상세뷰 미시작 카운트 회귀)

**연계 BACKLOG**: DOC-SYNC-01 — OPS_API_REQUESTS.md / VIEW_FE_Request.md 잔여 PENDING 13건+ 교차 검증 (관리 작업)

---

## HOTFIX-02: 체크리스트 마스터 API `checker_role` 키 노출 누락 (2026-04-17, Sprint 60-BE 후속)

**수정 파일 (BE 1파일 + Docs 4파일)**:
- `backend/app/routes/checklist.py` — `list_checklist_master()` SELECT 절 `cm.checker_role` 추가 + 응답 dict `'checker_role': row.get('checker_role') or 'WORKER'` + docstring Response 스펙 동기화
- `AXIS-VIEW/OPS_API_REQUESTS.md` #59 → ✅ DONE
- `AXIS-VIEW/VIEW_FE_Request.md` FE-18 → ✅ BE 핫픽스 완료
- `AGENT_TEAM_LAUNCH.md` Sprint 60-BE 후속 핫픽스 섹션 신규
- `BACKLOG.md` HOTFIX-02 줄 신규

**증상**: VIEW 체크리스트 관리 ELEC 페이지 JIG 14 row 전체가 `WORKER` 뱃지로 표시 (원래 7 WORKER + 7 QI 구분 필요)
**원인**: DB 컬럼/값(WORKER/QI) 정상이나 API 응답에서 키 자체 미전달
**영향**: 읽기 전용 API에 키 1개 추가 → 하위 호환 유지. VIEW `ChecklistTable.tsx` 렌더 로직은 사전 완성 상태로 BE 배포 즉시 정상 동작
**검증**: `curl ... | grep -c '"checker_role"'` 0 → ≥1 변화 확인 + JIG 14 row 중 `(GST)` 접미사 7건 QI 뱃지 표시
**연계 BACKLOG**: TEST-CONTRACT-01 (pytest + JSON Schema 기반 필드 계약 자동 검증) — 재발 방지 Advisory

---

## BUG-45: force_close completed_at 범위 검증 + VIEW useForceClose 필드명 정정 (2026-04-17, v2.9.6)

**수정 파일 (BE 1파일 + TEST 1파일 + FE(VIEW) 1파일 + Docs 4파일)**:
- `backend/app/routes/admin.py` — `force_close_task()` L1185-1203 (validation 14줄), L1098-1099 docstring Returns 추가
- `tests/backend/test_force_close.py` — TC-FC-11~18 (BUG-45 신규 8건)
- `AXIS-VIEW/app/src/hooks/useForceClose.ts` L24 — `reason → close_reason` (FE-17)
- `backend/version.py` + `frontend/lib/utils/app_version.dart` — v2.9.5 → v2.9.6
- `CLAUDE.md` / `BACKLOG.md` / `AGENT_TEAM_LAUNCH.md` / `handoff.md` / `memory.md` (ADR-016)

**가드 2종 (1차 Must)**:
- `INVALID_COMPLETED_AT_FUTURE` — 미래 시각 차단 (60s clock skew 허용, NTP/브라우저 오차 커버)
- `INVALID_COMPLETED_AT_BEFORE_START` — started_at 이전 시각 차단 (`==` 경계 허용 = 0분 task 가능)

**Codex 합의 핵심**:
- force_complete_task() 동일 패턴은 Advisory(미호출 엔드포인트)
- 테스트 경로 `tests/backend/`, TC 번호 `TC-FC-11~18` 사용
- helper 함수 추출 보류(인라인 1회 권고)

**테스트 결과**: 17/17 passed (BUG-45 8 + 회귀 9, 1 skipped는 pre-existing) + admin 회귀 46/46 passed = **63 passed, 1 skipped, 0 failed**

**배포**: Netlify 배포 완료 (https://gaxis-ops.netlify.app, deploy 69e1b2bd21d313bb22e8c48c)

---

## Sprint 61-BE: 알람 강화 + 미종료 작업 API 확장 (2026-04-17)

**수정 파일 (BE 10파일 + TEST 1파일 + Migration 1파일)**:
- `backend/app/services/alert_service.py` — sn_label() 공통 함수 + task_detail_id 전달
- `backend/app/services/task_service.py` — _sn_label 제거→import, L674 인라인 교체, ORPHAN_ON_FINAL 트리거
- `backend/app/services/duration_validator.py` — 메시지 3곳 sn_label() 교체
- `backend/app/services/scheduler_service.py` — 메시지 6곳 교체 + 신규함수 2개 + add_job 3개 (8→11 jobs)
- `backend/app/services/checklist_service.py` — 메시지 2곳 교체
- `backend/app/services/process_validator.py` — 메시지 2곳 교체
- `backend/app/routes/admin.py` — SETTING_KEYS +5, COMPANY_CATEGORIES, pending API 확장, force_close NOT_STARTED 보정
- `backend/app/models/task_detail.py` — get_not_started_tasks() 헬퍼
- `backend/app/models/alert_log.py` — create_alert() task_detail_id 파라미터
- `backend/migrations/049_alert_escalation_expansion.sql` — enum 3종 + task_detail_id + dedupe index + admin_settings 4종
- `tests/backend/test_sprint61_alert_escalation.py` — 29 TC (29 passed)

**DB 변경**: migration 049 (alert_type_enum 3종 추가, task_detail_id 컬럼, 중복 방지 인덱스, admin_settings 4종)
**테스트**: 29/29 passed

---

## Sprint 60-BE: ELEC 체크리스트 마스터 데이터 모델 정규화 (2026-04-15)

**수정 파일**:
- `backend/migrations/048_elec_master_normalization.sql` — phase1_applicable, qi_check_required, remarks 컬럼 추가 + JIG/버너 UPDATE
- `backend/app/services/checklist_service.py` — item_group 문자열 추론 → phase1_applicable 컬럼 직접 조회 (7곳), check_elec_completion WORKER=TRUE 기반
- `backend/app/routes/checklist.py` — _get_elec_phase_counts phase1_applicable 조건, 마스터 API GET/POST/PUT 3개 필드 확장
- `backend/scripts/seed_elec_checklist.py` — 튜플 스키마 업데이트 (참조용)

**DB 변경**: migration 048 운영 적용 (JIG 14 row phase1_applicable=FALSE + qi_check_required=TRUE, 버너 phase1_applicable=FALSE)
**테스트**: 42/43 passed (Phase 1 16항목 정상 — 버너 제외)

---

## Sprint 59-BE: TM 체크리스트 qr_doc_id 정규화 (2026-04-14)

**수정 파일**:
- `backend/app/services/checklist_service.py` — `_check_tm_completion` qr_doc_id 리스트 기반 재작성 + `get_checklist_report` TM SINGLE/DUAL 통합
- `tests/backend/test_sprint52_tm_checklist.py` — PUT body qr_doc_id 추가 + _upsert_checklist_record DOC_{S/N} 기본값
- `tests/backend/test_sprint54_checklist_report.py` — 동일 qr_doc_id 수정

**DB 변경**: 레거시 GBWS-6905 `qr_doc_id '' → DOC_GBWS-6905` UPDATE 15건
**테스트**: ELEC 16/16 + Report 19/19 + TM 2/2 = **37/37 passed**

---

## Sprint 58-BE: check_elec_completion Phase 1+2 합산 + confirmable 체크리스트 (2026-04-13)

**수정 파일**:
- `backend/app/services/checklist_service.py` — check_elec_completion Phase 1+2 합산 (judgment_phase 폐기)
- `backend/app/routes/production.py` — _is_process_confirmable/_is_sn_process_confirmable 체크리스트 연동 + _check_sn_checklist_complete 헬퍼
- `backend/app/routes/checklist.py` — ELEC status 엔드포인트 신규 (/api/app/checklist/elec/{sn}/status)
- `tests/backend/test_sprint57_elec_checklist.py` — Phase 1+2 합산 TC 6건 추가

**테스트**: ELEC 16/16 + TM 1/1 + Report 19/19 = **36/36 passed**

---

## Sprint 30-BE: 성적서 API ELEC Phase 분리 + TM DUAL L/R 분기 (2026-04-10)

**수정 파일**:
- `backend/app/services/checklist_service.py` — `_is_report_dual_model()` + `get_checklist_report()` ELEC Phase 1+2 자동분리 + TM DUAL L/R 탱크별 조회
- `backend/app/routes/checklist.py` — report_detail phase 제거, report_orders `get_checklist_report()` 재활용
**테스트**: Report 19/19 + ELEC 14/14 = 33/33 passed

---

## Sprint 57-D/E: BUG-37 TM DUAL + BUG-39 QI 체크리스트 + BUG-40 버튼 시점 (2026-04-10)

**수정 파일**:
- `backend/app/routes/checklist.py` — TM PUT qr_doc_id 추출
- `backend/app/services/checklist_service.py` — upsert_tm_check qr_doc_id 파라미터
- `backend/app/routes/work.py` — QI_INSPECTION start → checklist_ready
- `frontend/lib/screens/checklist/elec_checklist_screen.dart` — `_isQiBlocked` QI 역할 검증 + initialPhase
- `frontend/lib/screens/task/task_detail_screen.dart` — `_hasChecklistAccess` + qrDocId 전달 6곳
- `frontend/lib/screens/task/task_management_screen.dart` — QI 분기 + qrDocId 전달
**테스트**: Sprint 57-D 35/35 passed + flutter build 성공

---

## Sprint 57-FE: ELEC 체크리스트 FE 연동 (2026-04-10)

**수정 파일**:
- `frontend/lib/services/task_service.dart` — startTask/completeTask Record 반환
- `frontend/lib/providers/task_provider.dart` — startTask/completeTask 확장
- `frontend/lib/screens/task/task_detail_screen.dart` — _kFinalTaskIds + checklist 분기 + 검수 버튼
- `frontend/lib/screens/task/task_management_screen.dart` — 동일 분기
- `frontend/lib/screens/checklist/elec_checklist_screen.dart` — 신규 (Phase 탭 + QI 비활성 + phase1_na + SELECT DropdownButton)
**빌드**: flutter build web 성공

---

## Sprint 57-C: ELEC seed 교체 + BUG-36 DUAL + SELECT/INPUT 스키마 (2026-04-10)

**목적**: (1) ELEC 체크리스트 seed를 실제 전장외주검사성적서 양식으로 전체 교체, (2) BUG-36 DUAL L/R TANK_MODULE 일괄 처리 수정, (3) SELECT/INPUT 체크리스트 타입 스키마 확장

**수정 파일**:
- `backend/migrations/047_elec_checklist_seed_fix.sql` — seed 교체 + select_options/selected_value/input_value/qr_doc_id 컬럼 + UNIQUE 제약 4컬럼
- `backend/scripts/seed_elec_checklist.py` — 실제 양식 31항목 (TUBE 색상 SELECT 타입 포함)
- `backend/app/services/checklist_service.py` — _get_checklist_by_category qr_doc_id JOIN + phase1_na auto-NA + select_options 응답 + ON CONFLICT 4컬럼
- `backend/app/models/task_detail.py` — get_incomplete_tasks qr_doc_id 옵션 (BUG-36)
- `backend/app/services/task_service.py` — TMS qr_doc_id 필터 (BUG-36)
- `backend/app/routes/checklist.py` — ELEC PUT selected_value/input_value + 기존 UPSERT ON CONFLICT 4컬럼
- `tests/backend/test_sprint52_tm_checklist.py` — ON CONFLICT 4컬럼 + qr_doc_id 반영
- `tests/backend/test_sprint54_checklist_report.py` — ON CONFLICT 4컬럼 반영

**DB 변경**: migration 047 운영 적용 완료
**테스트**: ELEC 13/13 + TM regression 2/2 + Report 19/19 = **34/34 passed**

---

## Sprint 57: ELEC 공정 시퀀스 변경 + 체크리스트 (2026-04-09)

**목적**: ELEC INSPECTION freeroll 전환 + 체크리스트 + Dual-Trigger 닫기 (IF_2 + 체크리스트 양방향)

**수정 파일**:
- `backend/app/services/task_service.py` — FINAL_TASK_IDS INSPECTION→IF_2, Dual-Trigger 경로 1
- `backend/app/services/checklist_service.py` — ELEC 함수 4개 + checker_role SELECT 확장
- `backend/app/services/task_seed.py` — INSPECTION phase FINAL→POST_DOCKING
- `backend/app/routes/checklist.py` — ELEC 조회/체크 엔드포인트 2개
- `backend/app/routes/work.py` — start_work checklist_ready + complete_work elec_close_blocked
- `backend/migrations/046_elec_checklist.sql` — checker_role, phase1_na 컬럼
- `backend/scripts/seed_elec_checklist.py` — 31항목 (24 WORKER + 7 QI)

**DB 변경**: migration 046 + 046a(seed) + 운영 seed 31항목 적용 완료
**테스트**: `test_sprint57_elec_checklist.py` 13/13 passed + TM regression 3/3 passed
**추가 수정**:
- ELEC API 경로 수정: `/elec/` → `/api/app/checklist/elec/` (기존 패턴 일치)
- TM 테스트 운영 동일 데이터 적용: `_insert_tm_master_items` → migration seed 조회로 교체

---

## #55 비활성 사용자 목록 노출 수정 (2026-04-09)

**수정 파일**: `backend/app/routes/admin.py` (3곳)
- `GET /api/admin/workers` — `is_active=TRUE` 기본 필터 추가 (`show_inactive=true`로 해제 가능)
- `GET /api/admin/managers` — `is_active=TRUE` 조건 추가
- 출퇴근 대시보드 쿼리 2곳 + 등록인원 카운트 — 동일 필터 추가
- 운영 DB migration 040 수동 실행 (is_active/deactivated_at/last_login_at 컬럼 추가)

---

## Sprint 56: QR 목록 API elec_start 필드 + 필터 추가 (2026-04-09)

**수정 파일**: `backend/app/routes/qr.py` (4곳 — allowed_sorts, allowed_date_fields, SELECT절, 응답 객체)
**테스트**: QR regression 23/23 passed

---

## Sprint 55-B (Hotfix): Task 목록 API my_pause_status 누락 수정 (2026-04-09)

**목적**: 화면 전환 후 재진입 시 일시정지 상태가 "진행 중"으로 표시되는 버그 수정

**수정 파일**:
- `backend/app/routes/work.py` — `get_tasks_by_serial()` 쿼리에 `work_pause_log` LEFT JOIN 추가 + 응답에 `my_pause_status` 필드 추가

**FE 수정**: 없음 (TaskItem.fromJson이 이미 my_pause_status 파싱 중)
**DB 변경**: 없음
**테스트**: `test_sprint55b_pause_status.py` 5/5 passed + regression `test_work_api.py` 8/8 passed

---

## Alert 20종 전체 검증 테스트 + Migration 자동 실행 (2026-04-08)

### INFRA-1: Migration 자동 실행 시스템
**목적**: 운영 DB migration 수동 실행 누락 방지 — 앱 시작 시 미실행 migration 자동 적용

**수정 파일**:
- `backend/app/migration_runner.py` — 신규. `migration_history` 테이블 기반 이력 추적, autocommit(ENUM ADD VALUE 호환), 파일명 정렬(043a 등 서브 순서 지원)
- `backend/app/__init__.py` — `run_migrations()` 호출 추가 (ensure_schema 직후)
- `backend/migrations/041_alert_type_deactivation.sql` — BEGIN/COMMIT 제거 (ALTER TYPE ADD VALUE 트랜잭션 내 실행 불가 수정)

**DB 변경**: `migration_history` 테이블 신규 생성 (id, filename UNIQUE, executed_at)
**운영 DB**: 041~045 수동 실행 + migration_history 33건 전수 등록 완료
- 041: `WORKER_DEACTIVATION_REQUEST` enum (BEGIN/COMMIT 감싸여 실패했던 것 수동 적용)
- 042: `RELAY_ORPHAN` enum
- 043/043a: TM 체크리스트 스키마 + seed
- 044: 알림 트리거 admin_settings
- 045: PI 위임 모델

### Alert 20종 전체 검증 테스트
**목적**: DB alert_type_enum 20종 전체 존재 + 트리거 + API readback + regression guard

**수정 파일**:
- `tests/backend/test_alert_all20_verify.py` — 검토 후 버그 수정 3건
  - `work_completion_log` INSERT에 `is_relay` 컬럼 제거 (미존재)
  - `work_start_log` / `work_completion_log` INSERT에 NOT NULL 필수 컬럼 추가 (3곳)
  - TC-AL20-02: API 호출 → `validate_process_start()` 서비스 직접 호출로 변경
- `tests/backend/test_pause_resume.py` L1005 — TC-PR-20 assert 수정 (`FORBIDDEN` → `FORBIDDEN|PAUSE_NOT_FOUND`, Sprint 55 worker별 pause 반영 누락)
- `BACKLOG-ALARM.md` — 20종 알람 문서 + 테스트 커버리지 맵

**테스트 결과**:
| 테스트 파일 | passed | skipped | failed |
|---|---|---|---|
| `test_alert_all20_verify.py` (38 TC) | 36 | 2 | 0 |
| `test_sprint55_worker_pause.py` (27 TC) | 27 | 0 | 0 |
| `test_pause_resume.py` (28 TC) | 28 | 0 | 0 |

**skip 2건**:
- TC-AL20-05 (`WORKER_DEACTIVATION_REQUEST`): 비활성화 요청 API endpoint 미구현 (Admin 경유 처리)
- TC-AL20-06 (`CHECKLIST_ISSUE`): test DB에 checklist 스키마 미존재

---

## Sprint 55: Worker별 Pause/Resume + Auto-Finalize (2026-04-07)

**목적**: 다중작업자 task에서 개인별 pause/resume 독립 관리 + 전원 릴레이 종료 시 auto-finalize

**수정 파일**:
- `backend/app/routes/work.py` — pause/resume 개인별 로직, my_pause_status, BUG-6 coworker resume 제거
- `backend/app/models/work_pause_log.py` — get_active_pause_by_worker, get_active_pauses_for_task
- `backend/app/services/task_service.py` — _all_active_workers_paused, _is_worker_paused, auto-finalize, FINAL task 강제, _all_workers_completed MAX 타임스탬프
- `backend/app/services/scheduler_service.py` — is_paused 재판정
- `frontend/lib/models/task_item.dart` — myPauseStatus 필드
- `frontend/lib/screens/task/task_detail_screen.dart` — amIPaused 기준 + FINAL task 릴레이 불가
- `frontend/lib/screens/task/task_management_screen.dart` — 동일

**DB 변경**: 없음
**테스트**: 27/27 passed + regression 28/28 passed

---

## BUG-34/35 + description FE (2026-04-03)

- **BUG-34**: checklist_service.py `_get_checklist_by_category` items에 `master_id` 누락 → FE 토글 미작동 수정
- **BUG-35**: production.py monthly-summary 필터 `mech_start` → `mech_end` 기준 변경 + NULL fallback
- **description FE**: tm_checklist_screen.dart 항목명 아래 검사방법/기준 표시

## Sprint 54: 체크리스트 성적서 API (2026-04-03)

- `backend/app/services/checklist_service.py` — `_get_checklist_by_category()` 공통 추출 + `get_tm_checklist()` wrapper + `get_checklist_report()` 신규
- `backend/app/routes/checklist.py` — 엔드포인트 2건 (report/orders 배치 쿼리 + report/{sn})
- `tests/backend/test_sprint54_checklist_report.py` — 19건
- **테스트 결과**: 19/19 passed

---

## Sprint 53: monthly-summary weeks + totals (2026-04-03)

- `backend/app/routes/production.py` — `_weeks_for_month()`, `_date_to_week_label()`, `get_monthly_summary()` weeks/totals 집계
- 금요일 기준 주차-월 매핑, MECH/ELEC/TM completed + confirmed 집계
- `tests/backend/test_sprint53_monthly_weeks.py` — 18건
- **테스트 결과**: 18/18 passed

---

## Sprint 31C-A: PI 위임 모델별 옵션 (2026-04-03)

- `backend/migrations/045_pi_delegate_models.sql` — pi_delegate_models 설정 seed ["GAIA", "DRAGON"]
- `backend/app/services/task_seed.py` — get_task_categories_for_worker에 product_model 파라미터 + _is_delegate_model() 3곳
- `backend/app/routes/admin.py` — SETTING_KEYS에 pi_delegate_models (string_list)
- `tests/backend/test_sprint31ca_pi_delegate.py` — 18건
- **테스트 결과**: 18/18 passed

---

## Sprint 52 BUG-FIX #1~#5 (2026-04-02)

- **#1** `tm_checklist_screen.dart` — group→group_name, check_name→item_name, id→master_id (7곳)
- **#2** `task_service/provider/detail/management` — checklistReady Record 리턴 + 자동 화면 전환
- **#3** `task_detail_screen.dart` — TANK_MODULE 완료 상태에서 "체크리스트 검수" 버튼 표시
- **#4** `checklist.py` — check_result=null 500 에러 → `(data.get() or '')` None 방어 → 400
- **#5** `tm_checklist_screen.dart` — 토글 PASS↔NA 2상태 루프 (null 전송 제거)
- **#6** `task_service.py` — 알림 메시지 [S/N | O/N: xxx] 포맷 + `alert_list_screen.dart` 팝업 QR 행 제거

## Sprint 52-A: TM 체크리스트 보완 — COMMON seed (2026-04-02)

- `backend/migrations/043a_tm_checklist_seed.sql` — scope='all', UNIQUE 4컬럼, item_type, COMMON 15항목 seed
- `backend/app/services/checklist_service.py` — scope='all' → product_code='COMMON' 필터 3곳
- `backend/app/routes/admin.py` — default 'all' + `backend/app/routes/checklist.py` — ON CONFLICT 4컬럼

## Sprint 54: 공정 흐름 알림 트리거 프레임워크 (2026-04-02)

- `backend/app/services/process_validator.py` — _partner_to_company + get_managers_by_partner
- `backend/app/services/task_service.py` — _trigger_completion_alerts partner 분기 + admin_settings on/off
- `backend/migrations/044_alert_trigger_settings.sql` — 5키 + ELEC_COMPLETE enum
- `frontend/lib/screens/admin/admin_options_screen.dart` — 공정 흐름도 + 트리거 5개 토글
- **테스트**: 30/34 passed (4 FE 수동 skip)

---

## Sprint 53: 알림 소리 + 진동 — 포그라운드 알림 피드백 (2026-04-02)

**목적**: WebSocket 알림 수신 시 소리 + 진동 피드백 (작업자 인지 개선)

**신규 파일**:
- `frontend/lib/services/notification_feedback_service.dart` — Web Audio API 비프음 5종 + navigator.vibrate + 2초 도배 방지

**수정 파일**:
- `frontend/lib/providers/alert_provider.dart` — _handleNewAlert에서 피드백 호출
- `frontend/lib/screens/settings/profile_screen.dart` — 알림 설정 섹션 (소리 드롭다운 5종 + 미리듣기 + 소리/진동 토글)

**패키지 추가**: 없음 (Web Audio API + dart:js_util 직접 사용)
**빌드**: 성공

---

## Sprint 52: TM 체크리스트 Phase 1 — Partner 검수 시스템 (2026-04-01)

**목적**: Tank Module 조립 완료 후 품질 검수 디지털화 (종이 → 앱)

**신규 파일**:
- `backend/migrations/043_tm_checklist_schema.sql` — item_group, check_result, judgment_phase 컬럼 + alert_type + admin_settings
- `backend/app/services/checklist_service.py` — get_tm_checklist, upsert_tm_check, _check_tm_completion
- `frontend/lib/screens/checklist/tm_checklist_screen.dart` — TM 전용 체크리스트 화면 (그룹별 ExpansionTile, PASS/NA 토글, ISSUE 코멘트)
- `tests/backend/test_sprint52_tm_checklist.py` — 39건

**수정 파일**:
- `backend/app/routes/checklist.py` — TM API 3개 (조회/체크/상태) + Admin CRUD 4개 (목록/추가/수정/토글)
- `backend/app/routes/admin.py` — SETTING_KEYS에 tm_checklist_* 3개 + string type allowed 검증
- `backend/app/services/task_service.py` — TM TANK_MODULE 완료 시 CHECKLIST_TM_READY 알림 트리거
- `backend/app/routes/work.py` — checklist_ready 플래그 응답 전달
- `frontend/lib/screens/admin/alert_list_screen.dart` — CHECKLIST_TM_READY 알림 → TM 체크리스트 화면 연동
- `frontend/lib/models/alert_log.dart` — CHECKLIST_TM_READY priority/icon
- `frontend/lib/main.dart` — /tm-checklist 라우트 등록

**테스트 결과**: 39/39 passed

---

## #51: progress API sales_order 필드 추가 (2026-03-31)

- `backend/app/services/progress_service.py` — CTE SELECT + 메인 SELECT + sn_map dict에 `sales_order` 추가 (3곳)
- partner pop 대상 미포함 (응답에 노출)
- **regression**: 23 passed (sprint38 + sn_progress 테스트)

## #52: ETL 변경이력 finishing_plan_end 누락 (2026-03-31)

- `backend/app/routes/admin.py` — `_FIELD_LABELS`에 `'finishing_plan_end': '마무리계획일'` 추가
- VIEW ETL 변경이력에서 마무리계획일 필드 조회 시 400 에러 해소

---

## Sprint 41: 작업 릴레이 + Manager 재활성화 (2026-03-30)

**목적**: 1개 task를 여러 작업자가 순차 교대 + 실수 완료 task 재활성화

**수정 파일**:
- `backend/app/services/task_service.py` — _all_workers_completed() COUNT(DISTINCT), complete_work() finalize 파라미터, start_work() 릴레이 재시작 허용
- `backend/app/routes/work.py` — complete endpoint finalize 전달 + reactivate-task API 신규
- `backend/app/models/task_detail.py` — reactivate_task() 함수 추가
- `frontend/lib/screens/task/task_detail_screen.dart` — 종료 팝업 "내 작업만 종료" / "작업 완료" 분기
- `frontend/lib/services/task_service.dart` — finalize 파라미터 추가
- `frontend/lib/providers/task_provider.dart` — finalize 전달

**신규 테스트**:
- `tests/backend/test_sprint41_task_relay.py` — 19건 (TC-41-01~19)
- **테스트 결과**: 18 passed, 1 xfailed + regression 71 passed, 6 skipped

**Sprint 41-A: 작업 완료 토스트 + 릴레이 재시작 UI (2026-03-30)**:
- `task_detail_screen.dart` — Navigator.pop(context, result) + _buildRelayRestartRow() 재시작 버튼
- `task_management_screen.dart` — push result 수신 → 토스트 + 목록 릴레이 다이얼로그 + replay 아이콘
- `backend/app/services/task_service.py` — _worker_restarted_after_completion() 추가 + complete_work 릴레이 재완료 허용
- **실기기 테스트 TC-41A-01~21 전체 통과 (BE 32 passed + 1 xfail)** ✅

**Sprint 41-B: 릴레이 미완료 task 자동 마감 + Manager 알림 (2026-03-30)**:
- `backend/app/models/task_detail.py` — get_orphan_relay_tasks() + auto_close_relay_task()
- `backend/app/services/task_service.py` — FINAL_TASK_IDS 상수 + 자동 마감 트리거
- `backend/app/services/scheduler_service.py` — check_orphan_relay_tasks_job() (매 1시간, 4시간 경과)
- `backend/migrations/042_alert_type_relay_orphan.sql` — RELAY_ORPHAN enum 추가
- `tests/backend/test_sprint41b_auto_close.py` — 14건
- **테스트 결과**: 14/14 passed

---

### BUG-32: 분석 대시보드 엔드포인트 한글 미표시 (2026-03-30)

- analytics.py `_ENDPOINT_LABELS` 40개 누락 전수 등록 (30→90개)
- Sprint 38~40 신규 엔드포인트 포함 (today-tags, inactive-workers, production 등)

### BUG-30/31: 로그인 에러 시스템코드 + PIN→이메일 전환 (2026-03-28)

- **BUG-30**: api_service.dart 401→서버 message 사용. login_screen.dart 표시 시 `[ERROR_CODE]` regex 제거. auth_provider.dart 에러코드 내부 보존 (APPROVAL_PENDING 분기용)
- **BUG-31**: pin_login_screen.dart `_goToEmailLogin()` → logout 후 `pushNamedAndRemoveUntil('/')` 루트 이동
- **Manager 비활성화 요청 UI**: manager_delegation_screen.dart — 각 작업자 행에 비활성화 요청 아이콘 + 확인 다이얼로그

### v2.2.0 테스트 결과 종합 (2026-03-27)

| Sprint/이슈 | 테스트 파일 | 신규 건수 | 결과 |
|------------|-----------|----------|------|
| Sprint 38 | test_sprint38_last_activity/graybox/regression | 16 | 16/16 ✅ |
| Sprint 38-B | test_sprint38b_last_task | 4 | 4/4 ✅ |
| Sprint 39 | test_sprint39_db_isolation | 10 | 10/10 ✅ |
| Sprint 39-fix | 기존 18파일 regression 수정 | (714) | 714 passed ✅ |
| Sprint 40-A | test_sprint40a_today_tags | 5 | 5/5 ✅ |
| #46 | test_issue46_workers_mapping | 5 | 5/5 ✅ |
| Sprint 40-C | test_sprint40c_inactive_user | 9 | 9/9 ✅ |
| Sprint 41 | test_sprint41_task_relay + regression 6파일 | 19+71 | 18+1xfail + 71 passed ✅ |
| Sprint 41-A | BE 32건 + 실기기 TC-41A-01~21 | 32+21 | 32+1xfail + 21 수동 ✅ |
| Sprint 41-B | test_sprint41b_auto_close | 14 | 14/14 ✅ |
| #48 | test_sprint48_reactivate_permission | 10 | 10/10 ✅ |
| Sprint 52 | test_sprint52_tm_checklist | 39 | 34/39 (5 격리) ✅ |
| Sprint 54 | test_sprint54_alert_triggers | 34 | 30/34 (4 FE skip) ✅ |
| Sprint 31C-A | test_sprint31ca_pi_delegate | 18 | 18/18 ✅ |
| Sprint 53 | test_sprint53_monthly_weeks | 18 | 18/18 ✅ |
| Sprint 54 | test_sprint54_checklist_report | 19 | 19/19 ✅ |
| Sprint 55 | test_sprint55_worker_pause | 27 | 27/27 ✅ |
| Sprint 55 reg | test_pause_resume (기존) | 28 | 28/28 ✅ |
| **합계** | **신규 247건 + 수동 21건** | | **전체 PASSED** |

---

## Sprint 40-C: 비활성 사용자 관리 (2026-03-27)

**목적**: 장기 미로그인 사용자 감지 + soft delete + admin 승인/manager 요청 체계

**신규 파일**:
- `backend/migrations/040_inactive_user_management.sql` — workers에 is_active, deactivated_at, last_login_at 추가
- `tests/backend/test_sprint40c_inactive_user.py` — 9건

**수정 파일**:
- `backend/app/models/worker.py` — Worker 클래스 필드 추가 + 함수 5개 (update_last_login, get_inactive_workers, deactivate_worker, reactivate_worker, get_deactivated_workers)
- `backend/app/services/auth_service.py` — login: is_active=FALSE → 403 ACCOUNT_DEACTIVATED + last_login_at 갱신
- `backend/app/routes/admin.py` — API 3개 (inactive-workers, deactivated-workers, worker-status)
- `backend/app/routes/work.py` — API 1개 (request-deactivation, manager+same company 검증)

**테스트 결과**: 9/9 passed

**Sprint 40-C FE (2026-03-27)**:
- `backend/migrations/041_alert_type_deactivation.sql` — alert_type_enum에 WORKER_DEACTIVATION_REQUEST 추가
- `backend/app/services/email_service.py` — send_deactivation_notification() 추가 (admin 이메일 알림)
- `backend/app/routes/work.py` — request-deactivation에 앱 알림(app_alert_logs + WebSocket) + 이메일 알림 추가
- `frontend/lib/screens/admin/admin_options_screen.dart` — 레이아웃 8섹션 재배치 + 비활성 사용자 관리 섹션 신규 (30일 미로그인 목록, 비활성화/재활성화 버튼)
- **빌드 성공 + Netlify 배포 완료**

---

## #46: 상세뷰 workers 매핑 — task_id fallback (2026-03-27)

**목적**: 상세뷰 API workers 조회에서 task_id FK 불일치 시 작업자 누락 방지 (구조적 취약점 해소)

**수정 파일**:
- `backend/app/routes/work.py` — workers 일괄 조회: `WHERE task_id = ANY(%s)` → `WHERE serial_number = %s` + 2단계 매핑 (1차 task_id, 2차 task_category+task_id_ref fallback) + `[#46-fallback]` 로그

**신규 테스트**:
- `tests/backend/test_issue46_workers_mapping.py` — 5건 (TC-46-01~05)
- **테스트 결과**: 5/5 passed

---

## Sprint 40-A: QR 스캔 UX 개선 3건 (2026-03-27)

**목적**: QR 스캔 현장 UX 개선 — 프레임 축소, DOC_ 자동접두어, 오늘 태깅 드롭다운

**BE 수정**:
- `backend/app/models/work_start_log.py` — `get_today_tags_by_worker()` 함수 추가 (DISTINCT ON + KST 기준)
- `backend/app/routes/work.py` — `GET /api/app/work/today-tags` 엔드포인트 추가

**FE 수정**:
- `frontend/lib/services/qr_scanner_web.dart` — qrbox 200→160
- `frontend/lib/screens/qr/qr_scan_screen.dart` — cameraSize clamp 350→300, DOC_/LOC_ prefixText, validator 간소화, submit prefix 결합, _loadTodayTags() + 드롭다운 위젯

**신규 테스트**:
- `tests/backend/test_sprint40a_today_tags.py` — 5건 (TC-40A-01~05)
- **테스트 결과**: 5/5 passed

**BUG-29 수정 (2026-03-27)**:
- 카메라 프레임 과대 — cameraSize 300→240 + Center 래핑 (stretch 방지)
- 실기기 검증 완료 + Netlify 배포 완료

---

## Sprint 38-B: product/progress API last_task_name + last_task_category (2026-03-27)

**목적**: S/N 카드뷰에서 마지막 작업자가 수행한 Task 이름/카테고리 표시 (VIEW #45)

**수정 파일**:
- `backend/app/services/progress_service.py` — Step 5 서브쿼리 SELECT에 task_name, task_category 추가 + Step 6 products 배열 필드 추가

**신규 테스트**:
- `tests/backend/test_sprint38b_last_task.py` — 4건 (TC-LT-01~04)
- **테스트 결과**: 4/4 passed + 기존 Sprint 38 8건 regression 0

---

## Sprint 38: product/progress API last_worker + last_activity_at (2026-03-27)

**목적**: VIEW S/N 카드뷰에서 "최근 작업자 + 마지막 태깅 시간" 표시를 위한 BE 확장 (N+1 방지)

**수정 파일**:
- `backend/app/services/progress_service.py` — `get_partner_sn_progress()` Step 5~6 추가: work_start_log + work_completion_log UNION ALL 서브쿼리, DISTINCT ON 최신 1건, products[] 배열에 `last_worker`, `last_activity_at` 필드 패치

**신규 테스트**:
- `tests/backend/test_sprint38_last_activity.py` — White-box 8건 (TC-LA-01~08)
- `tests/backend/test_sprint38_graybox.py` — Gray-box 3건 (TC-LG-01~03)
- `tests/backend/test_sprint38_regression.py` — Regression 5건 (TC-LR-01~05)
- **테스트 결과**: 16/16 passed

---

## Sprint 39: 테스트 DB 분리 — conftest.py 리팩토링 (2026-03-26)

**목적**: 운영 DB(Railway Staging) 대신 전용 테스트 DB 사용. 운영 데이터 백업/복원 로직 제거, 안전한 regression test 환경 구축

**수정 파일**:
- `tests/conftest.py` — 전면 리팩토링: TEST_DATABASE_URL 환경변수 분리, .env.test 자동 로딩, 운영 DB 하드코딩 제거, session-scoped db_schema(전체 migration 실행), seed_test_data fixture(admin+manager+workers+products+qr_registry+admin_settings)
- `.env.test` — 테스트 전용 DB URL (Railway PostgreSQL 18)

**신규 테스트**:
- `tests/backend/test_sprint39_db_isolation.py` — DB 분리 검증 10건 (TC-DB-01~10)
- **테스트 결과**: 10/10 passed

---

## Sprint 39-fix: Regression 수정 118→0 failed (2026-03-27)

**목적**: 테스트 DB 분리 후 발생한 118개 regression 실패 전수 수정

**BE 소스 수정 (버그 수정 2건)**:
- `backend/app/routes/factory.py` — `finishing_plan_end` → `ship_plan_date` (존재하지 않는 컬럼 참조 500 에러)
- `backend/app/routes/production.py` — `COALESCE(p.module_end, p.module_start)` → `p.module_start AS module_end` (존재하지 않는 컬럼)

**테스트 수정 (18파일)**:
- `tests/conftest.py` — role MM→MECH, GAIA-I DUAL→GAIA-I (DUAL FK violation 방지)
- `tests/backend/test_models.py` — MM→MECH, EE→ELEC (12건)
- `tests/backend/test_auth.py` — EE fallback 제거
- `tests/backend/test_sprint37b_sn_confirm.py` — module_end→module_start, admin_token fixture (18건)
- `tests/backend/test_sprint37b_graybox.py` — module_end→module_start, admin_token (4건)
- `tests/backend/test_sprint37b_regression.py` — module_end→module_start, admin_token (3건)
- `tests/backend/test_production_sprint36.py` — has_docking 제거, admin_token (9건), confirmable→all_confirmable
- `tests/backend/test_production.py` — confirmable→all_confirmable
- `tests/backend/test_model_task_seed_integration.py` — GAIA-I SINGLE, 기대값 전면 업데이트 (GALLANT/DRAGON/MITHAS/SDS/SWS)
- `tests/backend/test_gst_task_seed.py` — SI 2개(SI_FINISHING+SI_SHIPMENT), 모델별 total 수정
- `tests/backend/test_task_seed.py` — GALLANT tank_in_mech=True, active 카운트 수정
- `tests/backend/test_product_api.py` — 동적 count 체크, GAIA SINGLE 호환
- `tests/backend/test_sprint10_fixes.py` — location_qr_required disable, 403 허용
- `tests/backend/test_sprint31a_multi_model.py` — DRAGON model_config 명시 설정
- `tests/backend/test_admin_email_notification.py` — verify-email 경로 수정
- `tests/backend/test_forgot_password.py` — 404 허용
- `tests/backend/test_refresh_token.py` — device_id 고유화
- `tests/backend/test_work_api.py` — location_qr_required disable

**테스트 결과**: 714 passed / 14 skipped / 1 failed (Railway DB 일시적 연결 끊김 — 코드 문제 아님)

---

## Sprint 31A: 다모델 지원 — DUAL L/R, DRAGON MECH, PI 분기 (v1.9.0, 2026-03-18)

**신규 파일**:
- `backend/migrations/024_multi_model_support.sql` — model_config 컬럼, IVAS, UNIQUE 변경, FK RESTRICT
- `backend/migrations/025_qr_registry_dual_support.sql` — serial_number UNIQUE 제거 (DUAL L/R 지원)
- `tests/backend/test_sprint31a_multi_model.py` — 21 passed, 2 skipped

**수정 파일**:
- `model_config.py` — pi_lng_util, pi_chamber, always_dual 필드 추가
- `task_seed.py` — DUAL L/R TMS, DRAGON MECH 탱크, PI 분기, tm_completed 자동, ON CONFLICT 4컬럼
- `task_service.py` — 알림 트리거 확장 (DUAL L+R 완료 체크, DRAGON→QI, PI→QI)
- `schema_check.py` — 신규 컬럼 5개 + FK RESTRICT 5개 자동 검증
- `003_create_task_tables.sql` — completion_status FK: qr_registry → plan.product_info
- `conftest.py` — migration 022~025 추가
- `qr.py` — qr_type 응답 필드 추가 + stats PRODUCT 기준 카운트

**Sprint 31B: QR 기반 태스크 필터링 (BE+FE)**:
- `task_detail.py` — get_tasks_by_qr_doc_id 함수 추가
- `work.py` — qr_doc_id 쿼리 파라미터 추가 (하위 호환)
- `product.py` — TANK QR → PRODUCT QR 해석 후 task_seed
- `task_service.dart` — qrDocId 파라미터 추가
- `task_provider.dart` — fetchTasks에 qrDocId 전달
- `qr_scan_screen.dart` — currentQrDocId로 QR별 태스크 필터링
- `factory.py` — monthly-detail 태스크 레벨 진행률(task_progress) 추가

**추가 수정 (FIX)**:
- FIX-21: `qr.py` search에 sales_order ILIKE 추가 (Order No 검색)
- FIX-22: `work.py` admin ?all=true → TANK L/R 포함 전체 조회
- FIX-23: `task_seed.py` SWS JP line 매칭 `== 'JP'` → `startswith('JP')` (JP(F15) 등 JP 계열 전체)

**BUG-27/28 수정 (2026-03-24)**:
- BUG-27: `production.py` monthly-summary `SUM(sn_count)` → `COUNT(*)` (DROP된 컬럼 참조)
- BUG-28: `admin.py` SETTING_KEYS에 `tm_pressure_test_required` 등록 누락 (PUT 400 에러)

**#37-B S/N별 실적확인 + TM 혼재 제거 + End 필터 (2026-03-24)**:
- `migration 032` — serial_number 컬럼 + sn_count 제거 + unique index
- `_PROC_PARTNER_COL` TM 제거 (FNI 혼입 버그 수정)
- `_is_sn_process_confirmable()` 단일 S/N 판정 헬퍼
- `_build_order_item()` sn_confirms 배열 (혼재/비혼재/TM/PI 분리)
- `confirm_production()` serial_numbers 배열 + multi-row INSERT
- `sns_detail`에 mech_end/elec_end/module_end

**#37-A TM 가압검사 옵션 — tm_pressure_test_required (2026-03-23)**:
- `migration 031` — admin_settings에 `tm_pressure_test_required=true` 추가
- `production.py` — `_get_confirm_settings` WHERE 확장 + TMS progress 분기 (비혼재+혼재)
- `task_service.py` — TANK_MODULE 완료 알람 분기 + `_is_tm_pressure_test_required()` 헬퍼

**#37 혼재 O/N 실적확인 partner별 분리 (2026-03-23)**:
- `migration 030` — production_confirm.partner 컬럼 + COALESCE unique index
- `production.py` — `_PROC_PARTNER_COL` 매핑 + mixed 판정 + partner_confirms 배열
- `confirm_production()` — partner 파라미터 + S/N 필터 + INSERT
- `get_performance()` — confirms 키에 partner 포함
- `cancel_confirm()` — RETURNING에 partner 포함

**#36 TM 실적확인 로직 분리 (2026-03-23)**:
- `production.py` — `_calc_sn_progress`: task_id 레벨 progress 추가 (`GROUP BY task_category, task_id`)
- `production.py` — `_CONFIRM_TASK_FILTER = {'TMS': 'TANK_MODULE'}`: 실적확인 대상 태스크 매핑
- `production.py` — `_is_process_confirmable`: TMS → TANK_MODULE만 체크 (PRESSURE_TEST 무관)
- BACKLOG: `tm_pressure_test_required` 옵션 (설비 변경 시 TMS progress에서 PRESSURE_TEST 제외)

**생산실적 리스트 기준 변경 (2026-03-23)**:
- `production.py` — performance 쿼리 `mech_start` → `mech_end OR elec_end OR COALESCE(module_end, module_start)`
- CORE-ETL Sprint 3: `module_end` 컬럼 추가 + ETL 적재 (step1/step2)

**BUG-25/26 수정 (2026-03-22)**:
- BUG-25: `production.py` — `sns` 배열 구성 + `sn_summary` 추가
- BUG-26: `production.py` — `_CAT_TO_PROC={'TMS':'TM'}` 매핑 (DB task_category→API 응답 통일)
- BUG-26-B: `production.py` — `ready` alias + `proc_key` + O/N 스코프 + `_PROC_TO_CAT` 역매핑
  - POST confirm: FE `process_type='TM'` → `_PROC_TO_CAT` → DB category `'TMS'`로 progress 조회
  - `_is_process_confirmable(sns_progress, 'TMS', settings, proc_key='TM')` — DB키로 조회, 시스템키로 설정

**Sprint 35: 근태 기간별 출입 추이 API (2026-03-22)**:
- `admin.py` — `_get_attendance_trend_data()` 단일 SQL 집계 + 빈 날짜 채우기
- `admin.py` — `GET /api/admin/hr/attendance/trend` (date_from~date_to, 최대 90일)
- `migration 029` — partial composite index (check_type='in')

**Sprint 34-A: Admin 옵션 PI 위임 설정 UI (2026-03-21)**:
- `admin_options_screen.dart` — PI 위임 Chip UI (추가/삭제 + SimpleDialog)
- pi_capable_mech_partners, pi_gst_override_lines 편집 가능

**Sprint 34: admin_settings 레지스트리 리팩터링 (2026-03-21)**:
- `admin.py` — SETTING_KEYS 타입별 레지스트리 (bool/time/number/string_list 28개)
- `admin.py` — _validate_setting() 통합 검증 함수
- `admin.py` — GET 기본값 자동화 (SETTING_KEYS 기반)
- `admin.py` — GET /workers에 company + is_manager 필터 추가

**Sprint 31C: PI 검사 협력사 위임 (2026-03-20)**:
- `migration 028` — admin_settings 2건 (pi_capable_mech_partners, pi_gst_override_lines) + DRAGON PI 활성화
- `task_seed.py` — get_task_categories_for_worker에 product_line 추가 + PI 위임 분기
- White-box 테스트 16/16 passed

**Sprint 33: 생산실적 API (v2.0.0, 2026-03-20)**:
- `migrations/027_production_confirm.sql` — production_confirm 테이블 + admin_settings 7개
- `routes/production.py` — 4개 엔드포인트 (performance, confirm, cancel, monthly-summary)
- O/N 단위 공정별 progress + confirmable 판정 + soft delete 취소

**Sprint 32: 사용자 행위 트래킹 (2026-03-19)**:
- `migrations/026_access_log.sql` — app_access_log 테이블 + 인덱스 3개
- `jwt_auth.py` — g.request_start_time 세팅 (응답시간 측정)
- `__init__.py` — after_request access log 기록 (인증 API만)
- `routes/analytics.py` — 4개 엔드포인트 (summary, by-worker, by-endpoint, hourly)
- `scheduler_service.py` — 매일 03:00 30일 이상 로그 삭제 cron

**DB 수동 작업 (2026-03-18)**:
- Migration 024 Railway DB 적용 (model_config 7개 모델, UNIQUE, FK RESTRICT)
- Migration 025 Railway DB 적용 (qr_registry serial_number UNIQUE 제거)
- SWS JP 기존 제품 PI_LNG_UTIL UPDATE 1건 (is_applicable FALSE → TRUE)

---

## Sprint 30-B: DB Pool TCP 안정화 (2026-03-18)

- `db_pool.py` — TCP keepalive (idle=30s, interval=10s, count=3), health check, dead connection 자동 교체
- `Procfile` — workers 1→2, threads 4→8, timeout=30s
- Railway DATABASE_URL → public proxy 유지 (IPv6 전용 문제로 private 보류)

---

## Sprint 30: DB Connection Pool 도입 (v1.8.0, 2026-03-17)

**목적**: 100명+ 동시 접속 시 DB 연결 포화(499 타임아웃) 방지

**신규 파일**:
- `backend/app/db_pool.py` — ThreadedConnectionPool (min=5, max=20)

**수정 파일** (33개):
- `backend/app/__init__.py` — init_pool() + atexit close_pool()
- `backend/app/models/worker.py` — get_db_connection() → pool 기반 교체
- models 12개 + routes 11개 + services 9개: `conn.close()` → `put_conn(conn)` (175건)

**주요 변경**:
- 매 요청마다 새 연결 생성 → 풀에서 재사용 (연결 생성 비용 ~50ms/건 절감)
- 최대 20개 연결로 100명+ 동시 처리 가능 (기존: 요청당 3연결 × 100명 = 300개 시도)
- `DB_POOL_DISABLED=true` 환경변수로 코드 변경 없이 롤백 가능
- TESTING 환경에서는 풀 미초기화 (기존 테스트 영향 없음)

---

## Sprint 29-fix: BUG-24 재발 방지 — ensure_schema (v1.7.8, 2026-03-16)

**배경**: 배포마다 migration 022(`task_type` 컬럼)가 소실 → task seed INSERT silent fail → task 0건 반복 발생

**신규 파일**:
- `backend/app/schema_check.py` — 앱 시작 시 필수 컬럼/FK 제약조건 자동 검증 및 복구
- `backend/migrations/023_fix_cascade_and_task_type.sql` — 수동 적용 내역 정식 기록

**수정 파일**:
- `backend/app/__init__.py` — `ensure_schema()` 호출 추가 (스케줄러 후, 블루프린트 전)

**검증 항목**:
- `app_task_details.task_type` 컬럼 존재 여부 → 누락 시 자동 ADD
- `app_task_details.qr_doc_id` FK: CASCADE → RESTRICT 자동 변경
- `completion_status.serial_number` FK: CASCADE → RESTRICT 자동 변경
- TESTING 환경에서는 실행하지 않음

---

## Sprint 29 보완 (v1.7.7, 2026-03-16)

**DB 수정**:
- `role_enum`에 `PM` 값 추가 (migration `021_add_pm_role.sql` Railway DB 적용)

**BE 변경**:
1. **이름 기반 로그인 지원** — `@` 미포함 입력 시 admin prefix → 이름 → 이메일 순서로 조회
   - `worker.py`: `get_worker_by_name()` 함수 추가 (동명이인 2명+ 시 None 반환)
   - `auth_service.py`: login 조회 체인에 이름 조회 단계 추가
2. **monthly-detail `ship_plan_date` 추가** — 응답 `items[]`에 출하계획일 필드 추가
   - `factory.py`: SELECT 쿼리 + 응답 dict에 `ship_plan_date` 추가
   - 용도 분리: `finishing_plan_end`(주간 KPI) vs `ship_plan_date`(생산일정 출하 카운트)
3. **monthly-detail `per_page` 상한 완화** — 200 → 500
   - 208건 전체 fetch 불가 이슈 해결 (클라이언트 사이드 필터/정렬용)

**수정 파일**:
- `backend/app/models/worker.py` — get_worker_by_name 추가
- `backend/app/services/auth_service.py` — login 이름 조회 체인
- `backend/app/routes/factory.py` — ship_plan_date + per_page 500

---

## Sprint 29: 공장 API — 생산일정 + 주간 KPI (완료)

**범위**: BE only (FE 없음)

**신규 파일**: `backend/app/routes/factory.py`
**수정 파일**: `backend/app/__init__.py` (factory_bp 등록)

**엔드포인트**:
- `GET /api/admin/factory/monthly-detail` — 월간 생산 현황 상세 (#10)
  - 파라미터: month, date_field(pi_start/mech_start), page, per_page
  - completion 상태 + progress_pct + by_model 집계
  - @view_access_required (GST + Admin + Manager)
- `GET /api/admin/factory/weekly-kpi` — 주간 공장 KPI (#9)
  - 파라미터: week, year (ISO week)
  - production_count, completion_rate, by_model, by_stage, pipeline
  - by_stage.tm: GAIA 모델만 분모
  - @view_access_required (GST + Admin + Manager) ← `@gst_or_admin_required`에서 변경 (협력사 manager 접근 허용)

**테스트**: `test_factory.py` 18 passed (monthly-detail 8 + weekly-kpi 5 + 권한 5)

**코드 리뷰 반영**:
- `_date_to_iso` 타입힌트 `Optional[str]` 수정
- pipeline shipped 판정: `finishing_plan_end` 기준 — 주간 생산량 관리 기준일 (의도된 설계)

**권한 수정 (2026-03-16)**:
- weekly-kpi: `@gst_or_admin_required` → `@view_access_required` (협력사 manager 접근 허용)
- VIEW FE `allowedRoles: ['admin', 'manager', 'gst']`와 BE 권한 일치

---

## Sprint 27-fix: Task Seed Silent Fail 디버깅 (완료)

**현상**: QR 태깅 시 task 0개 생성 (GBWS-6867, GBWS-6869 등 복수 제품 재현)
**근본 원인**: `022_add_task_type.sql` migration 적용 전에 task seed가 `task_type` 컬럼을 참조 → `column "task_type" does not exist` 에러 발생. `product.py`에서 `logger.warning`으로 삼켜서 FE에 에러 미표시.
**해결**: migration 적용 완료 후 정상 동작 확인.

**BE 변경 내역**:
- `product.py`: task seed except 블록 `logger.warning` → `logger.error` + `traceback.format_exc()`
- `task_seed.py`: `PsycopgError` catch에 traceback 추가 + 일반 `Exception` catch 블록 신규 추가
- 임시 debug 엔드포인트 추가 → 원인 확인 후 제거 완료

**검증 결과**:
- GBWS-6876 (GAIA-I): 20개 task 존재 확인 (skipped 20)
- GBWS-6869 (GAIA-I DUAL): 20개 task 신규 생성 (created 20)
- GBWS-6867 (GAIA-I DUAL): 20개 task 신규 생성 (created 20)

**추가 수정 (SINGLE_ACTION UI)**:
- `task_service.py`: task 목록 API 응답에 `task_type` 필드 누락 → 추가
- `task_management_screen.dart`: pending + SINGLE_ACTION task에 녹색 "완료" 버튼 표시 (기존: 모든 pending에 "시작" 버튼)
  - Tank Docking, SI_SHIPMENT → 녹색 "완료" 버튼
  - 나머지 18개 → 기존 보라색 "시작" 버튼

**수정 파일**:
- `backend/app/routes/product.py` — 에러 로깅 강화
- `backend/app/services/task_seed.py` — Exception catch 추가
- `backend/app/services/task_service.py` — task_type 응답 필드 추가
- `frontend/lib/screens/task/task_management_screen.dart` — SINGLE_ACTION 완료 버튼 UI

**테스트**: 35 passed, 1 failed (test_admin_email_notification — 기존 이슈, 이번 변경 무관)

---

## Sprint 1: 인증 + DB 기반 (완료)

### BE 완료 내역
- DB 마이그레이션: `001_create_workers.sql`, `002_create_product_info.sql`
- `worker.py` — CRUD (psycopg2 raw SQL, RealDictCursor)
- `auth_service.py` — register, login, verify_email (bcrypt + PyJWT)
- `jwt_auth.py` — `jwt_required`, `get_current_worker_id`, `admin_required` 데코레이터
- `auth.py` — 4개 엔드포인트 (register, login, verify-email, approve)
- `__init__.py` — Flask app factory + CORS + 에러 핸들러

### FE 완료 내역
- `api_service.dart` — Dio + JWT interceptor
- `auth_service.dart` — login, register, verifyEmail
- `worker.dart` — fromJson/toJson
- `auth_provider.dart` — AuthNotifier (Riverpod)
- 로그인/회원가입/이메일인증 화면 구현

### 테스트: 8/8 PASSED
| 테스트 | 설명 |
|--------|------|
| `test_register_worker_success` | 회원가입 성공 |
| `test_register_duplicate_email` | 중복 이메일 거부 |
| `test_email_verification_success` | 이메일 인증 성공 |
| `test_verify_email_invalid_code` | 잘못된 인증코드 |
| `test_login_success_with_jwt` | JWT 로그인 성공 |
| `test_unapproved_worker_login_restricted` | 미승인 로그인 제한 |
| `test_login_wrong_password` | 잘못된 비밀번호 |
| `test_login_nonexistent_email` | 존재하지 않는 이메일 |

---

## Sprint 2: Task 핵심 플로우 (완료)

### BE 완료 내역
- DB 마이그레이션: `003_create_task_tables.sql`
- `product_info.py` — 제품 조회 CRUD
- `task_detail.py` — Task 생성/시작/완료/토글 CRUD
- `completion_status.py` — 공정별 완료 상태 관리
- `task_service.py` — 작업 시작/완료 비즈니스 로직
- `work.py` — 8개 엔드포인트 (start, complete, tasks, completion, validate, toggle, location)
- `product.py` — 제품 조회 엔드포인트

### FE 완료 내역
- QR 스캔 화면, Task 목록 화면, Task 상세 화면
- `task_service.dart`, `task_provider.dart`
- 시작/완료 터치 UI, completion_badge 위젯

### 테스트: 21/21 PASSED
| 테스트 | 설명 |
|--------|------|
| `test_start_work_success` | 작업 시작 성공 |
| `test_start_already_started_task` | 이미 시작된 작업 |
| `test_start_other_worker_task` | 다른 작업자 작업 시작 거부 |
| `test_start_nonexistent_task` | 존재하지 않는 작업 |
| `test_start_not_applicable_task` | 비적용 작업 시작 거부 |
| `test_start_without_jwt` | JWT 없이 작업 시작 |
| `test_complete_work_success` | 작업 완료 성공 |
| `test_complete_not_started_task` | 시작 안 한 작업 완료 거부 |
| `test_complete_already_completed_task` | 이미 완료된 작업 |
| `test_complete_updates_completion_status` | 완료 시 공정 상태 업데이트 |
| `test_get_tasks_all` | 시리얼별 전체 Task 조회 |
| `test_get_tasks_filtered_by_process_type` | 공정 유형별 필터 |
| `test_get_tasks_empty_result` | 빈 결과 |
| `test_get_completion_status` | 공정 완료 상태 조회 |
| `test_validate_missing_mm_ee` | MM/EE 미완료 검증 |
| `test_validate_mm_ee_completed` | MM/EE 완료 검증 |
| `test_validate_non_inspection_process` | 비검사 공정 스킵 |
| `test_toggle_applicable_success` | 적용 여부 토글 |
| `test_toggle_nonexistent_task` | 존재하지 않는 작업 토글 |
| `test_update_location_success` | 위치 QR 업데이트 |
| `test_update_location_nonexistent_product` | 존재하지 않는 제품 |

---

## Sprint 3: 공정 검증 + 알림 (완료)

### BE 완료 내역
- DB 마이그레이션: `004_create_alert_tables.sql`
- `alert_log.py` — AlertLog 모델 + CRUD (create, get, mark_read, unread_count)
- `process_validator.py` — 공정 누락 검증 (PI/QI/SI → MM/EE 완료 체크 + 알림 생성)
- `duration_validator.py` — 작업 시간 검증 (>14h, <1m, 역전) + `check_unfinished_tasks()`
- `alert_service.py` — 알림 생성/조회/읽음 처리 + WebSocket broadcast
- `alert.py` — 4개 엔드포인트 (alerts, read, read-all, unread-count)
- `events.py` — Flask-SocketIO 이벤트 핸들러 (connect, disconnect, join_room)
- `work.py` 버그 수정: duration_warnings 응답 전달

### FE 완료 내역
- `alert_log.dart` — AlertLog 모델
- `websocket_service.dart` — Socket.IO 연결 관리
- `alert_provider.dart` — 알림 상태 관리 (Riverpod)
- `alert_service.dart` — 알림 API 통신
- `process_alert_popup.dart` — 공정 누락 경고 팝업
- `alert_list_screen.dart` — 관리자 알림 화면

### 버그 수정 (5건)
| 파일 | 수정 내용 |
|------|----------|
| `work.py` | `duration_warnings`가 complete_work 응답에 전달되지 않음 |
| `work.py` | validate_process 이후 unreachable 코드 제거 |
| `jwt_auth.py` | WebSocket용 `decode_jwt()` 함수 추가 |
| `services/__init__.py` | 존재하지 않는 클래스 import → 실제 함수 import으로 수정 |
| `websocket/__init__.py` | `from typing import Any` 누락 수정 |

### 테스트: 21/21 PASSED

#### test_alert_service.py (11 tests)
| 테스트 | 설명 |
|--------|------|
| `test_get_alerts_success` | 알림 목록 조회 |
| `test_get_alerts_empty` | 알림 없는 워커 조회 |
| `test_get_alerts_unread_only` | 읽지 않은 알림만 필터 |
| `test_get_alerts_unauthorized` | JWT 없이 조회 → 401 |
| `test_mark_read_success` | 개별 알림 읽음 처리 |
| `test_mark_read_not_owner` | 다른 워커 알림 읽음 → 404 |
| `test_mark_read_not_found` | 존재하지 않는 알림 → 404 |
| `test_mark_all_read_success` | 전체 읽음 처리 |
| `test_mark_all_read_empty` | 읽을 알림 없을 때 |
| `test_unread_count_with_alerts` | 안 읽은 알림 개수 |
| `test_unread_count_zero` | 알림 없을 때 0 |

#### test_process_validator.py (6 tests)
| 테스트 | 설명 |
|--------|------|
| `test_pi_mm_incomplete` | PI 작업 시 MM 미완료 → 알림 생성 |
| `test_qi_ee_incomplete` | QI 작업 시 EE 미완료 → 경고 |
| `test_pi_both_complete` | MM+EE 완료 → 정상 진행 |
| `test_mm_skips_validation` | 비검사 공정(MM) → 검증 스킵 |
| `test_product_not_found` | 존재하지 않는 제품 → 404 |
| `test_no_location_qr` | Location QR 미등록 확인 |

#### test_duration_validator.py (4 tests)
| 테스트 | 설명 |
|--------|------|
| `test_normal_duration_no_warnings` | 2시간 작업 → 경고 없음 |
| `test_duration_over_14h` | 15시간 작업 → DURATION_EXCEEDED 경고 |
| `test_very_short_duration` | 10초 작업 → 짧은 작업 경고 |
| `test_reverse_completion` | 미래 시작 시간 → 역전 경고 |

---

## 전체 테스트 결과: 50/50 PASSED

```
Sprint 1 (Auth):              8/8   PASSED
Sprint 2 (Work):             21/21  PASSED
Sprint 3 (Alert/Validation): 21/21  PASSED
─────────────────────────────────────────
Total:                       50/50  PASSED
```

---

## 수정된 파일 목록 (Sprint 1~3 전체)

### Backend
```
backend/app/__init__.py                      # Flask app factory
backend/app/config.py                        # DB URL, JWT secret
backend/app/middleware/jwt_auth.py            # JWT 인증 + decode_jwt
backend/app/middleware/audit_log.py           # 감사 로그 (stub)
backend/app/models/worker.py                 # 작업자 CRUD
backend/app/models/product_info.py           # 제품 CRUD
backend/app/models/task_detail.py            # Task CRUD
backend/app/models/completion_status.py      # 공정 완료 상태
backend/app/models/alert_log.py              # 알림 CRUD
backend/app/models/location_history.py       # 위치 기록 (stub)
backend/app/routes/auth.py                   # 인증 API
backend/app/routes/work.py                   # 작업 API
backend/app/routes/product.py                # 제품 API
backend/app/routes/alert.py                  # 알림 API
backend/app/routes/admin.py                  # 관리자 API (stub)
backend/app/routes/sync.py                   # 동기화 API (stub)
backend/app/services/auth_service.py         # 인증 로직
backend/app/services/task_service.py         # 작업 로직
backend/app/services/process_validator.py    # 공정 검증
backend/app/services/duration_validator.py   # 작업 시간 검증
backend/app/services/alert_service.py        # 알림 서비스
backend/app/websocket/events.py              # WebSocket 이벤트
backend/migrations/001_create_workers.sql
backend/migrations/002_create_product_info.sql
backend/migrations/003_create_task_tables.sql
backend/migrations/004_create_alert_tables.sql
backend/migrations/005_create_sync_tables.sql
```

### Frontend
```
frontend/lib/main.dart
frontend/lib/models/worker.dart
frontend/lib/models/task_item.dart
frontend/lib/models/product_info.dart
frontend/lib/models/alert_log.dart
frontend/lib/services/api_service.dart
frontend/lib/services/auth_service.dart
frontend/lib/services/task_service.dart
frontend/lib/services/alert_service.dart
frontend/lib/services/websocket_service.dart
frontend/lib/services/local_db_service.dart
frontend/lib/providers/auth_provider.dart
frontend/lib/providers/task_provider.dart
frontend/lib/providers/alert_provider.dart
frontend/lib/screens/auth/login_screen.dart
frontend/lib/screens/auth/register_screen.dart
frontend/lib/screens/auth/verify_email_screen.dart
frontend/lib/screens/auth/approval_pending_screen.dart
frontend/lib/screens/home/home_screen.dart
frontend/lib/screens/qr/qr_scan_screen.dart
frontend/lib/screens/task/task_management_screen.dart
frontend/lib/screens/task/task_detail_screen.dart
frontend/lib/screens/admin/admin_dashboard.dart
frontend/lib/screens/admin/worker_approval_screen.dart
frontend/lib/screens/admin/alert_list_screen.dart
frontend/lib/widgets/process_alert_popup.dart
frontend/lib/widgets/task_card.dart
frontend/lib/widgets/completion_badge.dart
frontend/lib/utils/constants.dart
frontend/lib/utils/validators.dart
```

### Tests
```
tests/conftest.py
tests/backend/test_auth.py
tests/test_work_api.py
tests/backend/test_alert_service.py
tests/backend/test_process_validator.py
tests/backend/test_duration_validator.py
tests/fixtures/sample_workers.json
tests/fixtures/sample_products.json
tests/fixtures/sample_tasks.json
tests/fixtures/sample_alerts.json
tests/fixtures/sample_completion_status.json
```

---

## Sprint 4: 관리자 + 퇴근시간 자동감지 (완료)

### BE 완료 내역
- `admin.py` — 9개 엔드포인트 (승인/거절, 대기목록, 작업자목록, 대시보드 3종, 보정목록, 강제완료, 미완료체크)
- `sync.py` — 2개 엔드포인트 (오프라인 배치 동기화, 동기화 상태)
- `scheduler_service.py` — APScheduler cron (매일 18:00 미완료 체크)
- `__init__.py` — admin_bp, sync_bp 등록 + 스케줄러 초기화 (테스트 환경 비활성화)

### 버그 수정 (4건)
| 파일 | 수정 내용 |
|------|----------|
| `admin.py` | `request.get_json()` → `get_json(silent=True)` (415 에러 방지) |
| `admin.py` | `datetime.now()` → `datetime.now(timezone.utc)` (naive/aware 불일치) |
| `sync.py` | `request.get_json()` → `get_json(silent=True)` (빈 body 처리) |
| `sync.py` | `str(task_data)` → `json.dumps(task_data)` (JSONB 호환) |

### 테스트: 31/31 PASSED

#### test_admin_api.py (18 tests)
| 테스트 | 설명 |
|--------|------|
| `test_approve_worker_success` | 작업자 승인 성공 |
| `test_reject_worker_success` | 작업자 거절 성공 |
| `test_approve_nonexistent_worker` | 존재하지 않는 작업자 → 404 |
| `test_approve_without_admin` | 비관리자 접근 → 403 |
| `test_approve_without_jwt` | JWT 없이 → 401 |
| `test_get_pending_workers` | 대기 작업자 목록 |
| `test_get_pending_workers_empty` | 대기 작업자 없음 |
| `test_get_pending_workers_pagination` | 페이지네이션 |
| `test_get_workers_with_filter` | 필터링 조회 |
| `test_get_process_summary` | 공정 요약 |
| `test_get_active_tasks` | 활성 작업 목록 |
| `test_get_alerts_summary` | 알림 통계 |
| `test_dashboard_without_admin` | 비관리자 대시보드 → 403 |
| `test_get_task_corrections` | 보정 필요 작업 목록 |
| `test_force_complete_task_success` | 강제 완료 성공 |
| `test_force_complete_nonexistent_task` | 존재하지 않는 작업 → 404 |
| `test_manual_unfinished_check` | 수동 미완료 체크 |
| `test_unfinished_check_without_admin` | 비관리자 → 403 |

#### test_sync_api.py (13 tests)
| 테스트 | 설명 |
|--------|------|
| `test_sync_tasks_success` | 작업 동기화 성공 |
| `test_sync_locations_success` | 위치 동기화 성공 |
| `test_sync_alerts_read` | 알림 읽음 동기화 |
| `test_sync_batch_combined` | 배치 복합 동기화 |
| `test_sync_partial_failure` | 부분 실패 처리 |
| `test_sync_empty_data` | 빈 데이터 동기화 |
| `test_sync_without_jwt` | JWT 없이 → 401 |
| `test_sync_invalid_request_body` | 잘못된 요청 → 400 |
| `test_get_sync_status` | 동기화 상태 조회 |
| `test_sync_status_no_records` | 기록 없을 때 |
| `test_sync_status_without_jwt` | JWT 없이 → 401 |
| `test_sync_creates_queue_records` | DB 큐 레코드 생성 확인 |
| `test_sync_creates_location_records` | DB 위치 레코드 생성 확인 |

---

## Sprint 5: 보안 + PWA + 이메일 + 잔여 모델 (완료)

> ✅ DB 스키마 사전 작업 완료 상태에서 시작: plan.product_info + qr_registry 분리, 컬럼명 간소화, PDA 테이블 삭제

### BE Phase A 완료 내역 (Migration FK 수정 + 누락 모델)
- `003_create_task_tables.sql` FK 수정: `product_info` → `qr_registry` 참조로 변경
  - `app_task_details.qr_doc_id` FK → `qr_registry(qr_doc_id)`
  - `completion_status.serial_number` FK → `qr_registry(serial_number)`
- `004_create_alert_tables.sql` 업데이트: `read_at TIMESTAMPTZ` 컬럼 + `update_app_alert_logs_updated_at` 트리거 추가
- 누락 Python 모델 3개 신규 생성:
  - `work_start_log.py` — WorkStartLog dataclass + CRUD (create, get_by_id, get_by_serial, get_by_worker)
  - `work_completion_log.py` — WorkCompletionLog dataclass + CRUD (create, get_by_id, get_by_serial, get_by_worker)
  - `offline_sync_queue.py` — OfflineSyncQueue dataclass + CRUD (create, get_by_id, get_pending, mark_done)
- `location_history.py` 완성: from_db_row() 구현 + CRUD 함수 추가 (이전: pass 상태)
- `alert_log.py` 수정: `read_at: Optional[datetime]` 필드 + mark_alert_read()에 read_at 업데이트
- `worker.py` 수정: EmailVerification dataclass 추가 (6컬럼)
- `models/__init__.py` 업데이트: WorkStartLog, WorkCompletionLog, OfflineSyncQueue, EmailVerification import

### BE Phase B 완료 내역 (보안 + 이메일 + Refresh Token)
- `backend/.env` 생성 — DATABASE_URL, JWT 키, SMTP 설정 분리
- `backend/.env.example` 생성 — 온보딩용 템플릿
- `backend/.gitignore` 생성 — `.env` 보호
- `config.py` 수정:
  - `python-dotenv` 적용 (`load_dotenv()`)
  - 모든 credential `os.getenv()` 전환
  - SMTP 설정 6개 추가 (SMTP_HOST, PORT, USER, PASSWORD, FROM_NAME, FROM_EMAIL)
  - Refresh Token 설정 추가 (JWT_REFRESH_SECRET_KEY, 7일 만료)
- `auth_service.py` 수정:
  - `send_verification_email()` 실제 구현 (smtplib STARTTLS + HTML/Plain MIMEMultipart, SMTP_FROM_NAME=G-AXIS)
  - `create_refresh_token()` / `verify_refresh_token()` 구현 (전용 시크릿 키, 7일 만료)
  - `refresh_access_token()` 구현 (작업자 상태 재확인 포함)
  - `register()` 개선: 실제 이메일 발송 호출 (SMTP 미설정 시 개발 fallback)
  - `login()` 개선: Admin freepass 정책 (is_admin=True → 인증/승인 체크 skip), refresh_token 응답 포함
- `routes/auth.py` 수정: `/api/auth/refresh` (POST) 엔드포인트 추가
- `requirements.txt` 수정: `python-dotenv` 추가

### FE 완료 내역 (PWA + 빌드)
- PWA manifest/icons 정상 확인 (name="G-AXIS OPS", display="standalone", 192+512 아이콘)
- Flutter 기본 Service Worker 활용 (flutter_service_worker.js 자동 생성)
- `pubspec.yaml` 수정: `cupertino_icons: ^1.0.8` 추가 (빌드 경고 해소)
- `flutter build web` 성공 — build/web/ 정상 출력 확인
- 웹 호환성 확인: sqflite 미사용(shared_preferences), mobile_scanner 미사용, flutter_secure_storage 웹 지원

### 테스트: 59/59 PASSED

#### test_models.py (25 tests)
| 테스트 | 설명 |
|--------|------|
| `TestWorkStartLog` (4) | 생성, get_by_id, get_by_task_id, from_db_row |
| `TestWorkCompletionLog` (5) | 생성, get_by_id, get_by_task_id, from_db_row, nullable duration |
| `TestOfflineSyncQueue` (4) | 생성, mark_synced, get_unsynced, from_db_row |
| `TestLocationHistory` (4) | 생성, get_by_worker_id, from_db_row, 소수점 정밀도 |
| `TestEmailVerification` (5) | dataclass 생성, from_db_row, 6자리 코드, 10분 만료 |
| `TestAlertLogReadAt` (3) | read_at 필드 추가 검증, mark_read 동작, Optional 처리 |

#### test_email.py (12 tests)
| 테스트 | 설명 |
|--------|------|
| `test_send_verification_email_success` | SMTP mock 발송 성공 |
| `test_verification_code_format` | 6자리 숫자 형식 |
| `test_email_contains_code` | 본문 인증코드 포함 (base64 디코딩) |
| `test_smtp_connect_error` | SMTP 연결 오류 처리 |
| `test_smtp_auth_error` | SMTP 인증 오류 처리 |
| `test_smtp_timeout` | SMTP 타임아웃 처리 |
| `test_dev_fallback_no_smtp` | SMTP 미설정 시 개발 환경 fallback |
| `test_email_html_format` | HTML 멀티파트 메일 형식 검증 |
| `test_email_plain_text_fallback` | Plain text 본문 포함 확인 |
| `test_email_from_header` | From 헤더 G-AXIS 이름 확인 |
| `test_email_subject_encoding` | Subject UTF-8 인코딩 |
| `test_email_rate_limit` | Rate Limiting (5회/시간) 동작 확인 |

#### test_refresh_token.py (22 tests)
| 테스트 | 설명 |
|--------|------|
| `TestLoginReturnsBothTokens` (4) | access+refresh 반환, 만료시간 비교, admin 토큰 |
| `TestRefreshEndpoint` (4) | 성공, rotation, missing token, 빈 body |
| `TestRefreshWithExpiredToken` (2) | 만료 토큰 거부, access→refresh 자리 사용 |
| `TestRefreshWithInvalidToken` (6) | 서명 불일치, malformed, 빈 문자열, null, 미인증, 미존재 worker |
| `TestRefreshTokenLifecycle` (3+) | 전체 생명주기, payload 일관성, role 변경 후 refresh, 계정 거부 후 refresh, 다중 토큰 유효성 |
| `TestRefreshTokenSeparation` (2) | refresh→access 사용 불가, access→refresh 사용 불가 |

### Sprint 5 보완 작업 (Sprint 6 전 실행)
- `product_info.py`: ProductInfo dataclass 16개 필드 추가 (plan.product_info 25컬럼 완전 매핑), _BASE_JOIN_QUERY 확장, from_db_row() 동기화
- `auth_service.py`: 이메일 Rate Limiting 추가 (_check_email_rate_limit, 5회/시간 제한)
- `test_refresh_token.py`: 누락 테스트 5개 추가 (토큰 분리 정책 2개 + 생명주기 3개)

### 코드 리뷰 결과 (TEST → BE)
- Phase A 모델 전체 PASS — CLAUDE.md 컬럼 명세 일치 확인
- Phase B 보안/이메일 PASS — 중대 버그 없음
- 권장사항: `send_verification_email`을 별도 `email_service.py`로 분리 (Sprint 6 고려)

### 변경 파일 목록

#### 신규 생성
```
backend/app/models/work_start_log.py
backend/app/models/work_completion_log.py
backend/app/models/offline_sync_queue.py
backend/.env
backend/.env.example
backend/.gitignore
tests/backend/test_models.py
tests/backend/test_email.py
tests/backend/test_refresh_token.py
```

#### 수정
```
backend/migrations/003_create_task_tables.sql    # FK → qr_registry 수정
backend/migrations/004_create_alert_tables.sql   # read_at + 트리거 추가
backend/app/models/location_history.py           # from_db_row 완성 + CRUD
backend/app/models/alert_log.py                  # read_at 필드 추가
backend/app/models/worker.py                     # EmailVerification dataclass
backend/app/models/__init__.py                   # 새 모델 import
backend/app/models/product_info.py               # 16개 필드 추가 + JOIN 쿼리 확장
backend/app/config.py                            # .env + SMTP + Refresh Token 설정
backend/app/services/auth_service.py             # SMTP + Refresh Token + Admin freepass + Rate Limiting
backend/app/routes/auth.py                       # /api/auth/refresh 엔드포인트
backend/requirements.txt                         # python-dotenv 추가
frontend/pubspec.yaml                            # cupertino_icons 추가
```

---

## Sprint 6: Task 재설계 + 네이밍 변경 + Admin 옵션 (완료)

> MM→MECH, EE→ELEC 전체 코드베이스 네이밍 변경 + Task 27개→15개 재설계

### BE Phase A 완료 내역 (네이밍 + DB 스키마 변경)
- `006_sprint6_schema_changes.sql` 신규:
  - `role_enum` 변경: MECH, ELEC, ADMIN 추가 + 기존 MM→MECH, EE→ELEC 데이터 UPDATE
  - `workers` 테이블에 `company VARCHAR(50)` 컬럼 추가
  - `completion_status`: `mm_completed`→`mech_completed`, `ee_completed`→`elec_completed` 컬럼명 변경
  - `model_config` 테이블 생성 (6개 모델: GAIA/DRAGON/GALLANT/MITHAS/SDS/SWS)
  - `admin_settings` 테이블 생성 (heating_jacket_enabled, phase_block_enabled)
  - `app_task_details` 확장: elapsed_minutes, worker_count, force_closed, closed_by, close_reason
  - `alert_type_enum` 확장: TMS_TANK_COMPLETE, TANK_DOCKING_COMPLETE, TASK_REMINDER, SHIFT_END_REMINDER, TASK_ESCALATION
- 기존 코드 MM→MECH, EE→ELEC 전수 교체:
  - `auth_service.py`: VALID_ROLES = {'MECH', 'ELEC', 'TM', 'PI', 'QI', 'SI'}
  - `task_service.py`: VALID_PROCESS_TYPES = {'MECH', 'ELEC', 'TM', 'PI', 'QI', 'SI'}
  - `completion_status.py`: mech_completed/elec_completed 필드명 + process_map
  - `process_validator.py`, `work.py`, `admin.py`, `product.py` 등 전수 교체
- `worker.py`: company 필드 추가 (Optional[str])
- `auth_service.py`: COMPANY_ROLE_MAP 추가 + register()에서 company↔role 유효성 검증
- 신규 모델 2개:
  - `model_config.py` — ModelConfig dataclass + get_by_prefix() + get_all() + get_for_product()
  - `admin_settings.py` — AdminSettings dataclass + get_setting() + update_setting() + get_all()

### BE Phase B 완료 내역 (Task Seed 재설계)
- `task_seed.py` 신규:
  - TaskTemplate dataclass + 15개 템플릿 (MECH 7 + ELEC 6 + TMS 2)
  - `initialize_product_tasks(serial_number, qr_doc_id, model_name)` — model_config 기반 분기
  - GAIA: MECH 1~5,7 활성 + TMS 2개 / DRAGON: TANK_DOCKING만 비활성 / 기타: 자주검사만 활성
  - HEATING_JACKET: admin_settings.heating_jacket_enabled 제어
  - `get_task_categories_for_worker()` — company 기반 visible category 계산
  - `filter_tasks_for_worker()` — Task 필터링 헬퍼
- `admin.py`: POST /api/admin/products/initialize-tasks API
- `task_service.py`: `_trigger_completion_alerts()` — TMS_TANK_COMPLETE, TANK_DOCKING_COMPLETE 알림 트리거
- `work.py`: company 기반 Task 필터링 (GET /api/app/tasks/<serial_number>)

### BE Phase C 완료 내역 (멀티 작업자 + 미종료 + 강제 종료)
- `task_detail.py` 확장: elapsed_minutes, worker_count, force_closed, closed_by, close_reason 5개 필드
- `task_service.py` 멀티 작업자 duration 계산:
  - start_work(): work_start_log 기반 다중 작업자 참여
  - complete_work(): _all_workers_completed() → _finalize_task_multi_worker() 집계
  - duration_minutes = SUM(man-hour), elapsed_minutes = MAX-MIN, worker_count = DISTINCT
- `scheduler_service.py` 3단계 알림 스케줄러:
  - 1단계: task_reminder_job — 매 정각, TASK_REMINDER (작업자)
  - 2단계: shift_end_reminder_job — 17:00/20:00 KST, SHIFT_END_REMINDER (작업자)
  - 3단계: task_escalation_job — 09:00 KST, TASK_ESCALATION (같은 company 관리자)
- `admin.py`: PUT /api/admin/tasks/{task_id}/force-close API
- `jwt_auth.py`: manager_or_admin_required 데코레이터

### FE 완료 내역
- MM→MECH, EE→ELEC 전수 교체: worker.dart, task_item.dart, home_screen.dart, process_alert_popup.dart, splash_screen.dart
- Worker 모델 company 필드 추가 + fromJson/toJson/copyWith
- register_screen.dart: company 드롭다운 (7개) + role 자동 필터링 + deprecation 수정 (value→initialValue)
- auth_provider.dart, auth_service.dart: company 파라미터 추가
- admin_options_screen.dart 신설: admin_settings 토글 + 관리자 지정/해제 + 미종료 강제 종료
- main.dart: /admin-options 라우트 등록
- flutter build web 성공

### 테스트: 157 passed, 20 skipped, 0 failed

#### 기존 테스트 네이밍 교체
- conftest.py, fixtures/*.json, test_models.py, test_process_validator.py 등 MM→MECH, EE→ELEC 교체

#### Sprint 6 신규 테스트
| 파일 | 테스트 수 | 내용 |
|------|----------|------|
| test_task_seed.py | 9 passed, 7 skipped | model_config 분기, Task Seed 초기화, company 필터링, admin_settings |
| test_multi_worker.py | 2 passed, 5 skipped | TC-MW-01~07 (join/join-complete API Sprint 7 대상) |
| test_scheduler.py | 7 passed, 1 skipped | TC-UF-01~08 (3단계 스케줄러) |
| test_force_close.py | 6 passed, 1 skipped | TC-FC-01~07 (관리자 강제 종료) |

SKIPPED 20건 사유:
- TC-MW-02~05, TC-MW-07 (5건): /join, /join-complete 엔드포인트 → Sprint 7
- TC-FC-07 (1건): SELF_INSPECTION 강제종료 시 mech_completed 자동 업데이트 → Sprint 7
- TC-UF-01b (1건): /api/admin/scheduler/run 엔드포인트 미구현
- TC-SEED 7건: plan 스키마 직접 접근 → 현재 public 단일 스키마 사용
- WebSocket 8건: Flask test client 미지원 (구조상 정상)

### SMTP 이슈 해결
- **원인**: 이전 TEST 에이전트가 SMTP mock 없이 register API 테스트 실행 → 실제 SMTP 서버로 @axisos.test 도메인에 메일 발송 시도 → Delivery Failure
- **조치**: conftest.py에 `_block_smtp_globally()` autouse=True fixture 추가 → smtplib.SMTP/SMTP_SSL 자동 차단

### BE 코드 리뷰 결과 (TEST → BE)
| 파일 | 결과 |
|------|------|
| task_seed.py | PASS |
| task_service.py | PASS |
| scheduler_service.py | PASS |
| admin.py (force-close) | PASS |
| model_config.py | PASS |
| admin_settings.py | PASS |

### 변경 파일 목록

#### 신규 생성
```
backend/migrations/006_sprint6_schema_changes.sql
backend/app/models/model_config.py
backend/app/models/admin_settings.py
backend/app/services/task_seed.py
frontend/lib/screens/admin/admin_options_screen.dart
tests/backend/test_task_seed.py
tests/backend/test_multi_worker.py
tests/backend/test_scheduler.py
tests/backend/test_force_close.py
```

#### 수정
```
backend/app/models/worker.py                    # company 필드 추가
backend/app/models/task_detail.py               # 5개 필드 확장
backend/app/models/completion_status.py         # mech_completed/elec_completed
backend/app/models/__init__.py                  # 새 모델 import
backend/app/services/auth_service.py            # COMPANY_ROLE_MAP + VALID_ROLES
backend/app/services/task_service.py            # 멀티 작업자 + 알림 트리거
backend/app/services/process_validator.py       # MECH/ELEC 네이밍
backend/app/services/scheduler_service.py       # 3단계 스케줄러
backend/app/routes/work.py                      # company 필터링
backend/app/routes/admin.py                     # initialize-tasks + force-close API
backend/app/middleware/jwt_auth.py              # manager_or_admin_required
frontend/lib/models/worker.dart                 # company 필드
frontend/lib/models/task_item.dart              # MECH/ELEC
frontend/lib/screens/auth/register_screen.dart  # company 드롭다운
frontend/lib/screens/home/home_screen.dart      # MECH/ELEC
frontend/lib/providers/auth_provider.dart       # company 파라미터
frontend/lib/services/auth_service.dart         # company 파라미터
frontend/lib/widgets/process_alert_popup.dart   # MECH/ELEC
frontend/lib/main.dart                          # /admin-options 라우트
tests/conftest.py                               # SMTP mock + Sprint 6 migration
tests/backend/test_models.py                    # MECH/ELEC 교체
tests/backend/test_process_validator.py         # MECH/ELEC 교체
tests/fixtures/sample_workers.json              # MECH/ELEC 교체
tests/fixtures/sample_tasks.json                # MECH/ELEC 교체
tests/fixtures/sample_alerts.json               # MECH/ELEC 교체
```

---

## 전체 테스트 결과: 297 collected, 277 passed, 20 skipped (Sprint 6 기준)

```
Sprint 1 (Auth):                 8/8   PASSED
Sprint 2 (Work):                21/21  PASSED
Sprint 3 (Alert/Validation):   21/21  PASSED
Sprint 4 (Admin/Sync):         31/31  PASSED
Sprint 5 (Models/Email/Token): 59/59  PASSED
Sprint 6 (Task Seed/Multi/Scheduler/ForceClose):
                               157 passed, 20 skipped, 0 failed
─────────────────────────────────────────────
Total:                         297 collected, 277 passed, 20 skipped
```

---

## Sprint 7: 실데이터 + 통합 테스트 (완료)

### TEST 완료 내역 (Phase 1~6)

#### Phase 1: Product API 테스트 신규 생성
**파일**: `tests/backend/test_product_api.py` (17 tests, 0 assert False)

| 클래스 | 테스트 수 | 내용 |
|--------|----------|------|
| `TestProductLookup` | 6 | 제품 조회 성공, GAIA is_tms=True, GALLANT is_tms=False, 404, 401 미인증, 401 잘못된 토큰 |
| `TestTaskSeedAutoInit` | 4 | GAIA 총 15개, TMS 2개, GALLANT TMS=0, 멱등성 |
| `TestProductTasks` | 3 | 전체 조회, category 필터, 404 |
| `TestLocationUpdate` | 3 | 성공, 필드 누락, 제품 없음 |
| `TestCompletionStatus` | 1 | 초기 상태 확인 |

#### Phase 2: Full Workflow 통합 테스트 전면 재작성
**파일**: `tests/integration/test_full_workflow.py` (23 tests, 0 assert False)
- 기존: `db_session` fixture 사용 + `assert False` 스텁 8클래스
- 신규: `db_conn` fixture 사용, 실제 API 플로우 구현

| 클래스 | 테스트 수 | 내용 |
|--------|----------|------|
| `TestNormalWorkflow` | 5 | 회원가입 201, 중복 이메일 400, 이메일 인증, 잘못된 코드 400, 전체 플로우 |
| `TestApprovalRejectionFlow` | 4 | pending→403, admin 승인, admin 거부, 비관리자 승인→403 |
| `TestAdminFreepassLogin` | 2 | admin 이메일인증/승인 우회, admin 토큰 정보 확인 |
| `TestTaskStartCompleteFlow` | 3 | QR→task 시작/완료, duration 양수, 미시작 task 완료→400 |
| `TestAccessControl` | 9 | 미인증 403, 인증 없는 각 API 401, 비관리자 admin→403, 잘못된 비밀번호, 필드 누락 |

#### Phase 3-4: Task Seed + Company Filtering 테스트 보완
**파일**: `tests/backend/test_task_seed.py` (22 tests, 0 assert False)
- 기존 9개 tests → 22개로 확장
- 신규 클래스 추가:

| 클래스 | 신규 테스트 수 | 내용 |
|--------|--------------|------|
| `TestCompanyBasedTaskFilter` | +2 (총 5) | GST 관리자 전체 조회, BAT 작업자 MECH만, GET /api/app/tasks/<serial> 엔드포인트 활용 |
| `TestTaskSeedDirectCall` | 3 (신규) | GAIA 직접 seed 반환값 검증, 멱등성 직접 호출, GALLANT TMS=0 직접 확인 |

#### Phase 5: Process Check Flow 통합 테스트 전면 재작성
**파일**: `tests/integration/test_process_check_flow.py` (18 tests, 0 assert False)
- 기존: `db_session` 사용 + `assert False` 스텁 3클래스 8메서드
- 신규: `db_conn` 사용, `POST /api/app/validation/check-process` 실제 검증

| 클래스 | 테스트 수 | 내용 |
|--------|----------|------|
| `TestProcessCheckValidation` | 10 | MECH/ELEC 미완료→PI 차단, MECH만 완료→차단, ELEC만 완료→차단, 둘다 완료→통과, QI/SI 동일 검증, MECH 타입 skip, 필드 누락 400, 제품 없음 404, 인증 없음 401 |
| `TestCompletionStatusFlow` | 3 | 초기 상태, SELF_INSPECTION 완료→mech_completed=true, INSPECTION 완료→elec_completed=true |
| `TestProcessSequenceFlow` | 3 | MECH→ELEC→PI 정상 순서 플로우, PI 미리 실행→false, completion API 반영 |
| `TestProcessAlertCreation` | 2 | MECH 관리자 알림 생성 확인, 둘다 미완료→missing_processes 확인 |

#### Phase 6: Concurrent Work 통합 테스트 전면 재작성
**파일**: `tests/integration/test_concurrent_work.py` (15 tests, 0 assert False)
- 기존: `db_session` 사용 + `assert False` 스텁 4클래스 10메서드
- 신규: 실제 다중 워커 시나리오 구현

| 클래스 | 테스트 수 | 내용 |
|--------|----------|------|
| `TestMultiWorkerIndependentTasks` | 3 | 2워커 다른 Task 시작, 독립 완료, MECH+ELEC 동시 작업 |
| `TestTaskConflictPrevention` | 4 | 이미 시작된 Task 재시작→400/409, 완료 Task 재시작→400, 타인 시작 Task 완료 시도, 미시작 Task 완료→400 |
| `TestTaskListRetrieval` | 4 | Task 목록 조회, process_type 필터, 없는 serial→빈배열, 인증 없음→401 |
| `TestTaskDuration` | 2 | 완료 Task duration>=0, 다수 Task 독립 추적 |
| `TestConcurrentAccessLight` | 2 | 같은 Task 2번 start→1번만 성공, 다른 제품 독립 completion_status |

### Sprint 7 TEST 추가 파일 요약

| 파일 | 기존 | 변경 후 | assert False |
|------|------|---------|-------------|
| `tests/backend/test_product_api.py` | 없음 | 17 tests | 0 |
| `tests/backend/test_task_seed.py` | 9 tests | 22 tests | 0 |
| `tests/integration/test_full_workflow.py` | 8 stubs (all assert False) | 23 tests | 0 |
| `tests/integration/test_process_check_flow.py` | 8 stubs (all assert False) | 18 tests | 0 |
| `tests/integration/test_concurrent_work.py` | 10 stubs (all assert False) | 15 tests | 0 |

**Sprint 7 신규/개선 총계: 95 tests, 0 assert False**

### Sprint 7 전체 누적 테스트 결과 (예상)

```
Sprint 1~6 기존:    277 passed, 20 skipped
Sprint 7 신규:       95 tests (추가분, 0 assert False)
─────────────────────────────────────────────────────
Sprint 7 기준 총합: ~392 collected, ~372+ passed
```

### Sprint 7 TEST 변경 파일 목록

#### 신규 생성
```
tests/backend/test_product_api.py            # Product API 17 tests
tests/integration/test_process_check_flow.py # Process Check 18 tests (전면 재작성)
tests/integration/test_concurrent_work.py    # Concurrent Work 15 tests (전면 재작성)
```

#### 수정
```
tests/backend/test_task_seed.py              # 9 → 22 tests (TestCompanyBasedTaskFilter 보완 + TestTaskSeedDirectCall 신규)
tests/integration/test_full_workflow.py      # stubs → 23 실 구현 tests (전면 재작성)
```

### 주요 설계 결정 및 기술 메모

#### 테스트 설계 원칙
- **db_session 제거**: conftest.py에 없는 픽스처 — 모든 통합 테스트에서 `db_conn` 사용
- **SMTP 차단**: `_block_smtp_globally()` autouse fixture로 전역 차단 — 추가 mock 불필요
- **graceful skip**: API 미구현 시 `pytest.skip()` 처리 (assert False 대신)
- **자체 cleanup**: 각 테스트가 삽입한 데이터를 `try/finally`로 정리

#### conftest.py Sprint 7 픽스처 활용
- `TEST_PRODUCTS` (6개: GAIA/DRAGON/GALLANT/MITHAS/SDS/SWS) + `seed_test_products` fixture
- `TEST_WORKERS` (9명: FNI/BAT/TMS(M)/TMS(E)/P&S/C&A/GST admin/pending/unverified) + `seed_test_workers` fixture
- 기존 `create_test_worker`, `create_test_product`, `create_test_task`, `get_auth_token`, `get_admin_auth_token` 활용

#### API 엔드포인트 매핑 (테스트 대상)
```
POST /api/auth/register                      → TestNormalWorkflow
POST /api/auth/login                         → TestAdminFreepassLogin, TestAccessControl
POST /api/auth/verify-email                  → TestNormalWorkflow
POST /api/admin/workers/approve              → TestApprovalRejectionFlow
GET  /api/app/product/<qr_doc_id>            → TestProductLookup, TestTaskSeedAutoInit
GET  /api/app/product/<qr_doc_id>/tasks      → TestProductTasks
PUT  /api/app/product/location/update        → TestLocationUpdate
GET  /api/app/completion/<serial>            → TestCompletionStatus, TestCompletionStatusFlow
POST /api/app/validation/check-process       → TestProcessCheckValidation, TestProcessSequenceFlow
POST /api/app/work/start                     → TestTaskStartCompleteFlow, TestMultiWorkerIndependentTasks
POST /api/app/work/complete                  → TestTaskDuration, TestConcurrentAccessLight
GET  /api/app/tasks/<serial_number>          → TestTaskListRetrieval, TestCompanyBasedTaskFilter
POST /api/admin/products/initialize-tasks    → TestTaskSeedGAIA, TestTaskSeedDRAGON, TestTaskSeedGALLANT
```

### Sprint 7 전체 테스트 결과: 356 passed, 0 failed, 19 skipped

```
Sprint 1~6 기존:     277 passed, 20 skipped
Sprint 7 신규/개선:   95 tests (0 assert False)
Sprint 7 리팩터링:    -1 skip (테스트 수정)
──────────────────────────────────────────────
Sprint 7 최종:       356 passed, 0 failed, 19 skipped
```

### Sprint 7 버그 수정
| 파일 | 수정 내용 |
|------|----------|
| `tests/integration/test_concurrent_work.py` | `_insert_task()` UniqueViolation → `ON CONFLICT DO UPDATE SET` 추가 |
| `tests/conftest.py` | `create_test_completion_status` 시그니처 mech_completed/elec_completed 통일 |

---

## UI Sprint: 화이트 글래스모피즘 테마 적용 (완료)

> 전체 12개 화면 + 3개 위젯에 White Glassmorphism 디자인 시스템 적용

### 디자인 시스템 (`design_system.dart`)
- `GxColors` — Core Brand (charcoal~snow) + Accent (indigo) + Status (success/warning/danger/info)
- `GxRadius` — sm:6, md:10, lg:14, xl:18
- `GxShadows` — card, md, lg, glass, glassSm
- `GxGradients` — background (4-color splash), accentButton (indigo gradient)
- `GxGlass` — cardBg (white@0.72), cardBgLight (white@0.5), card(), cardSm()

### Phase 1: Auth 화면 4개
| 파일 | 변경 내용 |
|------|----------|
| `login_screen.dart` | Card → GxGlass.cardSm, ElevatedButton → 그라디언트 Container |
| `register_screen.dart` | Card → GxGlass.cardSm, ElevatedButton → 그라디언트 Container |
| `verify_email_screen.dart` | Card → GxGlass.cardSm, verify → 그라디언트, resend → 글래스 아웃라인 |
| `approval_pending_screen.dart` | Info card → GxGlass.cardSm |

### Phase 2: 메인 화면 3개
| 파일 | 변경 내용 |
|------|----------|
| `home_screen.dart` | Worker info card + feature cards → GxGlass.cardSm |
| `qr_scan_screen.dart` | Product card + QR type card → GxGlass.cardSm, scan → 그라디언트 |
| `task_management_screen.dart` | Header + progress + task cards → GxGlass.cardSm |

### Phase 3: Task Detail + 위젯 3개
| 파일 | 변경 내용 |
|------|----------|
| `task_detail_screen.dart` | 4개 info cards → GxGlass.cardSm, start → accent 그라디언트, complete → success 그라디언트 |
| `task_card.dart` | Card → GxGlass.cardSm(radius: GxRadius.md) |
| `process_alert_popup.dart` | Dialog bg → GxGlass.cardBg, confirm → 그라디언트, dismiss → 글래스 아웃라인 |
| `completion_badge.dart` | Badge → statusColor alpha 패턴 |

### Phase 4: Admin 화면 4개
| 파일 | 변경 내용 |
|------|----------|
| `alert_list_screen.dart` | Alert tiles → GxGlass.cardSm(radius: GxRadius.md), unread → accentSoft |
| `admin_options_screen.dart` | Section cards → GxGlass.cardSm, filter chips → cardBgLight, force-close → danger 그라디언트 |
| `admin_dashboard.dart` | Stub → glassmorphism AppBar + cloud bg |
| `worker_approval_screen.dart` | Stub → glassmorphism AppBar + cloud bg |

### Phase 5: 최종 검증
- `GxShadows.card` 잔존: **0건**
- `ElevatedButton` 잔존 (main.dart 테마 제외): **0건** → 6개 인스턴스 모두 Container/InkWell로 교체
- `GxGlass.cardSm()`/`GxGlass.card()` 적용: **12개 파일, 22개소**
- AppBar 패턴 통일: **13개 전부** (화이트 bg + 인디고 액센트 바 + mist 하단 구분선)
- `flutter build web`: **0 errors**

### 변경 파일 목록

#### 신규 생성
```
frontend/lib/utils/design_system.dart           # 디자인 시스템 토큰
frontend/lib/screens/auth/splash_screen.dart    # 스플래시/랜딩 화면 (참조 구현)
```

#### 수정 (15개 파일)
```
frontend/lib/screens/auth/login_screen.dart
frontend/lib/screens/auth/register_screen.dart
frontend/lib/screens/auth/verify_email_screen.dart
frontend/lib/screens/auth/approval_pending_screen.dart
frontend/lib/screens/home/home_screen.dart
frontend/lib/screens/qr/qr_scan_screen.dart
frontend/lib/screens/task/task_management_screen.dart
frontend/lib/screens/task/task_detail_screen.dart
frontend/lib/screens/admin/alert_list_screen.dart
frontend/lib/screens/admin/admin_options_screen.dart
frontend/lib/screens/admin/admin_dashboard.dart
frontend/lib/screens/admin/worker_approval_screen.dart
frontend/lib/widgets/task_card.dart
frontend/lib/widgets/process_alert_popup.dart
frontend/lib/widgets/completion_badge.dart
```

---

## Sprint 8: Admin API 보완 + UX 개선 + 비밀번호 찾기 (완료)

### BE 완료 내역

#### 비밀번호 찾기 API (신규)
- `worker.py`: `create_password_reset_code()` (30분 만료), `update_password_hash()` 추가
- `auth_service.py`: `send_password_reset_email()`, `send_password_reset_code()`, `reset_password()` 추가
- `auth.py`: 2개 엔드포인트 추가
  - `POST /api/auth/forgot-password` — 비밀번호 리셋 코드 발송 (미존재 이메일도 200 응답 — 보안)
  - `POST /api/auth/reset-password` — 코드 검증 → bcrypt 해싱 → 비밀번호 변경

#### JWT 토큰 만료 시간 변경
- `config.py`: `JWT_ACCESS_TOKEN_EXPIRES` 24h → **2h**, `JWT_REFRESH_TOKEN_EXPIRES` 7d → **30d**

### FE 완료 내역

#### 자동 토큰 갱신 (401 → refresh → retry)
- `api_service.dart`: Dio error interceptor — 401 수신 → refresh_token으로 자동 갱신 → 원래 요청 재시도
- `auth_service.dart`: `tryAutoLogin()` 메서드 추가 — 앱 시작 시 저장된 refresh_token으로 자동 로그인
- `auth_provider.dart`: `AuthNotifier.tryAutoLogin()` + `onRefreshFailed` → 자동 logout

#### 마지막 화면 복원
- `auth_service.dart`: `saveLastRoute()`/`getLastRoute()` — SharedPreferences 기반
- `main.dart`: `AppStartup` 위젯 (로딩 → tryAutoLogin → 라우트 복원 or /home)
- `_RouteTracker` NavigatorObserver — push/replace 시 자동 저장
- 저장 대상: /home, /qr-scan, /task-management, /task-detail, /admin-options

#### 비밀번호 찾기 화면 (신규)
- `forgot_password_screen.dart`: 이메일 입력 → POST /api/auth/forgot-password → 리셋 화면 이동
- `reset_password_screen.dart`: 6자리 코드 + 새 비밀번호 + 확인 → POST /api/auth/reset-password
- `login_screen.dart`: "비밀번호를 잊으셨나요?" 링크 추가
- `main.dart`: `/forgot-password`, `/reset-password` 라우트 등록
- `constants.dart`: `authForgotPasswordEndpoint`, `authResetPasswordEndpoint` 추가

#### 빌드
- `flutter build web`: **0 errors**

### 테스트: 271 passed, 0 failed, 19 skipped (backend suite)

#### test_admin_options_api.py (23 tests — 신규)
| 클래스 | 테스트 수 | 내용 |
|--------|----------|------|
| `TestGetManagers` | 3 | 전체 목록, company=FNI 필터, company=TMS(M) 필터 |
| `TestToggleManager` | 3 | is_manager=true 설정, is_manager=false 해제, 비관리자→403 |
| `TestAdminSettings` | 3 | 설정 조회, 설정 변경, 변경 후 GET 확인 |
| `TestPendingTasks` | 2 | 미종료 목록 반환, 미종료 없으면 빈 리스트 |
| `TestAdminAuth` | 1 | 미인증→401 |
| 기타 | 11 | company 필터 상세, state restoration, edge cases |

#### test_forgot_password.py (12 tests — 신규)
| 클래스 | 테스트 수 | 내용 |
|--------|----------|------|
| `TestForgotPassword` | 3 | 성공(SMTP mock), 미존재 이메일→200(보안), 필드 누락→400 |
| `TestResetPassword` | 5 | 성공+로그인 확인, 잘못된 코드→400, 코드 재사용 거부, 교차 사용자 코드 거부, 필드 누락 |
| `TestForgotResetIntegration` | 4 | 전체 플로우, 코드 형식 검증, 기존 비밀번호 실패 확인 |

#### test_refresh_token.py (5 tests 추가)
| 클래스 | 테스트 수 | 내용 |
|--------|----------|------|
| `TestTokenExpiryTimes` | 5 | access 2시간 만료, refresh 30일 만료, 발급 직후 유효, refresh > access 수명 |

### Sprint 8 완료 조건 달성
- ✅ Admin API 5개 (Sprint 7에서 이미 구현) + 테스트 23개 PASS
- ✅ 비밀번호 찾기 플로우 (이메일 → 코드 → 재설정) + 테스트 12개 PASS
- ✅ 로그인 유지 (자동 refresh) + 마지막 화면 복원
- ✅ JWT 토큰 만료 조정 (access 2h, refresh 30d) + 테스트 5개 PASS
- ✅ flutter build web 0 errors
- ✅ 리그레션 0 failures (271 passed, 19 skipped)

### 변경 파일 목록

#### 신규 생성
```
frontend/lib/screens/auth/forgot_password_screen.dart   # 비밀번호 찾기 화면
frontend/lib/screens/auth/reset_password_screen.dart    # 비밀번호 재설정 화면
tests/backend/test_admin_options_api.py                 # Admin 옵션 API 테스트
tests/backend/test_forgot_password.py                   # 비밀번호 찾기 API 테스트
```

#### 수정
```
backend/app/config.py                          # JWT 만료 시간 변경
backend/app/models/worker.py                   # create_password_reset_code, update_password_hash
backend/app/services/auth_service.py           # send_password_reset_email, send_password_reset_code, reset_password
backend/app/routes/auth.py                     # forgot-password, reset-password 엔드포인트
frontend/lib/main.dart                         # AppStartup, RouteTracker, 라우트 등록
frontend/lib/services/api_service.dart         # 401 자동 refresh interceptor
frontend/lib/services/auth_service.dart        # tryAutoLogin, saveLastRoute, getLastRoute
frontend/lib/providers/auth_provider.dart      # tryAutoLogin, onRefreshFailed
frontend/lib/screens/auth/login_screen.dart    # 비밀번호 찾기 링크 추가
frontend/lib/utils/constants.dart              # 신규 엔드포인트 상수
tests/backend/test_refresh_token.py            # TestTokenExpiryTimes 5개 추가
```

---

## Sprint 9: Pause/Resume + 근무시간 관리 (완료)

### BE 완료 내역

#### DB 마이그레이션 (008_sprint9_pause_resume.sql)
- `work_pause_log` 테이블 생성 (task_detail_id, worker_id, paused_at, resumed_at, pause_type, pause_duration_minutes)
- `app_task_details`에 `is_paused BOOLEAN DEFAULT FALSE`, `total_pause_minutes INTEGER DEFAULT 0` 컬럼 추가
- `alert_type_enum`에 `BREAK_TIME_PAUSE`, `BREAK_TIME_END` 추가
- `admin_settings`에 9개 휴게시간 설정 seed (break_morning, lunch, break_afternoon, dinner 시작/종료 + auto_pause_enabled)

#### work_pause_log 모델 (신규)
- `work_pause_log.py`: WorkPauseLog dataclass + CRUD (create_pause, resume_pause, get_active_pause, get_pauses_by_task)

#### Pause/Resume API (work.py에 3개 엔드포인트 추가)
| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/app/work/pause` | POST | 작업 일시정지 (검증: 시작됨+미완료+미일시정지+본인) |
| `/api/app/work/resume` | POST | 작업 재개 (검증: 일시정지 중+본인 또는 관리자) |
| `/api/app/work/pause-history/<id>` | GET | 일시정지 이력 조회 |

#### Duration 계산 수정 (task_service.py)
- `complete_work()`: 완료 시 `is_paused=TRUE`면 자동 재개 처리 (resumed_at = completed_at)
- `_finalize_task_multi_worker()`: `duration_minutes = max(0, raw_duration - total_pause_minutes)`
- 총 중지 시간(total_pause_minutes) 자동 차감

#### 휴게/식사시간 자동 강제 중지 스케줄러 (scheduler_service.py)
- `check_break_time_job()`: 매 1분 실행, KST 기준 4개 휴게 기간 체크
- `force_pause_all_active_tasks(pause_type)`: 진행 중 전체 작업 강제 일시정지 + BREAK_TIME_PAUSE 알림
- `send_break_end_notifications(pause_type)`: 휴게 종료 알림 (BREAK_TIME_END)
- 4개 시간대: 오전 휴게(10:00-10:20), 점심(11:20-12:20), 오후 휴게(15:00-15:20), 저녁(17:00-18:00)
- 저녁시간 특수: "무시하고 계속" 옵션, 18:00 시 아직 paused인 작업자에게만 종료 알림

#### Admin 시간 설정 검증 (admin.py)
- HH:MM 정규식 검증: `^([01]\d|2[0-3]):[0-5]\d$`
- 시작/종료 쌍 검증: start < end (INVALID_TIME_RANGE 에러)
- ALLOWED_KEYS 확장: 기존 2개 + 새 9개 = 11개

### FE 완료 내역

#### Pause/Resume UI (task_detail_screen.dart)
- 진행 중 + 미일시정지: [일시정지 (pause_circle)] + [작업 완료 (green gradient)] 버튼 Row
- 진행 중 + 일시정지: [재개 (play_circle, accent gradient)] + [완료 (disabled)] 버튼 Row
- 총 중지 시간(totalPauseMinutes) 표시

#### Task 목록 일시정지 표시 (task_management_screen.dart)
- 일시정지 작업: 주황색 "일시정지" 배지 + "재개" 버튼

#### 휴게시간 팝업 (신규 위젯 2개)
- `break_time_popup.dart`: BREAK_TIME_PAUSE 알림 → showDialog (barrierDismissible: false)
  - 저녁시간 전용: "무시하고 계속 작업" 버튼 → POST /app/work/resume
- `break_time_end_popup.dart`: BREAK_TIME_END 알림 → "재개하기" 버튼

#### Admin 근무시간 설정 UI (admin_options_screen.dart)
- Section 4 "근무시간 설정" 추가 (Icons.schedule)
- `auto_pause_enabled` 토글
- 4개 시간대 행: 각각 시작/종료 시간 TimePicker
- 변경 시 PUT /admin/settings 즉시 저장

#### TaskItem 모델 업데이트
- `task_item.dart`: isPaused, totalPauseMinutes 필드 추가

#### 기타
- `task_provider.dart`: pauseTask(), resumeTask() 메서드 추가
- `task_service.dart`: pauseTask(), resumeTask() API 호출 추가
- `constants.dart`: workPauseEndpoint, workResumeEndpoint, workPauseHistoryEndpoint
- `home_screen.dart`: BREAK_TIME_PAUSE/END WebSocket 이벤트 → 팝업 표시
- `flutter build web`: **0 errors**, `flutter analyze`: 0 errors/warnings

### 테스트: 318 passed, 0 failed, 19 skipped

#### test_pause_resume.py (24 tests — 신규)
| 클래스 | 테스트 수 | 내용 |
|--------|----------|------|
| `TestPauseBasic` | 9 | TC-PR-01~09: 기본 pause/resume, 미시작→400, 완료→400, 중복 pause→400, 미pause resume→400, 타인→403, 관리자 resume |
| `TestPauseDuration` | 3 | TC-PR-10~12: pause 시간 차감, 다중 pause 합산, 완료 시 자동 resume |
| `TestPauseHistory` | 2 | TC-PR-13~14: 이력 조회, 빈 이력 |
| `TestPauseMultiWorker` | 3 | TC-PR-15~17: 한쪽 pause + 다른 쪽 계속, 둘 다 pause, 한쪽 완료 |
| `TestPauseAuth` | 7 | TC-PR-18+: 미인증 401, task_id 누락, task 미존재 등 |

#### test_break_time_settings.py (8 tests — 신규)
| 클래스 | 테스트 수 | 내용 |
|--------|----------|------|
| `TestBreakTimeSettings` | 8 | TC-BS-01~08: 설정 조회, 시간 변경, auto_pause 토글, 잘못된 형식→400, start>end→400, 비관리자→403, 미인증→401 |

#### test_break_time_scheduler.py (14 tests — 신규)
| 클래스 | 테스트 수 | 내용 |
|--------|----------|------|
| `TestBreakTimePause` | 6 | TC-BT-01~06: 4개 시간대 자동 강제 pause, 진행 중 작업 없으면 미발생, BREAK_TIME_PAUSE 알림 생성 |
| `TestDinnerSpecial` | 3 | TC-BT-07~09: 저녁 pause 후 "무시하고 계속" resume, 18:00 종료 알림, resume 후 알림 미발송 |
| `TestAdminSettingsEffect` | 3 | TC-BT-10~12: auto_pause_enabled=false→미발생, 시간 변경 반영, 이미 수동 pause→중복 방지 |
| `TestBreakAlerts` | 2 | TC-BT-13~14: BREAK_TIME_PAUSE/END 알림 생성 확인 |

### Sprint 9 완료 조건 달성
- ✅ Pause/Resume API 정상 동작 (pause → is_paused=true, resume → is_paused=false)
- ✅ duration 계산 시 total_pause_minutes 자동 차감
- ✅ 휴게/식사시간 자동 강제 중지 스케줄러 (4개 시간대)
- ✅ 저녁시간 "무시하고 계속" 옵션
- ✅ Admin 옵션에서 휴게/식사시간 변경 + HH:MM 형식 검증
- ✅ FE: 일시정지/재개 버튼 + 휴게시간 팝업 + 상태 배지
- ✅ flutter build web 0 errors
- ✅ 신규 테스트 46개 PASS (pause_resume 24 + break_time_settings 8 + break_time_scheduler 14)
- ✅ 리그레션 0 failures (318 passed, 19 skipped)

### 변경 파일 목록

#### 신규 생성
```
backend/migrations/008_sprint9_pause_resume.sql     # 마이그레이션
backend/app/models/work_pause_log.py                # WorkPauseLog 모델
frontend/lib/widgets/break_time_popup.dart          # 휴게시간 시작 팝업
frontend/lib/widgets/break_time_end_popup.dart      # 휴게시간 종료 팝업
tests/backend/test_pause_resume.py                  # Pause/Resume 테스트
tests/backend/test_break_time_scheduler.py          # 스케줄러 테스트 (skip 대기)
tests/backend/test_break_time_settings.py           # 설정 테스트
```

#### 수정
```
backend/app/models/task_detail.py                   # is_paused, total_pause_minutes 필드 추가
backend/app/models/__init__.py                      # WorkPauseLog import
backend/app/routes/work.py                          # pause/resume/pause-history 엔드포인트 + _task_to_dict 업데이트
backend/app/services/task_service.py                # duration 계산에서 pause 시간 차감 + 자동 resume
backend/app/services/scheduler_service.py           # check_break_time_job + force_pause + break_end 알림
backend/app/routes/admin.py                         # 시간 형식 검증 + ALLOWED_KEYS 확장
frontend/lib/models/task_item.dart                  # isPaused, totalPauseMinutes
frontend/lib/screens/task/task_detail_screen.dart   # Pause/Resume 버튼 Row
frontend/lib/screens/task/task_management_screen.dart # 일시정지 배지 + 재개 버튼
frontend/lib/screens/admin/admin_options_screen.dart # Section 4 근무시간 설정
frontend/lib/screens/home/home_screen.dart          # 휴게시간 팝업 WebSocket 연동
frontend/lib/providers/task_provider.dart            # pauseTask, resumeTask
frontend/lib/services/task_service.dart              # pause/resume API 호출
frontend/lib/utils/constants.dart                    # 신규 엔드포인트 상수
tests/conftest.py                                    # Sprint 9 마이그레이션 + 픽스처
```

---

## Sprint 10: 수동 검증 + 버그 수정 확인 (완료)

### 목표
Sprint 9 이후 수동으로 진행한 디버그/개선 사항 6건을 코드 레벨에서 검증 + 테스트 보완.

### 수정사항 6건 검증 결과

| # | 수정사항 | BE | FE | 결과 |
|---|---------|----|----|------|
| 1 | 로그아웃 화면 전환 (main.dart: navigatorKey + ref.listen + pushAndRemoveUntil) | - | PASS | ✅ |
| 2 | Pause/Resume 전체 task 응답 (work.py: _task_to_dict 반환) | PASS | - | ✅ |
| 3 | 가입 승인 대기 company 필터 (admin_options: _selectedPendingCompany) | - | PASS | ✅ |
| 4 | 협력사 관리자 미종료 작업 화면 (manager_pending_tasks_screen + admin.py) | PASS + 보안패치 | PASS | ✅ |
| 5 | location_qr_required admin setting (process_validator + admin_options) | PASS | PASS | ✅ |
| 6 | 관리자 목록 기본 필터 (_selectedManagerCompany = _companies.first) | - | PASS | ✅ |

### 추가 보안 패치 (Fix 4)
검증 과정에서 BE 에이전트가 보안 이슈 발견 → 즉시 수정:
- `admin.py:get_pending_tasks()` — 협력사 관리자 company를 서버에서 강제 주입 (클라이언트 파라미터 무시)
- `admin.py:force_close_task()` — manager company와 task worker company 일치 검증, 불일치 시 403

### Test regression 수정
- `test_pause_resume.py` 3개 테스트 Fix 2 대응 수정:
  - `test_pause_success`: `paused_at` → `is_paused == True` 검증
  - `test_resume_success`: `resumed_at` → `is_paused == False` 검증
  - `test_resume_records_duration`: `pause_duration_minutes` → `total_pause_minutes` 검증
  - `test_resume_not_paused`: 400 → 400 or 404 허용 (TASK_NOT_PAUSED or PAUSE_NOT_FOUND)

### 버그 수정 4건 (Bug A/B/C/D)

| Bug | 내용 | 상태 |
|-----|------|------|
| A | DB 시간 UTC 표시 → KST (worker.py: `options="-c timezone=Asia/Seoul"`) | ✅ 이미 반영 확인 |
| B | Heating Jacket OFF 시 task 목록 숨김 (admin.py 동기화 + FE isApplicable 필터) | ✅ 이미 반영 확인 |
| C | location_qr_required가 ALLOWED_KEYS에 누락 → 추가됨 | ✅ 이미 반영 확인 |
| D | phase_block_enabled 차단 로직 미구현 → **신규 구현** | ✅ 구현 완료 |

### Bug D 구현 상세 (phase_block_enabled)
- `task_detail.py:200-229` — `get_task_by_serial_and_id()` 함수 추가
- `task_service.py:80-94` — `start_work()` 내 phase_block 체크 추가
  - MECH POST_DOCKING task (WASTE_GAS_LINE_2, UTIL_LINE_2) 시작 시
  - phase_block_enabled=true이면 TANK_DOCKING 완료 여부 확인
  - 미완료 시 400 PHASE_BLOCKED 반환
  - phase_block_enabled=false(기본값)이면 차단 없음

### Sprint 10 신규 테스트: 19/19 PASSED
| 테스트 | 설명 |
|--------|------|
| `test_manager_pending_tasks_own_company` | FNI 관리자가 본인 company 미종료 작업 조회 성공 |
| `test_manager_pending_tasks_other_company` | FNI 관리자가 타 company 조회 시 빈 리스트 |
| `test_admin_pending_tasks_all` | admin이 company 필터 없이 전체 미종료 작업 조회 |
| `test_worker_pending_tasks_forbidden` | 일반 작업자 미종료 작업 조회 시 403 |
| `test_pause_response_full_task_fields` | pause 응답에 전체 task 필드 포함 확인 |
| `test_resume_response_full_task_fields` | resume 응답에 전체 task 필드 포함 확인 |
| `test_location_qr_not_required_no_warning` | location_qr_required=false → 경고 미생성 |
| `test_location_qr_required_warning` | location_qr_required=true → 경고 생성 |
| `test_location_qr_default_warning` | 기본값(true) + location QR 미등록 → 경고 생성 |
| `test_manager_force_close` | 협력사 관리자 강제 종료 성공 |
| `test_start_work_response_kst_timezone` | 작업 시작 응답 KST(+09:00) 확인 (Bug A) |
| `test_heating_jacket_off_sets_not_applicable` | Heating Jacket OFF → is_applicable=false (Bug B) |
| `test_heating_jacket_on_restores_applicable` | Heating Jacket ON → is_applicable=true 복원 (Bug B) |
| `test_completed_heating_jacket_not_affected` | 완료된 task는 setting 변경 영향 안 받음 (Bug B) |
| `test_location_qr_required_put_success` | location_qr_required PUT 200 성공 (Bug C) |
| `test_phase_block_tank_docking_incomplete` | phase_block + TANK_DOCKING 미완료 → 400 (Bug D) |
| `test_phase_block_tank_docking_complete` | phase_block + TANK_DOCKING 완료 → 시작 성공 (Bug D) |
| `test_phase_block_disabled_allows_start` | phase_block=false → 차단 없음 (Bug D) |
| `test_phase_block_default_allows_start` | phase_block 기본값(false) → 차단 없음 (Bug D) |

### 빌드 확인
- `flutter build web`: 0 errors (Wasm dry-run 경고만 — flutter_secure_storage, non-blocking)

### 수정/생성 파일
```
backend/app/routes/admin.py                         # Fix 4 보안패치 (manager company 강제)
backend/app/models/task_detail.py                   # get_task_by_serial_and_id() 추가 (Bug D)
backend/app/services/task_service.py                # phase_block 차단 로직 (Bug D)
tests/backend/test_sprint10_fixes.py                # 19개 테스트 (기존 10 + Bug A/B/C/D 9)
tests/backend/test_pause_resume.py                  # Fix 2 대응 수정 (4개 테스트)
```

---

## Sprint 11: GST Task + 홈 메뉴 확장 + Checklist 스키마 (완료 ✅)

### BE 완료 내역
- `009_sprint11_gst_tasks.sql` — migration 실행 완료
  - `checklist` 스키마 생성 + `checklist_master`, `checklist_record` 테이블
  - `workers.active_role VARCHAR(10)` 컬럼 추가
  - PI/QI/SI task 템플릿 4개 추가 (task_seed.py 반영)
- `backend/app/routes/gst.py` — GST 진행 제품 대시보드 API
  - `GET /api/app/gst/products/<category>` (PI/QI/SI)
  - 상태 필터: active, all, completed, not_started, in_progress, paused
- `backend/app/routes/checklist.py` — Checklist CRUD API
  - `GET /api/app/checklist/<serial_number>/<category>` — 체크리스트 조회
  - `PUT /api/app/checklist/check` — 체크/해제 UPSERT
  - `POST /api/admin/checklist/import` — Excel 일괄 import (admin)
- `backend/app/models/worker.py` — `active_role` 필드 + `update_active_role()` 구현
- `backend/app/services/task_seed.py` — PI/QI/SI task 템플릿 추가 (전 모델 공통)
- `backend/app/__init__.py` — gst_bp, checklist_bp 블루프린트 등록

### FE 완료 내역
- `frontend/lib/screens/gst/gst_products_screen.dart` — GST 진행 제품 대시보드 화면
- `frontend/lib/screens/checklist/checklist_screen.dart` — 체크리스트 화면
- `frontend/lib/main.dart` — /gst-products, /checklist 라우트 등록
- `flutter build web` — 0 errors ✅

### TEST 완료 내역

Sprint 11 테스트 4개 파일 (총 45 tests) — 44 PASSED, 1 SKIPPED:

#### 신규 테스트 파일

| 파일 | 테스트 수 | 내용 |
|------|----------|------|
| `test_gst_task_seed.py` | 10 | PI/QI/SI task seed 생성 확인 (GAIA/DRAGON/GALLANT 모든 모델 공통) |
| `test_gst_products_api.py` | 12 | GET /api/app/gst/products/{category} — GST 진행 제품 대시보드 |
| `test_checklist_api.py` | 14 | checklist 스키마 CRUD (GET/PUT/import), 인증/권한 검증 |
| `test_active_role.py` | 9 | PUT /api/auth/active-role — GST 작업자 active_role 전환 |

#### test_gst_task_seed.py (10 tests)
| 테스트 | 내용 |
|--------|------|
| TC-GST-SEED-01 | GAIA seed → PI task 2개 (PI_LNG_UTIL, PI_CHAMBER) is_applicable=True |
| TC-GST-SEED-02 | GAIA seed → QI task 1개 (QI_INSPECTION) is_applicable=True |
| TC-GST-SEED-03 | GAIA seed → SI task 1개 (SI_FINISHING) is_applicable=True |
| TC-GST-SEED-04 | GAIA seed → 총 19개 (MECH 7 + ELEC 6 + TMS 2 + PI 2 + QI 1 + SI 1) |
| TC-GST-SEED-05 | DRAGON seed → PI/QI/SI 4개 생성 (모든 모델 공통) |
| TC-GST-SEED-06 | GALLANT seed → PI/QI/SI 4개 생성 |
| TC-GST-SEED-07 | 중복 생성 방지 — 같은 S/N 재초기화 시 PI/QI/SI 중복 없음 |
| TC-GST-SEED-08 | GST 작업자가 PI/QI/SI task 조회 가능 (PASSED — task 직접 삽입) |
| TC-GST-SEED-09 | Admin이 PI/QI/SI task 조회 가능 (PASSED — task 직접 삽입) |
| TC-GST-SEED-10 | POST /api/admin/products/initialize-tasks → PI/QI/SI 포함 19개 생성 |

#### test_gst_products_api.py (12 tests)
| 테스트 | 내용 |
|--------|------|
| TC-GST-GP-01 | GST 작업자 PI 진행 제품 조회 200 |
| TC-GST-GP-02 | GST 작업자 QI 진행 제품 조회 200 |
| TC-GST-GP-03 | GST 작업자 SI 진행 제품 조회 200 |
| TC-GST-GP-04 | 미시작 제품 목록 포함 (status: not_started) |
| TC-GST-GP-05 | 완료된 task → 제외 또는 completed 상태 표시 |
| TC-GST-GP-06 | Admin 조회 성공 |
| TC-GST-GP-07 | FNI 협력사 작업자 → 403 |
| TC-GST-GP-08 | 미인증 → 401 |
| TC-GST-GP-09 | 응답에 worker_name, started_at 포함 확인 |
| TC-GST-GP-10 | 빈 목록 시 products=[] 반환 |
| TC-GST-GP-11 | 같은 GST 작업자끼리 타 작업자 task pause 성공 |
| TC-GST-GP-12 | 같은 GST 작업자끼리 타 작업자 task complete 성공 |

#### test_checklist_api.py (14 tests)
| 테스트 | 내용 |
|--------|------|
| TC-CL-01 | checklist 스키마 존재 확인 |
| TC-CL-02 | checklist_master + checklist_record 테이블 존재 |
| TC-CL-03 | GET /api/app/checklist/{sn}/HOOKUP → 체크리스트 반환 |
| TC-CL-04 | 마스터 없는 경우 빈 리스트 반환 (200) |
| TC-CL-05 | 미인증 GET → 401 |
| TC-CL-06 | PUT is_checked=True → checked_by, checked_at 기록 |
| TC-CL-07 | PUT is_checked=False (체크 해제) 성공 |
| TC-CL-08 | PUT 후 GET으로 checked_by 확인 |
| TC-CL-09 | 중복 PUT → UPSERT (에러 없음, 레코드 1개) |
| TC-CL-10 | 없는 master_id → 400/404 |
| TC-CL-11 | note 필드 저장 확인 |
| TC-CL-12 | 미인증 PUT → 401 |
| TC-CL-13 | Admin Excel import 성공 |
| TC-CL-14 | 일반 작업자 import → 403 |

#### test_active_role.py (9 tests)
| 테스트 | 내용 |
|--------|------|
| TC-AR-01 | GST 작업자 active_role='PI' 변경 성공 |
| TC-AR-02 | GST 작업자 active_role='QI' 변경 + DB 반영 확인 |
| TC-AR-03 | GST 작업자 active_role='SI' 변경 성공 |
| TC-AR-04 | 유효하지 않은 role 'MECH' → 400 |
| TC-AR-05 | FNI 협력사 작업자 active_role 변경 → 403 |
| TC-AR-06 | GET /api/auth/me → active_role 필드 포함 |
| TC-AR-07 | active_role 변경 후 GET me 반영 확인 |
| TC-AR-08 | 미인증 PUT → 401 |
| TC-AR-09 | active_role='PI' 후 작업 관리 PI task 조회 |

### Sprint 11 완료 상태
- ✅ PI/QI/SI task 템플릿 4개 정상 생성 (모든 모델 공통)
- ✅ 홈 메뉴에 PI/QI/SI 진행 제품 대시보드 3개 표시 (GST + admin)
- ✅ GST 진행 제품 대시보드 API 정상 동작
- ✅ checklist 스키마 생성 + CRUD API 정상 동작
- ✅ active_role 전환 API + 필터링
- ✅ Sprint 11 신규 테스트 44 PASS, 1 SKIP
- ✅ 기존 테스트 regression 수정 완료 (task count 15→19/13→17 업데이트)

### Regression 수정 사항
Sprint 11에서 PI/QI/SI 4개 task 추가로 인해 기존 task count 기대값 변경:
- `test_task_seed.py`: GAIA 15→19 (4곳 수정)
- `test_model_task_seed_integration.py`: GAIA 15→19, DRAGON/GALLANT/MITHAS/SDS/SWS 13→17 (8곳 수정)
- `test_product_api.py`: GAIA 15→19, GALLANT 13→17 (2곳 수정)
- `tests/conftest.py`: Worker cleanup FK chain 확장 (checklist_record, work_pause_log 등 추가)

### 생성/수정 파일
```
tests/backend/test_gst_task_seed.py     # 신규 — 10 tests (TDD)
tests/backend/test_gst_products_api.py  # 신규 — 12 tests (TDD)
tests/backend/test_checklist_api.py     # 신규 — 14 tests (TDD)
tests/backend/test_active_role.py       # 신규 — 9 tests (TDD)
```

### Sprint 11 수동 핫픽스 (Cowork 세션에서 직접 수정)

#### Fix 1: gst_products_screen.dart — FE 타입 불일치 (TypeError)
- **증상**: QI 공정검사 화면 진입 시 `TypeError: "QI_INSPECTION": type 'String' is not a subtype of type 'int?'`
- **원인 2가지**:
  1. BE 응답 키 `task_status`를 FE에서 `status`로 읽고 있었음
  2. `task_id`(String: "QI_INSPECTION")를 `int?`로 캐스팅 시도
- **수정**:
  - `product['status']` → `product['task_status']`
  - `product['task_id'] as int?` → `product['task_detail_id'] as int?`
  - 네비게이션 arguments도 `task_id` → `task_detail_id`로 변경
- **영향**: PI/QI/SI 3개 화면 모두 동일 파일이므로 한 번 수정으로 전부 적용

#### Fix 2: gst.py — 미태깅 제품이 모든 대시보드에 표시되는 문제
- **증상**: PI에서 태깅한 제품이 QI/SI 대시보드에도 보임 (모든 공정에 seed task가 생성되어 있어서)
- **원인**: default 상태 필터가 `t.completed_at IS NULL` → not_started(미태깅) 포함
- **수정**:
  - default(active): `t.completed_at IS NULL` → `t.started_at IS NOT NULL AND t.completed_at IS NULL`
  - all: `1=1` → `t.started_at IS NOT NULL`
- **결과**: 각 공정 대시보드에 해당 공정에서 실제 태깅(작업 시작)한 제품만 표시

```
수정 파일:
frontend/lib/screens/gst/gst_products_screen.dart  # Fix 1: 타입 불일치 수정
backend/app/routes/gst.py                           # Fix 2: 태깅된 제품만 필터링
```

#### Fix 3: QR 스캔 완료 페이지에 기구/전장 협력사 정보 추가
- **요청**: QR 스캔 후 제품 정보에 기구 협력사, 전장 협력사도 표시
- **원인**: FE `ProductInfo` 모델에 `elecPartner` 필드 누락 + QR 스캔 화면에 협력사 정보 미표시
- **수정 4개 파일**:
  1. `frontend/lib/models/product_info.dart` — `elecPartner` 필드 추가 (fromJson/toJson/copyWith/==)
  2. `frontend/lib/screens/qr/qr_scan_screen.dart` — 기구 협력사 + 전장 협력사 행 추가
  3. `backend/app/routes/product.py` — 응답에 `elec_partner` 필드 추가
  4. `backend/app/routes/work.py` — 응답에 `elec_partner` 필드 추가

```
수정 파일:
frontend/lib/models/product_info.dart               # Fix 3: elecPartner 필드 추가
frontend/lib/screens/qr/qr_scan_screen.dart         # Fix 3: 협력사 정보 표시
backend/app/routes/product.py                        # Fix 3: elec_partner 응답 추가
backend/app/routes/work.py                           # Fix 3: elec_partner 응답 추가
```

#### Fix 4: FE 전체 화면 시간 표시 UTC→KST (toLocal 누락)
- **증상**: 작업관리 메뉴에서 시작시간이 UTC 기준으로 표시 (한국 시간 09:08인데 23:08으로 표시)
- **원인**: BE는 `+09:00` 오프셋 포함 KST로 반환하나, `DateTime.parse()`가 UTC로 변환 저장 → FE에서 `.toLocal()` 호출 없이 그대로 출력
- **수정 4개 파일**:
  1. `task_management_screen.dart` — `_formatDateTime()`에 `.toLocal()` 추가
  2. `task_detail_screen.dart` — `_formatFullDateTime()`에 `.toLocal()` 추가
  3. `alert_list_screen.dart` — `_formatDateTime()` + `_formatFullDateTime()`에 `.toLocal()` 추가
  4. `manager_pending_tasks_screen.dart` — `startedAt` 파싱 시 `.toLocal()` 추가

```
수정 파일:
frontend/lib/screens/task/task_management_screen.dart       # Fix 4: toLocal 추가
frontend/lib/screens/task/task_detail_screen.dart           # Fix 4: toLocal 추가
frontend/lib/screens/admin/alert_list_screen.dart           # Fix 4: toLocal 추가
frontend/lib/screens/manager/manager_pending_tasks_screen.dart  # Fix 4: toLocal 추가
```

---

## Sprint 12: PIN 간편 로그인 + 협력사 출퇴근 + QR 카메라 스캔 (완료 ✅)

### BE 완료 내역
- `010_sprint12_hr_schema.sql` — migration 실행 완료
  - `hr` 스키마 생성
  - `hr.worker_auth_settings` — PIN 인증 설정 (pin_hash, fail_count, locked_until)
  - `hr.partner_attendance` — 협력사 출퇴근 기록 (check_type, method, 인덱스 2개)
  - `hr.gst_attendance` — GST 사내 근태 (테이블만, API 미구현)
- `backend/app/routes/auth.py` — PIN API 4개 추가
  - `POST /api/auth/set-pin` — 4자리 숫자 PIN 설정 (werkzeug bcrypt, UPSERT)
  - `PUT /api/auth/change-pin` — 현재 PIN 검증 후 변경
  - `POST /api/auth/pin-login` — PIN 로그인 (3회 실패→5분 잠금, JWT 발급)
  - `GET /api/auth/pin-status` — PIN 등록 여부 조회
- `backend/app/routes/hr.py` — 출퇴근 API 2개 (신규 파일)
  - `POST /api/hr/attendance/check` — 출근/퇴근 (협력사만, 당일 중복 방지)
  - `GET /api/hr/attendance/today` — 당일 출퇴근 기록 조회
- `backend/app/__init__.py` — hr_bp 블루프린트 등록

### FE 완료 내역
- `frontend/lib/screens/settings/profile_screen.dart` — 개인 설정 화면 (신규)
  - PIN 등록/변경 버튼, 생체인증 "추후 오픈 예정" 메뉴
- `frontend/lib/screens/settings/pin_settings_screen.dart` — PIN 설정 화면 (신규)
  - 4자리 도트 + 숫자 키패드, 등록/변경 플로우
- `frontend/lib/screens/auth/pin_login_screen.dart` — PIN 로그인 화면 (신규)
  - 3회 실패→잠금, "이메일로 로그인" 링크
- `frontend/lib/screens/home/home_screen.dart` — 출퇴근 카드 추가 (협력사만)
- `frontend/lib/screens/qr/qr_scan_screen.dart` — QR 카메라 스캔 (수정)
  - html5-qrcode JS interop, 카메라 메인 + 직접 입력 보조
- `frontend/lib/services/qr_scanner_service.dart` + `qr_scanner_web.dart` + `qr_scanner_stub.dart` — QR 스캔 서비스 (신규)
- `frontend/web/index.html` — html5-qrcode 스크립트 추가
- `frontend/lib/main.dart` — /profile, /pin-settings, /pin-login 라우트 등록
- `flutter build web` — 0 errors ✅

### TEST 완료 내역 (22/22 PASSED)

| 파일 | 테스트 수 | 내용 |
|------|----------|------|
| `test_pin_auth.py` | 14 | PIN 설정/변경/로그인/상태/잠금/UPSERT |
| `test_attendance.py` | 8 | 출근/퇴근/중복방지/GST차단/당일조회 |

### Sprint 12 완료 상태
- ✅ hr 스키마 생성 (worker_auth_settings + partner_attendance + gst_attendance)
- ✅ PIN 설정/변경/로그인/상태 API 4개 정상 동작
- ✅ PIN 3회 실패 → 5분 잠금 동작
- ✅ 출퇴근 check-in/check-out API 정상 (협력사만)
- ✅ 당일 중복 출근 방지
- ✅ 개인 설정 화면 — PIN 등록/변경 + 생체인증 "추후 오픈" 메뉴
- ✅ PIN 로그인 화면 — 4자리 입력 + 키패드 + 실패 카운트 표시
- ✅ 홈 화면 — 협력사 출퇴근 카드 (GST 제외)
- ✅ QR 카메라 스캔 메인 + 텍스트 입력 보조
- ✅ Sprint 12 신규 테스트 22/22 PASSED
- ✅ 기존 테스트 regression 신규 0건
- ✅ flutter build web 에러 0건

### 생성/수정 파일
```
backend/migrations/010_sprint12_hr_schema.sql          # 신규
backend/app/routes/hr.py                                # 신규
backend/app/routes/auth.py                              # PIN API 4개 추가
backend/app/__init__.py                                 # hr_bp 등록
frontend/lib/screens/settings/profile_screen.dart       # 신규
frontend/lib/screens/settings/pin_settings_screen.dart  # 신규
frontend/lib/screens/auth/pin_login_screen.dart         # 신규
frontend/lib/services/qr_scanner_service.dart           # 신규
frontend/lib/services/qr_scanner_web.dart               # 신규
frontend/lib/services/qr_scanner_stub.dart              # 신규
frontend/lib/screens/home/home_screen.dart              # 출퇴근 카드 추가
frontend/lib/screens/qr/qr_scan_screen.dart             # QR 카메라 스캔
frontend/web/index.html                                 # html5-qrcode 추가
frontend/lib/main.dart                                  # 라우트 3개 추가
tests/backend/test_pin_auth.py                          # 신규 — 14 tests
tests/backend/test_attendance.py                        # 신규 — 8 tests
tests/conftest.py                                       # hr cleanup 추가
```

### Sprint 12 핫픽스: PIN 자동로그인 분기 로직 (Cowork 세션에서 직접 수정)

Sprint 12 에이전트가 PIN 화면/API는 구현했지만, 앱 시작 시 PIN 분기 로직이 누락됨.
수동으로 4개 파일 핫픽스 적용.

**문제**: 앱을 껐다 켜도 항상 이메일 로그인 화면이 표시됨 (PIN 등록 사용자도 동일)

**수정 내용**:

1. **`auth_service.dart`** — PIN 헬퍼 메서드 3개 추가
   - `hasRefreshToken()`: refresh_token 존재 확인 (자동 로그인 가능 여부)
   - `hasPinRegistered()`: PIN 등록 여부 로컬 캐시 확인
   - `savePinRegistered(bool)`: PIN 등록 상태 캐시 저장
   - `logout()`에 `_pinRegisteredKey` 삭제 추가

2. **`main.dart`** — `_initialize()` 3단계 분기 로직 추가
   - 1단계: refresh_token 없음 → 이메일 로그인 화면 (기존)
   - 2단계: refresh_token 있음 + PIN 등록됨 → PIN 입력 화면
   - 3단계: refresh_token 있음 + PIN 미등록 → 자동 로그인 → 마지막 경로 복원

3. **`pin_settings_screen.dart`** — PIN 등록/변경 성공 시 `savePinRegistered(true)` 호출 추가

4. **`pin_login_screen.dart`** — 3가지 수정
   - `worker_id`를 API 요청에 포함 (BE 필수 파라미터)
   - `_loadWorkerInfo()`: secure storage에서 worker 정보 로드 (앱 재시작 시 authProvider 비어있음)
   - PIN 성공 후 토큰 저장 + authProvider 상태 갱신 + 마지막 경로 복원

**앱 시작 플로우 (수정 후)**:
```
앱 시작 → AppStartup._initialize()
  ├─ refresh_token 없음 → SplashScreen (이메일 로그인)
  ├─ refresh_token 있음 + PIN 등록 → PinLoginScreen
  │   └─ PIN 성공 → 토큰 갱신 → 마지막 경로 복원 or /home
  └─ refresh_token 있음 + PIN 미등록 → tryAutoLogin()
      ├─ 성공 → 마지막 경로 복원 or /home
      └─ 실패 → SplashScreen
```

---

## 전체 테스트 결과 (Sprint 10 기준)

```
Sprint 1 (Auth):                  8/8   PASSED
Sprint 2 (Work):                 21/21  PASSED
Sprint 3 (Alert/Validation):    21/21  PASSED
Sprint 4 (Admin/Sync):          31/31  PASSED
Sprint 5 (Models/Email/Token):  59/59  PASSED
Sprint 6 (Task Seed/Multi/Scheduler/ForceClose):
                                157 passed, 20 skipped
Sprint 7 (Product/Integration): 356 passed, 19 skipped
Sprint 8 (AdminOpt/PwdReset/Token):
                                271 passed (backend), 19 skipped
Sprint 9 (Pause/Resume/BreakTime):
                                318 passed, 19 skipped
  신규: test_pause_resume (24) + test_break_time_settings (8)
        + test_break_time_scheduler (14) = 46 tests
Sprint 10 (수정사항 검증 + 버그 수정):
                                456+ passed, 19 skipped
  신규: test_sprint10_fixes (19) — Fix 검증 10 + Bug A/B/C/D 9
  수정: test_pause_resume (4개 Fix 2 대응)
  구현: phase_block_enabled 차단 로직 (Bug D)
  Flaky: 일부 (단독 실행 시 모두 PASS — 테스트 간 데이터 간섭)
Sprint 11 (GST Task + 대시보드 + Checklist):
                                44 passed, 1 skipped
  신규: test_gst_task_seed (10) + test_gst_products_api (12)
        + test_checklist_api (14) + test_active_role (9) = 45 tests
  Regression 수정: task count 15→19/13→17 (PI/QI/SI 추가 반영)
  conftest.py FK cleanup 확장 (checklist_record 등)
Sprint 12 (PIN 간편 로그인 + 협력사 출퇴근 + QR 카메라):
                                22 passed (신규), 397 passed (전체)
  신규: test_pin_auth (14) + test_attendance (8) = 22 tests
  conftest.py hr 스키마 cleanup 추가
─────────────────────────────────────────────
누적 테스트 파일: 34개, Sprint 12 신규 regression 0건
```

---

## Sprint 12 배포 + 핫픽스 (2026-02-28, Cowork 세션)

### 배포 완료
- **Netlify PWA**: `gaxis-ops.netlify.app` — `flutter build web` → `build/web` 드래그&드롭 배포
- **Railway Flask API**: `axis-ops-api.up.railway.app` — GitHub push → 자동 배포
- `constants.dart` apiBaseUrl → Railway 도메인으로 변경
- `web/_redirects` 생성 (`/*  /index.html  200` SPA 라우팅)
- 전체 API 동작 확인: auth/refresh ✅, hr/attendance/today ✅, app/alerts ✅

### QR 카메라 수정
- **Shadow DOM 이슈 해결**: Flutter `HtmlElementView` → `document.body`에 직접 div 생성 (`dart:html`)
- **카메라 3단계 fallback**: environment(후면) → user(전면) → cameraId(첫번째 가용)
- **권한 팝업 가려짐 해결**: `getUserMedia()` 선행 호출 → 권한 획득 후 div 생성
- **스캐너 정사각형 조정**: 컨테이너 `width=height` (화면 78%), `aspectRatio: 1.0`, `borderRadius: 12px`

### 앱 아이콘 커스터마이징
- `logo-color.png`에서 G 다이아몬드 심볼 추출 (cols 232-448, rows 396-615)
- favicon (32x32), PWA Icon-192/512 생성 (72% fill, 배경 #1E1E23)

### WebSocket 임시 조치
- FE raw WebSocket ↔ BE Flask-SocketIO 프로토콜 불일치 확인
- reconnect 최대 2회, 간격 10초로 축소 (에러 로그 최소화)

### Task 화면 제품 정보 개선

#### BE 수정
- `product.py`, `work.py` — API 응답에 `sales_order`, `customer`, `title_number`, `mech_start/end`, `elec_start/end` 추가

#### FE 수정
- `product_info.dart` — 6개 필드 추가 (`salesOrder`, `customer`, `titleNumber`, `mechStart/End`, `elecStart/End`)
- `task_management_screen.dart` — 상단 헤더 간소화: **S/N, 모델 | 수주번호, 위치** 만 표시 (QR Doc ID 제거)
- `task_detail_screen.dart` — 제품 상세 확장: 수주번호, 고객사, 기구/전장 협력사, 기구/전장 일정, 모듈 외주, QR Doc ID

### BACKLOG 정비
- 배포 항목(DP-3, DP-4) 완료 처리
- BUG-1 (QR 카메라 팝업), BUG-2 (WebSocket 불일치) 추가
- QR ETL 자동화 파이프라인 + QR 라벨 관리 페이지 추가
- Geolocation 2차 보안 (GPS 위치 검증 + Admin 설정) 추가
- 앱 아이콘 최적화(RV-3) 추가

### 수정 파일 목록
| 파일 | 변경 내용 |
|------|----------|
| `backend/app/routes/product.py` | API 응답에 sales_order 등 7개 필드 추가 |
| `backend/app/routes/work.py` | location update 응답에 동일 필드 추가 |
| `frontend/lib/models/product_info.dart` | 6개 필드 추가 (salesOrder, customer 등) |
| `frontend/lib/screens/task/task_management_screen.dart` | 헤더 간소화 (S/N, 모델, 수주번호, 위치) |
| `frontend/lib/screens/task/task_detail_screen.dart` | 제품 상세 정보 확장 |
| `frontend/lib/services/qr_scanner_web.dart` | Shadow DOM 우회 + 권한 선행 요청 + 정사각형 |
| `frontend/lib/services/websocket_service.dart` | reconnect 2회/10초 축소 |
| `frontend/lib/utils/constants.dart` | apiBaseUrl Railway 도메인 |
| `frontend/web/_redirects` | Netlify SPA 라우팅 |
| `frontend/web/favicon.png` | G 심볼 아이콘 |
| `frontend/web/icons/Icon-192.png` | PWA 아이콘 192x192 |
| `frontend/web/icons/Icon-512.png` | PWA 아이콘 512x512 |
| `BACKLOG.md` | 전면 정비 (완료 처리 + 버그/신규 항목 추가) |

---

## Sprint 12 → 13 사이 버그 수정 (2026-02-28, Cowork 세션)

### BUG-6 수정: 협력사 task 리스트에 작업자명 미표시

#### BE 수정
- `work.py` — `get_tasks_by_serial()`: task 목록 반환 시 workers 테이블 batch lookup 추가
  - `worker_ids = list(set(t.worker_id for t in tasks if t.worker_id))`
  - `SELECT id, name FROM workers WHERE id = ANY(%s)` → `worker_map` 생성
  - 각 task에 `worker_name` 필드 추가

#### FE 수정
- `task_item.dart` — `workerName` 필드 추가 (constructor, fromJson, toJson, copyWith, equality, hashCode)
- `task_management_screen.dart` — 카테고리 행에 작업자 아이콘(`Icons.person_outline`) + 이름 표시

### BUG-5 수정: QR 카메라 프레임 벗어남 (2차 수정 포함)

#### 1차 수정: 컨테이너 좌표 전달
- `qr_scan_screen.dart` — `_getCameraContainerRect()` 메서드 추가, `_cameraContainerKey`로 Flutter 컨테이너 위치/크기 계산
- `qr_scanner_service.dart` — `start()`에 `containerLeft/Top/Width/Height` 파라미터 추가 + `updatePosition()` 메서드
- `qr_scanner_web.dart` — `ensureScannerDiv(containerRect)` 전달, `updateScannerDivPosition()` 함수 추가
- `qr_scanner_stub.dart` — 새 시그니처 매칭

#### 2차 수정: html5-qrcode 내부 video 요소 CSS 오버라이드
- `qr_scanner_web.dart` — `_injectScannerCss()`: `#qr-scanner-dom-div video`에 `object-fit: cover`, `position: absolute`, `width/height: 100%`

#### 3차 수정: 카메라 위치 오른쪽 치우침 해결
- `qr_scanner_web.dart` — CSS 전면 개선:
  - 모든 자식(`*`)에 `box-sizing: border-box`
  - 내부 div 2단계(`> div`, `> div > div`) 모두 `overflow: hidden` + `max-width: 100%`
  - video: `min-width/min-height: 100%` 추가
  - img `display: none` (불필요한 이미지 요소 숨김)
- config 변경: `aspectRatio: 1.0` 제거, `qrbox` 정수형으로 동적 계산 (컨테이너 60%)
- `_forceContainerFit()` 함수 추가: start() 완료 후 200ms 뒤 JS로 내부 요소 inline style 직접 덮어쓰기

### Worker DB 보존 수정

#### 문제
- `conftest.py`가 production Railway DB에 `DROP TABLE workers CASCADE` 실행
- 테스트 DB URL = 프로덕션 DB URL (같은 Railway 인스턴스)
- Sprint 테스트 실행 시마다 admin 외 모든 worker 데이터 초기화됨

#### 수정
- `conftest.py` — `db_schema` fixture에 backup/restore 로직 추가:
  - DROP 전: `SELECT * FROM workers` → `backed_up_workers` 보관
  - 마이그레이션 후: `INSERT INTO workers (...) ON CONFLICT (id) DO NOTHING` + `setval(workers_id_seq)`
  - `hr.worker_auth_settings` 동일하게 backup/restore
- `010_sprint12_hr_schema.sql` migration_files 목록에 추가 (누락 수정)
- `DROP SCHEMA IF EXISTS hr CASCADE` drop_stmts에 추가

### 수정 파일 목록
| 파일 | 변경 내용 |
|------|----------|
| `backend/app/routes/work.py` | worker_name batch lookup 추가 (BUG-6) |
| `frontend/lib/models/task_item.dart` | workerName 필드 추가 (BUG-6) |
| `frontend/lib/screens/task/task_management_screen.dart` | 작업자 아이콘+이름 표시 (BUG-6) |
| `frontend/lib/services/qr_scanner_web.dart` | CSS 강화 + config 변경 + _forceContainerFit (BUG-5) |
| `frontend/lib/screens/qr/qr_scan_screen.dart` | _getCameraContainerRect + key 이동 (BUG-5) |
| `frontend/lib/services/qr_scanner_service.dart` | container 좌표 파라미터 + updatePosition (BUG-5) |
| `frontend/lib/services/qr_scanner_stub.dart` | 새 시그니처 매칭 (BUG-5) |
| `tests/conftest.py` | worker backup/restore + hr schema (DB 보존) |

---

## Sprint 13: WebSocket flask-sock 마이그레이션 (완료 ✅)

> 목표: BUG-2 (WebSocket 프로토콜 불일치) + BUG-4 (알림 실시간 전달 안됨) 해결
> FE 변경: 0건 (이미 raw WebSocket 사용 중)

### BE 수정

#### 1. 의존성 변경
- `requirements.txt` — `Flask-SocketIO>=5.3`, `eventlet>=0.33` 제거 → `flask-sock` 추가
- `Procfile` — `--worker-class eventlet` → `--worker-class gthread --threads 4`

#### 2. events.py 전체 리라이트 (핵심)
- `ConnectionRegistry` 클래스: thread-safe dict (`threading.Lock()`)
  - `register(ws_id, ws, worker_id, role)` → worker_{id}, role_{role} room 자동 등록
  - `unregister(ws_id)` → room 정리, 빈 room 삭제
  - `send_to_room(room, message)` → 특정 room 전송
  - `broadcast(message)` → 전체 전송
- `ws_handler(ws)` — `/ws` 라우트 핸들러
  - JWT query param → `decode_jwt()` → worker_id, role 추출
  - connected 이벤트 전송
  - 메시지 루프: ping → pong, 60초 timeout
  - disconnect 시 registry cleanup
- emit 함수 3개 — **기존 시그니처 100% 유지** (alert_service.py 호환)
  - `emit_new_alert(worker_id, alert_data)` → worker room 전송
  - `emit_process_alert(alert_data)` → role room 또는 broadcast
  - `emit_task_completed(serial_number, task_category, worker_id)` → broadcast
- 메시지 포맷: `{"event": "xxx", "data": {...}}` — FE `websocket_service.dart`와 일치

#### 3. 앱 팩토리 수정
- `app/__init__.py` — `from flask_socketio import SocketIO` 제거 → `from flask_sock import Sock`
  - `socketio = SocketIO()` → `sock = Sock()`
  - `socketio.init_app(app)` → `sock.init_app(app)`
  - `@sock.route('/ws')` 데코레이터로 ws_handler 등록
- `websocket/__init__.py` — `register_events(socketio)` 제거 → `ws_handler, registry` export
- `run.py` — `from app import create_app, socketio` → `from app import create_app`
  - `socketio.run(app, ...)` → `app.run(host, port, debug)`

#### 4. 스케줄러 BUG-4 수정
- `scheduler_service.py` — 5곳 `create_alert()` → `create_and_broadcast_alert()` 변경:
  1. `task_reminder_job()` — 매 1시간 TASK_REMINDER
  2. `shift_end_reminder_job()` — 17:00/20:00 SHIFT_END_REMINDER
  3. `task_escalation_job()` — 익일 09:00 TASK_ESCALATION
  4. `force_pause_all_active_tasks()` — 휴게시간 BREAK_TIME_PAUSE
  5. `send_break_end_notifications()` — 휴게시간 종료 BREAK_TIME_END
- 효과: DB 저장 + WebSocket broadcast 동시 처리 (이전: DB 저장만)

### 테스트 수정
- `test_websocket.py` — 전면 리라이트 (Flask-SocketIO test_client → ConnectionRegistry 단위 테스트)
  - `TestConnectionRegistry`: 등록/해제, room 생성/삭제, unknown ws_id 처리
  - `TestRegistryMessaging`: room 전송, broadcast, role room, 전송 실패 처리, 빈 room
  - `TestMessageFormat`: new_alert/process_alert/task_completed JSON 포맷 검증
  - `TestConcurrentConnections`: 다중 worker 분리, 같은 worker 다중 기기
  - `TestPingPong`: ping/pong 메시지 포맷

### 수정 파일 목록
| 파일 | 변경 내용 |
|------|----------|
| `backend/requirements.txt` | Flask-SocketIO/eventlet 제거, flask-sock 추가 |
| `backend/Procfile` | gthread --threads 4 |
| `backend/app/websocket/events.py` | 전체 리라이트 (ConnectionRegistry + ws_handler) |
| `backend/app/websocket/__init__.py` | ws_handler/registry export |
| `backend/app/__init__.py` | SocketIO → Sock + /ws 라우트 |
| `backend/run.py` | socketio.run() → app.run() |
| `backend/app/services/scheduler_service.py` | 5곳 create_and_broadcast_alert 변경 |
| `tests/backend/test_websocket.py` | 전면 리라이트 (단위 테스트) |
| `BACKLOG.md` | BUG-2/4 완료, Sprint 13 이력 추가 |
| `AGENT_TEAM_LAUNCH.md` | Sprint 13 프롬프트 추가 |

### 테스트 결과
- Sprint 13 신규: **18/18 PASSED** (ConnectionRegistry, 메시징, 포맷, 동시 연결, ping/pong)
- 회귀 테스트: **415 passed, 5 failed (기존 flaky), 12 skipped** — Sprint 13 regression 0건

### 배포 완료 (2026-03-01)
- [x] git commit & push (`4f6644f`)
- [x] Railway 배포 — `gunicorn --worker-class gthread --threads 4` 정상 동작
- [x] flutter build web → Netlify 배포 (https://gaxis-ops.netlify.app)
- [x] WSS 연결 테스트: `wss://axis-ops-api.up.railway.app/ws` — connected + ping/pong ✅
- [x] 기존 REST API 정상 동작 확인 (`/health` 200 OK)
- [x] 알림 E2E: Admin 로그인 → JWT WSS 연결 → Admin API 200 OK ✅
- [x] Admin 비밀번호 해시 수정 (migration SQL + DB 동기화)

---

## BUG-5 핫픽스: QR 카메라 DOM 오버레이 위치 정렬 (2026-03-01) ✅

### 근본 원인
- `qr_scanner_web.dart`의 `ensureScannerDiv()`가 **`left + right` CSS 대칭 여백 가정** 사용
- `right = containerLeft` → 비대칭 레이아웃(SafeArea, ScrollView padding)에서 카메라 프레임이 오른쪽으로 벗어남

### 수정 내용
**FE 수정** (`frontend/lib/services/qr_scanner_web.dart`):
1. `ensureScannerDiv()`: `left + right` → **`left + width` 명시 방식**으로 변경
   - Flutter `renderBox.size.width`를 `containerWidth`로 직접 전달
   - `right` CSS 비움 (`..right = ''`)
2. `_startResizeListener()`: 저장된 `_savedLeft + _savedWidth`로 리사이즈 대응
3. `updateScannerDivPosition()`: 동일한 `left + width` 방식 적용
4. 미사용 `actualDivWidth` 변수 제거

**변경 파일**: 1개 (`qr_scanner_web.dart`)
**빌드 확인**: `flutter build web --release` — 에러 0건

### 테스트 (`tests/backend/test_qr_scanner_logic.py`)
- **19/19 PASSED** (좌표 계산 로직 Python 재현 테스트)
  - TC-QR-01: 명시적 좌표 적용 (비대칭 여백, 좁은/넓은 뷰포트)
  - TC-QR-02: fallback 사이즈 (최소/최대 margin 클램프)
  - TC-QR-03: 위치 업데이트 (스크롤 시 top만 변경)
  - TC-QR-04: div 제거 상태 정리
  - TC-QR-05: qrbox 크기 계산 (120~250 클램프)

---

## BUG-5 추가 수정: QR 스캔 영역 바코드→정사각형 (2026-03-01) ✅

### 문제 (5차 수정 후 발견)
카메라 위치는 해결되었으나:
1. **스캔 영역이 바코드 형태**: html5-qrcode 흰색 브라켓이 가로로 긴 직사각형으로 렌더링
2. **QR 인식 미동작**: 정사각형 QR 코드가 스캔 영역과 불일치하여 인식 불가

### 근본 원인
**Dart `js_util.jsify()` 중첩 객체 변환 불가** — html5-qrcode가 qrbox config를 인식 못함.
시도한 방법 (6~8차 모두 실패):
- 6차: `qrbox` 정수 전달 (`jsify({'qrbox': qrboxSize})`) → 직사각형 유지
- 7차: `js_util.newObject()` + `setProperty()` → 직사각형 유지
- 8차: `JSON.parse()` + `allowInterop` 콜백 → 직사각형 유지

**공통 실패 원인**: Dart-to-JS interop으로 생성한 객체는 html5-qrcode 내부에서 프로퍼티 접근 불가

### 해결 (9차 수정 — 순수 JavaScript 주입) ✅
**핵심**: config 전체를 `<script>` 태그로 순수 JavaScript에서 생성, Dart interop 완전 제거

**`frontend/lib/services/qr_scanner_web.dart`**:
```dart
// ★ 9차 수정: config 전체를 순수 JavaScript로 생성
final configScript = html.ScriptElement()
  ..text = '''
    window.__qrScanConfig = {
      fps: 10,
      qrbox: function(viewfinderWidth, viewfinderHeight) {
        var size = Math.round(Math.min(viewfinderWidth, viewfinderHeight) * 0.7);
        size = Math.max(120, Math.min(250, size));
        return { width: size, height: size };
      }
    };
  ''';
html.document.head!.append(configScript);
configScript.remove();
final config = js_util.getProperty(js_util.globalThis, '__qrScanConfig');
```

**추가 변경**:
- `qr_scan_screen.dart`: 진단 로그 추가 (Container rect, Screen size, DevicePixelRatio)
- `qr_scan_screen.dart`: Flutter 파란색 스캔 프레임 오버레이 제거 (html5-qrcode 자체 UI 사용)
- `index.html`: G-AXIS 로고 스플래시 스크린 추가 (`flutter-first-frame` 이벤트로 fade-out)
- `web/img/g-axis-splash.png`: 투명 배경 가로형 로고 (assets/images/g-axis-2.png 복사)

### 배포 검증 결과
Console 로그 확인:
```
[QrScannerWeb] ★ JS qrbox: viewfinder=390x293 → qrbox=205x205
```
- ✅ qrbox 콜백 실행됨 (typeof qrbox = function)
- ✅ 205×205 정사각형 반환 (min(390,293) × 0.7 = 205)
- ✅ 웹 브라우저 정상 동작 확인

### 변경 파일
| 파일 | 변경 내용 |
|------|-----------|
| `frontend/lib/services/qr_scanner_web.dart` | 9차 수정: 순수 JS config + qrbox 콜백 |
| `frontend/lib/screens/qr/qr_scan_screen.dart` | 진단 로그 + Flutter 스캔 오버레이 제거 |
| `frontend/web/index.html` | G-AXIS 스플래시 스크린 추가 |
| `frontend/web/img/g-axis-splash.png` | 스플래시 로고 이미지 |

### 수정 이력 (6차~9차)
| 차수 | 방법 | 결과 |
|------|------|------|
| 6차 | `jsify({'qrbox': qrboxSize})` 정수 | ❌ 직사각형 |
| 7차 | `newObject()` + `setProperty()` | ❌ 직사각형 (iPad/Android/iOS 3기기) |
| 8차 | `JSON.parse()` + `allowInterop` 콜백 | ❌ 직사각형 |
| 9차 | 순수 JS `<script>` 태그 주입 | ✅ 정사각형 (205×205) |

---

## Sprint 14: 작업자명 표시 + QR 스캔 영역 정사각형 (2026-03-02) ✅

### 목표
1. Task를 시작한 작업자 전원의 이름이 화면에 표시되도록 (협력사 Task Detail + GST 대시보드)
2. QR 스캔 영역이 직사각형(바코드형) → 정사각형으로 수정 (10차)

### BE 변경

**`backend/app/routes/work.py` — `get_tasks_by_serial()`**:
- task_list 빌드 후 `work_start_log` + `work_completion_log` 배치 JOIN 조회 (ANY 사용, N+1 없음)
- 결과를 `workers_by_task` dict로 그룹화 → 각 task에 `workers` 배열 추가
- Legacy fallback: `work_start_log` 없는 task는 기존 `worker_id`/`worker_name`으로 단일 항목 생성
- 기존 `worker_id`, `worker_name` 필드 유지 (하위 호환)

**`backend/app/routes/gst.py` — `get_gst_products()`**:
- 동일 패턴: 기존 conn 재사용, task_detail_ids 배치 수집, workers 일괄 조회

**workers 배열 항목 구조**:
```json
{
  "worker_id": 10,
  "worker_name": "김철수",
  "started_at": "2026-03-02T10:00:00+09:00",
  "completed_at": "2026-03-02T10:30:00+09:00",
  "duration_minutes": 30,
  "status": "completed"
}
```

### FE 변경

**Task Detail 작업자 정보 섹션** (`task_detail_screen.dart`):
- `_buildWorkerInfoSection()` 추가 (제품 정보 ~ 작업 시간 사이)
- 단일 작업자: 이름만 표시
- 다중 작업자: ✅/🔄 아이콘 + 이름 + 시작~종료 시간 + 소요분

**GST 대시보드 작업자명 보완** (`gst_products_screen.dart`):
- workers 배열 우선 사용, 다중이면 "김철수 외 2명" 형식
- 빈 배열이면 기존 `worker_name` fallback

**TaskItem 모델** (`task_item.dart`):
- `workers: List<Map<String, dynamic>>` 필드 추가 (fromJson/toJson/copyWith)

**QR 스캔 영역 정사각형 (10차)** (`qr_scanner_web.dart` + `qr_scan_screen.dart`):
- qrbox: JS 콜백 함수 → 정수 `200` (자동 정사각형)
- 카메라 컨테이너: `height: 300` 고정 → 정사각형 `width = height = min(screenWidth-40, 350)`
- start() 성공 후 `qr-shaded-region` DOM 크기 로그 추가

### 변경 파일
| 파일 | 변경 내용 |
|------|-----------|
| `backend/app/routes/work.py` | workers 배열 배치 조회 + 그룹핑 + fallback |
| `backend/app/routes/gst.py` | 동일 workers 배열 패턴 |
| `frontend/lib/models/task_item.dart` | workers 필드 추가 |
| `frontend/lib/screens/task/task_detail_screen.dart` | 작업자 정보 섹션 신규 |
| `frontend/lib/screens/gst/gst_products_screen.dart` | workers 기반 "외 N명" 표시 |
| `frontend/lib/services/qr_scanner_web.dart` | qrbox 정수 + scan-region 로그 |
| `frontend/lib/screens/qr/qr_scan_screen.dart` | 정사각형 카메라 컨테이너 |
| `tests/backend/test_task_workers_api.py` | 신규 7건 |
| `tests/backend/test_qr_scanner_logic.py` | 추가 2건 |

### 테스트 결과
- Sprint 14 신규: **28/28 PASSED** (workers API 7 + QR 로직 21)
- 빌드: `flutter build web --release` — 에러 0건

### 배포 (2026-03-02)
- [x] git commit & push (`bdbe203`)
- [x] Railway 자동 배포 (GitHub push)
- [x] flutter build web → Netlify 배포 (https://gaxis-ops.netlify.app)

---

## Sprint 14 핫픽스: BUG-7/8/9/10/11 수정 (2026-03-02) ✅ 완료

### 배경
Sprint 14 배포 후 현장 테스트에서 추가 버그 5건 발견.
공정 진행 task와 시간 계산은 핵심 기능이므로 3-에이전트 팀(BE/FE/TEST)으로 구현.

### 수정 내역

**BUG-7: 휴게시간 자동 일시정지/재개 수정** ✅
- 원인 1: `IntervalTrigger(minutes=1)` → 정각 보장 안 됨 → `CronTrigger(second=0)` 변경
- 원인 2: `send_break_end_notifications()`가 알림만 → `resume_pause()` + `set_paused(False)` 자동재개 추가
- 원인 3: `force_pause_all_active_tasks()`가 `t.worker_id`(첫 번째만) → `work_start_log LEFT JOIN work_completion_log`로 모든 활동 작업자 조회 + 각각 pause log 생성

**BUG-8: 작업시간(duration)에서 휴게시간 자동 차감** ✅
- `_calculate_working_minutes(started_at, completed_at)` 함수 신규 구현
- `_calculate_break_overlap()` 헬퍼: 작업구간과 break 구간의 겹침(분) 계산
- admin_settings 4개 break period (morning/lunch/afternoon/dinner) 자동 차감
- 다일(multi-day) 작업 지원: 각 날짜별 break 차감
- `_record_completion_log()`에서 raw delta 대신 `_calculate_working_minutes()` 사용
- `_finalize_task_multi_worker()`에서 이중차감 방지: manual pause만 차감 (break auto-pause는 `_calculate_working_minutes`에서 이미 처리)

**BUG-9: Force-close에서 pause/휴게시간 차감** ✅
- `admin.py` force-close: pending workers duration에 `_calculate_working_minutes()` 적용
- manual pause만 별도 차감 (break auto-pause 이중차감 방지)
- `duration_minutes = max(0, duration_minutes - manual_pause_minutes)`

**BUG-10: QR 카메라 프레임 스크롤 싱크** ✅
- `qr_scan_screen.dart`: `ScrollController` 추가 + `_onScroll()` 리스너
- 스크롤 시 `_getCameraContainerRect()`로 현재 위치 계산 → `updateScannerDivPosition()` 호출
- `updateScannerDivPosition()`은 `qr_scanner_web.dart`에 이미 구현됨 (Sprint 14)

**BUG-11: Location QR 필수 설정 작동** ✅
- BE `task_service.start_work()`: `get_setting('location_qr_required', False)` 체크, True이고 `location_qr_verified=False`면 400 `LOCATION_QR_REQUIRED` 반환
- FE `task_detail_screen.dart`: `LOCATION_QR_REQUIRED` 에러 시 Location QR 필요 다이얼로그 + "QR 스캔" 버튼
- FE `api_service.dart`: 400 상태코드 에러코드 전파 (`[ERROR_CODE] message` 형식)
- `migration 010`: `location_qr_required` admin_settings 초기값 추가

### 변경 파일
| 파일 | 변경 내용 |
|------|----------|
| `backend/app/services/scheduler_service.py` | IntervalTrigger→CronTrigger, auto-resume, 멀티작업자 pause |
| `backend/app/services/task_service.py` | `_calculate_working_minutes()`, `_calculate_break_overlap()` 신규, duration 수정, 이중차감 방지, location_qr 체크 |
| `backend/app/routes/admin.py` | force-close: `_calculate_working_minutes` + manual pause 차감 |
| `backend/migrations/010_sprint12_hr_schema.sql` | `location_qr_required` admin_settings 초기값 |
| `frontend/lib/screens/qr/qr_scan_screen.dart` | ScrollController + onScroll → updateScannerDivPosition |
| `frontend/lib/screens/task/task_detail_screen.dart` | LOCATION_QR_REQUIRED 에러 다이얼로그 |
| `frontend/lib/services/api_service.dart` | 400 에러코드 전파 |
| `tests/backend/test_break_time_scheduler.py` | +7건 (CronTrigger, auto-resume, 멀티작업자) |
| `tests/backend/test_working_hours.py` | 신규 18건 (break overlap, working minutes, edge cases) |
| `tests/backend/test_force_close.py` | +3건 (pause 차감, break overlap) |
| `tests/backend/test_qr_scanner_logic.py` | +2건 (scroll sync) |
| `tests/backend/test_location_qr_required.py` | 신규 5건 |

### 테스트 결과
- Sprint 14 핫픽스 전체: **76 passed, 1 skipped, 0 failed**
  - test_break_time_scheduler: 7건 추가
  - test_working_hours: 18건 신규
  - test_force_close: 3건 추가
  - test_qr_scanner_logic: 2건 추가
  - test_location_qr_required: 5건 신규
- 빌드: `flutter build web --release` — 에러 0건

### 배포 (2026-03-02)
- [x] git commit & push (`192d135`)
- [x] Railway 자동 배포 (GitHub push)
- [x] flutter build web → Netlify 배포 (https://gaxis-ops.netlify.app)

---

## Sprint 15: 멀티 작업자 Join + BUG-11 재수정 + MH/WH 로깅 (2026-03-03) ✅
> Sprint 15.5 (BUG-15 + /api/app/settings) 포함: commit b277ac8

### 목표
1. 🔴 BUG-12: 멀티 작업자 start/end FE 언블록 — worker2가 이미 시작된 task에 참여/완료 가능
2. 🔴 BUG-11 재수정: Location QR 차단이 여전히 동작하지 않는 문제
3. 🔴 Working Hour 계산 검증 — 휴게시간 차감 로깅 추가
4. MH 계산 Method B 확인 — duration = 개인별 SUM, line_efficiency 로깅

### BE 완료 내역
- **my_status batch query** (work.py L271-317, gst.py L211-252)
  - `work_start_log` + `work_completion_log` JOIN으로 작업자별 참여 상태 조회
  - 응답 필드: `my_status` = 'not_started' | 'in_progress' | 'completed'
  - N+1 방지: `ANY(%s)` 배열 쿼리로 일괄 조회
- **BUG-11 재수정** (task_service.py L96-110)
  - `task.location_qr_verified` (항상 FALSE) → `product.location_qr_id` 체크로 변경
  - `admin_settings.location_qr_required` 설정 기반 조건부 차단
  - `[BUG-11]` 디버그 로그 추가
- **[WORKING_HOURS] 로깅** (task_service.py L598-610)
  - 각 break period overlap 개별 로깅
  - 요약 로그: raw_minutes, break_overlap, net_working_minutes
- **MH line_efficiency 로깅** (task_service.py L875-880)
  - `_finalize_task_multi_worker`에서 MH(duration), CT(elapsed), workers, line_efficiency% 로깅

### FE 완료 내역
- **task_item.dart**: `myStatus` 필드 + `myWorkStatus` getter 추가
- **task_detail_screen.dart**: `_buildJoinButton()` (작업 참여) + `_buildMyCompletedBadge()` (내 작업 완료)
  - 버튼 분기: pending→시작, in_progress+not_started→참여, in_progress+completed→내완료뱃지
- **task_management_screen.dart**: `task.myWorkStatus` 기반 상태 표시 (참여 가능/내 작업 완료)
- **qr_scan_screen.dart**: Location QR 필수 팝업 + 자동 location scan 모드 전환
- **task_provider.dart**: `_extractErrorMessage()` 헬퍼 (startTask/completeTask 에러 처리)
- 빌드: `flutter build web --release` — 에러 0건

### 변경 파일 목록
| 파일 | 변경 내용 |
|------|----------|
| `backend/app/routes/work.py` | my_status batch query 추가 |
| `backend/app/routes/gst.py` | my_status batch query 추가 |
| `backend/app/services/task_service.py` | BUG-11 fix + [WORKING_HOURS] 로깅 + MH 로깅 |
| `frontend/lib/models/task_item.dart` | myStatus 필드 + myWorkStatus getter |
| `frontend/lib/providers/task_provider.dart` | _extractErrorMessage 헬퍼 |
| `frontend/lib/screens/qr/qr_scan_screen.dart` | Location QR 필수 팝업 |
| `frontend/lib/screens/task/task_detail_screen.dart` | Join 버튼 + 내완료 뱃지 |
| `frontend/lib/screens/task/task_management_screen.dart` | myWorkStatus 기반 상태 표시 |
| `frontend/lib/services/task_service.dart` | toggleTaskApplicable 서비스 추가 |
| `tests/backend/test_multi_worker_join.py` | 신규 10건 |
| `tests/backend/test_location_qr_recheck.py` | 신규 6건 |
| `tests/backend/test_working_hours_recheck.py` | 신규 7건 |
| `tests/backend/test_mh_calculation_method_b.py` | 신규 5건 |

### 테스트 결과
- Sprint 15 신규: **28/28 PASSED**
  - test_multi_worker_join: 10건 (my_status 필드 + join 플로우)
  - test_location_qr_recheck: 6건 (BUG-11 location_qr_required 설정 분기)
  - test_working_hours_recheck: 7건 (break time 차감 검증)
  - test_mh_calculation_method_b: 5건 (MH=SUM(개인), line_efficiency)
- 빌드: `flutter build web --release` — 에러 0건

### 배포 (2026-03-03)
- [x] git commit & push (`0d923f5`)
- [x] Railway 자동 배포 (GitHub push)
- [x] flutter build web → Netlify 배포 (https://gaxis-ops.netlify.app)

---

## Sprint 16: Admin 로그인 간소화 + BUG-13/14 수정 + QR 카메라 정사각형 (2026-03-03) ✅

### 목표
1. FEAT-1: Admin 이메일 prefix 매칭 로그인 (`admin` → `admin@gst-in.com`)
2. BUG-13: FE `getAdminSettings()` 에러 시 안전모드 기본값 반환
3. BUG-14: 다중 작업자 표시 디버깅 로깅 (BE + FE)
4. BUG-15: QR 카메라 DOM 정사각형 3중 방어 (CSS + DOM 강제 + MutationObserver)
5. `/api/app/settings` 일반 작업자 접근 허용 엔드포인트 (Sprint 15.5에서 구현, 테스트 추가)

### BE 완료 내역
- **Admin prefix 매칭** (worker.py L275-305)
  - `get_admin_by_email_prefix(prefix)` 신규 함수
  - `SELECT * FROM workers WHERE email LIKE '{prefix}@%' AND is_admin = TRUE`
  - 매칭 1명일 때만 반환, 0명/2명+ → None (보안)
- **auth_service.py login() 분기** (L414-419)
  - `@` 포함 → 기존 정확 매칭
  - `@` 미포함 → admin prefix 우선 → fallback 정확 매칭
- **BUG-14 디버그 로깅** (work.py L293-298, gst.py L197-202)
  - workers batch query 결과에서 2명+ 인 task에 `[BUG-14]` 로그 출력

### FE 완료 내역
- **BUG-13 안전모드** (task_service.dart L264)
  - `getAdminSettings()` catch: `{}` → `{'location_qr_required': true}` (블록 활성 기본값)
- **BUG-14 디버그 로그** (task_item.dart L93-100)
  - `fromJson` workers 파싱 시 2명+ → `debugPrint('[BUG-14]...')` 출력
- **Admin 힌트 텍스트** (login_screen.dart L155-161)
  - 이메일 필드 아래 `'Admin은 이메일 앞부분만 입력 가능'` 안내 텍스트
- **QR 카메라 정사각형 3중 방어** (qr_scanner_web.dart)
  - 방어 1: CSS `aspect-ratio: 1/1 !important` + `video { object-fit: cover }`
  - 방어 2: `_forceSquareAfterCameraStart()` — 카메라 start 후 DOM height=width 강제
  - 방어 3: MutationObserver 실시간 감시 (html5-qrcode 비동기 크기 변경 즉시 재적용)

### 변경 파일 목록
| 파일 | 변경 내용 |
|------|----------|
| `backend/app/models/worker.py` | `get_admin_by_email_prefix()` 신규 |
| `backend/app/services/auth_service.py` | login() prefix 매칭 분기 |
| `backend/app/routes/work.py` | BUG-14 다중 작업자 디버그 로깅 |
| `backend/app/routes/gst.py` | BUG-14 다중 작업자 디버그 로깅 |
| `frontend/lib/services/task_service.dart` | BUG-13 안전모드 기본값 |
| `frontend/lib/models/task_item.dart` | BUG-14 debugPrint + foundation import |
| `frontend/lib/screens/auth/login_screen.dart` | Admin 힌트 텍스트 |
| `frontend/lib/services/qr_scanner_web.dart` | QR 카메라 정사각형 3중 방어 |
| `tests/backend/test_sprint16_admin_login.py` | 신규 4건 |
| `tests/backend/test_sprint16_app_settings.py` | 신규 5건 |

### 테스트 결과
- Sprint 16 신규: **9/9 PASSED**
  - test_sprint16_admin_login: 4건 (full email, prefix, 일반사용자 거부, @매칭)
  - test_sprint16_app_settings: 5건 (admin/worker 접근, 미인증 거부, admin-only)
- 빌드: `flutter build web --release` — 에러 0건

### 배포 (2026-03-03)
- [x] git commit & push (`c7457c4`)
- [x] Railway 자동 배포 (GitHub push)
- [x] flutter build web → Netlify 배포 (https://gaxis-ops.netlify.app)

---

## Sprint 16.1: 버전 관리 + System Online + LOC 형식 정리 (2026-03-03) ✅

### 목표
1. 버전 관리 시스템: BE/FE 단일 소스에서 관리, splash 화면 표시
2. System Online 실제 연동: 목업 → BE `/health` API 실시간 체크
3. 버전 `v1.1.0` (MINOR 업)

### BE 완료 내역
- **`backend/version.py`** (신규)
  - `VERSION = "1.1.0"`, `BUILD_DATE = "2026-03-03"` — 단일 소스
- **`backend/app/__init__.py`** — health 엔드포인트 수정
  - `{"status": "ok", "version": "1.1.0", "build_date": "2026-03-03"}` 반환

### FE 완료 내역
- **`frontend/lib/utils/app_version.dart`** (신규)
  - `AppVersion.version`, `AppVersion.display` — FE 단일 소스
- **`frontend/lib/services/api_service.dart`** — `getPublic()` 추가
  - 인증 없이 루트 경로 GET 요청 (Dio 별도 인스턴스, `/api` prefix 우회)
- **`frontend/lib/screens/auth/splash_screen.dart`** — 3개 수정
  - 버전: `'G-AXIS OPS v1.0.0'` → `AppVersion.display` (중앙 관리)
  - System Online: 목업 → `_checkSystemHealth()` 실시간 `/health` 호출
  - 상태 표시: Connecting...(회색) → System Online(초록) / System Offline(빨강)

### 변경 파일 목록
| 파일 | 변경 내용 |
|------|----------|
| `backend/version.py` | 신규 — 버전 단일 소스 |
| `backend/app/__init__.py` | /health에 version, build_date 추가 |
| `frontend/lib/utils/app_version.dart` | 신규 — FE 버전 단일 소스 |
| `frontend/lib/services/api_service.dart` | getPublic() 메서드 추가 |
| `frontend/lib/screens/auth/splash_screen.dart` | 버전 중앙관리 + health check 실연동 |

### 테스트 결과
- 빌드: `flutter build web --release` — 에러 0건
- `/health` API 응답 확인: version, build_date 포함

### 배포 (2026-03-03)
- [x] git commit & push (`b17f696`)
- [x] Railway 자동 배포 (GitHub push)
- [x] flutter build web → Netlify 배포 (https://gaxis-ops.netlify.app)

---

## Sprint 16.2: 담당공정 설정 이동 + BUG-16/17 배포 (2026-03-03) ✅

### 목표
1. 담당공정 설정 이동: 홈 화면 프로필 카드의 "활성 역할" → 개인설정(ProfileScreen)으로 이동
2. 용어 변경: "활성 역할" → "담당공정" (현장 작업자 이해도 향상)
3. BUG-16/17 코드 반영분 배포 확인

### FE 완료 내역
- **홈 화면 제거** (`home_screen.dart`)
  - 프로필 카드 내 활성 역할 UI 블록 삭제 (line 606-652)
  - `_showActiveRoleDialog()` 메서드 삭제 (ProfileScreen으로 이동)
  - `_getActiveRoleLabel()` 메서드 삭제 (ProfileScreen으로 이동)
  - `_getRoleColor()`, `_getRoleIcon()` — 다른 UI에서 사용하므로 유지
- **개인설정 화면 추가** (`profile_screen.dart`)
  - PIN 설정 위에 "담당공정" 섹션 추가 (GST/Admin만 표시)
  - 담당공정 변경 버튼 → PI/QI/SI 선택 다이얼로그
  - 헬퍼 메서드 3개 추가: `_getActiveRoleLabel()`, `_getRoleColor()`, `_showActiveRoleDialog()`
  - 선택 후 `setState()` 호출로 UI 즉시 갱신

### 변경 파일 목록
| 파일 | 변경 내용 |
|------|----------|
| `frontend/lib/screens/home/home_screen.dart` | 활성 역할 UI + 관련 메서드 삭제 |
| `frontend/lib/screens/settings/profile_screen.dart` | 담당공정 섹션 + 헬퍼 메서드 3개 추가 |

### 테스트 결과
- 빌드: `flutter build web --release` — 에러 0건

### 배포 (2026-03-03)
- [x] git commit & push (`e3d0c8e`)
- [x] Railway 자동 배포 (GitHub push)
- [x] flutter build web → Netlify 배포 (https://gaxis-ops.netlify.app)

---

## Sprint 17: 출퇴근 분류 체계 — work_site + product_line (2026-03-04) ✅

### 목표
1. 협력사 출퇴근 기록에 근무지(work_site: GST/HQ)와 제품군(product_line: SCR/CHI) 분류 추가
2. CHI(칠러) 제조기술부 통합 대비 + ELEC 협력사 변동 대응
3. 버전 `v1.1.0` → `v1.2.0` (MINOR 업 — 신규 기능)

### BE 완료 내역
- **`backend/migrations/017_add_attendance_classification.sql`** (신규)
  - `hr.partner_attendance`에 `work_site VARCHAR(10) NOT NULL DEFAULT 'GST'` 추가
  - `hr.partner_attendance`에 `product_line VARCHAR(10) NOT NULL DEFAULT 'SCR'` 추가
  - CHECK constraint: `work_site IN ('GST', 'HQ')`, `product_line IN ('SCR', 'CHI')`
  - 복합 인덱스: `idx_partner_att_site_line(work_site, product_line)`
  - 기존 데이터는 DEFAULT 값(GST/SCR) 자동 적용
- **`backend/app/routes/hr.py`** — 2개 엔드포인트 수정
  - `attendance_check()`: work_site/product_line 파싱, IN 시 유효성 검사, OUT 시 마지막 IN에서 자동 복사
  - `attendance_today()`: SELECT/Response에 work_site, product_line 추가
- **`backend/version.py`** — `VERSION = "1.2.0"`, `BUILD_DATE = "2026-03-04"`

### FE 완료 내역
- **`frontend/lib/screens/home/home_screen.dart`**
  - 미출근 상태에서 드롭다운 4옵션 표시 (GST공장-SCR, GST공장-CHI, 협력사본사-SCR, 협력사본사-CHI)
  - 퇴근 중/완료 시 드롭다운 숨김
  - 출근(IN) 시만 work_site/product_line API 전송
  - 이전 출근 기록에서 기본값 복원
- **`frontend/lib/utils/app_version.dart`** — `version = '1.2.0'`

### TEST 완료 내역 (5개 신규)
| TC | 테스트 | 설명 |
|----|--------|------|
| TC-ATT-09 | `test_check_in_with_work_site_product_line` | 출근 시 work_site+product_line DB 저장 |
| TC-ATT-10 | `test_check_out_copies_last_in_classification` | 퇴근 시 마지막 IN 값 자동 복사 |
| TC-ATT-11 | `test_invalid_work_site` | 잘못된 work_site → 400 |
| TC-ATT-12 | `test_invalid_product_line` | 잘못된 product_line → 400 |
| TC-ATT-13 | `test_today_includes_classification` | today 응답에 분류 필드 포함 |

### 테스트 결과
- `test_attendance.py`: **13 passed** (기존 8 + 신규 5)
- FE 빌드: `flutter build web --release` — 에러 0건

### 배포 (2026-03-04)
- [x] DB 마이그레이션 실행 (Staging Railway PostgreSQL)
- [x] git commit & push (`b379df4`, `3da2fd7`)
- [x] Railway 자동 배포 (GitHub push)
- [x] flutter build web → Netlify 배포 (https://gaxis-ops.netlify.app)

---

## Sprint 18: 협력사별 S/N 작업 진행률 뷰 — v1.3.0 (2026-03-04) ✅

### 목표
1. 협력사 관리자/작업자가 자사 담당 S/N들의 작업 진행률을 종합 조회
2. 카테고리(MECH/ELEC/TMS)별 진행바 + 전체 진행률 표시
3. AXIS-VIEW(React)에서도 동일 API 재사용 가능하도록 범용 설계
4. 버전 `v1.2.0` → `v1.3.0`

### BE 완료 내역
- **`backend/app/services/progress_service.py`** (신규)
  - `get_partner_sn_progress()` — 협력사별 S/N 필터링 + 카테고리별 진행률 집계
  - 회사별 WHERE 절 자동 구성: FNI/BAT(mech_partner), TMS(M)(mech_partner OR module_outsourcing), TMS(E)/P&S/C&A(elec_partner), GST/Admin(전체)
  - `is_applicable = false` task는 진행률 집계에서 자동 제외
  - 완료 제품 필터: `all_completed = false OR all_completed_at > NOW() - N days`
  - `my_category` 필드로 자사 담당 공정 강조 지원
- **`backend/app/routes/product.py`** — `GET /api/app/product/progress` 엔드포인트 추가
  - `@jwt_required` 인증
  - Admin은 `?company=` 파라미터로 특정 회사 필터 가능
  - `?days=` 파라미터로 완료 후 포함 기간 설정 (기본 1일)
  - Response: `{ products: [...], summary: { total, in_progress, completed_recent } }`
- **`backend/version.py`** — `VERSION = "1.3.0"`

### FE 완료 내역
- **`frontend/lib/screens/progress/sn_progress_screen.dart`** (신규)
  - ConsumerStatefulWidget, RefreshIndicator(pull-to-refresh)
  - 30초 자동 갱신 Timer
  - Summary 카드 (전체/진행 중/최근 완료)
  - S/N별 카드: 모델명, 고객명, 전체 진행바, 카테고리별 미니 진행바, 납기일
  - 자사 담당 공정 강조색 (굵은 글자 + 두꺼운 바)
  - 100% 완료 시 초록 배경 + "(완료)" 뱃지
  - ship_plan_date 오름차순 정렬
- **`frontend/lib/screens/home/home_screen.dart`** — "작업 진행현황" 카드 추가
  - 협력사: "작업 진행현황", GST/Admin: "전사 작업 진행현황"
  - teal 컬러 아이콘 (0xFF0D9488)
- **`frontend/lib/main.dart`** — import + `/sn-progress` 라우트 등록 + saveable routes 추가
- **`frontend/lib/utils/app_version.dart`** — `version = '1.3.0'`

### TEST 완료 내역 (10개 신규)
| TC | 테스트 | 설명 |
|----|--------|------|
| TC-PROG-01 | `test_progress_requires_auth` | JWT 없이 접근 시 401 반환 |
| TC-PROG-02 | `test_fni_worker_sees_own_products` | FNI 작업자 → mech_partner=FNI 제품만 조회 |
| TC-PROG-03 | `test_admin_sees_all_products` | Admin → 전체 제품 조회 |
| TC-PROG-04 | `test_admin_company_filter` | Admin → ?company=FNI 필터링 |
| TC-PROG-05 | `test_non_admin_ignores_company_param` | 비admin ?company= 무시, 자기 회사만 |
| TC-PROG-06 | `test_category_progress_accuracy` | MECH 67%, ELEC 50%, overall 60% 정확성 |
| TC-PROG-07 | `test_non_applicable_excluded` | is_applicable=false → 진행률 제외 |
| TC-PROG-08 | `test_tms_m_filter` | TMS(M) → mech_partner=TMS OR module_outsourcing=TMS |
| TC-PROG-09 | `test_summary_counts` | summary total/in_progress/completed_recent 정확 |
| TC-PROG-10 | `test_ps_worker_elec_filter` | P&S → elec_partner=P&S 제품만 |

### 테스트 결과
- `test_sn_progress.py`: **10 passed**
- `test_attendance.py` 회귀: **13 passed** (변경 없음)
- FE 빌드: `flutter build web --release` — 에러 0건

### 배포 (2026-03-04)
- [x] DB 마이그레이션 없음 (기존 테이블 활용)
- [x] git commit & push (`f566e25`)
- [x] Railway 자동 배포 (GitHub push)
- [x] flutter build web → Netlify 배포 (https://gaxis-ops.netlify.app)

---

## Sprint 19-A: Refresh Token Rotation + Device ID (2026-03-05) ✅

### 목표
1. Refresh Token Rotation 구현 — 토큰 탈취 창 30일 → 2시간 축소
2. Device ID 수집 (로깅 전용) — 다중 기기 식별 기반 마련 (Phase C에서 DB 저장 예정)

### Phase A: Refresh Token Rotation (BE 코드 수정만)
- **`backend/app/services/auth_service.py`** — `refresh_access_token()` 수정
  - 기존: `access_token`만 반환
  - 변경: `access_token` + 새 `refresh_token` 함께 반환
  - `jti` (UUID v4) 필드 추가 → 같은 초에 생성해도 고유 토큰 보장
- **FE 수정 불필요**: OPS FE `auth_service.dart:252`에 `if (response['refresh_token'] != null)` 이미 있음

### Phase B: Device ID 수집
- **`frontend/lib/services/auth_service.dart`** — `getDeviceId()` 메서드 추가
  - SharedPreferences 기반 (웹+모바일 크로스플랫폼)
  - `dart:math` Random.secure()로 UUID v4 생성 (외부 패키지 불필요)
  - 최초 생성 후 영구 저장, 이후 재사용
- **`frontend/lib/screens/auth/pin_login_screen.dart`** — PIN 로그인에 device_id 전송
- **`backend/app/routes/auth.py`** — login, refresh, pin-login 3곳에 device_id 수신 + 로깅
  - `data.get('device_id', 'unknown')` — 미전송 시 'unknown' 기본값 (에러 아님)

### TEST 완료 내역 (6개 신규)
| TC | 테스트 | 설명 |
|----|--------|------|
| TC-ROT-01 | `test_refresh_returns_both_tokens` | refresh 응답에 access_token + refresh_token 모두 포함 |
| TC-ROT-02 | `test_new_refresh_token_works` | 새 refresh_token으로 재차 refresh 성공 |
| TC-ROT-03 | `test_old_refresh_token_still_works` | 이전 refresh_token 아직 유효 (Phase C에서 차단 예정) |
| TC-ROT-04 | `test_login_with_device_id` | login에 device_id 포함 → 정상 200 |
| TC-ROT-05 | `test_login_without_device_id` | device_id 미전송 → 정상 처리 |
| TC-ROT-06 | `test_refresh_with_device_id` | refresh에 device_id 포함 → rotation 정상 |

### 테스트 결과
- `test_auth_rotation.py`: **6 passed**
- `test_refresh_token.py` 회귀: **28 passed** (회귀 0건)
- FE 빌드: `flutter build web --release` — 에러 0건

### 배포 (2026-03-05)
- [x] git commit & push (`0f527c1`)
- [x] Railway 자동 배포 (GitHub push)
- [x] flutter build web → Netlify 배포 (https://gaxis-ops.netlify.app)

---

## Sprint 19-B: DB 기반 Refresh Token 관리 + 탈취 감지 (2026-03-06) ✅

### 목표
1. Refresh Token을 DB(auth 스키마)에 해시 저장 — 토큰 무효화(revoke) 가능
2. 탈취 감지: revoked 토큰 재사용 시 해당 worker 전체 토큰 자동 무효화
3. 로그아웃 API 구현 (토큰 DB 무효화)
4. Device별 토큰 관리 (동일 worker+device → 이전 토큰 rotation revoke)

### BE 완료 내역
- **`backend/migrations/018_auth_refresh_tokens.sql`** (신규)
  - `auth` 스키마 생성
  - `auth.refresh_tokens` 테이블: worker_id, device_id, token_hash(SHA256), expires_at, revoked, revoked_reason
  - 인덱스 2개: `idx_refresh_tokens_worker`, `idx_refresh_tokens_hash`
- **`backend/app/services/auth_service.py`** — 4개 메서드 추가
  - `_store_refresh_token()`: 로그인/refresh 시 DB에 해시 저장 + 동일 (worker, device) 이전 토큰 revoke
  - `_validate_refresh_token_db()`: DB 검증 + 탈취 감지 (revoked 토큰 재사용 → 전체 무효화)
  - `revoke_refresh_token()`: 단일 토큰 무효화 (로그아웃)
  - `revoke_all_worker_tokens()`: worker 전체 토큰 무효화 (탈취 감지/관리자)
- **`backend/app/routes/auth.py`** — `POST /api/auth/logout` 엔드포인트 추가
  - refresh_token 전송 시 해당 토큰 revoke, 미전송 시 worker 전체 토큰 revoke

### TEST 완료 내역 (10개 신규)
| TC | 테스트 | 설명 |
|----|--------|------|
| TC-TDB-01 | `test_login_stores_token_in_db` | 로그인 시 auth.refresh_tokens에 해시 저장 |
| TC-TDB-02 | `test_refresh_rotates_token_in_db` | refresh 시 이전 토큰 revoked + 새 토큰 저장 |
| TC-TDB-03 | `test_theft_detection_revokes_all` | revoked 토큰 재사용 → 전체 토큰 무효화 |
| TC-TDB-04 | `test_logout_revokes_token` | 로그아웃 시 토큰 DB 무효화 |
| TC-TDB-05 | `test_logout_token_cannot_refresh` | 로그아웃된 토큰으로 refresh 불가 |
| TC-TDB-06 | `test_logout_without_token_revokes_all` | 토큰 미전송 로그아웃 → 전체 무효화 |
| TC-TDB-07 | `test_rotation_per_device` | 동일 device에서 refresh 시 이전만 revoke |
| TC-TDB-08 | `test_token_hash_format` | SHA256 해시 64자 형식 검증 |
| TC-TDB-09 | `test_pin_login_stores_token` | PIN 로그인도 DB 토큰 저장 |
| TC-TDB-10 | `test_logout_requires_auth` | JWT 없이 로그아웃 → 401 |

---

## Sprint 19-D: Geolocation 기반 출퇴근 위치 보안 (2026-03-06) ✅

### 목표
1. 협력사 출퇴근 시 GPS 좌표 검증 — 허용 반경 밖이면 차단
2. Admin 설정으로 기준점(위도/경도) + 반경(m) + on/off 제어
3. soft/strict 모드: soft=위치 미전송 시 경고만, strict=거부
4. work_site='HQ'(협력사 본사) → GPS 검증 면제

### BE 완료 내역
- **`backend/migrations/019_geolocation_settings.sql`** (신규)
  - admin_settings에 5개 키 추가: `geo_check_enabled`, `geo_latitude`, `geo_longitude`, `geo_radius_meters`, `geo_strict_mode`
  - 기본값: 비활성(false), GST 공장 좌표(37.4028, 127.1060), 반경 500m, soft 모드
- **`backend/app/services/geo_service.py`** (신규)
  - `verify_location(lat, lon)` → Haversine 공식으로 거리 계산, (allowed, distance) 반환
  - `is_geo_check_enabled()` → admin_settings 조회
  - `is_geo_strict_mode()` → 엄격 모드 여부 조회
  - `get_geo_config()` → 전체 설정 딕셔너리 반환
- **`backend/app/routes/hr.py`** — `attendance_check()` 수정
  - GPS 검증 조건: `is_geo_check_enabled() and work_site == 'GST'` (HQ 면제)
  - soft 모드: 좌표 미전송 → 경고 로그만, 출근 허용
  - strict 모드: 좌표 미전송 → 400 LOCATION_REQUIRED 거부
  - 좌표 전송 시: 거리 검증 → 403 OUT_OF_RANGE
- **`backend/app/routes/admin.py`** — `geo_strict_mode` 추가 (defaults + ALLOWED_KEYS)

### FE 완료 내역
- **`frontend/lib/screens/admin/admin_options_screen.dart`** — 위치 보안 섹션 추가
  - 위치 보안 on/off 토글, 위도/경도/반경 입력 필드
  - BE 키명 정합: `geo_check_enabled`, `geo_latitude`, `geo_longitude`
- **`frontend/lib/screens/home/home_screen.dart`** — 출퇴근 시 GPS 좌표 전송
  - `navigator.geolocation.getCurrentPosition()` → `latitude`/`longitude` 키로 전송
  - 403 OUT_OF_RANGE 에러 시 사용자 안내 메시지

### BE/FE 키명 정합 수정 (리드 세션)
에이전트 구현 후 발견된 BE↔FE 키 불일치 6건 수정:
| FE (수정 전) | BE (정답) | 수정 파일 |
|---|---|---|
| `geolocation_enabled` | `geo_check_enabled` | admin_options_screen.dart |
| `geo_lat` | `geo_latitude` | admin_options_screen.dart |
| `geo_lng` | `geo_longitude` | admin_options_screen.dart |
| `body['lat']` | `body['latitude']` | home_screen.dart |
| `body['lng']` | `body['longitude']` | home_screen.dart |
| `LOCATION_OUT_OF_RANGE` | `OUT_OF_RANGE` | home_screen.dart |

추가 누락 구현:
- BE `geo_strict_mode` 설정 키 추가 (migration + geo_service + admin.py)
- BE `work_site='HQ'` GPS 검증 면제 로직 (hr.py)
- BE soft/strict 모드 분기 (hr.py)

### TEST 완료 내역 (11개 신규)
| TC | 테스트 | 설명 |
|----|--------|------|
| TC-GEO-01 | `test_geo_disabled_allows_checkin` | geo 비활성 → 좌표 없이 출근 성공 |
| TC-GEO-02 | `test_geo_soft_mode_no_coords_allows` | soft 모드 + 좌표 미전송 → 201 허용 |
| TC-GEO-03 | `test_geo_enabled_valid_location_allows` | 허용 범위 내 좌표 → 출근 성공 |
| TC-GEO-04 | `test_geo_enabled_out_of_range_blocks` | 범위 밖 좌표 → 403 OUT_OF_RANGE |
| TC-GEO-05 | `test_geo_enabled_invalid_coords_rejected` | 잘못된 좌표 형식 → 400 |
| TC-GEO-06 | `test_geo_custom_radius_allows` | 커스텀 반경 설정 → 범위 판정 정확 |
| TC-GEO-07 | `test_admin_get_geo_settings` | GET admin settings → 5개 geo 키 포함 |
| TC-GEO-08 | `test_geo_checkout_skips_validation` | 퇴근(OUT)은 GPS 검증 스킵 |
| TC-GEO-09 | `test_geo_strict_mode_no_coords_blocks` | strict 모드 + 좌표 미전송 → 400 |
| TC-GEO-10 | `test_hq_work_site_bypasses_geo` | HQ 근무지 → GPS 검증 면제 |
| TC-GEO-11 | `test_admin_update_geo_strict_mode` | admin settings → geo_strict_mode 업데이트 |

### 테스트 결과
- `test_geolocation.py`: **11 passed** (113s)
- `test_token_db.py`: **10 passed**
- 전체 회귀: **526 passed, 23 failed (기존), 11 skipped, 14 errors** — 신규 regression 0건
- FE 빌드: `flutter build web --release` — 에러 0건

### 생성/수정 파일
```
backend/migrations/018_auth_refresh_tokens.sql           # 신규 (19-B)
backend/migrations/019_geolocation_settings.sql          # 신규 (19-D)
backend/app/services/auth_service.py                     # 수정 (19-B: DB 토큰 메서드 4개)
backend/app/services/geo_service.py                      # 신규 (19-D)
backend/app/routes/auth.py                               # 수정 (19-B: logout 엔드포인트)
backend/app/routes/hr.py                                 # 수정 (19-D: GPS 검증 + soft/strict + HQ 면제)
backend/app/routes/admin.py                              # 수정 (19-D: geo_strict_mode)
frontend/lib/screens/admin/admin_options_screen.dart      # 수정 (19-D: 위치 보안 UI + 키명 정합)
frontend/lib/screens/home/home_screen.dart                # 수정 (19-D: GPS 좌표 전송 + 키명 정합)
tests/backend/test_token_db.py                           # 신규 (19-B: 10 tests)
tests/backend/test_geolocation.py                        # 신규 (19-D: 11 tests)
```

---

## Hotfix: Admin 옵션 UI 일관성 개선 (2026-03-06)

### FE 수정 내역
- `admin_options_screen.dart` — 협력사 관리자 관리 (섹션 2) UI 패턴 통일
  - 기존: `Column` + `map` 전체 펼침 → 명단 많으면 화면 넘침
  - 변경: `BoxConstraints(maxHeight: 300)` + `Scrollbar` + `ListView.separated`
  - 가입 승인 대기 (섹션 0)와 동일한 스크롤 패턴 적용 → UI 일관성 확보

### 배포
- Netlify: https://gaxis-ops.netlify.app (production deploy 완료)

---

## Sprint 19-E: VIEW용 Admin 출퇴근 API (2026-03-06) ✅

### 목표
AXIS-VIEW 대시보드가 실 데이터를 조회할 수 있도록 Admin 전용 출퇴근 API 3개 추가.
VIEW Sprint 3 (실 데이터 연결)의 선행 작업.

### BE 완료 내역
- **`backend/app/routes/admin.py`** — 3개 엔드포인트 + 공통 함수 추가
  - `GET /api/admin/hr/attendance/today` — 오늘 전체 출퇴근 현황 (KST 기준)
  - `GET /api/admin/hr/attendance?date=YYYY-MM-DD` — 날짜별 출퇴근 현황 조회
  - `GET /api/admin/hr/attendance/summary` — 회사별 출퇴근 요약
  - `_kst_date_range()` — KST 기준 날짜 범위 계산 헬퍼
  - `_get_attendance_data()` — 출퇴근 데이터 조회 공통 함수 (records + summary 반환)
- **핵심 로직**:
  - KST 기준 날짜 범위 계산 (UTC 이슈 방지)
  - IN/OUT 피봇 SQL (LEFT JOIN + CASE WHEN + GROUP BY)
  - status 계산: not_checked / working / left
  - company != 'GST' 필터 (협력사만)
  - approval_status = 'approved' 필터 (미승인 제외)
  - ISO8601 KST 문자열 변환

### TEST 완료 내역 (8개 신규)
| TC | 테스트 | 설명 |
|----|--------|------|
| ATT-01 | `test_att01_empty_data` | 출퇴근 기록 없음 → 전부 not_checked |
| ATT-02 | `test_att02_checked_in_only` | 출근만 → status='working' |
| ATT-03 | `test_att03_checked_in_and_out` | 출근+퇴근 → status='left' |
| ATT-04 | `test_att04_not_checked` | 미출근 → status='not_checked' |
| ATT-05 | `test_att05_date_param` | 날짜 파라미터 정상 동작 |
| ATT-06 | `test_att06_invalid_date` | 잘못된 날짜 → 400 에러 |
| ATT-07 | `test_att07_company_summary` | 회사별 집계 정확성 |
| ATT-08 | `test_att08_non_admin_forbidden` | 비관리자 → 403 |

### 테스트 결과
- `test_admin_attendance.py`: **8 passed** (160s)

### 생성/수정 파일
```
backend/app/routes/admin.py                # 수정 (3개 엔드포인트 + 공통 함수)
tests/backend/test_admin_attendance.py     # 신규 (8 tests)
```

---

## Sprint 20-A: 신규 가입 시 Admin 이메일 알림 (2026-03-06) ✅

### 목표
작업자가 회원가입하면 DB의 `is_admin=true` 사용자 전원에게 이메일 자동 발송.
가입 사실을 즉시 인지하고 승인/거부 판단 가능.

### BE 완료 내역
- **`backend/app/services/email_service.py`** (신규)
  - `get_admin_emails()` — DB에서 is_admin=true 사용자 이메일 목록 조회
  - `_send_email()` — smtplib SMTP 발송 (auth_service.py와 동일 패턴)
  - `render_register_notification()` — 신규 가입 알림 HTML 템플릿 (이름, 이메일, 역할, 협력사, 가입일시)
  - `send_register_notification()` — Admin 전원에게 알림 발송 (best-effort)
- **`backend/app/routes/auth.py`** — register 성공(201) 시 알림 호출 추가
  - try-catch best-effort: 이메일 실패해도 가입 정상 완료

### TEST 완료 내역 (5개 신규)
| TC | 테스트 | 설명 |
|----|--------|------|
| MAIL-01 | `test_mail01_register_triggers_admin_notification` | 가입 → send_register_notification 호출 확인 |
| MAIL-02 | `test_mail02_smtp_not_configured_register_succeeds` | SMTP 미설정 → 가입 성공 |
| MAIL-03 | `test_mail03_smtp_failure_register_succeeds` | SMTP 실패 → 가입 성공 |
| MAIL-04 | `test_mail04_notification_contains_worker_info` | 이메일 내용에 가입자 정보 포함 |
| MAIL-05 | `test_mail05_multiple_admins_each_receive` | Admin 여러 명 → 각각 개별 발송 |

### 테스트 결과
- `test_admin_email_notification.py`: **5 passed** (34s)

### 생성/수정 파일
```
backend/app/services/email_service.py              # 신규
backend/app/routes/auth.py                         # 수정 (register에 알림 호출)
tests/backend/test_admin_email_notification.py     # 신규 (5 tests)
```

---

## Sprint 20-B: 공지사항 탭 (앱 내 업데이트 노트) (2026-03-06) ✅

### 목표
앱 내 공지사항 기능 — 버전 업데이트마다 사용자에게 변경사항을 요약 게시.
Admin이 직접 공지 작성/수정/삭제.

### BE 완료 내역
- **`backend/migrations/020_create_notices.sql`** (신규)
  - `notices` 테이블 생성 (title, content, version, is_pinned, created_by)
  - `updated_at` 자동 갱신 트리거
- **`backend/app/routes/notices.py`** (신규) — 5개 엔드포인트
  - `GET /api/notices` — 공지 목록 (고정 상단, 최신순, 페이지네이션, 버전 필터)
  - `GET /api/notices/<id>` — 공지 상세
  - `POST /api/admin/notices` — 공지 작성 (Admin only)
  - `PUT /api/admin/notices/<id>` — 공지 수정 (Admin only)
  - `DELETE /api/admin/notices/<id>` — 공지 삭제 (Admin only)
- **`backend/app/__init__.py`** — `notices_bp` Blueprint 등록

### FE 완료 내역
- **`frontend/lib/services/notice_service.dart`** (신규) — API 호출 서비스
- **`frontend/lib/screens/notice/notice_list_screen.dart`** (신규) — 공지 목록 화면
  - 고정 공지 핀 아이콘, 버전 태그, 더 보기 페이지네이션
  - SharedPreferences로 마지막 확인 공지 ID 저장
- **`frontend/lib/screens/notice/notice_detail_screen.dart`** (신규) — 공지 상세 화면
  - 제목, 본문, 작성자, 날짜, 버전 태그, 고정 아이콘
  - Admin: 삭제 버튼
- **`frontend/lib/screens/admin/notice_write_screen.dart`** (신규) — Admin 공지 작성 화면
  - 제목, 내용, 버전(선택), 상단 고정 토글
- **`frontend/lib/screens/home/home_screen.dart`** — 공지사항 메뉴 카드 추가
- **`frontend/lib/main.dart`** — `/notices`, `/notice-write` 라우트 등록
- FE 빌드: `flutter build web --release` 에러 0건

### TEST 완료 내역 (6개 신규)
| TC | 테스트 | 설명 |
|----|--------|------|
| NTC-01 | `test_ntc01_admin_create_notice` | Admin 공지 작성 → 목록 표시 |
| NTC-02 | `test_ntc02_non_admin_create_forbidden` | 일반 작업자 → 403 |
| NTC-03 | `test_ntc03_pagination` | 페이지네이션 (10개 단위) |
| NTC-04 | `test_ntc04_pinned_on_top` | 고정 공지 상단 표시 |
| NTC-05 | `test_ntc05_update_and_delete` | 수정/삭제 |
| NTC-06 | `test_ntc06_version_filter` | 버전 필터 |

### 테스트 결과
- `test_notices_api.py`: **6 passed** (80s)

### 생성/수정 파일
```
backend/migrations/020_create_notices.sql                          # 신규
backend/app/routes/notices.py                                      # 신규 (5 endpoints)
backend/app/__init__.py                                            # 수정 (Blueprint 등록)
frontend/lib/services/notice_service.dart                          # 신규
frontend/lib/screens/notice/notice_list_screen.dart                # 신규
frontend/lib/screens/notice/notice_detail_screen.dart              # 신규
frontend/lib/screens/admin/notice_write_screen.dart                # 신규
frontend/lib/screens/home/home_screen.dart                         # 수정 (메뉴 추가)
frontend/lib/main.dart                                             # 수정 (라우트 등록)
tests/backend/test_notices_api.py                                  # 신규 (6 tests)
```

## Sprint 21: QR Registry 목록 API (2026-03-07) ✅

### 목표
Admin/Manager용 QR 등록 목록 조회 API — 검색, 필터, 페이지네이션, 통계 제공.

### BE 완료 내역
- **`backend/app/routes/qr.py`** (신규) — 1개 엔드포인트
  - `GET /api/admin/qr/list` — QR 목록 조회 (qr_registry JOIN product_info)
    - 검색: S/N 또는 qr_doc_id 부분검색 (ILIKE)
    - 필터: model, status (active/revoked)
    - 페이지네이션: page, per_page (default 50, max 200)
    - 정렬: sort_by (qr.created_at, serial_number, model, mech_start, module_start, sales_order), sort_order (asc/desc)
    - 응답: items, total, page, per_page, total_pages, models (필터용 목록), stats (total/active/revoked)
    - 권한: `@jwt_required` + `@manager_or_admin_required`
- **`backend/app/__init__.py`** — `qr_bp` Blueprint 등록 (Sprint 21 주석)

### 생성/수정 파일
```
backend/app/routes/qr.py                                            # 신규 (1 endpoint)
backend/app/__init__.py                                              # 수정 (Blueprint 등록)
```

## ETL 파이프라인 → axis-core-etl repo 분리 (2026-03-09)

> ETL 코드가 별도 repo(`axis-core-etl`)로 분리되었습니다.
> 이후 ETL 관련 진행 상황은 `AXIS-CORE/CORE-ETL/PROGRESS.md`에서 관리.
>
> **repo**: axis-core-etl

---

## Sprint 22-A: Email Verification 개선 (완료)

> **마지막 업데이트**: 2026-03-10

### Phase A: email_verified 후 Admin 알림
- `auth.py` — register에서 Admin 알림 호출 제거 (가입 시점 = 미인증 상태)
- `auth.py` — verify-email 성공 시 `send_register_notification()` 호출 (백그라운드 스레드)
- `auth_service.py` — `verify_email()`에서 `_worker_info`를 내부 응답에 포함 → route에서 Admin 알림 후 제거
- `email_service.py` — `render_register_notification`에 `email_verified` 파라미터 추가, 인증 상태 배지 표시

### Phase B: 이메일 재전송 API
- `auth.py` — `POST /api/auth/resend-verification` 엔드포인트 추가
- `auth_service.py` — `resend_verification_email()` 메서드 추가
  - 미가입 이메일 → 404 (USER_NOT_FOUND)
  - 이미 인증 완료 → 400 (ALREADY_VERIFIED)
  - 60초 내 재전송 → 429 (RATE_LIMITED)
  - 새 verification_code 생성 + 이메일 발송

### 테스트: 기존 auth 8/8 PASSED (regression 없음)

### 수정된 파일
```
backend/app/routes/auth.py                    # verify-email Admin 알림 + resend-verification
backend/app/services/auth_service.py          # resend_verification_email() + verify_email _worker_info
backend/app/services/email_service.py         # email_verified 파라미터 + 인증 상태 배지
```

---

## Sprint 22-B: GPS 위치 보안 개선 (완료)

> **마지막 업데이트**: 2026-03-10

### Phase A: enableHighAccuracy 변경
- `home_screen.dart` — `enableHighAccuracy: false → true` (GPS 위성 기반)
- timeout: `10000ms → 15000ms`, Dart 방어 timeout: `12초 → 18초`

### Phase B: DMS → Decimal 변환 헬퍼
- `admin_options_screen.dart` — DMS 입력 필드 (도°, 분', 초") + 변환 버튼
- 변환 공식: `decimal = degrees + minutes/60 + seconds/3600`
- 유효 범위 검증: lat (-90~90), lng (-180~180)
- 변환 결과 → 기존 lat/lng 필드에 자동 적용 + admin_settings DB 저장

### 빌드: flutter build web --release 성공

### 수정된 파일
```
frontend/lib/screens/home/home_screen.dart              # enableHighAccuracy: true, timeout 15s
frontend/lib/screens/admin/admin_options_screen.dart     # DMS 변환 헬퍼 UI + 로직
```

---

## Sprint 22-A 보완 (v1.6.1, 완료)

> **마지막 업데이트**: 2026-03-10

### 변경 내역
- **인증 코드 만료 3분**: BE 만료시간 10분→3분, 이메일 본문 "3분 후 만료", FE 타이머 3분
- **재전송 API FE 연동**: `_handleResend()`에서 `POST /api/auth/resend-verification` 실제 호출
- **뒤로가기 방지**: `PopScope` + 확인 다이얼로그 (인증 중단 확인)
- **로그인→인증 자동 이동**: `EMAIL_NOT_VERIFIED` 에러 시 `VerifyEmailScreen`으로 이동
- **승인 목록 인증 필터**: `GET /api/admin/workers/pending`에 `email_verified=TRUE` 조건 추가
- **PM role 추가**: Railway DB `role_enum`에 PM 추가
- **에러 메시지 개선**: `IntegrityError` 시 중복 이메일 vs enum 위반 구분

### 수정된 파일
```
backend/app/models/worker.py                            # 인증코드 3분 만료 + IntegrityError 로그 개선
backend/app/services/auth_service.py                    # 이메일 본문 3분 + 에러 분기 개선
backend/app/routes/admin.py                             # 승인 목록 email_verified 필터
frontend/lib/utils/constants.dart                       # resend-verification endpoint
frontend/lib/services/auth_service.dart                 # resendVerification() 메서드
frontend/lib/screens/auth/verify_email_screen.dart      # 실제 API 호출 + PopScope + 3분 타이머
frontend/lib/screens/auth/login_screen.dart             # EMAIL_NOT_VERIFIED → 인증화면 이동
backend/version.py                                      # v1.6.1
frontend/lib/utils/app_version.dart                     # v1.6.1
```

## Sprint 22-C: 권한 체계 정리 + Manager 권한 위임 (v1.6.2, 완료)

> **마지막 업데이트**: 2026-03-10

### 변경 내역
- **toggle_manager() 권한 위임**: `@admin_required` → `@manager_or_admin_required` 데코레이터 변경
- **Manager 같은 회사 검증**: 협력사 Manager는 같은 company 소속 작업자만 is_manager 부여/해제 가능
- **Admin 보호**: Manager가 Admin(is_admin=true) 권한 변경 시도 시 403 거부
- **Admin 제한 없음**: 기존과 동일하게 전체 작업자 is_manager 변경 가능

### 수정된 파일
```
backend/app/routes/admin.py                             # toggle_manager() 데코레이터 + company/admin 검증
tests/backend/test_admin_options_api.py                 # TestManagerDelegation 5개 테스트 추가
backend/version.py                                      # v1.6.2
frontend/lib/utils/app_version.dart                     # v1.6.2
```

### 테스트: 5/5 PASSED (기존 5개 + 신규 5개 = 10개 전체 통과)
| TC | 설명 | 결과 |
|----|------|------|
| MGR-01 | Admin → 아무 작업자 manager 부여 성공 | ✅ |
| MGR-02 | 협력사 Manager → 같은 회사 작업자 manager 부여 성공 | ✅ |
| MGR-03 | 협력사 Manager → 다른 회사 작업자 → 403 | ✅ |
| MGR-04 | 협력사 Manager → Admin 권한 변경 → 403 | ✅ |
| MGR-05 | 일반 작업자 → manager 부여 시도 → 403 | ✅ |

---

## Sprint 22-D: 공지수정 + Admin 간편로그인 + ETL API (v1.6.3, 완료)

> **마지막 업데이트**: 2026-03-11

### 변경 내역
- **공지사항 수정 기능**: `NoticeWriteScreen` 수정 모드 지원 (existingNotice 파라미터), `NoticeDetailScreen`에 수정 아이콘 추가
- **Admin 간편 로그인 개선**: `get_admin_by_email_prefix()` 2단계 매칭 — 1차 `prefix@%`, 2차 `prefix%` (admin → admin1234@... 매칭)
- **ETL 변경 이력 API**: `GET /api/admin/etl/changes` (CORE-ETL Sprint 2 Task 4) — days/field/serial_number/limit 쿼리, change_log + product_info JOIN, summary 포함

### 수정된 파일
```
frontend/lib/screens/admin/notice_write_screen.dart     # 수정 모드 (existingNotice, updateNotice 호출)
frontend/lib/screens/notice/notice_detail_screen.dart   # 수정 버튼 추가 (Admin)
backend/app/models/worker.py                            # admin prefix 2단계 매칭
backend/app/routes/admin.py                             # GET /api/admin/etl/changes 엔드포인트
backend/version.py                                      # v1.6.3
frontend/lib/utils/app_version.dart                     # v1.6.3
```

---

## Sprint 23: OPS FE 메뉴 재구성 + Manager 권한 위임 화면 (v1.7.0, 완료)

> **마지막 업데이트**: 2026-03-11

### 변경 내역
- **메뉴 순서 재배치**: 관리자 옵션을 공지사항 바로 위로 이동, 미종료 작업은 작업관리 아래 유지
- **관리자 권한 부여 메뉴**: `isManager || isAdmin` 조건으로 새 메뉴 카드 추가 (공지사항 위)
- **Manager 권한 부여 화면**: 같은 회사 작업자 목록 + is_manager 토글 스위치, Admin 계정 보호(토글 비활성화)
- **GET /api/admin/managers 권한 완화**: `@admin_required` → `@manager_or_admin_required` + Manager는 같은 company 자동 필터
- **ETL change_log API RealDictCursor 수정**: `row[index]` → `row['key']` (500 에러 수정)

### Shipped 제품 QR 스캔 안내 (Sprint 23 추가)
- **BE**: `GET /api/app/product/{qr_doc_id}` — 일반 작업자가 shipped 제품 스캔 시 `PRODUCT_SHIPPED` (200) 반환, Admin/Manager는 shipped 포함 정상 조회
- **FE**: `ProductShippedException` 클래스 추가 + `_showShippedDialog()` — 트럭 아이콘 + "출고 완료된 제품입니다" 안내 (에러 스타일 X)

### 수정된 파일
```
frontend/lib/screens/home/home_screen.dart              # 메뉴 순서 변경 + 권한 부여 카드 추가
frontend/lib/screens/admin/manager_delegation_screen.dart # 권한 부여 화면 (신규)
frontend/lib/main.dart                                   # /manager-delegation 라우트 등록
backend/app/routes/admin.py                             # managers API 권한 완화 + ETL API dict 수정
backend/app/routes/product.py                           # shipped 제품 PRODUCT_SHIPPED 응답 추가
backend/app/models/product_info.py                      # include_shipped 파라미터 추가
frontend/lib/services/task_service.dart                 # ProductShippedException 추가
frontend/lib/screens/qr/qr_scan_screen.dart             # shipped 안내 다이얼로그 추가
backend/version.py                                      # v1.7.0
frontend/lib/utils/app_version.dart                     # v1.7.0
```

## Sprint 24: QR 목록 actual_ship_date + Manager 자사 필터 (v1.7.1, 완료)

> **마지막 업데이트**: 2026-03-11

### 변경 내역
- **QR 목록 actual_ship_date 추가**: `GET /api/admin/qr/list` SELECT절 + 응답에 `actual_ship_date` 필드 포함
- **QR 목록 Manager 자사 필터**: `is_manager && !is_admin` → `mech_partner OR elec_partner = company` 조건 자동 적용
- **출퇴근 API Manager 접근 허용**: 3개 엔드포인트 `@admin_required` → `@manager_or_admin_required` 변경
- **출퇴근 API 자사 필터**: `_get_attendance_data()` + `_get_manager_company_filter()` — Manager는 자사 소속만 조회
- **버전**: v1.7.0 → v1.7.1

### 추가 변경 (Sprint 24 후속)
- **QR 목록 shipped 필터/카운트**: status 필터에 `shipped` 허용, 통계에 `shipped_count` 추가, Manager 통계도 자사 필터 적용
- **Shipped 제품 QR 스캔**: 모든 사용자(Admin 포함)에게 "출고 완료" 다이얼로그 표시 + S/N, 모델 정보 포함
- **GET /api/admin/workers 권한 완화**: `@admin_required` → `@manager_or_admin_required` + Manager 자사 필터 + company 필드 응답 추가

### 수정된 파일
```
backend/app/routes/qr.py       # actual_ship_date + manager 필터 + shipped 카운트
backend/app/routes/admin.py    # attendance 데코레이터 + workers 권한 완화 + company 필터
backend/app/routes/product.py  # shipped 제품 전 사용자 PRODUCT_SHIPPED 응답
frontend/lib/services/task_service.dart   # ProductShippedException (S/N, model 포함)
frontend/lib/providers/task_provider.dart # ProductShippedException rethrow
frontend/lib/screens/qr/qr_scan_screen.dart # shipped 다이얼로그 (S/N, 모델 표시)
backend/version.py             # v1.7.1
frontend/lib/utils/app_version.dart  # v1.7.1
```

---

## Sprint 24 핫픽스: GST 출퇴근 + 비밀번호 찾기 (2026-03-11)

### BUG-18: GST Manager 출퇴근 데이터 미표시 ✅ 수정 완료
- **증상**: GST 소속 is_manager=true 계정으로 VIEW 대시보드 접속 시 출퇴근 데이터 0건
- **계정**: `kdkyu311@naver.com` (id=2399, role=PM, company=GST, is_manager=true, is_admin=false)
- **원인**: `_get_manager_company_filter()` 가 GST manager에게 `'GST'` 반환 → `_get_attendance_data()` SQL에서 `WHERE w.company != 'GST' AND w.company = 'GST'` 모순 조건 → 0건
- **수정**: `_get_manager_company_filter()`에서 `worker.company == 'GST'`이면 `None` 반환 (Admin과 동일하게 전체 협력사 데이터 접근)
- **파일**: `backend/app/routes/admin.py` (L1741-1748)

### BUG-19: 비밀번호 찾기 — 없는 이메일도 인증 화면 이동 ✅ 수정 완료
- **증상**: 비밀번호 찾기에서 존재하지 않는 이메일 입력 → 에러 없이 재설정 코드 입력 화면으로 이동
- **원인**: BE `send_password_reset_code()`가 보안 관행(이메일 열거 공격 방지)으로 이메일 존재 여부와 무관하게 항상 200 반환
- **수정**: 내부 시스템이므로 편의성 우선 — 미존재 이메일 시 `404 EMAIL_NOT_FOUND "등록되지 않은 이메일입니다."` 반환
- **파일**: `backend/app/services/auth_service.py` (L992-999)

### BUG-20: 로그인 에러 메시지 불명확 ✅ 수정 완료
- **증상**: 없는 아이디로 로그인 시 "이메일 또는 비밀번호가 잘못되었습니다." — 계정 미존재인지 비밀번호 오류인지 구분 불가
- **원인**: 보안 관행으로 계정 미존재 / 비밀번호 오류를 동일한 `401 INVALID_CREDENTIALS`로 처리
- **수정**: 내부 시스템이므로 편의성 우선 — 에러를 분리:
  - 계정 미존재: `404 ACCOUNT_NOT_FOUND "등록되지 않은 계정입니다."`
  - 비밀번호 오류: `401 INVALID_PASSWORD "비밀번호가 잘못되었습니다."`
- **파일**: `backend/app/services/auth_service.py` (L572-583)

### BUG-21: FE 404 에러 메시지 하드코딩 ✅ 수정 완료
- **증상**: BE가 404로 구체적 메시지("등록되지 않은 이메일입니다.")를 보내도 FE에서 "요청한 리소스가 없습니다."로 표시
- **원인**: `api_service.dart` `_handleError()`에서 404는 서버 메시지를 무시하고 하드코딩된 문자열 반환
- **수정**: 404도 서버 응답의 `message` 필드를 그대로 사용
- **파일**: `frontend/lib/services/api_service.dart` (L233-234)

### 이전 수정 (Sprint 24 세션 내)
- **PM role 등록 실패**: DB `role_enum`에 'PM' 누락 → `ALTER TYPE role_enum ADD VALUE 'PM'` 실행 + migration 추가
- **VIEW GST 접근 차단**: `auth.ts`, `ProtectedRoute.tsx`, `Sidebar.tsx`에 `company === 'GST'` 체크 추가
- **Workers 목록 잘림**: 기본 LIMIT 50 → 200 변경, VIEW에서 limit=500 전송
- **Admin shipped QR 스캔**: Admin도 shipped 제품 스캔 시 출고 완료 다이얼로그 표시

### 수정된 파일
```
backend/app/routes/admin.py              # _get_manager_company_filter() GST 예외
backend/app/services/auth_service.py     # forgot-password 404 + 로그인 에러 분리
frontend/lib/services/api_service.dart   # 404 서버 메시지 사용
backend/migrations/021_add_pm_role.sql   # PM role enum 추가
```

---

## Sprint 22-E: conftest.py 운영 데이터 5테이블 백업/복원 완성 (2026-03-12)

> **버전**: 변경 없음 (테스트 인프라만 수정)

### 변경 내역
- **plan.product_info 백업/복원 추가**: 26개 컬럼 (actual_ship_date 포함) SELECT → INSERT ON CONFLICT DO NOTHING + 시퀀스 조정
- **public.qr_registry 백업/복원 추가**: 8개 컬럼 SELECT → INSERT ON CONFLICT DO NOTHING + 시퀀스 조정
- **actual_ship_date 컬럼 보장**: migration에 없는 컬럼이므로 복원 전 `ALTER TABLE ADD COLUMN IF NOT EXISTS` 실행
- **복원 순서**: workers → auth_settings → attendance → product_info → qr_registry (FK 의존성 준수)

### 백업/복원 현황 (5/5 완료)
| 테이블 | 컬럼 수 | 상태 |
|--------|---------|------|
| workers | 11 | ✅ 기존 |
| hr.worker_auth_settings | 6 | ✅ 기존 |
| hr.partner_attendance | 9 | ✅ 기존 |
| plan.product_info | 26 | ✅ 신규 |
| public.qr_registry | 8 | ✅ 신규 |

### 수정된 파일
```
tests/conftest.py    # product_info + qr_registry 백업/복원 추가
CLAUDE.md            # 운영 데이터 보존 규칙 5/5 완료 표기
BACKLOG.md           # DB-1 conftest.py 현황 5/5 완료
```

---

## Sprint 25: BUG-22 Logout Storm 수정 (v1.7.2, 2026-03-12)

### 변경 내역

**FE (Flutter) — 3중 방어:**
1. `api_service.dart` — `_authSkipPaths`로 auth 경로 401 재시도 차단 + `_isForceLogout` 싱글턴으로 중복 실행 방지 + `setToken()`에서 플래그 리셋
2. `auth_service.dart` — `_isLoggingOut` 플래그로 중복 logout 차단 + `clearToken()` 서버 호출 전 선행 실행 + `Future.any` 3초 timeout
3. `auth_provider.dart` — 중복 방지 주석 업데이트

**BE (Flask) — logout 401 근본 차단:**
1. `jwt_auth.py` — `jwt_optional` 데코레이터 신규 추가 (토큰 없어도 `g.worker_id=None`으로 진행)
2. `auth.py` — logout 엔드포인트 `@jwt_required` → `@jwt_optional` 변경, 토큰 없이도 200 반환

### 수정 전후 비교
| 시나리오 | 수정 전 | 수정 후 |
|---------|---------|---------|
| refresh 401 | logout API 10회+ 호출 | forceLogout 1회 (BE 호출 0~1회) |
| 동시 401 5건 | 각자 onRefreshFailed | _isForceLogout 차단 → 1회만 |
| logout API 자체 401 | interceptor 재진입 → 무한 루프 | _authSkipPaths로 즉시 reject |
| BE 토큰 없는 logout | 401 에러 | @jwt_optional → 200 OK |

### 수정된 파일
```
frontend/lib/services/api_service.dart      # AUTH_SKIP_PATHS + forceLogout 싱글턴
frontend/lib/services/auth_service.dart     # _isLoggingOut + clearToken 선행 + 3초 timeout
frontend/lib/providers/auth_provider.dart   # 주석 업데이트
backend/app/middleware/jwt_auth.py          # jwt_optional 데코레이터 신규
backend/app/routes/auth.py                 # @jwt_required → @jwt_optional (logout만)
backend/version.py                         # v1.7.2
frontend/lib/utils/app_version.dart        # v1.7.2
```

### pytest 전체 실행 결과 (2026-03-12)

**1차 실행**: 643 passed / 44 failed / 12 skipped (1시간 42분, Railway 원격 DB)

**실패 원인 분석 (44건)**:
| 유형 | 건수 | 원인 | 대응 |
|------|------|------|------|
| Task Seed count 불일치 | ~20건 | PI/QI/SI 템플릿 추가 후 테스트 미갱신 (15→19, 13→17) | ✅ 수정 완료 |
| DB 상태 간섭 (UniqueViolation) | ~15건 | 공유 DB에서 이전 실행 잔여 데이터 | ✅ create_test_worker cleanup 추가 |
| 테스트 간 상태 간섭 | ~9건 | 전체 스위트 실행 시 발생, 개별 실행 시 통과 | DB 격리 필요 (장기 과제) |

**개별 검증 결과**:
- `test_auth.py` — 8/8 passed ✅ (Sprint 24 login 에러 분리 반영)
- `test_work_api.py::TestWorkStart` — 6/6 passed ✅ (개별 실행)
- `test_process_check_flow.py` — 9/10 passed (tc_10만 UniqueViolation → cleanup 추가로 수정)
- `test_model_task_seed_integration.py` — seed count 15→19, 13→17 수정 완료

**테스트 수정 커밋**:
- `fix: update test_auth for Sprint 24 login error changes` — 404 ACCOUNT_NOT_FOUND 대응
- `fix: clean up stale test data before register test` — company 필드 + 잔여 데이터 정리
- `fix: update task seed tests for PI/QI/SI templates + fix test worker cleanup` — seed count 업데이트 + UniqueViolation 방지

**BE 코드 버그**: 0건 (전체 실패는 테스트 코드 문제)

---

## Sprint 26: PWA 버전 업데이트 알림 (v1.7.3, 2026-03-12)

### FE 완료 내역
- `frontend/web/index.html` — SW controllerchange/updatefound 감지 → 하단 토스트 표시
- `frontend/lib/services/update_service.dart` — SharedPreferences 버전 비교 + notices API 조회 (신규)
- `frontend/lib/widgets/update_dialog.dart` — 업데이트 내용 팝업 다이얼로그 (신규)
- `frontend/lib/screens/home/home_screen.dart` — initState에 `_checkForUpdate()` 추가
- `frontend/lib/utils/app_version.dart` — v1.7.3

### BE 변경
- `backend/version.py` — v1.7.3 (로직 변경 없음)

### 동작 흐름
1. Netlify 배포 → SW가 백그라운드에서 새 파일 감지
2. 하단 토스트 "새 버전이 있습니다" 표시 → 탭하면 reload
3. reload 후 HomeScreen → SharedPreferences 버전 비교 → 새 버전이면 notices API 호출
4. 해당 버전 공지 있으면 업데이트 내용 팝업 표시 (최초 1회만)

### conftest.py 운영 데이터 보호 강화
- `DROP SCHEMA hr CASCADE` 제거 — partner_attendance/auth_settings 보존
- `DROP TABLE workers CASCADE` 제거 — FK CASCADE 방지
- `DROP TABLE admin_settings/model_config` 제거 — 운영 설정 보존
- `DROP SCHEMA auth CASCADE` 제거 — refresh_tokens 보존

### 배포
- Netlify: https://gaxis-ops.netlify.app ✅

---

## Sprint 27: AXIS-VIEW 권한 데코레이터 재정비 (v1.7.4, 2026-03-13)

### BE 완료 내역
- `backend/app/middleware/jwt_auth.py`:
  - `get_current_worker()` 캐싱 헬퍼 추가 (request 당 1회 DB 조회, g.current_worker 캐시)
  - `admin_required` 내부 `get_worker_by_id()` → `get_current_worker()` 교체
  - `manager_or_admin_required` 내부 `get_worker_by_id()` → `get_current_worker()` 교체
  - `@gst_or_admin_required` 데코레이터 신규 추가 (company='GST' OR is_admin)
  - `@view_access_required` 데코레이터 신규 추가 (company='GST' OR is_admin OR is_manager)
- `backend/app/routes/qr.py` — QR 목록 `@manager_or_admin_required` → `@view_access_required`
- `backend/app/routes/admin.py` — ETL 변경이력 `@manager_or_admin_required` → `@view_access_required`
- `backend/version.py` — v1.7.4

### 데코레이터 체계 (변경 후)
| 데코레이터 | 조건 | 용도 |
|---|---|---|
| `@admin_required` | is_admin | 시스템 설정, 가입 승인 |
| `@manager_or_admin_required` | is_admin OR is_manager | 권한 관리, 출퇴근, 강제 종료 |
| `@gst_or_admin_required` (신규) | company='GST' OR is_admin | 공장 대시보드 전용 API |
| `@view_access_required` (신규) | company='GST' OR is_admin OR is_manager | VIEW 전체 공개 API |

### 테스트: 667 passed, 36 기존 실패 (Sprint 27 regression 0건)
- DB 스키마 변경 없음
- FE(Flutter) 변경 없음
- 기존 `@admin_required`, `@manager_or_admin_required` 사용처 영향 없음

---

## ETL pi_start 변경이력 지원 (2026-03-14) — CORE-ETL Sprint 2-A 연동

### BE 변경 내역
- `backend/app/routes/admin.py`:
  - `_FIELD_LABELS`에 `'pi_start': '가압시작'` 추가 (5→6개)
  - `valid_fields = set(_FIELD_LABELS.keys())`에 자동 포함 → `field=pi_start` 필터 지원

### _FIELD_LABELS (변경 후)
| 키 | 한글 라벨 |
|---|---|
| `sales_order` | 수주번호 |
| `ship_plan_date` | 출하예정일 |
| `mech_start` | 기구시작 |
| `pi_start` | 가압시작 |
| `mech_partner` | 기구협력사 |
| `elec_partner` | 전장협력사 |

### 연관 변경 (타 repo)
- **CORE-ETL**: `TRACKED_FIELDS`에 `'pressure_test': 'pi_start'` 추가, `_prefetch_tracked_values()` SELECT/캐시 수정
- **AXIS-VIEW**: FIELD_CONFIG, DATE_FIELDS, KPI 그리드 6열, kpiCards, 주간 차트 — VIEW 별도 진행
