# 📋 OPS Weekly Plan — 2026-05-04 주 (월~금)

> 머릿속 부담 줄이기용 한 페이지 plan. BACKLOG.md / AGENT_TEAM_LAUNCH.md 의 상세 설계는 필요할 때만 열어보고, **평소엔 이 파일만 보면 됨**.
>
> 매일 아침 10초만 훑고 → 오늘 할 거 1~2개 골라서 진행 → 끝나면 ✅ 체크.
>
> 마지막 업데이트: 2026-05-04 (월) — Cowork 자동 생성 (월요일 첫 sync 시드). 이번 주 시작 — 회고 1~2줄 추가 권장. 지난 주 (2026-04-27 주) 회고는 WEEKLY_PLAN_20260427.md 참고.

---

## 🧭 한눈에 (현재 상태, 2026-05-04 월요일 마감)

```
현재 버전 : v2.11.4 (2026-05-06, main commit — Sprint 63 후속 hotfix 옵션 C UI 가이드 + description 렌더)
최근 작업 : ✅ v2.11.4 — Sprint 63 후속 hotfix (P0, FE only ~30 LoC). v2.11.3 R1 부작용 가시화 — 옵션 C 채택 (UI 가이드 + description 렌더, ELEC L898-909 패턴 정합). Codex 라운드 1 M=0 합의. ADR-023 신설 (ELEC 패턴 정확 검증 표준)
이전 트랙 : v2.11.3 R1 check_result null 차단 + R2 phase=2 read-only / v2.11.2 진입점 누락 hotfix / v2.11.1 Sprint 63-FE / v2.11.0 Sprint 63-BE / v2.10.17 HOTFIX-09
이전 트랙 : v2.11.0 Sprint 63-BE / v2.10.17 HOTFIX-09 / v2.10.16 watchdog / v2.10.15 access_log 90d / v2.10.14 KPI v2.4 / v2.10.13 묶음 / v2.10.12 DURATION_WARNINGS
진행 중   : (없음 — Sprint 63 종료)
대기 중   : push (퇴근 후 main + v2.11.0 + v2.11.1 + Netlify deploy) / AXIS-VIEW Sprint 39 (~0.5d, 별 repo) / BUG-TM-...-STALE-TC (P3, 1h)
```

→ 5-04 (월) **Sprint 63 전체 정식 종료** — 양식 73 항목 디지털화 + Flutter UI + qr_doc_id 공유 normalizer 표준 (ADR-020) + DUAL split-token 패턴 (ADR-021). 하루 안에 BE 인프라 + FE UI + Codex 라운드 1+2 + N1/N2 모두 완료.

---

## 🎯 이번 주 핵심 3가지

```
1. ✅ Sprint 63-BE MECH 체크리스트 BE 인프라 (5-04 v2.11.0 release)
2. ✅ Sprint 63-FE Flutter UI + R2-1 BE patch (5-04 v2.11.1 release) — 라운드 1+2+N1+N2 모두 정정
3. ⏳ AXIS-VIEW Sprint 39 BLUR 해제 + AddModal 토글 (5-05~08, 0.5d, 별 repo)
```

→ Sprint 63 OPS repo 전체 (BE + FE) 1일 만에 마무리. AXIS-VIEW 만 별 repo 잔존. 후속 잔존:
- Sprint 64-BE Tank Module Batch 3 endpoint (다음 주 또는 여유 시)
- FIX-ELEC-QR-DOC-ID-HARDCODE-20260502 (P2, 1h, Sprint 63-BE 후속 HOTFIX)
- Sentry 운영 1주 결과 검토 (5-04 이후 누적 검토)
- AUDIT-PWA-SW-INDEXEDDB-PRESERVE (PIN 후속, 30분)
- UX-LOGIN-FALLBACK-PIN-RESET-LINK (UX, 1h)
- Railway DB rotation / GitHub repo private (보안)

---

## ✅ 최근 완료 (지난 주, 2026-04-27 ~ 2026-05-01) — 11 배포

