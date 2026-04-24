# UI Sprint — 화이트 글래스모피즘 전체 적용 가이드

## 사전 조건
- ✅ Sprint 1~7 완료
- ✅ `design_system.dart` 글래스모피즘 토큰 추가 완료 (GxGradients, GxGlass, GxShadows.glass)
- ✅ `splash_screen.dart` 글래스모피즘 레퍼런스 구현 완료 (기준 화면)
- ✅ `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` = "1" 설정 완료
- ✅ 전체 12개 화면 + 3개 위젯 GxColors 기본 적용 완료

---

## 디자인 컨셉

### 화이트 글래스모피즘 테마
- **배경**: 4색 그라디언트 (`#667EEA → #764BA2 → #F093FB → #4FACFE`) — Splash 전용
- **내부 화면**: `GxColors.cloud` 배경 유지 + 카드에 glass 효과 적용
- **카드**: `rgba(255,255,255,0.72)` 배경 + `backdrop-filter: blur(24px)` + glass border
- **버튼**: 그라디언트 (primary) / 글래스 아웃라인 (secondary)
- **AppBar**: 통일된 스타일 — 화이트 배경 + 인디고 액센트 바 + 하단 구분선

### 디자인 시스템 토큰 참조 (`design_system.dart`)

```dart
// ── 글래스모피즘 그라디언트 ──
class GxGradients {
  static const background = LinearGradient(
    begin: Alignment(-1, -1), end: Alignment(1, 1),
    colors: [Color(0xFF667EEA), Color(0xFF764BA2), Color(0xFFF093FB), Color(0xFF4FACFE)],
    stops: [0.0, 0.33, 0.66, 1.0],
  );
  static const accentButton = LinearGradient(
    begin: Alignment(-1, -1), end: Alignment(1, 1),
    colors: [Color(0xFF6366F1), Color(0xFF818CF8)],
  );
}

// ── 글래스 카드/보더 스타일 ──
class GxGlass {
  static Color cardBg = Colors.white.withValues(alpha: 0.72);
  static Color cardBgLight = Colors.white.withValues(alpha: 0.5);
  static Color borderColor = Colors.white.withValues(alpha: 0.25);
  static Color borderLight = Colors.white.withValues(alpha: 0.5);

  static BoxDecoration card({double radius = 24}) => BoxDecoration(
    color: cardBg,
    borderRadius: BorderRadius.circular(radius),
    border: Border.all(color: borderColor, width: 1),
    boxShadow: GxShadows.glass,
  );

  static BoxDecoration cardSm({double radius = 10}) => BoxDecoration(
    color: cardBgLight,
    borderRadius: BorderRadius.circular(radius),
    border: Border.all(color: borderColor, width: 1),
    boxShadow: GxShadows.glassSm,
  );
}

// ── 글래스 쉐도우 ──
static List<BoxShadow> glass = [
  BoxShadow(color: Color(0xFF6366F1).withValues(alpha: 0.18), blurRadius: 48, offset: Offset(0, 16)),
];
static List<BoxShadow> glassSm = [
  BoxShadow(color: Colors.black.withValues(alpha: 0.06), blurRadius: 16, offset: Offset(0, 4)),
];
```

---

## 현재 상태 (Before)

| 파일 | GxColors | 글래스모피즘 | 상태 |
|------|----------|------------|------|
| `splash_screen.dart` | ✅ | ✅ | **완료 (레퍼런스)** |
| `login_screen.dart` | ✅ | ❌ | 흰색 카드, cloud 배경 |
| `register_screen.dart` | ✅ | ❌ | 흰색 카드, cloud 배경 |
| `verify_email_screen.dart` | ✅ | ❌ | 흰색 카드, cloud 배경 |
| `approval_pending_screen.dart` | ✅ | ❌ | 흰색 카드, cloud 배경 |
| `home_screen.dart` | ✅ | ❌ | 흰색 카드, cloud 배경 |
| `qr_scan_screen.dart` | ✅ | ❌ | 흰색 카드, cloud 배경 |
| `task_management_screen.dart` | ✅ | ❌ | 흰색 카드, cloud 배경 |
| `task_detail_screen.dart` | ✅ | ❌ | 흰색 카드, cloud 배경 |
| `alert_list_screen.dart` | ✅ | ❌ | 흰색 카드, cloud 배경 |
| `admin_options_screen.dart` | ✅ | ❌ | 흰색 카드, cloud 배경 |
| `admin_dashboard.dart` | ❌ | ❌ | **빈 스텁** |
| `worker_approval_screen.dart` | ❌ | ❌ | **빈 스텁** |
| `task_card.dart` | ✅ | ❌ | 흰색 카드 위젯 |
| `process_alert_popup.dart` | ✅ | ❌ | 다이얼로그 |
| `completion_badge.dart` | ✅ | ❌ | 상태 뱃지 위젯 |

