# AXIS-OPS Memory

> 세션 간 누적되는 의사결정, 아키텍처 판단, 감사 결과를 기록합니다.
> CLAUDE.md = 프로젝트 고정 정보 / memory.md = 누적 학습 / handoff.md = 세션 인계
> 마지막 업데이트: 2026-06-11 (ADR-035 추가 — 태깅 커버리지 분모 정의: 자동/admin완료=미추적 포함, CT와 다른 모집단(v2.36.0). 선행 ADR-034 미종료 기준 통일)

---

## 1. 아키텍처 의사결정 기록 (ADR)

### ADR-035: 태깅 커버리지 분모 정의 — 자동/admin완료=미추적 포함 (Sprint 90-BE, v2.36.0, 2026-06-11)
- **맥락**: `종료 누락 분석` TaggingCoverageCard(공정별 추적율/0초탭) 실데이터. 분모를 CT `_CLEAN_WHERE`(duration_source NORMAL only)로 할지, 자동마감·admin대행완료를 포함할지 갈림 — PI/QI/SI 숫자 정반대.
- **결정 (분모 = 포함)**: `_COVERAGE_WHERE` = 완료+active NOT NULL+applicable+`force_closed=FALSE`, TEST/TMS모듈 제외. **duration_source 필터 미적용** → 자동마감(close_reason AUTO)·admin대행(SHIP/ADMIN_COMPLETE)을 **미추적으로 분모 포함**. **이유**: 카드 목적 = "어느 공정이 태깅 안 되나"(데이터 품질 진단). PI/QI/SI는 작업자 실시간 태깅 거의 없이 admin 대행 → 대행을 빼면 "고 미추적" 신호 자체 소실. **CT task-stats `_CLEAN_WHERE`(시간정확도 모집단)와 의도적으로 다른 모집단**(태깅 유무 모집단). → 같은 "zero_tap"이라도 discipline(MECH/ELEC 평가, 자동/admin 제외)과 숫자 다름 = 정상.
- **결정 (3분류 close_reason override)**: `active_time_minutes`는 자동/admin완료도 세션 기반이라 active>1 가능 → active>1만으론 tracked 오분류. **tracked = NOT oneClick AND active>1 AND `close_reason IS NULL`**(정상완료=close_reason NULL, force_closed=FALSE 모집단에서 close_reason 존재 ⟺ 자동/admin/ship 대행, Codex R4 전수검증). zero_tap = NOT oneClick AND (active≤1 OR close_reason 존재). 우선순위 oneClick > zero_tap > tracked.
- **결정 (route 배치)**: `/api/ct/tagging-coverage`(CT primitive 응집 — is_instant_whitelisted/active_time/_resolve_window/Tukey). discipline(`/admin/discipline`)은 MECH/ELEC 평가전용 스코프 충돌로 제외. `gst_or_admin_required`(페이지 청중=admin+GST매니저, 협력사 차단과 일치). 신규 service 파일(statistics/dashboard 둘 다 800줄+ 새 로직 금지).
- **연계**: Sprint 90-BE-B = 마감 추이 zerotap 은 기존 `data-quality.auto_close_trend` 재사용(DRY, 신규 route X). [[sprint89-partner-discipline]] discipline zeroTap 과는 모집단·목적 다름.
- **영향**: VIEW FE = TaggingCoverageCard/CloseTrendChart/ZeroTapKpiCard 연동(별 repo). advisory A-1(auto>zerotap 역전 라벨)/A-2(private whitelist import) BACKLOG.

