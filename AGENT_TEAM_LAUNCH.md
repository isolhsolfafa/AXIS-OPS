# Agent Teams 실행 가이드

## 사전 조건 (이미 완료됨)
- ✅ `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` = "1" 설정 완료
- ✅ VS Code Claude 확장 Agent Teams 모드 활성화
- ✅ CLAUDE.md 팀 설정 완료
- ✅ 스캐폴드 파일 85개 생성 완료

---

## VS Code 터미널에서 실행

### Step 1: AXIS-OPS 폴더에서 Claude Code 시작
```bash
cd ~/Desktop/GST/AXIS-OPS
claude
```

### Step 2: 위임 모드 활성화
Claude Code 터미널이 열리면:
- **Shift+Tab** 을 눌러 Delegate 모드 활성화
  (리드가 직접 코드를 수정하지 않고 워커에게 위임만 함)

### Step 3: 팀 생성 프롬프트 입력
아래 프롬프트를 Claude Code 터미널에 붙여넣기:

---

## 🚀 팀 생성 프롬프트 (복사해서 사용)

```
CLAUDE.md를 읽고 Agent Teams를 구성해줘.

## 팀 구성
3명의 teammate를 생성해줘. 모든 teammate는 Sonnet 모델을 사용해:

1. **FE** (Frontend 담당)
   - 소유 파일: frontend/**
   - 절대 수정 금지: backend/**, tests/**
   - Sprint 1 작업: auth 화면 3개 (login, register, verify_email) + API 연동

2. **BE** (Backend 담당)
   - 소유 파일: backend/**
   - 절대 수정 금지: frontend/**, tests/**
   - Sprint 1 작업: DB migration 검토 → auth_service 구현 → JWT middleware → auth routes

3. **TEST** (테스트 담당)
   - 소유 파일: tests/**
   - 절대 수정 금지: backend/app/**, frontend/lib/**
   - Sprint 1 작업: conftest.py 구현 → test_auth.py 6개 테스트 케이스

## 작업 순서
Sprint 1 (인증 + DB 기반)부터 시작해줘.
BE가 먼저 시작하고, BE의 auth API가 준비되면 FE가 연동하고, TEST는 BE와 병렬로 진행.

## 규칙
- 각 teammate는 자신의 소유 파일만 수정 가능
- 코드 변경 전 반드시 나에게 승인 요청
- CLAUDE.md의 DB 규칙/API 규칙/코드 스타일 준수
- APP_PLAN_v4(26.02.16).md와 PROJECT_COMPREHENSIVE_ANALYSIS_2026(02.16).md 참조
```

---

## 주요 단축키 (실행 중 사용)

| 단축키 | 기능 |
|--------|------|
| **Shift+Tab** | Delegate 모드 토글 (리드 ↔ 직접 코드 수정) |
| **Shift+↑/↓** | Teammate 선택/전환 (직접 메시지) |
| **Ctrl+T** | 공유 Task List 보기 |
| **Escape** | 현재 Teammate 작업 중단 |

---

## 토큰 관리 전략

| 역할 | 모델 | 용도 | 토큰 효율 |
|------|------|------|----------|
| Lead (리드) | Opus | 설계 조율, 코드 리뷰, 의사결정 | 높은 품질, 토큰 많이 사용 |
| FE/BE/TEST (워커) | Sonnet | 코드 구현, 테스트 작성 | 토큰 효율적, 실행 속도 빠름 |

**핵심**: 리드(Opus)는 큰 방향만 잡고, 실제 코드 작성은 워커(Sonnet)가 수행.
이렇게 하면 Opus 토큰을 절약하면서도 아키텍처 품질을 유지할 수 있음.

---

## 트러블슈팅

### Agent Teams가 활성화되지 않을 때
```bash
# settings.json 확인
cat ~/.claude/settings.json | grep AGENT_TEAMS
# 출력: "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
```

### Teammate가 파일 소유권을 위반할 때
- Escape로 중단 → 리드에게 "파일 소유권 위반, 수정 취소해줘" 지시

### 모델을 변경하고 싶을 때
- Teammate 생성 시 "이 teammate는 Opus를 사용해" 라고 지시