---

## 레퍼런스: splash_screen.dart 패턴

완성된 `splash_screen.dart`를 기준으로 모든 화면에 적용할 공통 패턴:

### 1. AppBar 통일 패턴
```dart
AppBar(
  backgroundColor: GxColors.white,
  elevation: 0,
  leading: IconButton(
    icon: const Icon(Icons.arrow_back_ios, size: 18, color: GxColors.accent),
    onPressed: () => Navigator.of(context).pop(),
  ),
  title: Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      Container(
        width: 4, height: 20,
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            begin: Alignment.topCenter, end: Alignment.bottomCenter,
            colors: [GxColors.accent, GxColors.accentHover],
          ),
          borderRadius: BorderRadius.circular(2),
        ),
      ),
      const SizedBox(width: 12),
      const Text('화면제목', style: TextStyle(
        fontSize: 15, fontWeight: FontWeight.w600, color: GxColors.charcoal,
      )),
    ],
  ),
  centerTitle: false,
  bottom: PreferredSize(
    preferredSize: const Size.fromHeight(1),
    child: Container(height: 1, color: GxColors.mist),
  ),
)
```

### 2. 카드 컨테이너 패턴
```dart
// 기존 (변경 전)
Container(
  padding: const EdgeInsets.all(16),
  decoration: BoxDecoration(
    color: GxColors.white,
    borderRadius: BorderRadius.circular(GxRadius.lg),
    boxShadow: GxShadows.card,
  ),
  child: ...
)

// 글래스모피즘 (변경 후)
Container(
  padding: const EdgeInsets.all(16),
  decoration: GxGlass.cardSm(radius: GxRadius.lg),
  child: ...
)
```

### 3. 그라디언트 Primary 버튼 패턴
```dart
Container(
  height: 44,
  decoration: BoxDecoration(
    gradient: GxGradients.accentButton,
    borderRadius: BorderRadius.circular(GxRadius.sm),
    boxShadow: [
      BoxShadow(
        color: GxColors.accent.withValues(alpha: 0.35),
        blurRadius: 16, offset: const Offset(0, 4),
      ),
    ],
  ),
  child: Material(
    color: Colors.transparent,
    child: InkWell(
      onTap: onPressed,
      borderRadius: BorderRadius.circular(GxRadius.sm),
      child: Center(
        child: Text(label, style: const TextStyle(
          fontSize: 13, fontWeight: FontWeight.w600, color: Colors.white,
        )),
      ),
    ),
  ),
)
```

### 4. 섹션 헤더 패턴
```dart
Row(
  children: [
    Container(
      width: 28, height: 28,
      decoration: BoxDecoration(
        color: GxColors.accentSoft,
        borderRadius: BorderRadius.circular(GxRadius.md),
      ),
      child: const Icon(Icons.icon_name, size: 14, color: GxColors.accent),
    ),
    const SizedBox(width: 8),
    const Text('섹션 타이틀', style: TextStyle(
      fontSize: 14, fontWeight: FontWeight.w600, color: GxColors.charcoal,
    )),
  ],
)
```

### 5. 상태 뱃지 패턴
```dart
Container(
  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
  decoration: BoxDecoration(
    color: statusColor.withValues(alpha: 0.08),
    borderRadius: BorderRadius.circular(GxRadius.sm),
    border: Border.all(color: statusColor.withValues(alpha: 0.2)),
  ),
  child: Text(statusText, style: TextStyle(
    fontSize: 11, fontWeight: FontWeight.w600, color: statusColor,
  )),
)
```

---

## 실행 순서

### Step 1: tmux 세션 시작
```bash
tmux new -s axis-ui
```

### Step 2: Claude Code 시작
```bash
cd ~/Desktop/GST/AXIS-OPS
claude
```

### Step 3: Shift+Tab → accept edits on 확인

