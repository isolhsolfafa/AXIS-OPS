# Codex 3차 교차검증 프롬프트 — Sprint 62-BE v2.2 (축소 확정안)

> 생성일: 2026-04-23 (v2.2 갱신) | 대상: Codex (독립 검증자) | 작성자: Claude Code Opus Lead
> 검증 유형: 설계 단계 3차 교차검증 (v2 → v2.2 축소 확정안)
> 근거: CLAUDE.md AI 검증 워크플로우 v2 단계 ③
> 이전 검증: Codex 1차 (v1, M1/M2/M3 지적) + Codex 2차 (v2, M 2건/A 4건)

---

## 배경 — 왜 3차 검증인가

- **1차**: v1 원안 → Codex가 M1(UNION 중복)/M2(반개구간)/M3(`_FIELD_LABELS`) 지적
- **2차**: VIEW v2 역제안 → Codex가 M 2건(Q4 화이트리스트 불일치, Q5 `shipped_plan` 의미 모호) + A 4건 지적
- **Railway DB 실측**: 인덱스 3개 누락 확정 + shipped 3종 수치 (plan=0, actual=23, ops=0) 확보
- **Twin파파 피드백**: UNION 자동 합산 폐기 + 이행률/정합성 지표 BACKLOG 이관 + `shipped_realtime`→`shipped_ops` 리네임
- **v2.2 확정**: 데이터 공급 인프라만 본 Sprint, 경영 KPI 로직은 `BACKLOG-BIZ-KPI-SHIPPING-01`

---

## 본 검증에 필요한 참조 문서

1. **v2.2 최종 설계**: `/Users/twinfafa/Desktop/GST/AXIS-OPS/AGENT_TEAM_LAUNCH.md` — "Sprint 62-BE v2.2" 섹션 (L29327 부근)
2. **v1 원안 (역사)**: 동일 파일 L29099~29325
3. **v2 VIEW 역제안 (역사)**: `/Users/twinfafa/Desktop/GST/AXIS-VIEW/OPS_API_REQUESTS.md` L4384~4676
4. **현재 factory.py**: `/Users/twinfafa/Desktop/GST/AXIS-OPS/backend/app/routes/factory.py`
5. **기존 label 레지스트리**: `/Users/twinfafa/Desktop/GST/AXIS-OPS/backend/app/routes/admin.py` L2260~2268
6. **BACKLOG 이관 엔트리**: `/Users/twinfafa/Desktop/GST/AXIS-OPS/BACKLOG.md` — `BIZ-KPI-SHIPPING-01`, `POST-REVIEW-SPRINT-62-BE-V2.2-20260423`

---

## v2 → v2.2 핵심 축소 요약

| 조항 | v2 | **v2.2 확정** | 근거 |
|---|---|---|---|
| 출하 응답 필드 | 4필드 (`union/realtime/actual/plan`) | **3필드** (`plan/actual/ops`) | Twin파파: UNION 자동 합산은 의미 없음, 소스 비교가 본질 |
| `shipped_realtime` 이름 | `realtime` | **`shipped_ops`** 로 리네임 | 프로젝트 정체성(AXIS-OPS) + Codex Q5 의미 모호 해소 |
| `_count_shipped` 분기 | 4분기 (union/realtime/actual/plan) | **3분기** (plan/actual/ops) | UNION 자동 합산 폐기 |
| `_FIELD_LABELS` 확장 | 2개 (ship_plan_date + actual_ship_date) | **0개** | Codex Q1 A 지적: ship_plan_date 이미 존재 (admin.py:2262) |
| 이행률/정합성 계산 | — | **BACKLOG 이관** (BIZ-KPI-SHIPPING-01) | Twin파파: 경영 KPI는 App 베타 100% 전환 후 확정 |
| `null_count` 응답 필드 | v2 Codex Q4 권고 | **제거** | Twin파파: NULL = "아직 출하 안 됨" 정상 상태, 경고 아님 |
| 인덱스 migration 050 | 제안 | **확정 반영** | Railway 실측: 3개 누락 |

---

## 검증 요청 사항 (v2.2 신규 쟁점)

다음 6개 질문에 **M(Must) / A(Advisory) / N(No issue)** 라벨 + 구체 근거.

### [Q1] 3필드 독립 구조 적절성 (Twin파파 방향 검증)

```python
shipped_plan    = ship_plan_date + si_completed (계획 완료)
shipped_actual  = actual_ship_date             (Teams 수기 → cron)
shipped_ops     = SI_SHIPMENT.completed_at     (OPS 앱, 베타 전환 중)
```

- 3필드를 자동 합산하지 않고 독립 제공하는 설계가 경영 대시보드 지표 (이행률 = actual/plan, 정합성 = ops/actual) 확장성 관점에서 올바른가?
- 혹은 BE에서 이행률을 이미 계산해서 제공하는 것이 DRY 관점에서 옳은가? (BACKLOG-BIZ-KPI-SHIPPING-01이 아직 DRAFT라 추후 확정)
- `shipped_ops` 네이밍이 SI_SHIPMENT task 이외 의미로 확장될 리스크가 있는가?

### [Q2] `_count_shipped` 3분기 간단화

