# Sprint 29 Code Review — Factory API

**리뷰 대상**: `21bb00f feat: Sprint 29 공장 API — monthly-detail + weekly-kpi`
**리뷰어**: Claude
**날짜**: 2026-03-15
**변경 파일**: `factory.py`, `__init__.py`, `version.py`, `PROGRESS.md`, `CLAUDE.md`

---

## 전체 평가: ✅ PASS (이슈 4건, 권장사항 3건)

코드 품질 좋음. 기존 AXIS-OPS 라우트 패턴(admin.py, product.py)과 일관된 구조.
SQL Injection 방어, 파라미터 검증, 에러 핸들링 모두 적용됨.

---

## 🔴 이슈 (수정 권장)

### 이슈 1: `routes/__init__.py`에 factory_bp 미등록
**파일**: `backend/app/routes/__init__.py`
**심각도**: LOW (실동작 무관)

```python
# 현재 __init__.py — factory 없음
__all__ = [
    "auth_bp", "work_bp", "product_bp",
    "alert_bp", "admin_bp", "sync_bp",
]
```

`__init__.py`의 `__all__`에 `factory_bp`가 빠져있음. 실제 앱 등록은 `app/__init__.py`의 `create_app()`에서 직접 import하므로 **런타임 영향 없음**. 하지만 `gst_bp`, `checklist_bp`, `hr_bp`, `notices_bp`, `qr_bp`도 전부 빠져있어서, 이건 Sprint 29만의 문제가 아니라 오래된 누락. 정리할 때 한번에 하면 됨.

---

### 이슈 2: `weekly-kpi` pipeline 로직 — shipped 판정 기준 의문
**파일**: `factory.py` 라인 298-303
**심각도**: MEDIUM

```python
if r.get('si_completed'):
    fpe = r.get('finishing_plan_end')
    if fpe and fpe > today:
        pipeline['si'] += 1
    else:
        pipeline['shipped'] += 1
```

`finishing_plan_end`(출하 **예정일**)이 오늘 이전이면 shipped로 분류하는데, **실제 출하 여부**가 아닌 **예정일 경과**를 기준으로 판단함. `qr_registry.actual_ship_date`가 존재하는데 이걸 사용하는 게 더 정확할 수 있음.

현재 쿼리가 `plan.product_info`만 JOIN하고 `qr_registry`는 안 쓰므로, 의도적인 설계라면 주석으로 이유를 남기는 걸 권장.

**개선안 (선택)**:
```python
# actual_ship_date가 있으면 실제 출하, 없으면 예정일 기반 추정
# → 추후 VIEW FE 연동 시 qr_registry JOIN 검토
```

---

### 이슈 3: `test_factory.py` 미작성
**심각도**: MEDIUM

Sprint 프롬프트 Task 4에 명시된 `test_factory.py`가 생성되지 않음. 다른 라우트(admin, work, product 등)는 전부 테스트가 있음. 최소한 다음 항목 필요:

- `monthly-detail` 파라미터 검증 (잘못된 month, 허용 안 되는 date_field)
- `weekly-kpi` 파라미터 검증 (week=0, week=54, year=1999)
- 권한 테스트 (view_access vs gst_or_admin)
- GAIA/non-GAIA progress 계산 분기

---

### 이슈 4: cursor 명시적 close 누락
**파일**: `factory.py` 라인 111, 242
**심각도**: LOW

```python
conn = get_db_connection()
cur = conn.cursor()
# ... 쿼리 실행 ...
# cur.close() 호출 없이 conn.close()만 호출
```

`conn.close()` 시 cursor도 같이 해제되긴 하지만, 다른 라우트 파일(product.py 등)에서도 동일한 패턴이므로 프로젝트 전체 컨벤션으로 봐야 함. 장기적으로는 context manager (`with conn.cursor() as cur:`) 패턴이 더 안전.

---

## 🟡 권장사항 (선택)

### 권장 1: `_calc_progress`에서 boolean 비교 명시
```python
# 현재: if row.get(s)  ← truthy 체크 (0도 falsy)
# 권장: if row.get(s) is not None and row.get(s) is not False
```
DB에서 `completed` 컬럼이 boolean이면 문제없지만, 혹시 timestamp 타입이면 `0` 값이 falsy로 처리될 수 있음. 현재 `completion_status` 스키마가 boolean이면 OK.

### 권장 2: monthly-detail 쿼리 3회 → 2회 최적화 가능
현재 COUNT + 데이터 + by_model로 쿼리 3번 실행. Window function으로 2회로 줄일 수 있음:
```sql
SELECT *, COUNT(*) OVER() AS total_count FROM plan.product_info p ...
```
하지만 현재 데이터 규모(월 수십~수백 건)에서는 성능 차이 미미. VIEW FE에서 속도 이슈 나오면 그때 적용해도 됨.

### 권장 3: `_date_to_iso` 리턴 타입 불일치
```python
def _date_to_iso(val) -> str:
    if val is None:
        return None  # ← 타입힌트 str인데 None 리턴
```
`Optional[str]`로 수정하면 깔끔.

---

## ✅ 잘된 점

1. **SQL Injection 방어**: `_ALLOWED_DATE_FIELDS` 화이트리스트로 f-string 내 date_field 보호
2. **GAIA 모델 분기**: `_calc_progress`와 `by_stage`에서 tm_completed 조건 분리 처리 깔끔
3. **ISO week 변환**: `date.fromisocalendar()` 사용으로 53주차 엣지 케이스 안전 처리
4. **에러 핸들링**: PsycopgError catch + logger.error 패턴 일관됨
5. **블루프린트 등록**: `create_app()`에서 올바르게 import + 주석 달림
6. **코드 구조**: 기존 admin.py, product.py와 동일한 패턴 유지

---

## 요약

| 카테고리 | 상태 |
|---------|------|
| 보안 (SQL Injection) | ✅ 방어됨 |
| 인증/권한 | ✅ 엔드포인트별 적절한 데코레이터 |
| 에러 핸들링 | ✅ DB 에러 catch |
| 코드 일관성 | ✅ 기존 패턴 준수 |
| 테스트 | ❌ test_factory.py 미작성 |
| 엣지 케이스 | 🟡 shipped 판정 로직 확인 필요 |

**다음 액션**: test_factory.py 작성 → shipped 판정 로직 확인 → (선택) 타입힌트 정리