### Step 4: Phase별 프롬프트 입력

---

## 🎨 Phase 1 프롬프트 — Auth 화면 4개 업데이트 (복사해서 사용)

```
CLAUDE.md를 읽고, UI_SPRINT.md의 디자인 토큰과 레퍼런스 패턴을 숙지한 후 작업을 시작해줘.

⚠️ 이미 완료된 사항 (다시 하지 말 것):
- splash_screen.dart 글래스모피즘 완료 (레퍼런스 화면)
- design_system.dart에 GxGradients, GxGlass, GxShadows.glass/glassSm 토큰 추가 완료

## 팀 구성
1명의 teammate를 생성해줘. Sonnet 모델 사용:

1. **FE** (Frontend 담당) - 소유: frontend/**

## 목표
Auth 관련 화면 4개를 글래스모피즘 테마로 업데이트.
**기존 기능/로직은 절대 변경하지 않고, UI 스타일만 변경.**

### FE 작업 순서 (반드시 이 순서대로):

**1. login_screen.dart**
현재: cloud 배경 + 흰색 카드 + GxShadows.card
변경:
- 배경: GxColors.cloud 유지 (내부 화면이므로 그라디언트 X)
- 로그인 카드: `BoxDecoration(color: GxColors.white, boxShadow: GxShadows.card)` → `GxGlass.cardSm(radius: GxRadius.lg)`
- 로그인 버튼: `ElevatedButton` → 그라디언트 버튼 패턴 (GxGradients.accentButton)
  - ⚠️ 로딩 상태(CircularProgressIndicator) 유지 필수
  - ⚠️ disabled 상태 처리 유지 필수
- AppBar: 현재 이미 통일 패턴 적용됨 → 유지
- 에러 메시지 컨테이너: 스타일 유지 (GxColors.dangerBg 이미 적용됨)
- ⚠️ _handleLogin(), Navigator 로직, Form 검증, ApprovalPendingScreen 분기 등 기능 코드 절대 변경 금지

**2. register_screen.dart**
현재: cloud 배경 + 흰색 카드 + GxShadows.card
변경:
- 배경: GxColors.cloud 유지
- 회원가입 카드: → `GxGlass.cardSm(radius: GxRadius.lg)`
- 역할 선택 칩: 현재 스타일 → GxGlass.cardSm 적용된 작은 카드로
- Company 드롭다운: 현재 스타일 유지 + 테두리를 GxColors.mist로 통일
- 회원가입 버튼: → 그라디언트 버튼 패턴
- ⚠️ company↔role 검증 로직, 이메일 인증 플로우, validate 함수 절대 변경 금지

**3. verify_email_screen.dart**
현재: cloud 배경 + 흰색 카드
변경:
- 인증코드 입력 카드: → `GxGlass.cardSm(radius: GxRadius.lg)`
- 인증 버튼: → 그라디언트 버튼 패턴
- 재발송 버튼: → 글래스 아웃라인 버튼 (GxGlass.borderColor + GxColors.slate 텍스트)
- 타이머 표시: 현재 스타일 유지
- ⚠️ 인증코드 검증 로직, 타이머 로직, API 호출 절대 변경 금지

**4. approval_pending_screen.dart**
현재: cloud 배경 + 흰색 카드
변경:
- 상태 카드: → `GxGlass.cardSm(radius: GxRadius.lg)`
- 아이콘 컨테이너: GxColors.accentSoft 배경 유지
- 안내 텍스트 스타일: GxColors.slate + steel 유지
- ⚠️ 기능 로직 없는 정보 표시 화면 — 스타일만 변경

## 검증
1. `flutter build web` 에러 0건 확인
2. 각 화면에서 기존 기능 정상 동작 확인 (폼 검증, 버튼 클릭, 네비게이션)
3. 일관된 카드 스타일 (GxGlass.cardSm) 적용 확인

## 규칙
- UI_SPRINT.md의 "레퍼런스: splash_screen.dart 패턴" 섹션 참조
- 기능 코드 (로직, API 호출, 네비게이션) 절대 변경 금지
- import 추가 필요 시: `import '../../utils/design_system.dart';` (이미 있으면 생략)
- `dart:ui` import는 BackdropFilter 사용 시에만 추가 (내부 화면에서는 불필요)
```

---

## 🎨 Phase 2 프롬프트 — 메인 화면 3개 업데이트 (복사해서 사용)