| 버전 | 일자 | 작업 | 비고 |
|:---:|:---:|:---|:---|
| v2.10.4 | 04-27 월 | Health 체크 안정화 | "시스템 오프라인" 오표시 해소 |
| v2.10.5 | 04-27 월 | FIX-PIN-FLAG-MIGRATION-SHAREDPREFS | PWA 업데이트 후 PIN 화면 손실 방지 (1차) |
| v2.10.6 | 04-27 월 | FEAT-PIN-STATUS-BACKEND-FALLBACK + OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP | PIN 자동 복구 + DB Pool 안정화 |
| v2.10.7 | 04-27 월 | HOTFIX-06 warmup 시계 리셋 1줄 | 후속 결함 즉시 fix |
| v2.10.8 | 04-27 월 | Sentry 정식 + assertion + log level 통합 | 알람 silent failure 사후 검증 |
| v2.10.9 | 04-27 월 | HOTFIX-07 RealDictCursor row[0] | assertion 도입 후속 |
| v2.10.10 | 04-27 월 | HOTFIX-08 db_pool transaction 정리 + 046a auto-apply | 잠재 버그 자동 발견 |
| v2.10.11 | 04-28 화 | FIX-PROCESS-VALIDATOR-TMS-MAPPING (옵션 D-2, 5 파일 atomic) | Sentry 가치 입증 #3 |
| v2.10.12 | 04-28 화 | FIX-26-DURATION-WARNINGS-FORWARD | BACKLOG L362 close |
| v2.10.13 | 04-28 화 | 묶음 (DB-POOL-DIRECT-FALLBACK-LOG-LEVEL + WEBSOCKET-STOPITERATION-SENTRY-NOISE) | 잡음 분리 |
| v2.10.14 | 04-28 화 | FIX-FACTORY-KPI-SHIPPED-V2.4-AMENDMENT | `_count_shipped` 보정 |
| v2.10.15 | 04-29 수 | FIX-ACCESS-LOG-RETENTION-90D | 1줄 |
| v2.10.16 | 04-30 목 | FIX-DB-POOL-WARMUP-WATCHDOG | watchdog log 격상 |
| v2.10.17 | 05-01 금 | HOTFIX-09 access_log cleanup `get_db_connection` import | 43일 silent failure 종결, Sentry 가치 입증 #4 |

> 지난 주 누적: **11 배포 / 사용자 영향 0건 / Sprint 14건+ COMPLETED / Sentry 가치 입증 4건**

---

## 🟡 대기 중 (외부 의존)

| 항목 | 블로커 | 해소 시 액션 |
|:---|:---|:---|
| **Sprint 64-BE Tank Module Batch** | VIEW Sprint 40 (v1.40.0) FE 완료, BE 동반 배포 대기 | OPS work.py + admin/tasks.py + 화이트리스트 검증 (3 endpoint: start-batch / complete-batch / tasks/by-order) |
| **Sentry 운영 1주 결과 검토** | 4-27 활성화 → 5-04 D+7 도달 | alert rule 노이즈 비율 평가 + Source Maps / Performance monitoring 도입 검토 |
| **Railway DB 자격증명 갱신** | 보안 일정 협의 | rotation 일정 확정 시 진행 |
| **GitHub repo private 전환** | 보안 일정 협의 | 일정 확정 시 진행 |

---

## 🔴 OPEN (지금 손댈 수 있는 BE/Infra 작업)

| 순위 | ID | 작업 | 시간 | 비고 |
|:---:|:---|:---|:---:|:---|
| 1 | AUDIT-PWA-SW-INDEXEDDB-PRESERVE | PIN 후속 검증 | 30분 | 🟡 LOW · 짬 작업 |
| 2 | UX-LOGIN-FALLBACK-PIN-RESET-LINK | UX | 1h | 🟡 LOW |
| 3 | UX-SPRINT55-FINALIZE-DIALOG-WARNING | UX 마무리 | 1.5h | 🟡 LOW (여유 시) |
| 4 | OBSERV-MIGRATION-HISTORY-SCHEMA | 관찰성 | TBD | 🟢 OPEN |
| 5 | OBSERV-ADMIN-ACTION-AUDIT | 관찰성 | TBD | 🟢 OPEN |
| 6 | OBSERV-RAILWAY-HEALTH-TTFB-15S | 외부 모니터링 | TBD | 🟢 OPEN |
| 7 | OBSERV-SLOW-QUERY-ENDPOINT-PROFILING | slow query | TBD | 🟢 OPEN |

