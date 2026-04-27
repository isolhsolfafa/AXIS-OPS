# Codex 1차 advisory review 요청 — FIX-PIN-FLAG-MIGRATION-SHAREDPREFS-20260427

> **요청자**: Claude Code (Opus 4.7)
> **요청일**: 2026-04-27 KST
> **검토 대상**: `/Users/twinfafa/Desktop/GST/AXIS-OPS/AGENT_TEAM_LAUNCH.md` L31395+ (FIX-PIN-FLAG-MIGRATION-SHAREDPREFS-20260427 섹션)
> **이관 사유**: ⚠️ **인증 로직 영향** (PIN 등록 판단 → main.dart 라우팅 분기) — CLAUDE.md L130 Codex 이관 체크리스트 4번 (인증·권한 로직 변경) 해당 + "판정 애매 시 = 자동 이관" 적용
> **회신 방식**: M(Must) / A(Advisory) 라벨링, M 만 즉시 처리. A 는 BACKLOG 이관 가능

---

## 📋 검토 컨텍스트

### 본 Sprint 핵심

**문제**: Flutter PWA 의 `pin_registered` 플래그가 `flutter_secure_storage` (IndexedDB AES 암호화) 에 저장되어 SW 업데이트 / iOS Safari 7일 idle / Storage quota evict 시 손실 가능. 손실 시 main.dart 라우팅이 EmailLoginScreen 으로 빠지고 → 사용자 비번 모름 → 막힘.

**수정**: `pin_registered` 플래그 storage 를 SecureStorage (IndexedDB) → SharedPreferences (localStorage) 로 이전. 단, **양방향 sync 패턴** 채택 (rollback 안전 + IndexedDB fallback 유지).

**부수 가설**: PIN 손실 사용자가 새로고침 반복 → `/auth/refresh` + `/auth/login` 누적 호출 → connection burst 부수 기여 가능 (별건 FIX-DB-POOL-MAX-SIZE-20260427 의 Q-B 31 peak 일부 원인 후보).

### 코드 사실 (grep 검증 완료)

```
auth_service.dart:20    static const String _pinRegisteredKey = 'pin_registered';
auth_service.dart:243   logout: await _secureStorage.delete(key: _pinRegisteredKey);
auth_service.dart:349   hasPinRegistered() — _secureStorage.read
auth_service.dart:355   savePinRegistered() — _secureStorage.write
main.dart:260           hasPinRegistered() 호출 → PinLoginScreen / EmailLoginScreen 분기
main.dart:276           tryAutoLogin() 호출 (refresh API)
```

### Claude Code advisory 1차 (사전 자체 검증)

| # | 약점 | 정정 |
|:---:|:---|:---|
| A1 | 인증 로직 영향 (체크리스트 4번 해당) | Codex 이관 결정 (본 요청) |
| A2 | connection 인과 정량 입증 부재 | baseline SQL 3종 추가 |
| A3 | ⛔ 단방향 마이그레이션 시 rollback 위험 (신규 사용자 일괄 빠짐) | 양방향 sync 채택 |
| A4 | savePinRegistered() 양방향 write 패턴 | 코드 예시 업데이트 |
| A5 | race condition (낮은 위험) | 명시적 lock 선택 (적용 안 함) |
| A6 | IndexedDB 손실 trigger 정확성 (SW 업데이트 일반적으로 무영향) | AUDIT Sprint 사후 검증 |

---

## 🎯 Codex 검토 요청 사항 (Q1 ~ Q5)

### Q1 — 양방향 sync 패턴의 안전성

**현재 설계**:
```dart
Future<void> savePinRegistered(bool registered) async {
  final prefs = await SharedPreferences.getInstance();
  final value = registered ? 'true' : 'false';
  await prefs.setString(_pinRegisteredKey, value);                          // ① SharedPrefs write
  await _secureStorage.write(key: _pinRegisteredKey, value: value);        // ② SecureStorage write
}

Future<bool> hasPinRegistered() async {
  final prefs = await SharedPreferences.getInstance();
  final fromPrefs = prefs.getString(_pinRegisteredKey);
  if (fromPrefs != null) return fromPrefs == 'true';                       // ① 1순위 SharedPrefs

  final fromSecure = await _secureStorage.read(key: _pinRegisteredKey);
  if (fromSecure != null) {
    await prefs.setString(_pinRegisteredKey, fromSecure);                  // ② 2순위 SecureStorage + sync
    return fromSecure == 'true';
  }
  return false;
}
```

**검토 요청**:
- (a) `savePinRegistered()` 의 ① + ② 순서가 atomic 하지 않음 — ① 성공 + ② 실패 시 desync 가능. 무시 가능 수준인지?
- (b) `hasPinRegistered()` 의 read 순서 (SharedPrefs → SecureStorage) 가 적절한지? IndexedDB 손실 시나리오에서 SharedPrefs fallback 이 항상 정확한지?
- (c) 양방향 sync 가 단방향 (SecureStorage delete) 보다 storage 부담 / 성능 / 유지보수 측면에서 trade-off?

