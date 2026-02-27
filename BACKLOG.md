# AXIS-OPS 백로그

> 마지막 업데이트: 2026-02-27 (Sprint 12 준비 중)
> 이 파일은 보류/재검토/계획/아이디어를 한 곳에서 관리합니다.
> 완료된 항목은 PROGRESS.md로 이동합니다.

---

## 🔴 지금 진행 중

| ID | 항목 | 상태 | 비고 |
|----|------|------|------|
| S12 | Sprint 12: PIN 간편 로그인 + 협력사 출퇴근 + QR 카메라 | ✅ 완료 | 22/22 테스트 PASS |
| S12-HF | Sprint 12 핫픽스: PIN 자동로그인 분기 로직 | ✅ 완료 | 4개 파일 수동 수정 (main.dart, auth_service.dart, pin_login_screen.dart, pin_settings_screen.dart) |

---

## 🟡 재검토 (Review Needed)

보류해둔 항목. 다음 Sprint 기획 시 우선 검토.

### RV-1: checklist 스키마 vs 실제 Excel 양식 불일치
- **배경**: `출하 어플용의 사본.xlsx` (sheet=DB) 분석 결과, 현재 checklist_master 스키마(단순 item_name 기반)와 실제 데이터 구조가 다름
- **현재 스키마**: product_code + category + item_name
- **실제 Excel**: 자재코드(material_code) + 자재내역 + 규격1/규격2 + 수량 + 단위 + 상태(OK/NG)
- **차이점**: 현재는 체크리스트 "항목명"만 있지만, 실제는 BOM(자재 목록) 기반으로 각 자재별 OK/NG 판정
- **필요 작업**:
  - checklist_master에 material_code, spec1, spec2, qty, unit 컬럼 추가 검토
  - item_master 테이블 분리 여부 결정
  - status를 PENDING/OK/NG/NA로 확장
  - Excel ETL import 로직 수정
- **DB 현황**: checklist 스키마 생성됨, 테이블 비어있음 (테스트는 임시 데이터로 통과)
- **결정 시점**: Sprint 13 이전

### RV-2: FE 전역 시간 표시 검증
- **배경**: Sprint 11 핫픽스로 4개 화면 `.toLocal()` 추가했지만, 다른 화면에도 같은 문제 있을 수 있음
- **확인 대상**: 모든 DateTime 표시 화면에서 `.toLocal()` 호출 여부
- **우선순위**: 낮음 (현재 수정된 4개 화면이 주요 사용 화면)

---

## 🟠 배포 준비

| ID | 항목 | 설명 | 상태 |
|----|------|------|------|
| DP-1 | Railway Flask API 설정 | `axis-ops-api.up.railway.app` | ✅ 완료 |
| DP-2 | GitHub commit/push | Sprint 5~11 + 배포설정 push 완료 | ✅ 완료 |
| DP-3 | FE apiBaseUrl 변경 | 아래 상세 참조 | 대기 (Sprint 12 후) |
| DP-4 | PWA 배포 | `flutter build web` → Netlify에 `build/web` 드래그&드롭 배포 | 대기 |
| DP-5 | 베타 테스트 | 현장 작업자 실사용 테스트 | DP-3, DP-4 |
| DP-6 | CI/CD 구축 | GitHub Actions (CLAUDE.md에 추후로 기록됨) | 추후 |

**DP-3 상세: FE API 주소 변경 (Sprint 12 완료 후 배포 직전)**
```
파일: frontend/lib/utils/constants.dart

변경 전:
  const String apiBaseUrl = 'http://localhost:5001/api';
  const String webSocketUrl = 'ws://localhost:5001/ws';

변경 후:
  const String apiBaseUrl = 'https://axis-ops-api.up.railway.app/api';
  const String webSocketUrl = 'wss://axis-ops-api.up.railway.app/ws';
```

---

## 🔵 추후 구현 (Phase 로드맵)

CLAUDE.md Phase 계획 기반. 시급도순.

### Phase A 잔여: 생체인증
- **내용**: 지문/FaceID — WebAuthn API (HTTPS + Flutter Web JS interop)
- **현재**: Sprint 12에서 메뉴 UI만 생성 + "추후 오픈 예정" 안내
- **의존성**: PWA 배포(HTTPS) 완료 후

### Phase B 잔여: Admin 출퇴근 대시보드
- **내용**: 협력사 출퇴근 현황 조회 (당일 + 월간 집계)
- **결정**: App에서 제외 → AXIS-VIEW (React 대시보드)에서 구현
- **필요 API**: GET /api/admin/hr/attendance/dashboard, /monthly
- **의존성**: hr.partner_attendance 테이블 (Sprint 12에서 생성)

### Phase B 잔여: GST 근태 확장
- **내용**: hr.gst_attendance 테이블은 Sprint 12에서 생성, API/UI 미구현
- **용도**: 그룹웨어 RDB 연동 or 동기화
- **시기**: 미정 (그룹웨어 연동 계획 수립 후)

### Phase C: BOM 검증
- **내용**: product_bom 테이블 + bom_checklist_log
- **관련**: RV-1 (checklist 스키마 재검토)과 연결될 수 있음
- **시기**: checklist 스키마 확정 후

### defect 스키마
- **내용**: 불량 분석, 추적, 리포트 (QMS 연동)
- **시기**: 미정

---

## 🟢 아이디어 / 메모

- **AXIS-VIEW**: React 기반 관리자 대시보드 (출퇴근, 생산 현황, KPI 등). App과 분리.
- **PWA → Native 전환**: 현재 Flutter Web(PWA) 코드는 Native 전환 시 비즈니스 로직 그대로 재사용 가능. 플랫폼 의존 코드(html5-qrcode → mobile_scanner, secure storage 등)만 조건부 import 처리.
- **공용 태블릿 시나리오**: 공장 현장 공용 기기 사용 시 로그아웃 시 localStorage 클리어 로직 필요 (현재는 미구현, 필요 시 추가)
- **model_config 조회/수정**: CLAUDE.md에 "추후"로 기록됨. Admin이 모델별 설정(has_docking, is_tms 등) 수정 가능한 UI.

---

## 📋 Sprint 이력 요약

| Sprint | 주요 내용 | 테스트 |
|--------|----------|--------|
| 1 | 인증 + DB 기반 | 8 PASSED |
| 2 | Task 핵심 플로우 | 21 PASSED |
| 3 | 공정 검증 + 알림 | 21 PASSED |
| 4 | 관리자 + 퇴근시간 자동감지 | 31 PASSED |
| 5 | 보안 + PWA + 이메일 + 잔여 모델 | 59 PASSED |
| 6 | Task 재설계 + 네이밍 + Admin 옵션 | 157 PASSED, 20 SKIP |
| 7 | 실데이터 + 통합 테스트 | 356 PASSED, 19 SKIP |
| 8 | Admin API 보완 + UX + 비밀번호 찾기 | 271 PASSED, 19 SKIP |
| 9 | Pause/Resume + 근무시간 관리 | 318 PASSED, 19 SKIP |
| 10 | 수동 검증 + 버그 수정 | 456+ PASSED, 19 SKIP |
| 11 | GST Task + 대시보드 + Checklist | 44 PASSED, 1 SKIP |
| 11 핫픽스 | 타입 불일치, 필터링, 협력사 정보, UTC→KST | 수동 수정 4건 |
| 12 | PIN + 출퇴근 + QR 카메라 | 22 PASSED |
| 12 핫픽스 | PIN 자동로그인 분기 로직 | 수동 수정 4건 |