```
CLAUDE.md를 읽고, UI_SPRINT.md의 디자인 토큰과 레퍼런스 패턴을 숙지한 후 작업을 시작해줘.

## 팀 구성
1명의 teammate를 생성해줘. Sonnet 모델 사용:

1. **FE** (Frontend 담당) - 소유: frontend/**

## 목표
메인 화면 3개를 글래스모피즘 테마로 업데이트.
**기존 기능/로직은 절대 변경하지 않고, UI 스타일만 변경.**

### FE 작업 순서:

**1. home_screen.dart**
현재: cloud 배경 + 흰색 기능 카드들 + GxShadows.card
변경:
- 배경: GxColors.cloud 유지
- 상단 사용자 정보 카드: → `GxGlass.cardSm(radius: GxRadius.lg)`
- 기능 카드 (QR Scan, Task Management 등): → `GxGlass.cardSm(radius: GxRadius.md)`
- 카드 내 아이콘 컨테이너: 현재 역할별 색상 유지 (accentSoft, successBg, infoBg 등)
- ⚠️ 로그아웃 로직, WebSocket 연결, 역할별 UI 분기, 네비게이션 절대 변경 금지

**2. qr_scan_screen.dart**
현재: cloud 배경 + 흰색 컨테이너
변경:
- QR 타입 선택 토글 컨테이너: → `GxGlass.cardSm(radius: GxRadius.md)`
- 카메라 영역 프레임: 현재 스타일 유지 (카메라는 건드리지 않음)
- 스캔 결과 카드: → `GxGlass.cardSm(radius: GxRadius.lg)`
- 수동 입력 영역: → GxGlass 스타일 적용
- ⚠️ 카메라 초기화/해제 로직, QR 파싱 로직, API 호출 절대 변경 금지

**3. task_management_screen.dart**
현재: cloud 배경 + 흰색 헤더 카드 + task 리스트
변경:
- 제품 헤더 카드 (serial_number, model 표시): → `GxGlass.cardSm(radius: GxRadius.lg)`
- 진행률 바 컨테이너: 현재 스타일 유지 (색상 코드 유지)
- 카테고리 탭 (MECH/ELEC/TMS): 선택 상태 → GxColors.accent 배경, 비선택 → GxGlass.cardBgLight
- ⚠️ Task 리스트 데이터 로딩, 필터링, 시작/완료 로직 절대 변경 금지
- ⚠️ task_card.dart 위젯은 Phase 3에서 별도 업데이트 — 여기서는 건드리지 않음

## 검증
1. `flutter build web` 에러 0건 확인
2. 각 화면에서 기존 기능 정상 동작 확인
3. 일관된 카드 스타일 적용 확인

## 규칙
- UI_SPRINT.md의 레퍼런스 패턴 참조
- 기능 코드 절대 변경 금지
- 이미 import된 design_system.dart 활용
```

---

## 🎨 Phase 3 프롬프트 — Task Detail + 위젯 3개 업데이트 (복사해서 사용)