### Q2 — Rollback 시 사용자 영향 시나리오

| 사용자 케이스 | 본 Sprint 적용 후 storage 상태 | rollback 후 (SecureStorage-only 코드) |
|---|---|---|
| 기존 PIN 사용자 | SecureStorage 'true' (마이그레이션 전이라 sync 안 됨) + SharedPrefs 'true' (sync 후) | SecureStorage 'true' read → ✅ |
| 신규 PIN 등록 사용자 (양방향 sync 덕) | SecureStorage 'true' + SharedPrefs 'true' | SecureStorage 'true' read → ✅ |
| logout 사용자 | 양쪽 null | 양쪽 null → EmailLoginScreen ✅ |
| IndexedDB 손실 사용자 (적용 후) | SecureStorage null + SharedPrefs 'true' | SecureStorage null read → ❌ EmailLoginScreen 빠짐 |

**검토 요청**:
- (d) 마지막 케이스 (IndexedDB 손실 사용자) 의 rollback 영향이 본 Sprint 적용 전과 동일한 위험인지? (즉, rollback 자체가 그 사용자에 대해 악화시키지 않는지)
- (e) rollback 시 양방향 sync 가 보장되는 사용자 비율 추정 (기존 PIN 사용자 100% + 신규 등록 100% + IndexedDB 손실 사용자 0%)

### Q3 — Connection burst 가설 정량 입증 SQL 적정성

설계서 Baseline SQL 3종:
1. PIN 손실 의심 사용자 식별 (같은 날 `/auth/login` 2회 이상)
2. 사용자당 login attempts/day 추세
3. 출근 burst 시점 auth API 비중 (auth_pct)

**검토 요청**:
- (f) 위 SQL 들이 실제로 PIN 손실 → connection burst 인과를 증명하기 충분한지?
- (g) 다른 가설 (예: 네트워크 불안정, JWT expire, browser auth tab restore) 과 구분 가능한지?
- (h) baseline 측정 후 D+7 재측정 비교 가능 여부 + 통계 신뢰성

### Q4 — IndexedDB 손실 trigger 정확성

설계서 storage 안정성 비교 표 (L31441~31447):

| Storage | 저장 위치 | 손실 trigger |
|---|---|---|
| SharedPreferences | localStorage (plain) | "Clear site data" 만 |
| flutter_secure_storage | IndexedDB (AES) | SW 업데이트 / 캐시 정책 변경 / 일부 PWA 새로고침 / iOS Safari 7일 idle |

**검토 요청**:
- (i) "SW 업데이트 시 IndexedDB 손실" — Flutter 표준 SW 가 IndexedDB 를 건드리지 않는다는 사실과 충돌. 정확한 trigger 가 무엇인지?
- (j) iOS Safari 7일 idle policy 가 SharedPreferences (localStorage) 에도 적용되는지?
- (k) 본 Sprint 의 가설 ("SecureStorage 가 SharedPreferences 보다 손실 위험 ↑") 의 근거가 충분한지?

### Q5 — Codex 이관 적정성

본 작업은 단일 FE 파일 + 30분 작업 + Flutter widget test 가능 범위인데도 인증 로직 영향으로 이관 결정.

**검토 요청**:
- (l) Codex 이관 자체가 적정한지? (인증 로직이지만 마이그레이션 호환성 100% + rollback 안전 시 advisory 수준일 수도)
- (m) 본 작업과 별건 (FIX-DB-POOL-MAX-SIZE-20260427 Phase B 관찰 중) 병행 가능 여부 — 두 작업 충돌 가능성?
- (n) 향후 인증 로직 변경 시 동일 검토 깊이 권장 여부

---

## 📁 참고 파일 경로

- 설계서 본문: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` L31395 ~ L31843
- 코드 (대상): `AXIS-OPS/frontend/lib/services/auth_service.dart` (특히 L20, L243, L349-360)
- 코드 (라우팅): `AXIS-OPS/frontend/lib/main.dart` L243-300
- 별건 (병행): `AXIS-OPS/AGENT_TEAM_LAUNCH.md` L30859+ (FIX-DB-POOL-MAX-SIZE-20260427)
- CLAUDE.md L130 Codex 이관 체크리스트: `AXIS-OPS/CLAUDE.md`

---

## 📝 회신 양식

```
### Codex advisory 1차 (2026-04-27)

#### M (Must) — 즉시 해결 필수
- M1: ___
- M2: ___

#### A (Advisory) — BACKLOG 이관
- A1: ___
- A2: ___

#### Q1 ~ Q5 답변
- Q1.a: ___
- Q1.b: ___
...

#### 결론
- 본 Sprint 적용 가능 여부: ✅ / ⚠️ / ❌
- 추가 검토 필요 사항: ___
```