### ADR-034: 미종료 기준 단일화 + 규율 지표 정의 보정 (#87, v2.35.0, 2026-06-10 사용자 catch)
- **맥락**: v2.34.0 규율 대시보드 운영 catch — ① summary openTasks 가 month 무시한 실시간(월 summary인데 불일치) ② discipline 미종료 기준이 정식 "미종료 작업 현황"(`/tasks/pending/grouped`)보다 느슨(비해당·TEST 포함) ③ checkinNoTag 가 taggingRate 와 중복.
- **결정 (미종료 기준 단일화)**: discipline 의 미종료 정의 = **정식 미종료 작업 현황과 동일** — `started_at IS NOT NULL AND completed_at IS NULL AND is_applicable=TRUE AND COALESCE(force_closed,FALSE)=FALSE AND customer<>'TEST CUSTOMER'`. 한 시스템 안에서 "미종료" 정의가 갈리지 않게 canonical 기준 따름.
- **결정 (집계 anchor)**: summary 지표는 **월단위** — openTasks 는 `started_at`∈월(autoClose/zeroTap 의 completed_at, taggingRate 의 출근월과 anchor 일관). 단 `/open-tasks` 큐는 **realtime**(현재 backlog 드릴다운) → 카드(월)≠큐(현재)는 의도된 차이, meta `*_basis` 명시.
- **결정 (중복 지표 제거)**: `checkinNoTag`(출근−태깅 인원) = taggingRate(태깅÷출근)의 카운트 버전 = 중복 → 폐기. 그 슬롯 = `checkoutMiss`(퇴근미체크율, #86 근태 동일 기준 월 가중) **참고 지표(reference_only, 평가 제외)** — ADR-033 정합(근태 평가 X, 참고 표시 O).
- **결정 (비협력사 제외)**: `_EXCLUDED_PARTNERS`=('GST','SH') — 자체수행 GST + 비협력사 구데이터 SH. task/worker 파생 양쪽 NULL 처리. 향후 비협력사 발견 시 이 set 에 추가.
- **영향**: Codex 설계 R1 GO/실코드 R2 DEPLOY_SAFE M=0. pytest 32/32. [[project_sprint89_partner_discipline]]

### ADR-033: 근태(출근율·퇴근미체크) 협력사 평가 제외 정책 (2026-06-10, Twin파파 결정)
- **맥락**: #87 협력사 규율 대시보드 설계 중, 출근율·퇴근미체크를 평가 지표에 포함하면 근태 기반 "줄세우기"가 됨 → 협력사 반발·게이밍 우려.
- **결정**: **출근율·퇴근미체크(checkout-miss)·가동률(utilization)은 협력사 평가 지표에서 제외.** 출근 데이터는 Phase 2 `taggingRate`(GST 현장 출근자 분모)·`checkinNoTag`의 **분모로만** 사용. 퇴근미체크는 #86 checkout_status로 근태 페이지에만 표시(평가 X).
- **남는 평가 지표**: 미종료(openTasks)·자동마감(autoClose)·0초탭(zeroTap)·태깅율(taggingRate)·출근O·미태깅(checkinNoTag)·체크리스트(checklist) — 전부 "태깅 정착/작업 규율" 축이지 근태 축 아님.
- **영향**: VIEW PartnerDashboardPage 평가 카드에서 근태 컬럼 제외. #87 BACKLOG `checkout-miss-weekly` 별 항목 미진행. [[project_sprint89_partner_discipline]]

### ADR-032: #87 협력사 규율 대시보드 — namespace + 공정성 계약 (2026-06-10, Sprint 89-BE, v2.33.0)
- **맥락**: VIEW 협력사 공유 대시보드(PartnerDashboardPage) mockup → 실데이터. 협력사 데이터 환원으로 자가교정·태깅 정착 유도. 게이밍/줄세우기 방지가 핵심.
- **결정 (namespace)**: `/api/admin/discipline/*` (admin 통일 — VIEW 최초안 `/api/partner/discipline/*` 폐기). #86 A′ 정합, `resolve_company_scope` 재사용. 사내서버 이관 시 partner 동 분리.
- **결정 (공정성 계약)**: ① BE는 **raw + group_avg(peer-only)만** 산출, 등급·composite·줄세우기는 VIEW 책임. ② `group_avg` = 같은 group 내 **타사** 평균 + **peer_n≥3 충족 시만** 노출(소표본 역추론 차단) → 현 협력사 3사(MECH/ELEC 각 3)로는 협력사 매니저 peer=2<3 → **항상 suppress(정상·의도)**, admin/GST만 group_avg. ③ 협력사 매니저 = 자사 row만(타사 raw 미노출). ④ **MECH/ELEC only**(PI/QI/SI=GST 자체공정 제외). ⑤ 추적율<70% → `grade_eligible=false`(미태깅=데이터 누락 라벨). ⑥ 모든 지표 표준 envelope.
- **Phase 분할**: Phase 1(v2.33.0) = openTasks/autoClose 실측 + group_avg + open-tasks 큐 / Phase 2 = taggingRate/checkinNoTag/zeroTap/checklist/trend.
- **Codex**: 설계 R1 M=8→R2 조건부 GO(A-spec 5건) / 실코드 R3 M=1(`_PARTNER_SQL` 빈값 제외 누락)→fix(NULLIF+TRIM)→R4 DEPLOY_SAFE M=0. [[project_sprint89_partner_discipline]]

### ADR-031: #86 협력사 데이터 접근 RBAC — `resolve_company_scope()` SSoT (2026-06-10, Sprint 88-BE, v2.32.0)
- **맥락**: 근태·자동마감 라우트가 각자 company 필터(`_get_manager_company_filter`/`_build_partner_filter`)를 굴려 **company 없는 매니저가 전체 협력사 데이터에 접근**하는 누수 2곳 존재. #87 대시보드(협력사별 민감 데이터) 공유 전 차단 필수.
- **결정**: `middleware/jwt_auth.resolve_company_scope(worker)` 단일 진실원(SSoT) — admin/GST→전체(is_global), 협력사 매니저(company 有)→자사 exact(TMS(M)/(E) 보존), **company 없는 매니저·None·비매니저→`CompanyScopeError`→403**(전체 누수 차단). `@app.errorhandler` 등록.
- **핵심 규칙**: resolver는 **반드시 라우트 try/except 밖**에서 호출 — except Exception이 CompanyScopeError를 삼켜 500으로 바꾸면 errorhandler(403) 우회 = 게이트 무력화.
- **부수**: 근태 mutation 로직 `services/hr_attendance_service.py` 추출(admin.py 2,626→2,456줄, God-route 완화) + `checkout_status`(not_started/working/missed/done, cutoff=LEAST(익일 첫 in, D+1 02:00 KST)) + by_work_site 미체크율 additive.
- **Codex**: PR1 R3 DEPLOY_SAFE / 설계 R2 GO / step② GO 전부 M=0. **Fable 판정**으로 초기 B안(신규 endpoint) 차선 catch→A′(admin route 재사용+추출). [[project_sprint86_partner_attendance_rbac]]

### ADR-030: 리드·워커 하이브리드 모델 정책 — `claude-fable-5` 도입 + Opus 4.7 고착 정정 (2026-06-10, VIEW ADR-V026 동기화)
- **맥락**: 2026-06-09 Anthropic Claude Fable 5(Mythos-class, model id `claude-fable-5`) 공개 출시 — Opus 4.8 상위 추론 모델. Twin파파 catch → 웹 검색 검증 후 CLAUDE.md 모델 버전 관리 규칙대로 갱신. VIEW 세션에서 먼저 반영(ADR-V026), 본 ADR은 OPS 동기화.
- **결정 (양 티어 하이브리드)**: Fable 2배 단가 → 상시 사용 X, 복잡 판단에만 한시 투입.
  - **리드**: 기본 `claude-opus-4-8`(Opus 최상위) / Fable 5 승격 트리거 6종(① 아키텍처·3페이지+ cross-cutting ② God Component 분할 등 복잡 리팩토링 설계 ③ BE 계약·데이터 모델 모호 ④ 회귀 큰 root-cause(Opus로 막힐 때) ⑤ 다중 제약 trade-off ⑥ Codex 합의 실패 최종 판정).
  - **워커**: 기본 `claude-sonnet-4-6`(Sonnet 최상위) / 복잡 리팩토링·회귀 큰 Sprint만 `claude-opus-4-8`.
  - 근거: Fable = SWE-Bench Pro 80.3%(vs Opus 4.8 69.2%) 우수하나 단가 $10/$50 = Opus 2배 → 일반 Sprint엔 과투자. 어려운 설계 판단에만 ROI 확보.
- **부수 catch**: 갱신 과정에서 리드가 그동안 `claude-opus-4-7`에 고착 → Opus 4.8 출시 후에도 한 단계 낮은 모델로 운영된 사실 발견. "세션 시작 체크"가 실제로 안 돌고 있었음 = 교훈. 워커 Opus 승격 시에도 4.7 아닌 **4.8** 명시(고착 재발 방지).
- **주의**: Fable 5는 고위험 토픽(사이버보안·생물/화학·model distillation) 쿼리를 자동으로 Opus 4.8로 fallback(세션 ~5% 미만). GST 공장 대시보드 업무 특성상 영향 거의 없음.
- **영향**: AXIS-OPS/CLAUDE.md 리드/워커 모델 라인 + 모델 버전 관리 규칙 §"Claude 모델" 갱신 완료. VIEW ADR-V026 와 1:1 정합.
- **trail**: 출처 = anthropic.com/news/claude-fable-5-mythos-5, TechCrunch/IT Pro(2026-06-09). ⚠️ 본 모델명은 Claude Code 환경 기본 모델 목록(Claude 4.X)엔 미등재 — Twin파파 웹검증 기반 운영 정책 기록.

### ADR-029: Cowork ↔ Claude Code 작업 분리 정책 (2026-05-11)

**맥락**: 2026-05-07 memory.md ADR-023 2차 보강 영역에서 "ADR-024 분리 검토 영역 도달" 명시 (6건 누적 시점). 그 후 추가 3건 catch 누적 = 9건 도달, 분리 정식 채택 영역 임계 초과.

**Cowork 누적 실수 trail (9건, 2026-04~05)**:
```
1~6. ADR-023 2차 보강 시점 (5-07, 1차 누적):
  ① GxColors.background/surface/mistLight (commit 21c581e)
  ② check_result null 처리 (BE 400)
  ③ ELEC `_get_checklist_by_category` SQL 차용 phase 단일 join 한계
  ④ description 표시 영역 _buildInputField 만 적용
  ⑤ completion_status.ee_completed (실제 elec_completed)
  ⑥ @require_admin_or_gst (실제 @gst_or_admin_required, Sprint 27 표준 미확인)
7. 5-08 #7 — MFC 카테고리 합의 위반 (Codex M4 추측 수용, Twin파파 catch)
8. 5-09 #16 → HOTFIX-SPRINT66BE-ENRICH-SELECT-OPTIONS-ITEMCODE 폐기 (Codex M1~M5)
   - Sprint 66-BE Step 3+4 schema (int material_id) 설계 drift catch
9~10. 5-11 #18+#19 (2일 사이 동일 그룹 동시 발견):
  ⑨ #18 — HOTFIX-SPRINT66BE-MASTER-LIST-ITEM-TYPE (GET 응답 schema 누락)
  ⑩ #19 — HOTFIX-SPRINT66BE-CREATE-MASTER-ITEM-TYPE-AND-CONFLICT-MSG (POST INSERT 누락)
11. 5-15 #28 — pytest 결과 보고 검증 누락 (cowork 측 v2.15.0~v2.15.9 release trail "pytest GREEN" 보고 영역 실 환경 미실행 가능성 catch)
   - 본 환경 시점에 pytest 자체 미설치 + AXIS-OPS `.github/workflows/` CI 부재 → 이전 release trail 보고 = cowork 다른 환경/추정 보고 의심
   - v2.15.10 turn 시점부터 pytest 가용 (psycopg2-binary + bcrypt + Flask 등 deps 함께 설치)
   - CI 워크플로우 `.github/workflows/pytest.yml` 신규 도입 (push/PR 자동 pytest) — 5-15 옵션 2 진행
```

**결정 — Cowork 작업 영역 3단계 분류**:

#### ✅ Cowork 직접 작업 가능 영역 (Tier 1)

- **md 문서 작업** — CLAUDE / PROGRESS / CHANGELOG / handoff / BACKLOG / memory / AGENT_TEAM_LAUNCH
- **SQL 검증 query (read-only)** — SELECT 측정 + 통계 + 분석
- **데이터 분석** — pg_stat / Sentry trail / Railway logs 정리
- **사용자 인터뷰 정리** — 운영 영역 catch 기록
- **설계서 초안 작성** — design draft (검증 단계 필요)

근거: 누적 실수 9건 중 0건 = md / 문서 영역. cowork 강점 영역.

#### ⚠️ Cowork 작업 후 검증 필수 영역 (Tier 2 — Codex 라운드 + Claude Code cross-check 필수)

- **HOTFIX 설계서** — 5-09 #16 폐기 사례 (M1~M5) 직접 사례. 설계 시 Codex 라운드 1 필수.
- **API 응답 schema 변경** — 5-11 #18+#19 동일 그룹 동시 catch 실패 사례. endpoint 그룹 일관성 검증 필수 (GET + POST + PUT + DELETE 모두).
- **신규 코드 변경 (BE/FE)** — cowork 작성 후 Claude Code cross-check + pytest 작성 + Codex 라운드 1 필수.
- **Migration SQL 작성** — DB 영향 큰 영역. ROLLBACK 가이드 + 사전 검증 SQL 동봉 필수.
- **CONFLICT/ERROR 응답 영역** — 5-11 #19 사례 (사용자 디버깅 영역). FE/사용자 영향 분석 필수.

근거: 누적 실수 #1~#19 중 6건 = Tier 2 영역 (3,4,6,8,9,10). 검증 절차 강화로 사고 사전 차단.

#### ❌ Cowork 단독 작업 금지 영역 (Tier 3 — Claude Code/사용자 결정 우선)

- **prod DB 직접 변경** — DELETE / TRUNCATE / 운영 데이터 영향 큰 INSERT/UPDATE
- **보안 영역** — JWT / encryption / auth flow / refresh_token / PIN 영역 (FIX-PIN-FLAG 사례 ↗)
- **migration_history 직접 수정** — 자동 적용 영역 (HOTFIX-09 사례 ↗)
- **데코레이터 / 권한 가드 신규 작성** — 5-07 #6 사례 직접 (DRY + 표준 준수)
- **deploy 결정** — prod release 영역 (사용자 측 결정 영역, CLAUDE.md ⑦.5 사용자 배포 승인 게이트 정합)

근거: 누적 실수 분석 + 운영 영역 보호. cowork 영역 명확화로 운영 안정성 확보.

**검증 절차 표준 (Tier 2 영역)**:

```
① cowork 작업 완료
② Claude Code cross-check (grep / 동일 그룹 endpoint 정합성):
   - API 응답 schema 변경 시 → 동일 endpoint 그룹 GET/POST/PUT 일관성 grep
   - 코드 변경 시 → 기존 표준 grep (데코레이터 / 함수 / 헬퍼)
   - import 누락 검증 (HOTFIX-09 패턴)
③ Codex 라운드 1 (M/A 라벨)
④ pytest 작성 (검증 영역 명시)
⑤ Pre-deploy Gate 통과 → push
```

**잠재 ADR 후보 (미발번 — 현재 trail 영역, 미래 결정. ADR-031~033 은 2026-06-10 발번됨)**:

- cowork 측 사용 모델 영역 명시 (현재 정황 영역)
- cowork ↔ Claude Code ↔ Codex 3자 역할 분리 정책 표준화
- Sprint 설계서 작성자 영역 명시 (cowork / Claude Code 분리)

**ADR-023 영역 정정**: "ADR-024 분리 검토 영역" → **"ADR-029 분리 완료 (2026-05-11)"** trail 정합.

**연관 ADR**:
- ADR-023 (cowork 추측 작성 차단 — Flutter + DB 영역, 5-06 + 5-07 2차 보강)
- ADR-024 (phase=2 GET 시 phase=1 데이터 inherit, 5-06 v2.11.5)
- ADR-028 (운영 안정화 storage 손실 모니터링, 5-11)

**Why (긴급도 영역)**: 9건 누적 catch — 5-11 #18+#19 동일 endpoint 그룹 동시 catch 실패 = cowork 검증 절차 부재 입증. 운영 안정화 영역 (5월) 잦은 push 시기에 추가 사고 영역 차단 필요. Tier 2 영역 검증 절차 강화로 #20 (또는 그 이후) 사전 차단 목표.

---

### ADR-028: 운영 안정화 시기 storage 손실 모니터링 + 6월 재점검 (2026-05-11)

**맥락**: 2026-05-11 D+14 FIX-PIN-FLAG 측정 결과 **deploy ↔ storage 손실 상관관계 발견**. 5-10 evening v2.12.4 Netlify FE deploy → 5-11 morning 출근 burst 23명 일괄 PIN 재등록 (06:54~09:02 KST, 전 회사 광범위). 평소 1~2건/일 vs 5-11 23건 = polynomial spike. 5-08 v2.12.3 BE only (FE 빌드 X) → 5-09 PIN 재등록 0건 비교 = **PWA SW 업데이트 ↔ IndexedDB 일괄 손실 가설 강력**.

**결정 — 5월 안정화 시기 trade-off 영역, 6월 본격 재점검**:

| 영역 | 결정 | 이유 |
|:---|:---|:---|
| **5월 운영 시기** | 잦은 push 지속 영역, storage 손실 모니터링 (액션 X) | 운영 안정화 + 디버깅 + 편의사항 개선 우선 |
| **사용자 영향** | 신고 영역 0건 (사용자 측 자체 PIN 재설정 해결 가능) | backend fallback (v2.10.6) + 비번 로그인 폴백 활성 |
| **6월 재점검 트리거** | 5월 end 도달 (잦은 push 시기 종료) + 신규 BACKLOG `OBSERV-PIN-FLAG-DEPLOY-CORRELATION-RE-CHECK-20260601` | 본격 운영 상태에서 deploy 빈도 ↓ 영역에서 재측정 |
| **6월 재점검 영역** | (1) 5월 PIN 재등록 일별 추세 (deploy 매핑) (2) deploy 후 D+1 burst 패턴 통계 (3) backend fallback 우회 cohort 분석 (4) FE 측 IndexedDB vs SharedPrefs 측정 (5) 사용자 인터뷰 sample | 데이터 기반 결정 영역 |
| **잠재 결정 영역 (6월 재점검 결과 후)** | (a) FEAT-AUTH-STORAGE-MIGRATION-FULL 진행 (refresh_token + worker_id + worker_data SharedPrefs sync, 보안 trade-off 검토) (b) UX-LOGIN-FALLBACK-PIN-RESET-LINK 진행 (UX 보조 안내) (c) backend pin-status 흐름 재설계 (storage 의존도 0) | 측정 결과로 우선순위 결정 |
| **task #29 status** | **pending 유지** — 6월 재점검 후 정량 close 결정 | 정성 close (신고 0) ≠ 정량 close (storage 손실 0) |

**측정 trail (2026-05-11 D+14)**:

- Q1: pin_status_calls 14일 추세 = 93~100% 안정 ✅ (backend fallback 효과 입증)
- Q2: 활성 7d 54명 / PIN 등록 total 31명 / 비율 22.2% (5-04 31.1% 대비 -8.9pp, 휴일 영역)
- Q3: PIN 재등록 4-30 ~ 5-10 = 1~2건/일 / **5-11 = 23건 polynomial spike** ⚠️
- Q4: 23명 모두 5-11 인증 흔적 0건 (login/pin-login/pin-status 모두 0) + set-pin endpoint access_log 미기록 영역 발견

**연관 ADR**: ADR-023 (cowork 추측 작성 차단), ADR-025 (DB Pool per-worker 영역, 별 영역)

**연관 BACKLOG entry**:
- `OBSERV-PIN-FLAG-DEPLOY-CORRELATION-RE-CHECK-20260601` (6월 재점검 sprint, 신규 등록)
- `FEAT-AUTH-STORAGE-MIGRATION-FULL-20260427` (P2 OPEN, 6월 결정 영역)
- `UX-LOGIN-FALLBACK-PIN-RESET-LINK-20260427` (P3 OPEN, 6월 결정 영역)

**Why (긴급도 영역)**: 사용자 5-11 catch — "5월 운영 안정화 시기 잦은 push 영역 = storage 손실 trade-off 영역, 6월 본격 운영 상태에서 재점검". 사용자 측 신고 영역 0건이라 P1 영역 아님. 측정 데이터 명확 영역 = 가설 검증 가능 영역.

---

### ADR-027: 자재 마스터 인프라 도입 — material_id 직접 전달 + dual-format 호환 (2026-05-07, v2.12.0 FEAT-MATERIAL Step 1)

**맥락**: Sprint 63 의 51a seed `checklist_master.select_options` 가 placeholder JSON ("MKS GE50A | 5 SLM | 0.5 MPa | 0.1-0.7 MPa") 영구 차단 — 현장 작업자 무관 + DB 직접 수정 외 변경 불가. 5-07 Twin파파 catch — csv 1640 row + MFC xlsx 14 자재 = 186 unique 자재 데이터 보유. 4 step sprint (Migration 053 schema → 053a seed → BE override → AXIS-VIEW admin GUI) 도입.

**결정 — material_id 직접 전달 + dual-format 호환 + selected_material_id FK 분리 컬럼**:

| 영역 | 결정 | 이유 |
|:---|:---|:---|
| **schema 정규화** | `checklist.material_master` 신설 (item_code UNIQUE) — 같은 자재가 여러 product_code 등장 (max 105회) | 정규화 정합 + admin 측 자재 spec 변경 시 자동 반영 |
| **schema 위치 이전** | public.product_bom + bom_checklist_log + bom_csv_import → checklist schema 이전 | 5-Tier 아키텍처 (plan / app / checklist / hr / defect) 정합 |
| **표준 식별자** | `qr_doc_id` (D1-01 Codex 라운드 1) | google_doc_id 폐기 — CLAUDE.md L72 표준 준수, ADR-018 정합 |
| **NOT NULL 제약** | boolean / timestamp 영역 (D1-02) | partial WHERE is_active 영역의 silent NULL drop 방지 |
| **DROP 순서** | bom_checklist_log → product_bom (자식→부모) | FK direction `bom_item_id → product_bom.id` 기반 |
| **material_id 전달** | FE 가 dropdown underlying value (material_id) 직접 전달 (NEW-M-01 Codex 라운드 3) | 역추적 (display string → material_id) 비결정성 차단 — item_name+spec 조합 UNIQUE 부재 |
| **selected_material_id 분리 컬럼** | `checklist_record.selected_material_id INTEGER FK RESTRICT` 추가 (NEW-M-01) | selected_value (display string) ↔ selected_material_id (FK 추적) 양쪽 보유 — 자재 spec 변경 시 BE override 자동 반영 |
| **dual-format 호환** | 옛 51a placeholder string 배열 + 신규 material_id int 배열 양쪽 지원 | 작업자 측 회귀 0 (admin 매핑 미적용 영역 그대로 legacy 동작) |
| **deploy 순서** | ordered deploy with feature flag (D6-01 Codex 라운드 1) | "atomic" misleading — Step 4 가 별 repo 분리 영역. Step 3 BE first → Step 4 admin GUI |
| **권한 가드** | `@jwt_required` + `@gst_or_admin_required` 2단 적층 (D3-02 Codex 라운드 1) | jwt_auth.py L263 표준 (Sprint 27 v1.7.4 도입) — DRY + ADR-023 cross-check |

**Codex 검증 trail (5 라운드)**: M=8/A=6/N=9 → M=2/A=7/N=9 → M=1/A=2/N=1 → M=0/A=0/N=2 → **M=0/A=0/N=0 GREEN**

**Step 1 implementation 라운드 1 (2026-05-07)**: M=0/A=2/N=11 GREEN. A 2건 즉시 정정 — UNIQUE 컬럼 명시 검증 (key_column_usage JOIN) + index partial predicate 검증 (pg_get_expr() 괄호 wrapping 정합).

**Step 2 implementation 라운드 1~5 (2026-05-08)**: M=3/A=4 → M=2/A=2 → M=1/A=1 → M=0/A=2 → **M=0/A=1 GREEN**. 핵심 정정:
1. **MFC 단일 'MFC' 카테고리 합의 위반 catch (Twin파파, ADR-023 cross-check)** — Codex M4 advisory 따라 'MFC LNG/CDA/O2/N2' 분리 적용 → 5-07 사용자 합의 위반. 사용자 발견 후 즉시 'MFC' 단일 복원 + DB UPDATE 13건. ADR-023 cross-check 표준 1차 입증 #5 사례.
2. **'-' placeholder 자재 reject** (M1) — generator `parse_csv_bom_format()` 에 `if mapped['item_code'] == '-': continue` 추가. 186→185 unique, 1640→1626 BOM.
3. **description 컬럼 추가 (053b)** — admin AXIS-VIEW Step 4 측 ILIKE 검색 보조. 1110299900 = LNG/O2 dual-use → 단일 row + description='LNG,O2' (RFC 4180 quote csv).
4. **Generator self-containment** — 053a SQL 최상단 `ALTER TABLE ADD COLUMN IF NOT EXISTS description TEXT` prefix 추가. test DB fresh boot 시 alphabetic 순서로 053a > 053b 실행되어 INSERT 실패 → 자체 보장.

**적용 영역 (Step 1 v2.12.0 + Step 2 v2.12.1 운영 적용 2026-05-07~08)**:

- `backend/migrations/053_material_master_and_bom_schema_migration.sql` (175 LOC, Step 1)
- `backend/migrations/053a_material_master_and_bom_seed.sql` (115.5 KB, 자동 생성, Step 2)
- `backend/migrations/053b_material_master_add_description.sql` (Step 2 보완)
- `backend/scripts/generate_migration_053a.py` (~270 LOC, 자동 생성 스크립트)
- `tests/backend/test_migration_053_schema.py` (9 TC, 9/9 PASS)
- `tests/backend/test_migration_053a_seed.py` (11 TC, 11/11 PASS)
- 운영 DB psql 직접 적용 + migration_history INSERT (053 / 053a / 053b)

**Step 3 implementation 라운드 1~2 (2026-05-08, v2.12.2)**: M=2 (G+D 동일 경로) → **M=0/A=1 GREEN**. 핵심 정정:
1. **FE re-entry hydrate (G+D)** — Codex 라운드 1 catch — `_selectMaterialIdMap` 재진입 시 비어있어 PASS/NA 라디오 탭 시 selected_material_id NULL 덮어쓰기 silent bug. 정정: BE GET 응답에 `COALESCE(cr.selected_material_id, cr_p1.selected_material_id)` 추가 + FE `_fetchChecklist` 에서 `_selectMaterialIdMap` 복원 (`smid is int` 가드).
2. **N+1 BATCHED 정합 (Codex P0 #3)** — `_collect_material_ids` set 수집 + `_fetch_material_master_map` 단일 SELECT `WHERE id = ANY(%s)` (psycopg2 parametrized, SQL injection 안전). pytest `_CountingCursor` proxy 로 1 호출 검증.
3. **dual-format 호환** — 옛 string array (51a placeholder) 그대로 + 신규 int array (material_id) → tuple `(display_strings, material_ids)` parallel 반환. invalid material_id WARN log + skip (작업자 noise 0).
4. **옵션 Y 표시 형식** — 5-08 사용자 결정 — `name (description) | spec_1 | spec_2` (description 있으면 괄호 포함, 같은 spec MFC LNG/O2 분리 가시성).

**적용 영역 (Step 1 v2.12.0 + Step 2 v2.12.1 + Step 3 v2.12.2 운영 적용 2026-05-07~08)**:

- `backend/migrations/053_material_master_and_bom_schema_migration.sql` (Step 1)
- `backend/migrations/053a_material_master_and_bom_seed.sql` (Step 2 자동 생성)
- `backend/migrations/053b_material_master_add_description.sql` (Step 2 보완)
- `backend/scripts/generate_migration_053a.py` (Step 2 자동 생성 스크립트)
- `backend/app/services/checklist_service.py` (Step 3 — 4 신규 함수 + 3 함수 수정)
- `backend/app/routes/checklist.py` (Step 3 — 2 endpoint 수정)
- `frontend/lib/screens/checklist/mech_checklist_screen.dart` (Step 3 — 4 변경 + re-entry hydrate)
- `tests/backend/test_migration_053_schema.py` (9 TC)
- `tests/backend/test_migration_053a_seed.py` (11 TC)
- `tests/backend/test_sprint66_be_step3_enrich.py` (14 TC)
- 운영 DB psql 직접 적용 + migration_history INSERT (053 / 053a / 053b)
- pytest 총 34/34 PASS

**Step 4 implementation 라운드 1 (2026-05-08, v2.12.3, OPS BE 측)**: **M=0 / A=6 GREEN** (전부 advisory, BACKLOG 처리). admin endpoints 신규 7건 (자재 마스터 CRUD 5 + 체크리스트 매핑 2). AXIS-VIEW Sprint 42 (별 repo) 가 consume 할 인프라 확보. **Sprint 66-BE OPS 측 100% 완료** (Step 1+2+3+4 prod 적용 + 총 47/47 pytest GREEN). 핵심 정합:
1. **권한 정합 (ADR-023 #6)** — `@jwt_required + @gst_or_admin_required` 2단 적층. 새 데코레이터 작성 X (jwt_auth.py L263 표준 활용).
2. **dual-format 호환** — GET options 의 select_options_raw 분기: int array → JOIN+array_position 순서 보존 / string array → legacy_string flag.
3. **xmax trick idempotent** — POST `RETURNING id, (xmax = 0) AS created` PostgreSQL trick — 1차 INSERT created=true / 2차 ON CONFLICT UPDATE created=false.
4. **5종 validation** (PATCH options) — list / int (bool 차단) / 중복 / material_master 존재+is_active=TRUE / item_type='SELECT'.
5. **db_pool RealDictCursor 정합** — 1차 시도 실패 후 row[0] → row['id'] dict access fix (db_pool.py default cursor_factory).

**Codex A 6건 (BACKLOG 처리)**:
- I-1: inactive material stale mapping round-trip (admin 가시성 의도, AXIS-VIEW FE 시각 마킹)
- I-3: NULL vs `[]` 매핑 구분 소실 (FE 처리 규약 문서화)
- B-legacy: legacy string CI 커버리지 조건부 (seed fixture)
- B-coerce: PATCH string ID coercion 미구현 (AXIS-VIEW Sprint 42 측 int 전송 보장 필수)
- D-race: validation-update race window (운영 빈도 낮음)
- F-wildcard: ILIKE wildcard escape 미구현 (검색 의미론, 보안 X)

**적용 영역 (Sprint 66-BE 전체 — 4 step prod 적용 2026-05-07~08)**:

- Step 1 (v2.12.0): `backend/migrations/053_material_master_and_bom_schema_migration.sql` (175 LOC)
- Step 2 (v2.12.1): `backend/migrations/053a_material_master_and_bom_seed.sql` + `053b_material_master_add_description.sql` + `backend/scripts/generate_migration_053a.py` (~270 LOC)
- Step 3 (v2.12.2): `backend/app/services/checklist_service.py` (4 신규 함수) + `backend/app/routes/checklist.py` (2 endpoint 수정) + `frontend/lib/screens/checklist/mech_checklist_screen.dart` (5 변경 + 재진입 hydrate)
- Step 4 (v2.12.3): `backend/app/routes/admin_materials.py` (5 endpoint) + `backend/app/routes/admin_checklists.py` (2 endpoint) + `backend/app/__init__.py` (2 blueprint 등록)
- pytest 총 47/47 GREEN (9 + 11 + 14 + 13)
- migration_history INSERT — 053 / 053a / 053b 모두 등록

**후속 step**:

- **AXIS-VIEW Sprint 42** (별 repo) — `/materials` admin GUI + `/checklists` 매핑 GUI consume
  - admin 매핑 시 BE override (Step 3) 자동 작동 → 작업자 동적 자재 옵션 수신 시작
- Sprint 66-BE OPS 측은 v2.12.3 release 로 **종결**

**연관 ADR**: ADR-018 (qr_doc_id 표준), ADR-023 (cowork 추측 작성 차단), ADR-026 (체크리스트 phase split)

---

### ADR-026: 신규 체크리스트 카테고리 phase split 표준 (2026-05-06, v2.11.7 Sprint 65-BE)

**맥락**: Sprint 65-BE — VIEW `/partner/report` 성적서 MECH 섹션 input_value 가 `—` 로 렌더링. Root cause: `get_checklist_report` 의 `else` 분기에서 `qr_doc_id=''` (default) 로 SELECT → DB record (`DOC_<sn>`) 와 매칭 0건. 근본 원인 = 카테고리별 phase split 패턴 비일관 (ELEC 만 분리, MECH/TM 미분리).

**결정 — 카테고리별 phase split 적용 기준 표준화**:

| 카테고리 | phase split | qr_doc_id 처리 | 이유 |
|:---:|:---:|:---|:---|
| **ELEC** | ✅ Phase 1/2 | default `''` (모바일도 `''` 송신) | 1차 배선 → 2차 배선 흐름, 양쪽 빈 문자열 매칭 OK |
| **MECH** | ✅ Phase 1/2 | `_normalize_qr_doc_id(sn)` 명시 = `'DOC_<sn>'` | 1차 입력 → 2차 검수 흐름, 모바일 앱 `_normalizeQrDocId` 와 정확 일치 (Sprint 65-BE) |
| **TM** | ❌ SINGLE 흐름 | DUAL/SINGLE 분기 (`'DOC_<sn>-L/R'` 또는 `'DOC_<sn>'`) | Tank Module 검사는 1회 완료, phase 분리 무의미 |
| **PI/QI/SI** (미래) | 도입 시 결정 | 케이스별 검토 | 성적서 응답 schema 정합 검증 후 분기 |

**Phase split 적용 시 필수 영역**:
1. BE `checklist_service.py get_checklist_report` 분기 추가
2. `phase_label` 한국어 라벨 명시 (`'1차 입력'` vs `'2차 검수'` 등 카테고리별 적합)
3. `phase1_applicable=False` 항목 자동 제외 (Sprint 60-BE 컬럼 기반)
4. `total > 0` 조건으로 빈 phase 자동 제외
5. VIEW FE `ChecklistReportView` 측 `cat.phase_label` 표시 로직 (이미 ELEC 패턴 일반화됨)

**Phase split 미적용 (TM 패턴) 시 필수 영역**:
1. `qr_doc_ids` 배열 (DUAL 시 L/R 분리)
2. `qr_doc_id` 명시 호출 (`_normalize_qr_doc_id(sn, 'L')` 등)

**적용 흐름** (신규 카테고리 도입 시):
```
1. 카테고리 워커 입력 흐름 분석:
   - 1차 → 2차 분리 흐름 → Phase split 적용 (ELEC/MECH 패턴)
   - 1회 완료 흐름 → SINGLE 분기 (TM 패턴)
2. qr_doc_id 모바일 앱 송신 패턴 확인:
   - 빈 문자열 송신 → BE default `''` 매칭 OK
   - `'DOC_<sn>'` 송신 → BE `_normalize_qr_doc_id` 명시 호출 필수
3. BE/VIEW FE 회귀 검증:
   - pytest TC 신규 (qr_doc_id 매칭 + phase 분리)
   - VIEW `ChecklistReportView` 의 categories.map / phase_label 처리 검증
```

**위험 + 대응**:
- 신규 카테고리 도입 시 `else` fallback 사용하면 record 매칭 실패 가능 (Sprint 65-BE 사고 패턴 재발) → 명시 분기 강제
- 코드 중복 (ELEC + MECH 거의 1:1) → `OPS-CHECKLIST-PHASE-SPLIT-REFACTOR-01` BACKLOG 등록

**검증 trail**:
- pytest 3 TC 신규 (qr_doc_id 매칭 + phase 분리 + ELEC/TM 회귀 0)
- 운영 검증: TEST-1111 / TEST-2222 SN 의 MECH 섹션 input_value 정상 표시
- VIEW FE 변경 0건 입증 (4 angle prerequisite 검증 통과)

**선행/후속**:
- 선행: Sprint 39 (FE) ✅, Sprint 63-BE ✅ (master 73), Sprint 60-BE ✅ (phase1_applicable 컬럼)
- 후속: REFACTOR-CHECKLIST-PHASE-SPLIT (헬퍼 함수 추출, P3 LOW), FIX-MECH-DUAL-INLET-L-R-SEPARATION (운영 데이터 발생 시)

---

### ADR-025: DB Pool 자가 회복 메커니즘 — keepalive + warmup self-recovery (2026-05-06, v2.11.6)

**맥락**: 4-29 23:31 + 5-04 11:38 KST 사고 — 5일 주기 silent failure 패턴 확립. 2단계 root cause:
1. Railway network proxy idle TCP disconnect (`pg_settings` idle 정책 0 + `tcp_keepalives_idle=7200초` + Sprint 30-B 정책으로 client psycopg2 keepalive OFF)
2. `ThreadedConnectionPool` `_used` dict dead conn 정리 부재 → `getconn()` PoolError exhausted → warmup loop break → 0/0 8 cycles (40분) → Restart 외 회복 불가

**WATCHDOG 영역 외**: 기존 watchdog (`db_pool.py:267-277`) 은 `_pool=None` 만 감지 → 본 사고는 `_pool` object 살아있음 + internal `_used` state 깨짐 → Sentry 0 event (사용자 실측).

**결정 — keepalive 활성화 + 자가 회복 + WATCHDOG 확장**:

```python
# 1. _CONN_KWARGS 에 keepalive 4 args (Sprint 30-B 정책 update — 4-30+ Railway tier 변동으로 충돌 해결됐을 가능성)
_CONN_KWARGS = {
    'connect_timeout': 5,
    'keepalives': 1,                # OS 레벨 TCP keepalive 활성화
    'keepalives_idle': 60,          # 60초 idle 후 probe 시작 (vs 기존 OS 7200초)
    'keepalives_interval': 10,      # 10초 간격 probe
    'keepalives_count': 3,          # 3회 fail 시 dead 판정 (90초 안 끊김 발견)
}

# 2. warmup_pool 0/0 연속 3 cycles 시 close_pool + init_pool 자가 회복
_consecutive_zero_warmup: int = 0
if warmed == 0 and len(conns) == 0:
    _consecutive_zero_warmup += 1
    if _consecutive_zero_warmup >= 3:  # 15분 = 5분 cron × 3
        logger.error("[db_pool] 0/0 warmed for %d consecutive cycles — re-initializing pool")
        close_pool(); init_pool()
        _consecutive_zero_warmup = 0

# 3. logger.error → LoggingIntegration(event_level=ERROR) 자동 Sentry capture (WATCHDOG 확장)
```

**근거**:
- keepalive 60s idle + 30s probe = 90초 안 disconnect 발견 → fresh conn 생성 가능 (1단계 root cause 해소)
- 자가 회복 = 1단계 누설 시에도 15분 max 안 회복 (2단계 root cause 해소)
- per-worker 카운터 (의도된 설계 — Worker A 자가 회복해도 B 별개)
- additive 변경 — 정상 path 무영향 → 회귀 위험 0

**위험**: Sprint 30-B Railway proxy TCP_OVERWINDOW 충돌 재발 가능성 — staging 1h 검증 필수. 만약 재발 시 keepalive 만 부분 rollback 가능 (자가 회복 (변경 2/3) 만 유지).

**검증** — staging 1h + T+1h / T+24h / T+1주:
- staging: TCP_OVERWINDOW WARN 0건 + Railway logs 정상 boot
- T+1h: Sentry 신규 issue 0
- T+24h: warmup cron 정상 5/5 패턴 유지 (288 cycles) + `_consecutive_zero_warmup` 누적 0
- T+1주 (5-09 ± 1d): 재발 0 (keepalive 차단) 또는 자가 회복 작동 (init_pool 호출 logs + Sentry event) → 정량 입증

**선행/후속**:
- 선행: `OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP-20260427` ✅ (warmup cron) + `FIX-DB-POOL-DIRECT-FALLBACK-LOG-LEVEL-20260428` ✅ + `FIX-DB-POOL-WARMUP-WATCHDOG-20260430` ✅
- 후속 (선택): `INFRA-RAILWAY-PROXY-IDLE-INVESTIGATION-20260504` (P3) / `OBSERV-WARMUP-LOGGER-CLARIFY-20260504` (P3)

**pytest** — `tests/backend/test_db_pool.py` 신규 4 TC (8/8 PASS):
- `test_keepalive_args_passed_to_psycopg2`
- `test_consecutive_zero_warmup_triggers_init_pool`
- `test_zero_warmup_logger_error_captured`
- `test_normal_warmup_resets_consecutive_counter`

**🎯 첫 실전 작동 입증 (2026-05-07 20:54 KST, T+1d)**:
- 4-29 → 5-04 → **5-07** 5일 주기 사고 패턴 재발 확인 (Railway proxy idle disconnect 가설 입증)
- Sentry alert: `[db_pool] 0/0 warmed for 3 consecutive cycles — re-initializing pool (pid=2)` ERROR 정상 발화 ✅
- **9ms self-recovery latency**: Sentry breadcrumb 5-07 11:54:48.706 UTC ↔ DB pid 205810 backend_start 20:54:48.715 KST = +9ms 일치 + 168ms 안 5 conn 모두 fresh 생성
- 사용자 영향: 1.5h+ (4-29 수동 Restart) → 40분 (5-04 수동 Restart) → **15분 자동** (5-07 자가 회복) → 단계 감소 입증
- 시나리오 B (정상 fallback) 확정 — `DB_POOL_VERIFICATION_QUERIES_20260427.md` V4.1 결과란 채움 완료

**⚠️ 부수 발견 — per-worker 카운터 의도의 사각지대 (2026-05-07 21:46 KST 사후 측정)**:
- Boot logs: `[2]` + `[3]` 동시 boot (Procfile `-w 2` 정합) = 2 worker 운영
- pg_stat_activity: 5 conn 만 (단일 클러스터 205810~205814 sequential pid) → Worker A 만 활성 conn
- **사각지대 본질**: warmup_pool 이 fcntl lock 으로 단일 worker (scheduler owner) 만 실행 → 다른 worker 의 `_consecutive_zero_warmup` counter 는 영원히 0 → 자가 회복 trigger 도달 불가능
- Worker B 풀 dead 시 HTTP 요청은 `_create_direct_conn()` fallback (+0.3~0.5s) silent degradation
- → 본 ADR-025 의 'per-worker 카운터 의도' 가 실 운영에서 사각지대 발생함을 5-07 측정으로 확인
- → 별 sprint **`OBSERV-PER-WORKER-POOL-RECOVERY-20260507`** 등록 (옵션 B — HTTP path getconn 실패 시 자가 회복 hook 권장)

---

### ADR-024: phase=2 GET 시 phase=1 데이터 inherit BE SQL 표준 (2026-05-06, v2.11.5 hotfix)

**맥락**: v2.11.4 prod 운영 후 사용자 발견 — "2차 검사 화면에서 1차 SELECT 값 안 보임". BE SQL 단일 phase LEFT JOIN 한계.

**결정 — 옵션 A (phase=1 record 별도 LEFT JOIN + COALESCE 우선)**:

```sql
-- cr (phase=current) + cr_p1 (phase=1 고정) 동시 LEFT JOIN
-- cr_p1 4개 조건: master_id + serial_number + judgment_phase=1 + qr_doc_id (Codex M-A2)
COALESCE(cr.selected_value, cr_p1.selected_value) AS selected_value
COALESCE(cr.input_value,    cr_p1.input_value)    AS input_value
```

**핵심 검증 (Codex 라운드 1 M-A2)**:
- cr_p1 의 `qr_doc_id = %s` 필수 — 누락 시 DUAL L/R 오상속
- params placeholder: `[sn, phase, qr, sn, qr] + master_params`

**회귀 평가**:
- ELEC TUBE 색상 SELECT — phase 단일 결정 → 영향 0
- TM SINGLE/DUAL — INPUT 미사용 → 영향 0
- additive LEFT JOIN — 기존 응답 schema 무변경 (NULL → 1차 데이터 자동 채움)

**결과 (v2.11.5)**:
- TestPhase2InheritsPhase1Data 2 TC — 2/2 PASS (58.02s)
- ~25 LoC (BE 1 + FE 1)
- 회귀 영향 0건

**적용 가능 영역**:
- 향후 PI/QI/SI 체크리스트 도입 시 동일 BE SQL 패턴
- phase 다단 진행 카테고리 모두 적용

---

### ADR-023: 신규 코드 작성 시 ELEC 패턴 + DB 스키마 정확 검증 표준 (2026-05-06, v2.11.4 hotfix + 5-06 보강)

**맥락**:
- Sprint 63-FE prod 운영 후 cowork 추측 작성 실수 누적 발견:
  1. `GxColors.background/surface/mistLight` 미존재 → flutter analyze 7 error (commit 21c581e fix)
  2. `check_result: null` BE validator 거부 → 사용자 운영 검증 시 PUT 400 (v2.11.3 R1 fix)
  3. `description` 렌더 누락 (ELEC L898-909 패턴 미차용) → v2.11.4 추가 정정 1
  4. R1 부작용 가시화 누락 (사용자가 PASS/NA 미선택 인지 못함) → v2.11.4 옵션 C
  5. **(2026-05-06 보강)** ELEC-only 데이터 초기화 SQL 작성 시 `completion_status.ee_completed` 사용 → 실제 컬럼명은 `elec_completed` (Sprint 6 RENAME 마이그레이션 미확인). `app_task_details.task_category = 'EE'` 도 동일 — 실제는 `'ELEC'`. 003 마이그레이션 (코멘트 "MM, EE, ...") 만 보고 006 의 `MM→MECH`, `EE→ELEC` RENAME 누락
- Codex 라운드 1+2 검증으로 일부 catch 했지만 **ELEC 패턴 단순 차용** 시 실제 멤버/payload/흐름 미검증 영역 존재
- **DB 스키마 영역 추가** — 초기 마이그레이션 (예: 003) 만 보고 후속 ALTER/RENAME 마이그레이션 (예: 006) 누락 시 컬럼명/enum 값 불일치로 SQL 에러

**결정 — Flutter + DB 양쪽 검증 표준**:

### ✅ 권장 — Flutter 영역
1. **GxColors / GxRadius / GxGradients 멤버 grep** — `frontend/lib/utils/design_system.dart` 직접 확인 후 사용. 추측 X
2. **apiService 호출 패턴 1:1 차용** — ELEC 의 `_toggleResult` / `_showCommentDialog` / debounce 타이밍 그대로
3. **BE schema 정확 확인** — `check_result` enum / `input_value` nullable / `selected_value` nullable / `description` 응답 포함 여부 grep
4. **위젯 구조 시각 차용** — `description` 렌더 (item_name 아래 작은 글씨, fontSize 10 / silver / ellipsis 1줄) ELEC 와 시각 일관성
5. **flutter analyze + flutter build web --release 강제** — 작성 후 즉시 검증, info 만 허용 (error 0)
6. **모든 동등 위젯 일관 적용** — `_buildCheckRadio` / `_buildSelectDropdown` / `_buildInputField` 같은 _build* 함수군 = description / disabled / state reactive 영역 모두 동일 패턴 적용 검증 (한 위젯만 적용 후 누락 X)

### ✅ 권장 — DB 스키마 / SQL 영역 (보강 신규)
1. **마이그레이션 시간순 전체 grep** — 특정 테이블 / 컬럼 작업 시 초기 CREATE 마이그레이션만 보지 말고 후속 ALTER/RENAME 도 모두 시간순 확인
   - 예시: `Grep pattern="completion_status" path=migrations` → 003 (CREATE) + 006 (RENAME) + 023 (ALTER) 등 모두 확인
2. **컬럼명 / enum 값 코드 cross-check** — 실제 운영 코드 (services / routes / migrations) 에서 사용 중인 값 grep
   - 예시: `Grep pattern="task_category\s*=\s*['\"](MM|EE|MECH|ELEC|TM|PI|QI|SI)['\"]"` → 실제 값 'MECH' / 'ELEC' 확인 후 사용
3. **information_schema 검증 SQL** — 사용자에게 제공할 SQL 작성 시 사전 검증 쿼리 동봉
   - `SELECT column_name FROM information_schema.columns WHERE table_name = 'X'`
   - `SELECT DISTINCT column_value FROM table` (enum 실제 값 확인)
4. **트랜잭션 안전 패턴 권고** — `BEGIN; ... COMMIT;` 또는 `SAVEPOINT` 명시. 운영 DB 삭제 SQL 은 항상 트랜잭션 + 검증 쿼리 동봉
5. **단일 row 다중 컬럼 테이블 주의** — `completion_status` 처럼 시리얼 1개당 단일 row 에 여러 카테고리 boolean 보유 시 row DELETE 금지, 카테고리별 컬럼 UPDATE 만

### ❌ 금지
- 추측해서 작성 — 검증 안 된 멤버 / payload / 흐름 사용 금지
- BE validator 모르고 nullable 가정 — `check_result: null` 같은 사례 재발 차단
- ELEC 패턴 일부만 차용 — entry point / disabled UI / 경고 메시지 / state reactive 모두 검증
- **(보강)** 초기 마이그레이션 (CREATE) 만 보고 후속 ALTER/RENAME 무시 — 컬럼명/enum 값 변경 추적 누락 X
- **(보강)** 코멘트 (`-- MM, EE, TM, PI, QI, SI`) 의 표기를 그대로 신뢰 — 실제 운영 데이터 / 후속 마이그레이션 / 코드 사용처 cross-check 필수

### 📋 Pre-deploy Gate 강화
- pytest BE 테스트 + flutter analyze + flutter build web 모두 PASS
- 사용자 측 운영 검증 시나리오 4 상태 (초기 / 입력만 / 라디오 클릭 / 2차 진입) 명시
- **(보강)** SQL 작성 시 사전 검증 쿼리 (information_schema + 카테고리 분포) 동봉, 트랜잭션 BEGIN/COMMIT 패턴 권고

**결과 (v2.11.4 + 5-06 보강)**:
- Codex 라운드 1: M=0 / A=2 / N=3 (ELEC 패턴 정합 입증)
- ~30 LoC FE only, 회귀 영향 0건
- description + 옵션 C 경고 동시 추가, R1/R2 충돌 0
- ELEC-only 데이터 초기화 SQL 사용자 catch 2회 (column "category" + column "ee_completed") 후 정정 → DB 영역 검증 표준 ADR-023 보강

**적용 가능 영역**:
- 향후 PI/QI/SI Flutter UI 도입 시 동일 검증 표준 (멤버 grep + 패턴 1:1 + BE schema + 위젯 시각 + analyze/build)
- DB 스키마 작업 (ALTER/RENAME 영향 큰 컬럼) 시 동일 표준 (시간순 마이그레이션 grep + 코드 cross-check + information_schema 검증 + 트랜잭션 패턴)
- 사용자에게 SQL 제공 시 사전 검증 쿼리 동봉 + ROLLBACK 가이드 첨부

**Cowork 추측 작성 실수 trail 누적 6건** (2026-05-07 2차 보강) — ADR-024 분리 검토 영역 도달

---

### 🔄 2026-05-07 2차 보강 — 추측 작성 실수 #6 + 신규 표준 영역

**맥락**:
- Sprint FEAT-MATERIAL-MASTER-AND-BOM-INTEGRATION-20260507 작성 중 cowork 가 신규 인증 데코레이터 `@require_admin_or_gst` 작성
- 사용자 측 자체 검증 라운드 1 P0 #2 발견 — **기존 표준** `@gst_or_admin_required` (`backend/app/middleware/jwt_auth.py:263`, Sprint 27 v1.7.4 도입) 이 이미 존재
- **간단한 grep `gst_or_admin_required` 으로 즉시 발견 가능했던 영역** — cowork 가 cross-check 누락
- DRY 원칙 + CLAUDE.md L1009-1015 인증 표준 (`@admin_required` / `@manager_or_admin_required`) 위반

**추측 작성 실수 trail (6건 누적)**:
```
1. GxColors.background/surface/mistLight (commit 21c581e 사용자 fix)
2. check_result null 처리 (BE 400, 사용자 운영 catch)
3. ELEC `_get_checklist_by_category` SQL 차용 시 phase 단일 join 한계
4. description 표시 영역 _buildInputField 만 적용 + _buildCheckRadio/_buildSelectDropdown 누락
5. completion_status.ee_completed (실제 elec_completed, Sprint 6 RENAME 미확인)
6. ⭐ NEW (2026-05-07) — @require_admin_or_gst (실제 @gst_or_admin_required, Sprint 27 v1.7.4 미확인)
```

**신규 표준 영역 (2026-05-07 추가)**:

### ✅ 권장 — 신규 데코레이터 / 함수 / 헬퍼 작성 시 (보강 신규)
1. **신규 작성 전 grep 필수** — `Grep <name>` / `Grep <역할 keyword>` 으로 기존 코드 cross-check
   - 데코레이터: `Grep "_required\b"` 또는 `Grep "def.*required"` 또는 `Grep "@.*_required"`
   - 함수: `Grep "def <similar_name>"` 또는 `Grep "<core_keyword>"` (예: `gst`, `admin`, `auth`)
   - 헬퍼: `services/`, `utils/`, `middleware/` 디렉토리 grep
2. **인증/권한 영역 = jwt_auth.py 우선 grep** — `backend/app/middleware/jwt_auth.py` + `backend/app/auth.py` 전수 검토
3. **CLAUDE.md L1009-1015 표준 데코레이터 5종 명시** — `@admin_required` / `@manager_or_admin_required` / `@gst_or_admin_required` / `@view_access_required` / `@jwt_required` 중 정확 선택
4. **새 데코레이터 도입 권장 시 ADR 등록** — 5 표준에 6번째 추가 시 ADR 신설 필수

### ❌ 금지
- **기존 표준 cross-check 없이 신규 데코레이터 / 함수 작성** — DRY 위반 + 운영 표준 분열
- **role / permission 영역 신규 작성** — 기존 jwt_auth.py 패턴 복제 X
- **추측해서 데코레이터 작성** — Sprint 27 v1.7.4 같은 기존 도입 영역 미확인

### 📋 Pre-deploy Gate 강화 (2026-05-07 추가)
- 신규 작성 전 `Grep <name>` cross-check 결과 명시 (Sprint 설계서 본문에 trail 보존)
- 인증/권한 영역 = pytest 4 조합 (admin / 매니저 / GST / 일반 worker) 검증

**ADR-024 분리 검토 영역 (2026-05-07)**:
- 6건 catch 도달 = 분리 시점
- ADR-024 후보: "신규 코드 작성 시 기존 표준 cross-check 의무 표준" (데코레이터 / 함수 / 헬퍼 영역 grep + ADR 등록)
- ADR-023 (Flutter + DB 영역) 와 분리 시 명확성 ↑
- 사용자 결정 영역 — 본 sprint 진행 후 시점에 분리 권장

**적용 가능 영역**:
- 향후 모든 신규 데코레이터 / 함수 / 헬퍼 작성 시 grep cross-check 표준
- Sprint 설계서 본문에 grep trail 명시 (cowork 추측 작성 실수 영역 사전 차단)
- Codex 라운드 1 자동 검증 영역 (인증 영역 표준 정합 체크)

---

### ADR-022: 신규 체크리스트 카테고리 도입 시 진입점 검증 표준 (2026-05-04, v2.11.2 hotfix)

**맥락**:
- Sprint 63 (v2.11.0+v2.11.1) prod 배포 직후 사용자 검증에서 발견 — "체크리스트 자동 전환 안 됨" + "task 상세 메뉴 버튼 없음"
- Sprint 63-BE 설계 시 ELEC 패턴 차용 영역에서 **toast 알림 (CHECKLIST_*_READY) 만 매핑**, work/start 응답 분기 + FE task 상세 메뉴 버튼 = 진입점 (entry point) 영역 누락
- Sprint 63-FE `_navigateToChecklist` 함수는 task_management_screen 에만 MECH 분기 추가, task_detail_screen 의 동일 이름 함수는 누락 (dead code 상태)
- 추가 검토에서 5번째 위치 (`_buildCompletedBadge` onTap) 신규 catch — 4 → 5 위치 갱신

**결정 — 신규 카테고리 도입 시 진입점 검증 표준**:

### BE 측 (4 영역)
1. **`work.py` work/start 응답 분기** — `checklist_ready=True + checklist_category='{CATEGORY}'`
2. **`task_service.py` work/complete 응답 분기** (선택) — 완료 후 진입 유도 (ELEC IF_2 패턴)
3. **`trigger_task_id` 토스트 알림** (`CHECKLIST_*_READY` enum) — 51a seed 의 master 권위
4. **WebSocket emit 핸들러** (`alert_service`)

### FE 측 (5 영역)
1. **import** — 신규 ChecklistScreen 추가
2. **`_hasChecklistAccess`** — taskCategory + taskId 양쪽 매칭 필수 (단축 금지)
3. **`_buildChecklistButton` onTap** (in_progress 시) — 진입 분기
4. **`_navigateToChecklist`** — Screen 분기 (⚠️ task_management vs task_detail **두 파일 별도 정의**, 둘 다 정합 필수)
5. **`_buildCompletedBadge` onTap** (completed 시) — 진입 분기 (라운드 1 누락 영역, 추가 검토 catch)
6. **`alert_log` priority + iconName + alert_list_screen `_handleAlertTap`** — WebSocket alert 분기

### 검증 절차
- ELEC 패턴 동등 영역 grep 으로 모든 진입점 위치 확인
- prerequisite 명시 (Sprint 설계서 본문)
- prod 배포 직후 수동 시나리오 검증 (자동 전환 + 메뉴 버튼 클릭, in_progress + completed 양 시점)
- pytest TC: work/start 응답 키 검증 + 회귀 (기존 카테고리 무영향) + negative (의도적 제외)

**결과 (v2.11.2)**:
- pytest 30/30 PASS (24 기존 + 6 신규)
- 회귀 영향 0건
- 본 hotfix 변경 = BE 1 + FE 1 = 2 파일 ~25 LoC

**적용 가능 영역**:
- 향후 PI/QI/SI Flutter UI 도입 시 동일 진입점 표준 (BE 4 + FE 5 + alert 1 = 10 영역) 검증

---

### ADR-021: Sprint 63-FE Flutter UI + R2-1 BE patch + WebSocket 통합 (2026-05-04, v2.11.1)

**맥락**:
- Sprint 63-BE (v2.11.0) BE 인프라 squash merge 완료 직후 후속 piece
- Codex 라운드 1 (M=5/A=5/Q1~Q7) → 라운드 2 (R2-1~5/M=4) → 본 세션 N1/N2 모두 정정 후 release
- 누적 정정 trail 14건 (라운드 1 5건 + 라운드 2 9건 + N1/N2 2건) 모두 실코드 반영

**결정 (FE 패턴 표준 5건)**:
1. **DUAL 모델 추론**: `model.toUpperCase().split(RegExp(r'[\s\-]')).contains('DUAL')` — 'DUAL-300' / 'GAIA-DUAL-X' 같은 prefix/substring 충돌 차단. Sprint 59-BE `'DUAL' in model.upper().split()` 패턴 정합 + Dart RegExp 으로 하이픈도 split.
2. **DUAL 도면 qr_doc_id 정책**: `_qrDocIdForItem` 의 `requiresLrHint = (scope=='DRAGON' && type=='INPUT' && _isDualModel)` — DRAGON+INPUT+DUAL 만 hint 강제, 도면 항목은 SINGLE-style fallback. ArgumentError 안전망으로 누락 시 명시적 throw.
3. **judgment_phase 토글 권한**: `is_manager OR is_admin` 만 2차 토글 노출 — 일반 작업자는 1차 고정 (잘못된 record 생성 차단).
4. **debounce 500ms + 번들 PUT**: `_debouncedUpsert` per-master Timer + check_result + selected_value + input_value 항상 동시 전송 (BE upsert_mech_check check_result 필수 정합).
5. **WebSocket alert 처리 패턴**: `_handleNewAlert` 가 alert_type 무관 자동 state 등록 + `_handleAlertTap` 이 alert_type 별 화면 분기 (TM/MECH 같은 패턴). 즉시 토스트 X, 알림 목록 + 탭 시 진입.

**결과**:
- pytest test_mech_checklist 24/24 PASS (21 기존 + 3 신규 R2-1 회귀)
- +1,038 LoC (BE 18 + FE 844 + 라우팅 6 + alert 21 + pytest 47 + doc)
- 회귀 영향 0건

**적용 가능 영역**:
- 향후 PI/QI/SI Flutter UI 도입 시 동일 패턴 (`_isDualModel` split / role gate / debounce / alert 분기)
- DUAL 분기 코드의 표준 — `RegExp(r'[\s\-]').contains('DUAL')`

---

### ADR-020: Sprint 63-BE MECH 체크리스트 + qr_doc_id 공유 normalizer 표준 (2026-05-04, v2.11.0)

**맥락**:
- TM(Sprint 52) / ELEC(Sprint 57) 후 MECH 자주검사 체크리스트 디지털화 (양식 73 항목 / 20 그룹)
- Sprint 59-BE 사례: TM SINGLE 분기가 `qr_doc_id=''` 하드코딩 → LEFT JOIN 매칭 실패
- Codex 라운드 1+2+3 합의 (M=10 / A=11 / 추가 11) — 핵심 통찰 "설계서 정정 ≠ 실코드 미구현"

**결정**:
1. **schema 패턴 (재사용 가능)**: `scope_rule` (모델 분기 매크로) + `trigger_task_id` (1차 입력 토스트 발화 시점) + `item_type` enum 'INPUT' 추가 — 향후 다른 카테고리 도입 시 동일 패턴 활용
2. **qr_doc_id 공유 normalizer**: `_normalize_qr_doc_id(serial_number, hint)` 표준 함수 — TM/ELEC/MECH 모두 사용. SINGLE='DOC_{S/N}', DUAL='DOC_{S/N}-L|R' 일관 처리
3. **public 인터페이스 통일**: `check_tm_completion` / `check_elec_completion` / `check_mech_completion` 모두 public (private `_` prefix 제거)
4. **judgment_phase=2 (c)안**: 1차 record 강제 안 함 — 관리자가 phase=2 record 만으로 cover 가능 (작업자 미체크 시 관리자가 직접 입력)
5. **Python helper 우선**: stored function `_is_in_scope` 보류 → Python helper `_resolve_active_master_ids()` 채택 (단순성 + migration 부담 0)

**결과**:
- pytest 21/21 PASS (186.84s) ✅
- +1,415 LoC (BE only, 회귀 영향 0건)
- branch sprint-63-be-mech-checklist 11 commits squash merge → main v2.11.0
- migration 051/051a Railway 자동 적용 예정

**잔존 + 후속**:
- ELEC 의 `qr_doc_id=''` 하드코딩 (운영 record 31건) → 별 sprint `FIX-ELEC-QR-DOC-ID-HARDCODE-20260502` (P2)
- Sprint 63-FE: `mech_checklist_screen.dart` 신규 (~1,000~1,200 LoC, 2~3d)
- AXIS-VIEW Sprint 39: BLUR 해제 + AddModal 토글 (별 repo, 0.5d)

**적용 가능 영역**:
- 향후 PI/QI/SI 체크리스트 도입 시 동일 schema 패턴 (`scope_rule` + `trigger_task_id` + `item_type` 3종)
- `_normalize_qr_doc_id()` 는 모든 SINGLE/DUAL 모델 분기 코드의 표준 진입점

---



### ADR-001: FK CASCADE → RESTRICT 전환 (2026-03-15)
- **맥락**: 초기 migration(001-005)이 전부 CASCADE로 생성됨. worker 삭제 시 출퇴근/작업이력 전부 소실 위험
- **결정**: worker FK는 RESTRICT 또는 SET NULL로 전환
- **현황**: migration 023(qr_doc_id, serial_number), 024(work_start/completion_log, hr 테이블), 025(serial_number) 완료
- **잔존**: 001(email_verification→CASCADE), 005(offline_sync_queue, location_history→CASCADE), 018(refresh_tokens→CASCADE)
- **잔존 리스크**: 낮음 — email_verification, sync_queue, refresh_tokens는 일시적 데이터로 CASCADE 적절

### ADR-002: 테스트 DB 분리 (2026-03-26)
- **맥락**: Railway 운영 DB 하나에서 테스트+운영 동시 수행 → conftest.py가 운영 데이터 접근
- **결정**: `TEST_DATABASE_URL` 환경변수 분리 + `.env.test` 자동 로딩
- **결과**: Sprint 39 완료. regression 118건→0건 해결

### ADR-003: app_access_log 30일 보관 → last_login_at 컬럼 (2026-03-27)
- **맥락**: 비활성 사용자 감지에 app_access_log 사용하려 했으나 30일 보관 한계
- **결정**: workers 테이블에 `last_login_at` 컬럼 추가 (migration 040)
- **결과**: 로그인 시 auth_service.py가 last_login_at 갱신. 30일 미로그인 = 비활성 후보

### ADR-004: Soft Delete 패턴 — is_active (2026-03-27)
- **맥락**: 퇴사/비활성 사용자 처리. 물리 삭제 시 FK RESTRICT로 삭제 불가 + 이력 소실
- **결정**: `workers.is_active BOOLEAN DEFAULT TRUE` + `deactivated_at TIMESTAMPTZ`
- **결과**: Sprint 40-C 완료. login 시 is_active 체크, admin 승인 후 비활성화

### ADR-005: admin.py 모놀리스 유지 결정 (2026-03-29, 감사 리뷰)
- **맥락**: admin.py 2,352줄. worker/attendance/settings/kpi 서비스 미분리
- **결정**: 당장 분리하지 않음. APS Lite 작업이 더 시급. 분리는 체크리스트 BE Sprint 때 함께 진행
- **리스크**: 중간. 새 기능 추가 시 충돌 가능성 증가

### ADR-006: WebSocket flask-sock 전환 (2026-03-08)
- **맥락**: Flask-SocketIO 프로토콜 불일치 (BUG-2)
- **결정**: flask-sock(raw WebSocket) 마이그레이션. events.py 전체 리라이트
- **결과**: Sprint 13 완료. FE 변경 0건

### ADR-007: checklist 스키마 확장 방향 (2026-03-26)
- **맥락**: 기존 단순 item_name 기반 → 실제 MECH 양식은 20그룹 60항목 + CHECK/INPUT 구분
- **결정**: item_type(CHECK/INPUT) + inspection_group + spec_criteria 컬럼 추가. BOM 기반은 보류
- **선행조건**: ELEC 양식 수집 완료 후 진행
- **설계 원칙**: 대시보드 중심 관리 (코드 레벨 조건부 로직 사용 안 함)

### ADR-008: 작업 릴레이 — finalize 파라미터 분리 (2026-03-30)
- **맥락**: 판넬작업 등 1개 task를 여러 작업자가 순차 교대. 유저1이 종료하면 재시작 불가
- **결정**: complete_work()에 `finalize: bool = True` 추가. False="내 작업 종료"(task 열린 상태), True="작업 완료"(기존 동작)
- **결과**: Sprint 41 구현. 릴레이 재시작 허용(_worker_already_completed_task 체크), _all_workers_completed COUNT(DISTINCT worker_id) 버그 수정
- **하위 호환**: finalize 미전달 시 True → 기존 FE 정상 동작

### ADR-009: Manager 재활성화 — VIEW에 배치 (2026-03-30)
- **맥락**: 실수로 완료된 task 복구 기능. APP에 넣으면 현장 작업자 실수 리스크
- **결정**: VIEW 생산현황 S/N 디테일 ProcessStepCard worker 행 단위에 배치
- **정합성**: reactivate 시 completed_at/started_at/worker_id NULL + completion_status 롤백 + production_confirm soft-delete
- **권한**: is_manager || is_admin → canReactivate 단일 prop
- **task_detail_id**: BE 수정 불필요. SNDetailPanel 병합 시 t.id 주입으로 해결

### ADR-010: Partner → Company 매핑 규칙 및 알림 분기 참조 (2026-04-02)

#### 배경
product_info의 partner 컬럼(mech_partner, elec_partner, module_outsourcing)과 workers.company 사이에 매핑 규칙이 존재. TMS만 특수 케이스(회사 하나가 기구/전장/모듈 3역할 분리).
완료 알림이 `get_managers_for_role('MECH')` 등으로 전체 role에 발송하고 있었으나, 실제 의도는 해당 S/N의 partner 회사 매니저에게만 발송.

#### partner → company 매핑

| partner_field | partner값 | workers.company | 비고 |
|---|---|---|---|
| mech_partner | TMS | TMS(M) | 기구 담당 |
| mech_partner | FNI | FNI | 그대로 |
| mech_partner | BAT | BAT | 그대로 |
| elec_partner | TMS | TMS(E) | 전장 담당 |
| elec_partner | P&S | P&S | 그대로 |
| elec_partner | C&A | C&A | 그대로 |
| module_outsourcing | TMS | TMS(M) | 모듈 조립 담당 |

#### 공정 흐름 및 알림 트리거

```
TM ──(가압완료)──▶ MECH ──(도킹완료)──▶ ELEC ──(자주검사완료)──▶ PI ──▶ QI ──▶ SI
     trigger①         trigger②              trigger③
```

- trigger①: TMS 완료 → mech_partner company 매니저 (mech_partner=module_outsourcing 회사면 스킵)
- trigger②: MECH TANK_DOCKING 완료 → elec_partner company 매니저
- trigger③: ELEC 자주검사 전체 완료 → PI 매니저 (GST)
- CHECKLIST_TM_READY: TMS TANK_MODULE 완료(비매니저) → module_outsourcing company 매니저
- 각 트리거는 admin_settings on/off로 제어

#### 코드 참조 위치 (이 매핑을 사용하는 곳)

| 파일 | 라인 | 용도 | 방향 |
|------|------|------|------|
| `services/task_seed.py` | L495-600 | task 가시성 분기 (QR 스캔 시 어떤 task를 보여줄지) | company → partner |
| `services/progress_service.py` | L196-224 | 진행현황 조회 필터 (S/N 목록 조회) | company → partner |
| `routes/work.py` | L250-280 | 재활성화 권한 체크 | company → partner (접미사 제거) |
| `services/task_service.py` | L414-488 | 완료 알림 트리거 (**수정 대상**) | partner → company (신규) |
| `services/task_service.py` | L543-605 | CHECKLIST_TM_READY 알림 (**수정 대상**) | partner → company (신규) |

#### 결정
- 알림 트리거에서 `get_managers_for_role(role)` → `get_managers_by_partner(serial_number, partner_field)` 신규 함수로 교체
- 역방향 매핑 함수 `_partner_to_company(partner_value, partner_field)` 도입
- TMS 특수 케이스: mech_partner/module_outsourcing → TMS(M), elec_partner → TMS(E)
- 기타 회사: partner값 = company값 (FNI, BAT, P&S, C&A)

### ADR-011: Friday-based 주차→월 매핑 (2026-04-06)
- **맥락**: monthly-summary에서 W14(3/30~4/5)가 월요일 기준으로 3월에 배정되는 문제. 생산 현장은 금요일이 주의 마지막이므로 금요일 기준이 자연스러움
- **결정**: `friday = start_date + timedelta(days=4)` → friday의 month = 주차 소속 월
- **적용 범위**: VIEW 월별 조회 전용. 기존 `confirmed_month` 데이터는 변경 없음 (실적 처리는 주차 페이지에서)
- **한국 연휴**: 무관 — 캘린더 날짜 고정이므로 연휴 조건 불필요
- **참조**: `AGENT_TEAM_LAUNCH.md` Sprint 53, `OPS_API_REQUESTS.md` #53

### ADR-012: 개인정보 동의 — 필수/선택 분리 + 파견법 대응 (2026-04-06)
- **맥락**: 개인정보보호법 §15/§17/§21 준수 + 파견법 리스크(시스템 알림 ≠ 업무 명령) 대응 필요. 협력사 작업자 포함
- **결정**:
  - 이용약관 + 개인정보 수집·이용 = **필수 동의** (철회 = 탈퇴)
  - 제3자 제공 = **선택 동의** (토글로 철회 가능)
  - 최초 동의 = Blocking 팝업 (로그인 시 강제)
  - 설정 관리 = Non-blocking 토글 (profile_screen)
- **DB**: `terms_agreed_at`, `terms_version`, `privacy_agreed_at` on workers + 선택적 `third_party_agreed_at`
- **파견법 문구**: "본 시스템은 공정 현황 공유를 위한 도구이며, 시스템 알림은 업무 명령이 아닌 현장 상태 정보 공유"
- **보류 사항**: 제3자 제공 해당 여부 법적 검토, `consent_history` 이력 테이블
- **참조**: `AGENT_TEAM_LAUNCH.md` BACKLOG, `G-AXIS_앱_이용동의_화면명세.docx`

### ADR-013: analytics 스키마 = WH 분석 결과 적재소 + CT 분석 확장 (2026-04-07)
- **맥락**: `analytics` 스키마에 defect 가공 결과만 4개 테이블 존재. CT(Cycle Time) 분석 결과를 어디에 넣을지 결정 필요. 별도 `ct` 스키마 vs `analytics` 확장
- **결정**:
  - `analytics` 스키마는 **WH(Warehouse) 역할** — 각 도메인의 가공/분석 결과를 적재하는 곳
  - CT 분석 테이블은 `analytics` 스키마에 `ct_` prefix로 추가
  - 스키마 추가하지 않음 (8개 유지)
  - 원본 데이터는 각 도메인 스키마에 유지 (`public.app_task_details`, `hr.partner_attendance` 등)
- **네이밍 규칙**: `analytics.{도메인}_{내용}` — 예: `analytics.ct_task_realtime`, `analytics.defect_statistics`
- **설정값 위치**: 근무 스케줄(휴식/식사), 공수 기준(8H/440분) → `public.admin_settings` key-value 활용 (별도 테이블 생성 금지)
- **BE 모듈 구조**: `analytics_prod_service.py` + `analytics_prod.py` (route) — 분리 모듈로, 향후 서버 분리 시 떼어내기 용이
- **참조**: `sql/elec_realtime_analysis.sql` (프로토타입 쿼리)

- **스키마 맵 상세**: `DB_SCHEMA_MAP.md` 참조 (8개 스키마, 43개 테이블, FK 관계도 포함)

### ADR-014: resume 권한 — 다중작업자 동료 허용 → Sprint 55에서 제거 예정 (2026-04-07, BUG-6)
- **맥락**: Partner 회사(FNI, C&A) 다중작업자 task에서 동료가 resume 시 403 FORBIDDEN 발생
- **임시 수정 (배포 완료)**: `_worker_has_started_task` 조건 추가 — 같은 task 참여자도 resume 허용
- **최종 방향 (Sprint 55)**: worker별 독립 pause/resume로 전환 → 동료 resume 자체가 불필요해짐 (본인 pause만 본인이 resume)
- **참조**: `BUG-6_ANALYSIS.md`, `test_pause_resume.py` TC-PR-19~22

### ADR-015: Worker별 Pause + Auto-Finalize + FINAL task 릴레이 불가 (2026-04-07)
- **맥락**: task 단위 pause로는 개인별 작업시간 산출 불가 (CT 오차 최대 80%). 전원 릴레이 종료 시 task 미완료 (progress 0%). FINAL task(자주검사) 릴레이 시 자동 마감 트리거 미발동
- **결정 3가지**:
  1. **worker별 pause**: `work_pause_log`에 이미 worker_id 존재, DB 변경 없이 로직만 변경. `task.is_paused` = 전원 paused일 때만 true (하위호환)
  2. **auto-finalize**: `complete_work(finalize=false)`에서 전원 completion_log 도달 시 즉시 finalize. 스케줄러 지연 없이 실시간 progress
  3. **FINAL task 릴레이 불가**: `FINAL_TASK_IDS`(자주검사, 가압검사 등) → `finalize=true` 강제. 자주검사는 관리자 선언 행위이므로 릴레이 개념 부적합
- **work_completion_log 현황**: 다중작업자 task에서 completers=1 (현장에서 대표 1명만 완료 누름). 코드상 개인별 기록 지원 확인 (`_record_completion_log`). auto-finalize로 전원 completion_log 자연 수집
- **APS 연결**: 개인별 net_minutes → 표준공수 산출 → APS Lite 자원 배정 기초
- **참조**: Sprint 55 (AGENT_TEAM_LAUNCH.md), `SPRINT_WORKER_PAUSE.md` (설계 원본)

### ADR-018: 강제종료 응답 필드 바인딩 — 옵션 C' (모델 필드 + LEFT JOIN) 채택 (2026-04-17, HOTFIX-04)
- **맥락**: HOTFIX-04에서 `closed_by_name`(관리자 이름)을 API 응답에 노출해야 하는데, `_task_to_dict()` 단일 task 변환 함수에서는 `worker_map` 캐시 접근 불가
- **대안 3가지**:
  - 원안 (기각): `_task_to_dict()` 내부 `_lookup_worker_name(closed_by)` 호출 — worker_map 접근 불가로 구현 불가
  - 옵션 A (Codex 1차 권고, 반려): 후처리 루프에서 `worker_map`으로 `closed_by_name` 주입 — 단기 해법. 새 응답 경로마다 루프 복제 필요, 누락 시 `closed_by_name=None` 가비지 위험
  - **옵션 C' (채택)**: `TaskDetail` dataclass에 `closed_by_name: Optional[str]` 런타임 필드 추가 + `get_tasks_by_serial_number()`·`get_tasks_by_qr_doc_id()` SELECT에 `LEFT JOIN workers` 추가 → 모델 단계 바인딩으로 어떤 응답 경로에서도 자동 일관
- **선택 근거 (장기 시스템 원칙, APS-Lite 타겟)**:
  - 새 API 엔드포인트 추가 시 모델 변경 없이 쿼리만 JOIN 추가하면 됨
  - 타 조회 경로(scheduler, admin 통계, checklist 등) 쿼리 미변경 시에도 `closed_by_name=None`로 자동 backward-compat (LEFT JOIN 특성)
  - `SELECT *` → `SELECT td.*, w.name AS closed_by_name` — `td.*`로 기존 컬럼 전체 보존
- **M1 COALESCE(duration_minutes) 미반영 (옵션 α)**: Orphan worker 실제 작업시간 관측 불가. `td.duration_minutes` fallback 시 복수 orphan에서 N배 부풀림 → garbage data. `wcl.duration_minutes` NULL 유지로 SUM 집계 자연 제외
- **A1 TC 추가**: TC-FORCECLOSE-NS-03(혼재) / NS-04(legacy backward-compat) / NS-05(Case 1+2 경계 중첩)
- **A2 worker_ids 세트 확장 불필요**: 이름이 이미 모델 단계 바인딩되므로 `worker_map` 후처리 조회 대상에 `closed_by` 추가 불요
- **Codex 교차 검증**: 1차 옵션 A 권고 → Twin파파가 옵션 C'로 재확정 (장기 원칙). M1/M2 문서 정정 반영
- **참조**: HOTFIX-04 (AGENT_TEAM_LAUNCH.md L27112), BACKLOG.md HOTFIX-04, pytest `test_hotfix04_orphan.py` 9 TC GREEN

### ADR-017: 비활성 task 조회 필터 — 모델 레벨 (방안 A) 채택 (2026-04-17, HOTFIX-03)
- **맥락**: `is_applicable=FALSE` task가 조회 응답에 포함되어 VIEW 미시작 카운트 오염(Heating Jacket 사례). `filter_tasks_for_worker()`는 `task_category`만 필터하므로 모델 레벨에서 걸러야 함
- **대안 비교**:
  - **방안 A (채택)**: `get_tasks_by_serial_number()` + `get_tasks_by_qr_doc_id()` 4 SELECT 전체에 `AND is_applicable = TRUE` 추가. 단순·일관성·하위 호환
  - 방안 B: `?all=true` 파라미터 분기(관리자만 비활성 포함) — 현재 사용처 없어 YAGNI
  - 방안 C: 응답에 `is_applicable` 필드 포함하고 FE가 필터 — 양쪽 수정 + FE 부담
- **선택 근거**: 비활성 task는 DB에서 "해당 공정 건너뜀"으로 명시된 상태. 일반 조회에서 완전 제외가 업무 흐름상 자연스럽고, completion 판정(check_elec_completion 등)에서도 동일 처리가 일관성 있음. 관리자 설정 확인은 OPS 설정 페이지에서 수행
- **확장 여지**: 관리자용 전체 조회가 필요해지면 `?include_inactive=true` 파라미터(방안 C 축소판)로 확장 가능 — 당장은 도입하지 않음 (YAGNI)
- **영향 범위**: VIEW S/N 상세뷰 미시작 카운트 정상화 (FE 수정 불필요), OPS 앱 `all=true` 경로도 비활성 제외(의도), `filter_tasks_for_worker()` 후처리와 이중 필터되나 무해
- **참조**: AGENT_TEAM_LAUNCH.md HOTFIX-03 섹션, OPS_API_REQUESTS.md #60 DONE, BACKLOG.md HOTFIX-03

### ADR-016: 강제 종료 API 입력값 가드 — completed_at 범위 검증 (2026-04-17, BUG-45)
- **맥락**: VIEW `useForceClose.ts`가 `datetime-local` 입력으로 임의 시각 전달 가능. BE는 `datetime.fromisoformat()` 파싱 후 KST tz 보정만, 논리적 타당성(미래/started_at 이전) 검사 부재 → 음수 duration 위험
- **결정 4가지**:
  1. **미래 차단 + 60s clock skew 허용**: `completed_at > now_kst + timedelta(seconds=60)` → 400 `INVALID_COMPLETED_AT_FUTURE`. NTP/브라우저 시계 오차 커버 (30s는 false positive 위험, 5분은 너무 관대)
  2. **started_at 이전 차단**: `started_at != None and completed_at < started_at` → 400 `INVALID_COMPLETED_AT_BEFORE_START`. NOT_STARTED task(started_at=NULL)는 미래 검증만 적용
  3. **`==` 경계 허용**: `<`만 차단 = 0분 task 허용. 기존 NOT_STARTED 경로(`duration=0`)와 일관성
  4. **force_complete_task() 동일 가드는 Advisory**: OPS/VIEW 어디에서도 호출 안 하는 미사용 엔드포인트 → 1차 Must 범위에서 제외
- **계약 정합성**: VIEW `useForceClose.ts`가 `reason` 키로 전송하던 BUG는 OPS와 BE 계약(`close_reason`)에 맞춰 정정. 하위 호환 미지원 (전수 grep 결과 OPS는 `close_reason`만 사용)
- **참조**: BUG-45 (AGENT_TEAM_LAUNCH.md L28138), HANDOVER_FULL.md 3-6 섹션, Codex 1차 보정 합의 (force_complete → Advisory 하향, 테스트 경로 정정, TC 번호 `TC-FC-11~18` 사용)

---

## 2. 시스템 감사 결과 (2026-03-29 재검토)

### 점수카드
| 영역 | 점수 | 비고 |
|------|------|------|
| OPS BE | 6.4/10 | 소폭 개선 (6.25→6.4) |
| VIEW FE | 5.9/10 | 소폭 개선 (5.8→5.9) |

### 해결된 항목 (6건)
1. ✅ DB Connection Pool (Sprint 30, 33파일 175건)
2. ✅ FK CASCADE→RESTRICT (migration 023-025)
3. ✅ 테스트 DB 분리 (Sprint 39)
4. ✅ Logout Storm 수정 (Sprint 25, 3중 방어)
5. ✅ Refresh Token Rotation (Sprint 19-A/B)
6. ✅ QR 카메라 안정화 (BUG-5~BUG-29, 20회+ 수정)

### 미해결 이슈 (10건, 우선순위 순)
1. 🔴 **CORS `origins="*"` 전면 개방** — `__init__.py` 라인 41-44. 운영 환경에서 도메인 제한 필요
2. 🔴 **JWT_SECRET_KEY 하드코딩 dev 기본값** — config.py. 환경변수로 분리 필요
3. 🟠 **admin.py 모놀리스** (2,352줄) — 서비스 레이어 미분리
4. 🟠 **UnitOfWork 패턴 부재** — raw conn.commit/rollback 직접 호출
5. 🟠 **Down migration 없음** — 32개 migration 전부 UP only
6. 🟡 **work_site/product_line CHECK 제약** (mig 017) — enum 권장
7. 🟡 **quantity VARCHAR(50)** (mig 002) — NUMERIC 타입 권장
8. 🟡 **VIEW FE 테스트 2개뿐** — vitest 설치됨 but 테스트 부재
9. 🟡 **React.lazy/Suspense 미사용** — 코드 스플리팅 없음
10. 🟡 **ChartSection.tsx 하드코딩 색상** — GxColors 디자인 토큰 존재하나 미적용

---

### ADR-019: Sentry + assertion 자동 감지 layer 도입 (2026-04-27, v2.10.8 ~ v2.10.10)

**배경**: 4-22 알람 silent failure (5일 52건 NULL) 사고. Migration 049 silent gap → logger.error 만으로는 5일간 무인지 → 사용자 직접 신고로 발견. 외부 자동 감지 layer 부재가 사고 인지 시간을 좌우.

**의사결정**:
1. **Sentry 정식 연동** (OBSERV-ALERT-SILENT-FAIL):
   - `sentry-sdk[flask]>=2.0` requirements 정식 추가
   - `_init_sentry()` 함수 (~50 LOC) — DSN env 없으면 graceful skip (로컬/test 호환)
   - `FlaskIntegration` (HTTP exception) + `LoggingIntegration` (INFO breadcrumb / ERROR event capture)
   - `release` 자동 binding (version.py) + `send_default_pii=False` (PII 보호)
   - 환경변수: `SENTRY_DSN` (필수) + `SENTRY_ENVIRONMENT` (기본 production) + `SENTRY_TRACES_SAMPLE_RATE` (기본 0.0)

2. **migration sync assertion** (OBSERV-MIGRATION-RUNNER-STARTUP-ASSERTION):
   - `assert_migrations_in_sync()` 함수 (~40 LOC) — disk(코드) vs DB(`migration_history`) 동기화 검증
   - `not_yet_applied` 발견 시 `logger.error` + `sentry_sdk.capture_message` (외부 즉시 알림)
   - `run_migrations()` 직후 호출
   - **outer try/except 안전망 표준**: assertion 자체 실패가 worker boot 막지 않도록 (HOTFIX-07 lesson)

3. **log level 정확화** (OBSERV-RAILWAY-LOG-LEVEL-MAPPING):
   - `logging.basicConfig(stream=sys.stdout, force=True)` 명시 (기본 stderr 금지)
   - `Procfile` `--access-logfile=- --log-level=info` 추가
   - Python `logger.info()` 가 Railway 에서 `level: error` 잘못 태깅되던 문제 해소 → Sentry alert rule `level=error` 필터 정확 작동

**가치 입증 (도입 당일 + 8시간)**:
- 1차 — HOTFIX-07 (v2.10.9): assertion 첫 호출 시 `_get_executed()` `row[0]` KeyError 노출. 5일간 silent 흡수된 잠재 버그가 try/except 없는 경로에서 즉시 발견
- 2차 — HOTFIX-08 (v2.10.10): assertion 이 `046a_elec_checklist_seed.sql` silent gap (4-22 049 와 동일 Docker artifact 두 번째 사례) 자동 캡처 → db_pool transaction 정리 누락 + 046a 자동 적용. ON CONFLICT idempotent 로 사용자 영향 0
- 3차 — FIX-PROCESS-VALIDATOR-TMS-ROLE-MAPPING (BACKLOG L352, BE Sprint 예정): Sentry DSN 활성화 후 8시간 만에 매시간 cron 의 `Failed to get managers for role=TMS: invalid input value for enum role_enum: "TMS"` 31 events 자동 감지. 4-22 HOTFIX-ALERT-SCHEDULER-DELIVERY 가 scheduler 3곳만 수정하고 process_validator/duration_validator 의 enum cast 잠재 위험은 그대로 남았던 잔존 silent failure (TMS 매니저 UNFINISHED_AT_CLOSING 알람 미수신, 일 ~240건 / 주 ~1680건 silent skip). LoggingIntegration ERROR event capture 가 가설 검증 layer 가 아닌 **실제 운영 잔존 사고를 직접 발견** 한 첫 사례 — Sentry 가치 입증 = assertion 가치 입증 layer 의 외부 확장 성공
- **4차 — HOTFIX-ELEC-CHECKLIST-PLACEHOLDER-DEACTIVATE (v2.14.3, 2026-05-13)**: HOTFIX-08 (v2.10.10, 4-27 21:36:04) 부수 효과의 늦은 catch 사례. assertion + Sentry 가 silent gap 자체는 자동 캡처했으나, **046a 가 placeholder seed 파일 (제대로 된 seed 아님) 이라는 점은 자동 감지 layer 가 못 잡음** — 047 의 DELETE→정상 INSERT 이후 046a 재적용 시 UNIQUE 제약 회피 (item_name 불일치) 로 placeholder 31건 신규 INSERT 됨. 2026-05-13 사용자가 운영 화면에서 'Jig 검사 항목 1~7' 표시 직접 발견 → 진단 SQL 4건으로 root cause 확정 → migration 055 (soft delete) + 046a 본문 교체 (047 정상 31항목 + ON CONFLICT) 적용. **교훈**: assertion 은 "file applied or not" 만 자동 감지 — "file contents are correct" 는 잡지 못함. 동일 ON CONFLICT idempotent 패턴이라도 UNIQUE 키 정합성이 깨지면 사용자 영향 0 보장 X. 향후 placeholder/draft seed 파일 정책: ① 파일명에 `_placeholder.sql` suffix 명시 ② migration_runner 가 suffix 감지 시 적용 skip ③ 정식 seed 와 별도 디렉토리 분리.

**Before / After**:
```
Before (4-22 사고): silent gap → 5일 무인지 → 사용자 신고
After (4-27+):       silent gap → assertion 즉시 → Sentry email/push
                     평균 인지 시간: 5일 → ~1분
```

**시스템 신뢰성 1차 완성** — assertion + LoggingIntegration + FlaskIntegration = 외부 자동 감지 layer 가동.

**파생 표준 (lesson 흡수)**:
- 신규 assertion 도입 시 outer try/except 안전망 필수 (HOTFIX-07 재발 방지)
- psycopg2 `RealDictCursor` 환경에서는 `row['column_name']` 접근만 사용 (`row[0]` 금지)
- 풀에 conn 반납 전 SELECT 후 `conn.rollback()` 표준 (INTRANS 상태 회피, HOTFIX-08 재발 방지)

**Twin파파 측 활성화 완료 (2026-04-27)**:
- ✅ sentry.io 가입 + Python/Flask project 생성 + DSN 발급
- ✅ Railway env 등록: `SENTRY_DSN` / `SENTRY_ENVIRONMENT` / `SENTRY_TRACES_SAMPLE_RATE`
- 🟡 alert rule 미세 조정 (1주 운영 후 노이즈 비율 기반)

**산출물 trail**:
- `POST_MORTEM_MIGRATION_049.md` (4가지 가설 검증, 가설 ④ Docker artifact 가장 유력)
- CHANGELOG v2.10.8 / v2.10.9 / v2.10.10 entry
- BACKLOG: POST-REVIEW-MIGRATION-049 / OBSERV-ALERT-SILENT-FAIL / OBSERV-MIGRATION-RUNNER-STARTUP-ASSERTION / OBSERV-RAILWAY-LOG-LEVEL-MAPPING 4건 COMPLETED

---

## 3. APS Lite 데이터 준비도

### 5축 데이터 아키텍처 (2026-03-29 분석)

| 축 | 준비도 | AXIS 현황 | 필요 조치 |
|----|--------|-----------|-----------|
| 수요 (Demand) | 80% | product_info에 납기/수량 있음 | 우선순위 가중치 미정의 |
| 공정능력 (Capacity) | 90% | duration_minutes로 역산 가능 | 전용 standard_manhour 테이블 부재 |
| 자재 (Material) | **0%** | AXIS에 전혀 없음 | SAP MM 또는 구매팀 엑셀에서 수급 |
| 캘린더/인력 (Calendar) | 50% | partner_attendance 있음, 공장 캘린더 없음 | factory_calendar 테이블 설계 필요 |
| 공정 제약 (Constraint) | 30% | completion_status 선후관계 있음 | 명시적 dependency 테이블 없음 |

### 식별된 데이터 Gap (5건)
1. **PartnerEvaluation BE 부재** — VIEW UI mockup만 존재 (EvalRow 인터페이스). BE 테이블/API 없음
2. **표준공수 테이블 부재** — duration_minutes 역산은 가능하나 plan.standard_manhour 부재
3. **납기준수율 미정의** — KPI 산식/기준 없음
4. **자재 데이터 0%** — 입고예정일, 가용상태, 리드타임 전무
5. **공장 캘린더 부재** — factory_calendar(date, is_working, shift_hours, note) 필요

### 권고 Phase 수정 (2026-03-29)
- **기존**: Phase 1(사내서버+SAP) → Phase 2(APS 엔진)
- **수정**: Phase 0(데이터 축적) → Phase 1(APS 엔진, 현재 인프라) → Phase 2(사내서버+SAP RFC) → Phase 3(고도화)
- **이유**: 사내서버 마이그레이션 없이도 APS 엔진 개발/검증 가능. 데이터 축적이 먼저

---

## 4. ETL 변경이력 패턴 (2026-03-29 분석)

- **14일간 659건**, 일 평균 47건
- **빈도 순위**: 출하예정(175) > 가압시작(148) > 마무리계획(93)
- **O/N 종속 캐스케이드**: 동일 O/N(예: 6590)의 복수 S/N(GBWS-6889, 6890)이 동일 패턴(-9d, -6d)으로 변경
- **시사점**: APS에서 O/N 단위 일괄 조정 로직 필요. 개별 S/N 단위로만 관리하면 불일치 발생

---

## 5. 코드베이스 수치 (2026-03-29 기준)

### OPS BE
- **총 라인**: ~18,600줄
- **Routes**: 15파일 8,123줄 (admin.py 2,352줄 = 29%)
- **Services**: 11파일 4,868줄
- **Models**: 14파일 4,289줄
- **Migrations**: 32파일 (001-032 + 040-041, 번호 공백 011-016)
- **테스트**: 최근 기준 667+ passed

### OPS FE (Flutter)
- PWA 배포: gaxis-ops.netlify.app
- QR 카메라: html5-qrcode JS interop (BUG-5~29, 20회+ 수정 이력)
- 버전: v2.1.0

### VIEW FE (React)
- 19개 페이지
- 테스트: 2개 파일만 (productionFilters.test.ts, production.test.ts)
- vitest ^4.1.0 + @testing-library/react 설치됨

---

## 6. 반복 실수 방지

### QR 카메라 수정 금지 사항
- MutationObserver 로직 건드리지 말 것
- `_forceSquareAfterCameraStart` 건드리지 말 것
- CSS `aspect-ratio:1/1 !important` 건드리지 말 것
- qrbox 정수값과 cameraSize clamp 범위만 변경 가능
- **이력**: BUG-5~BUG-29까지 20회+ 수정. 매번 다른 환경(iOS Safari, Android Chrome, Desktop)에서 재발

### QR 명판 인식 개선 — 미완료 (2026-03-30)
- **현황**: qrbox 160→200 적용 완료. 스티커 QR 인식률 향상 확인. 명판 QR은 접사 포커싱 문제 잔존
- **원인**: html5-qrcode가 매크로 포커스 미지원. 폰 기본 카메라는 오토포커스+매크로로 정상 인식
- **시도 실패**: `advanced: [{focusMode: continuous}]`를 constraints에 넣으면 facingMode를 덮어써서 셀프 카메라로 전환됨 → 원복
- **해결 방향**: 카메라 start() 후 MediaStreamTrack.applyConstraints()로 focusMode 별도 설정 필요. html5-qrcode 내부 track 접근 방법 조사 필요
- **참조**: OPS_API_REQUESTS.md #47

### conftest.py 운영 데이터 보호
- workers, hr.worker_auth_settings, hr.partner_attendance, qr_registry, plan.product_info — 백업/복원 구현됨
- `ALTER TABLE` 실행 전 반드시 수동 pg_dump

### task_seed.py 주의사항
- migration 미적용 상태에서 silent fail 발생 이력 있음 (BUG-24)
- schema_check.py ensure_schema()가 앱 시작 시 자동 검증

### completion 함수 인터페이스 리팩토링 계획 (2026-04-13)
- **현재**: TM = `_check_tm_completion()` (private), ELEC = `check_elec_completion()` (public). 네이밍/접근수준 불일치
- **결정**: 지금은 private 그대로 import해서 사용. MECH 체크리스트 추가 시점에 TM/ELEC/MECH completion 함수를 공개(public) 인터페이스로 일괄 정리
- **사유**: 현재 wrapper 만들면 MECH 추가 시 또 수정 대상만 늘어남. 3개 공정 확정된 시점에 한번에 정리가 효율적
- **참조 위치**: `_check_sn_checklist_complete()` in `production.py` (Sprint 58-BE Task 2)

### ELEC 체크리스트 완료 기준 확정 (2026-04-13, Sprint 58-BE 완료 2026-04-14)
- **완료 기준**: Phase 1 (1차배선) + Phase 2 (2차배선) = **41건** 전체 완료
- Phase 1: PANEL 11 + 조립 6 = 17건 (JIG 제외)
- Phase 2: PANEL 11 + 조립 6 + JIG WORKER 7 = 24건
- QI 항목 (7건, checker_role='QI') 항상 제외 — GST 공정 체크이므로 협력사 실적과 무관
- **동적 COUNT**: 마스터 테이블 `is_active=TRUE AND checker_role!='QI'` 기준. VIEW에서 항목 추가/삭제 시 자동 반영
- **아이템 타입 분포**:
  - PANEL 검사: CHECK 다수 + SELECT 1건 (TUBE 종류 3가지 중 선택)
  - 조립 검사: CHECK
  - JIG 검사: CHECK만
- **해결 이력**: Sprint 58-BE에서 수정 완료. check_elec_completion()이 Phase 1(JIG 제외) + Phase 2(전체 WORKER) 각각 확인 → 둘 다 완료 시 True

### confirmable 판정 구조 (2026-04-13)
- **토글 OFF** (confirm_checklist_required=false): confirmable = progress 100% (기존)
- **토글 ON** (confirm_checklist_required=true): confirmable = progress 100% + 체크리스트 완료
- `_is_process_confirmable()` (production.py): progress 체크는 `_CONFIRM_TASK_FILTER` 기반. ELEC은 filter 미등록 → else 분기에서 카테고리 전체 체크 (정상 동작)
- 체크리스트 체크는 `_check_sn_checklist_complete()` 헬퍼로 분리. 공정별 분기 (TMS/ELEC/MECH)
- MECH: 체크리스트 BE 미구현 → `return True` (통과). 구현 시 분기 추가 필요
- **DB 확인 완료**: `admin_settings`에 `confirm_checklist_required` 키 존재. migration 불필요

---

## 7. 협력사 구조

| 코드 | 업종 | 공정 | 비고 |
|------|------|------|------|
| FNI | 기구 | MECH | PI 위임 코드 준비됨 (미적용) |
| BAT | 기구 | MECH | PI 위임 코드 준비됨 (미적용) |
| TMS(M) | 기구 | MECH + TMS | **PI 위임 적용 중** (pi_capable_mech_partners 설정) |
| TMS(E) | 전기 | ELEC | elec_partner 매칭 |
| P&S | 전기 | ELEC | elec_partner 매칭 |
| C&A | 전기 | ELEC | elec_partner 매칭 |
| GST | 자사 | PI/QI/SI/PM | 관리 + 자사 검사 공정 |

### 제품 모델
GAIA-I DUAL, DRAGON-V, GALLANT-III, MITHAS-II, SDS-100, SWS-200
- DUAL: L/R 분리 QR (migration 024-025)
- DRAGON: 전용 MECH 공정 + PI 위임 가능

---

## 8. 배포 환경

| 구성요소 | 환경 | URL |
|----------|------|-----|
| OPS BE | Railway (Flask) | axis-ops-api.up.railway.app |
| OPS FE | Netlify (PWA) | gaxis-ops.netlify.app |
| VIEW FE | (별도) | (AXIS-VIEW 참조) |
| DB | Railway PostgreSQL | 운영 DB 단일 인스턴스 |
| ETL | axis-core-etl repo | (별도) |

- Railway Pro: 자동 일일 백업 + 7일 보관
- CI/CD: 미구축 (GitHub Actions 예정)