```
CLAUDE.md를 읽고, UI_SPRINT.md의 디자인 토큰과 레퍼런스 패턴을 숙지한 후 작업을 시작해줘.

## 팀 구성
1명의 teammate를 생성해줘. Sonnet 모델 사용:

1. **FE** (Frontend 담당) - 소유: frontend/**

## 목표
Task Detail 화면 + 공유 위젯 3개를 글래스모피즘 테마로 업데이트.
**기존 기능/로직은 절대 변경하지 않고, UI 스타일만 변경.**

### FE 작업 순서:

**1. task_detail_screen.dart**
현재: cloud 배경 + 흰색 정보 카드
변경:
- Task 정보 카드 (task_name, category 등): → `GxGlass.cardSm(radius: GxRadius.lg)`
- 작업 시간 표시 영역: → `GxGlass.cardSm(radius: GxRadius.md)`
- 시작/완료 버튼:
  - 시작 버튼: → 그라디언트 버튼 패턴 (GxGradients.accentButton)
  - 완료 버튼: → GxColors.success 그라디언트 (success → success.withValues(alpha: 0.8))
- 작업 히스토리 리스트: → GxGlass.cardSm 적용
- ⚠️ 작업 시작/완료 API 호출, 타이머, 상태 변경 로직 절대 변경 금지

**2. task_card.dart (위젯)**
현재: 흰색 카드 + GxShadows.card
변경:
- 카드 외부 컨테이너: → `GxGlass.cardSm(radius: GxRadius.md)`
- 상태 뱃지: 현재 스타일 유지 (색상별 분기 유지)
- 카드 내 텍스트/아이콘: 현재 스타일 유지
- onTap 콜백: 절대 변경 금지

**3. process_alert_popup.dart (위젯)**
현재: AlertDialog 스타일
변경:
- Dialog 배경: → `GxGlass.cardBg` (반투명 흰색)
- Dialog shape: → RoundedRectangleBorder(borderRadius: GxRadius.lg)
- 경고 아이콘 컨테이너: 현재 색상 유지 (danger/warning 분기)
- 확인/취소 버튼: 확인 → 그라디언트 버튼, 취소 → 글래스 아웃라인 버튼
- ⚠️ 알림 데이터, 콜백 로직 절대 변경 금지

**4. completion_badge.dart (위젯)**
현재: 상태별 색상 뱃지
변경:
- 뱃지 컨테이너: → 상태 뱃지 패턴 적용 (statusColor.withValues(alpha: 0.08) 배경 + border)
- 텍스트 스타일: fontSize: 11, fontWeight: w600
- ⚠️ 상태 판단 로직 절대 변경 금지

## 검증
1. `flutter build web` 에러 0건 확인
2. task_card가 사용되는 task_management_screen에서 정상 렌더링 확인
3. process_alert_popup이 공정 누락 시 정상 표시 확인

## 규칙
- UI_SPRINT.md의 레퍼런스 패턴 참조
- 기능 코드 절대 변경 금지
- 위젯의 외부 인터페이스 (constructor, props) 절대 변경 금지
```

---

## 🎨 Phase 4 프롬프트 — Admin 화면 3개 업데이트 (복사해서 사용)

```
CLAUDE.md를 읽고, UI_SPRINT.md의 디자인 토큰과 레퍼런스 패턴을 숙지한 후 작업을 시작해줘.

## 팀 구성
1명의 teammate를 생성해줘. Sonnet 모델 사용:

1. **FE** (Frontend 담당) - 소유: frontend/**

## 목표
Admin 화면 3개를 글래스모피즘 테마로 업데이트.
**기존 기능/로직은 절대 변경하지 않고, UI 스타일만 변경.**

### FE 작업 순서:

**1. alert_list_screen.dart**
현재: cloud 배경 + 흰색 알림 타일
변경:
- 알림 타일 컨테이너: → `GxGlass.cardSm(radius: GxRadius.md)`
- 읽음/안읽음 상태 표시: 안읽음 → left border accent color 유지
- 알림 타입별 아이콘 컨테이너: 현재 색상 유지 (위험/경고/정보 분기)
- 필터 탭: 선택 → GxColors.accent 배경, 비선택 → GxGlass.cardBgLight
- ⚠️ 알림 로드, 읽음 처리 API, WebSocket 수신 로직 절대 변경 금지

**2. admin_options_screen.dart**
현재: cloud 배경 + 흰색 섹션 카드
변경:
- 섹션 카드 (매니저 관리, 설정, 미종료 작업): → `GxGlass.cardSm(radius: GxRadius.lg)`
- 토글 스위치: 현재 스타일 유지 (GxColors.accent activeColor)
- 작업자 리스트 아이템: → GxGlass.cardSm(radius: GxRadius.sm) 적용
- 강제 종료 버튼: → GxColors.danger 그라디언트
- Company 필터 드롭다운: 테두리 GxColors.mist 유지
- ⚠️ API 호출 (매니저 토글, 설정 변경, 강제 종료), 데이터 로딩 절대 변경 금지

**3. admin_dashboard.dart + worker_approval_screen.dart**
현재: 빈 스텁 (placeholder)
변경:
- ⚠️ 이 두 화면은 빈 스텁 상태. 실제 구현이 되어 있지 않으므로:
  - admin_dashboard.dart: 기본 레이아웃만 설정 (AppBar + "대시보드 준비 중" 메시지)
  - worker_approval_screen.dart: 기본 레이아웃만 설정 (AppBar + "작업자 승인 화면 준비 중" 메시지)
  - 두 화면 모두 글래스모피즘 AppBar 패턴 + GxColors.cloud 배경 적용
  - ⚠️ 실제 기능 구현은 이 Sprint 범위 아님 — 레이아웃 뼈대만

## 검증
1. `flutter build web` 에러 0건 확인
2. Admin 화면 네비게이션 정상 동작 확인
3. 알림 리스트 렌더링 확인

## 규칙
- UI_SPRINT.md의 레퍼런스 패턴 참조
- 기능 코드 절대 변경 금지
- admin_dashboard, worker_approval_screen은 최소한의 뼈대만 구현
```