---

## 🟢 다음 주 이후 — 머리에서 비워둬도 OK

> 잊어버려도 됨. 필요할 때 BACKLOG.md 다시 열기.

```
- FEAT-AUTH-STORAGE-MIGRATION-FULL                 (보안 trade-off, 3~4h)
- FEAT-SPRINT55-REACTIVATE-HYBRID-ROLE              (UX 개선)
- FEAT-SPRINT55-REACTIVATE-REQUEST-FLOW             (UX 개선)
- DOC-AXIS-VIEW-REACTIVATE-BUTTON                   (문서)
- INFRA-COLLATION-REFRESH                           (별건)
- TEST-CLEAN-CORE-01                                (회귀 테스트)
- 리팩토링 Sprint 12개 (REF-BE-* / REF-FE-*)        (코드 정리)
- DOC-HANDOFF-CLEANUP                               (handoff #18/#45/#52/#58/#59-A/B/C/#60/#61 표 정리, 30분)
```

---

## 🧠 의사결정 룰 — 머리 비우기용

**작업 들어갈 때 결정할 것 1개**:
- 1순위 트랙 지금 들어갈까? Yes → 집중 1.5h
- No → 짬 작업 (30분 단위) 1~2개

**검토 받을 때**:
- Codex / Claude Code 다라운드 검증 → advisory 정리만 보고 결정
- 검증 결과는 자동으로 Sprint 문서에 기록되니 머리에 외울 필요 없음

**중간에 발견된 버그**:
- 5분 안 끝나는 거면 → BACKLOG 등록만 하고 다음으로 (지금 처리 X)
- 5분 안 끝나면 → 그 자리에서 처리

**병행 진행**:
- FE + BE 다른 영역이면 병행 가능 (Risk 검토 후)

**HOTFIX 후속 결함**:
- 즉시 모두 해결 시도 X. **단계적 검증 + 데이터 기반 결정**

---

## 📚 어디 가면 뭐 있나 (cheat sheet)

```
"오늘 뭐 해야 되지?"
  → 이 파일 (WEEKLY_PLAN_20260504.md)

"작업 상세는 어떻게 했더라?"
  → AGENT_TEAM_LAUNCH.md (Sprint ID 로 검색)

"DB Pool 측정 결과 어디 적지?"
  → DB_POOL_VERIFICATION_QUERIES_20260427.md

"전체 BACKLOG 보려면?"
  → BACKLOG.md 의 "🗺️ 우선순위 로드맵" 섹션 (Phase A~G)

"어제 뭐 했지?"
  → handoff.md (세션 1/3 + 2/3 + 3/3)

"코드 규칙 다시 봐야겠다"
  → CLAUDE.md
```

---

## 💪 이번 주 끝났을 때 기대 상태 (2026-05-04 ~ 2026-05-08)

> 빈 템플릿 — 주 시작 시 회고 1~2줄 + 시나리오 분기 채워넣기.

### 시나리오 A
- (예: Sprint 64-BE 동반 배포 + VIEW Sprint 40 main merge + Sentry 1주 검토 보고서 작성 …)

### 시나리오 B
- (예: BE 측 일정 지연 시 짬 트랙 (AUDIT-PWA / UX-LOGIN-FALLBACK / OBSERV-*) 일부 진행 …)

---

## 🤝 혼자 들고 가지 마 — 도움 받을 곳

- **Codex review**: Sprint 설계서 정리 후 자동 분석 (텍스트 일관성 + 데이터 정합성)
- **Claude Code review**: 코드 grep + 구조적 검증 + advisory M/A 라벨링
- **나 (Cowork)**: plan 정리, BACKLOG 동기화, 문서 반영

검증/문서 작업은 던지고, 너는 **결정 + 코드 작업** 만 해도 됨.

---

> 머리 가벼워야 좋은 결정 나옴. 이 파일이 그 무게 덜어주는 용도.
> 자동 생성 시드 (2026-05-04). 회고 1~2줄 + 핵심 3가지 + 시나리오 A/B 본문은 주 진행하면서 채워넣기.