```python
def _count_shipped(conn, start, end, basis):
    # basis: 'plan' | 'actual' | 'ops'
    if basis == 'plan':   # ship_plan_date JOIN completion_status si_completed=TRUE
    elif basis == 'actual': # actual_ship_date
    elif basis == 'ops':    # SI_SHIPMENT.completed_at (+ force_closed=false)
    else: raise ValueError
```

- Codex 2차 Q2 지적(UNION+COUNT(DISTINCT) 중복 제거 2번)이 자동 해소됨 — 확인 요청
- `plan` 분기가 `LEFT JOIN completion_status`를 쓰는데, `si_completed=TRUE` 조건 때문에 결과적으로 INNER JOIN 동일. INNER JOIN으로 명시하는 게 의도 명확한가?

### [Q3] 인덱스 migration 050 (실측 근거 확정)

**Railway 실측 결과**:
- ✅ `idx_app_task_details_completed_at` 존재
- ❌ `plan.product_info.actual_ship_date` 없음
- ❌ `plan.product_info.ship_plan_date` 없음
- ❌ `plan.product_info.finishing_plan_end` 없음

```sql
-- migrations/050_factory_kpi_indexes.sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_info_actual_ship_date
  ON plan.product_info (actual_ship_date) WHERE actual_ship_date IS NOT NULL;
-- ... 3개 동일 패턴
```

- `WHERE actual_ship_date IS NOT NULL` partial index 사용이 적절한가?
  - NULL 비율 35.3% (실측) → partial index 공간/쓰기 비용 절감 가능
  - 단, 쿼리 optimizer가 `IS NOT NULL` 조건 없이도 해당 index 사용할지 검증 필요
- migration 파일 이름 `050_factory_kpi_indexes.sql` — 기존 번호 체계와 충돌 없는가? (최근 049 이후)
- SI_SHIPMENT 복합 인덱스 주석 처리 (Codex 2차 Q2 Advisory) — 본 Sprint 포함 vs BACKLOG?

### [Q4] 화이트리스트 2개 상수 분리 (Codex 2차 Q4 M 해소안)

```python
# monthly-kpi 전용 (pi_start 제외 — 출하 기준 date만)
_ALLOWED_DATE_FIELDS_MONTHLY_KPI = {
    'mech_start', 'finishing_plan_end', 'ship_plan_date', 'actual_ship_date'
}

# monthly-detail 기존 (pi_start 포함 — ProductionPlanPage 토글 유지)
_ALLOWED_DATE_FIELDS = {
    'pi_start', 'mech_start', 'finishing_plan_end', 'ship_plan_date', 'actual_ship_date'
}
```

- 2개 상수 분리가 Codex 2차 Q4 M을 완전 해소하는가?
- 네이밍이 명확한가? (`_ALLOWED_DATE_FIELDS_MONTHLY_KPI` vs `_ALLOWED_DATE_FIELDS`)
- 공통 부분 추출(`_COMMON_DATE_FIELDS`) 이 DRY 관점에서 유리한가?

### [Q5] `shipped_plan` 이름 변경 취소 (Codex 2차 Q5 M 처리)

- Codex 2차 Q5는 "`shipped_plan_in_range` 로 리네임" 권고
- v2.2에서는 **BACKLOG 이관으로 혼동 원천 차단** 방향 선택 (`shipped_plan`은 단순 COUNT 필드로만 존재, 이행률 계산 없음)
- `pipeline.shipped`는 기존 `today` 제한 로직 그대로 유지 → 두 필드 각각 독립 의미
- Codex 2차 Q5 M 해소 판정 가능한가?
- 혹은 여전히 FE 개발자 혼동 위험이 남아 리네임 필수인가?

### [Q6] pytest 10 TC 커버리지 (Codex 2차 Q7 A 반영)

```
TC-FK-01~10 (v2.2 최종 10 TC)
+ Codex Q7 3건 반영: TC-FK-05 (whitelist 분리) / TC-FK-09 (3필드 독립성) / TC-FK-10 (force_closed + actual 동시)
```

- 추가 권고 TC가 있는가?
- `BACKLOG-BIZ-KPI-SHIPPING-01` DRAFT 단계라 이행률/정합성 TC는 의도적으로 제외 — 적절한가?

---

## 응답 형식

```markdown
## [Q1] 라벨: M/A/N
... (근거, 파일:라인 인용) ...

## [Q2] 라벨: M/A/N
... (근거) ...

... Q3~Q6 동일 ...

## 종합 판정
- v2.2 채택 가능: Y/N
- 해결해야 할 M 건수: X
- Advisory 권고 건수: Y
- 재검증 필요 여부: Y/N
- 주요 코멘트 (축소 방향 자체의 적절성): ...
```

---

## 검증 후 Claude Code 대응 절차

1. Codex M 지적 전건 설계서 반영 (AGENT_TEAM_LAUNCH.md L29327 v2.2 section)
2. Advisory는 BACKLOG 등록 (🟡 LOW) 또는 POST-REVIEW-SPRINT-62-BE-V2.2 에 흡수
3. Twin파파 최종 승인 후 구현 착수
4. 침묵 승인(예: "v2.2 좋습니다" 류 한 줄) 시 자동 재질문