---

## 🔍 Phase 5 프롬프트 — 최종 검증 + 통일성 점검 (복사해서 사용)

```
CLAUDE.md를 읽고, UI_SPRINT.md를 참조해서 최종 검증을 진행해줘.

## 팀 구성
1명의 teammate를 생성해줘. Sonnet 모델 사용:

1. **FE** (Frontend 담당) - 소유: frontend/**

## 목표
전체 화면의 글래스모피즘 통일성 최종 점검 + 빌드 확인.

### FE 작업 순서:

**1. 전체 화면 코드 리뷰**
모든 화면 파일을 읽고 아래 체크리스트 확인:

체크리스트:
- [ ] 모든 카드 컨테이너가 GxGlass.cardSm() 또는 GxGlass.card() 사용
- [ ] 잔존하는 `GxShadows.card` → `GxGlass.cardSm()` 교체 필요한 곳 확인
- [ ] AppBar 패턴 통일 (화이트 배경 + 인디고 액센트 바 + 하단 구분선)
- [ ] Primary 버튼이 그라디언트 패턴 사용 (ElevatedButton 잔존 여부 확인)
- [ ] 상태 뱃지 스타일 통일 (statusColor.withValues(alpha: 0.08) 배경)
- [ ] 텍스트 색상 통일 (GxColors.charcoal/slate/steel 일관성)
- [ ] fontSize 체계 통일 (타이틀 15, 본문 13, 라벨 11, 캡션 10)

**2. 불일치 항목 수정**
위 체크리스트에서 발견된 불일치 항목 수정.

**3. flutter build web 최종 빌드**
- `flutter build web` 실행
- 에러 0건 확인
- warning 최소화

**4. 결과 보고**
수정된 파일 목록과 변경 사항을 정리해서 보고.

## 규칙
- 기능 코드 절대 변경 금지 (UI 스타일만)
- 새 파일 생성 금지
- 빌드 에러 발생 시 즉시 수정
```

---

## 전체 Phase 요약

| Phase | 대상 | 파일 수 | 예상 시간 |
|-------|------|---------|----------|
| Phase 1 | Auth 화면 | 4개 | login, register, verify_email, approval_pending |
| Phase 2 | 메인 화면 | 3개 | home, qr_scan, task_management |
| Phase 3 | Task + 위젯 | 4개 | task_detail, task_card, process_alert_popup, completion_badge |
| Phase 4 | Admin 화면 | 3개 | alert_list, admin_options, admin_dashboard, worker_approval |
| Phase 5 | 최종 검증 | 전체 | 통일성 점검 + 빌드 |

---

## 핵심 규칙 (모든 Phase 공통)

1. **기능 코드 변경 금지**: API 호출, 네비게이션, 상태 관리, 폼 검증 등 로직 코드는 절대 수정하지 않음
2. **UI 스타일만 변경**: 색상, 그림자, 테두리, 배경, 버튼 스타일만 수정
3. **design_system.dart 토큰 사용**: 하드코딩 색상/값 금지, 반드시 GxColors/GxGlass/GxGradients 사용
4. **splash_screen.dart 참조**: 완성된 레퍼런스 화면의 패턴을 따름
5. **빌드 확인 필수**: 매 Phase 완료 시 `flutter build web` 에러 0건 확인
6. **위젯 인터페이스 유지**: 위젯의 constructor, props, 콜백은 변경 금지
7. **import 정리**: 불필요한 import 추가 금지, `dart:ui`는 BackdropFilter 사용 시에만

---

## 완료 조건

✅ 전체 12개 화면 + 3개 위젯 글래스모피즘 적용
✅ AppBar 스타일 100% 통일
✅ 카드 컨테이너 GxGlass.cardSm() 적용
✅ Primary 버튼 그라디언트 패턴 적용
✅ `flutter build web` 에러 0건
✅ 기존 기능 regression 0건
