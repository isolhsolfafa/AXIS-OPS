# 개발 개념 레퍼런스

> 유튜브 학습 + AXIS SYSTEM 점검 보고서(2026-03-22) 연계 정리
> 작성일: 2026-03-31

---

## 1. 소프트웨어 설계 원칙

### MECE (Mutually Exclusive, Collectively Exhaustive)

항목 간 **중복 없이**, 전체적으로 **누락 없이** 분류하는 원칙. 맥킨지 컨설팅에서 유래.

**적용 중인 곳:**
- handoff.md Sprint 우선순위: 🔴즉시 / 🟡중기 / 🟢장기 (겹치지 않고 빠짐없이)
- task_category: MECH / ELEC / TMS / PI / QI / SI (공정 분류)
- 테스트 케이스: TC-41A-01~21 (시나리오별 MECE 분류)

**적용 필요한 곳:**
- API 엔드포인트 분류 (현재 admin.py에 20개+ 혼재 → 점검 보고서 §3.2 "God Route 문제")
- 에러 코드 체계 (TASK_NOT_FOUND / TASK_ALREADY_COMPLETED / FORBIDDEN 등이 일관성 부족)

---

### 멱등성 (Idempotency)

같은 요청을 **여러 번 보내도 결과가 동일**한 성질. API 설계의 핵심 원칙.

- GET: 본질적으로 멱등 (조회만 하니까)
- PUT: 멱등이어야 함 (같은 데이터로 업데이트 → 결과 동일)
- POST: 기본적으로 멱등 아님 (중복 생성 위험)
- DELETE: 멱등이어야 함 (이미 삭제된 것 다시 삭제해도 에러 아님)

**현재 시스템 적용 사례:**
- `complete_work()`: `TASK_ALREADY_COMPLETED` 체크 → 중복 완료 방지 ✅
- `start_work()`: `TASK_ALREADY_STARTED` 체크 → 중복 시작 방지 ✅
- `reactivate_task()`: 이미 재활성화된 task → 어떻게 되는지? → 검증 필요

**점검 보고서 연계:** §3.3 "트랜잭션 관리" — 부분 실패 시 멱등성 보장 안 됨. UnitOfWork 패턴으로 해결 권고.

---

### Linter

코드 실행 **전에** 문법 오류, 스타일 위반, 잠재적 버그를 자동 감지하는 도구.

| 언어 | Linter | 현재 프로젝트 적용 |
|------|--------|-------------------|
| Python (OPS BE) | `flake8`, `ruff` | ❌ 미적용 |
| Dart (OPS FE) | `dart analyze` | ⚠️ 부분 적용 |
| TypeScript (VIEW) | `eslint` | ⚠️ 부분 적용 |

**점검 보고서 연계:** §2.6 / §5-#5 "테스트 기반 구축" — linter는 테스트보다 도입 비용이 낮으면서 버그 예방 효과가 큼. 커밋 전 자동 실행(pre-commit hook) 권장.

---

## 2. 문서화 / 설계 프레임워크

### Context → Problem → Solution 프레임워크

문서를 쓸 때 쓰는 구조화 프레임워크:

```
Context (배경): 상황이 이렇고
Problem (문제): 이런 문제가 있고
Solution (수정): 이렇게 해결한다
```

**현재 적용 중:** AGENT_TEAM_LAUNCH.md의 모든 Sprint가 이 구조:
- "배경" → Context
- "원인" / "원인 분석" → Problem
- "수정 방침" / Task 0~N → Solution

**점검 보고서 연계:** 보고서 자체가 이 프레임워크로 작성됨:
- §1 감사 개요 (Context) → §4 위험 평가 (Problem) → §5 우선 조치 항목 (Solution)

---

### PRD (Product Requirements Document)

**무엇을 왜 만드는지**, 성공 기준이 뭔지 정의하는 제품 요구사항 문서.

구성 요소:
- 배경/목적 (Why)
- 사용자 스토리 (Who + What)
- 기능 요구사항 (What — 상세)
- 성공 지표 (How to measure)
- 기술 제약사항 (Constraints)

**현재 시스템에서의 대응:**
- Sprint 문서 = 간이 PRD (배경 + 수정 방침 + 테스트)
- OPS_API_REQUESTS.md = API 수준 PRD (증상 + 원인 + 수정 요청 + 검증)
- DESIGN_FIX_SPRINT.md = 설계 수준 PRD (VIEW Sprint 23)

---

### Blueprint (블루프린트)

시스템 전체 구조를 한눈에 보여주는 **설계도/청사진**.

- 인프라: AWS/Azure에서 서버·DB·네트워크 전체 구성도
- 소프트웨어: 시스템 아키텍처 다이어그램 (어떤 서비스가 어떤 DB를 쓰고, 어떤 API로 통신하는지)
- 데이터: ERD (테이블 간 관계도)

**현재 시스템 관련:**
- `analytics_prod_erd.mermaid`: 생산 분석 데이터 블루프린트
- 점검 보고서 §3.1: 스키마/ERD 감사 (4개 스키마, 39개 테이블, 69개 인덱스)
- APS_LITE_PLAN.md: APS 시스템 블루프린트

---

## 3. AI / LLM 엔지니어링

### "프롬프트가 아니라 하네스 깎기"

LLM을 잘 쓰려면 프롬프트 문구를 다듬는 게 아니라, **프롬프트를 감싸는 시스템(harness)**을 설계하는 게 중요하다는 개념.

하네스 = 입력 검증 + 컨텍스트 주입 + 출력 파싱 + 에러 핸들링 + 재시도 로직

**현재 시스템에서의 사례:**
- AGENT_TEAM_LAUNCH.md 자체가 하네스 — Sprint 프롬프트 + 코드 + 테스트를 구조화해서 Claude에게 주는 것
- CLAUDE.md = 프로젝트 컨텍스트 주입
- handoff.md = 세션 간 상태 전달 (하네스의 메모리 역할)

---

### MCP (Model Context Protocol)

Anthropic이 만든 표준. LLM이 **외부 도구**(DB, API, 파일시스템, 브라우저 등)에 접근하는 통일된 프로토콜.

- 지금 이 Cowork 세션이 MCP로 동작 중 (파일 읽기/쓰기, 터미널 실행 등)
- Slack, Gmail, Linear 등 외부 서비스도 MCP 커넥터로 연결 가능
- "모델컨텍스트 프로토콜" = 모델에게 컨텍스트(도구, 데이터)를 제공하는 규약

---

### RAG (Retrieval-Augmented Generation)

LLM이 답변할 때 **외부 문서를 검색해서 참조**하는 방식.

```
질문 → 문서 DB 검색 → 관련 문서 추출 → LLM에 컨텍스트로 주입 → 답변 생성
```

**활용 가능 시나리오:**
- 회사 매뉴얼/규정을 DB에 넣어두고, 작업자가 질문하면 관련 문서 기반 답변
- QMS 불량 이력 검색 → 유사 불량 사례 + 해결 방법 자동 추천
- 현재 analytics.defect_keyword 테이블(NLP 키워드 추출)이 RAG 파이프라인의 전처리 단계에 해당

---

### LangChain

LLM 애플리케이션을 만드는 **Python 프레임워크**.

주요 기능: 프롬프트 체이닝, 도구 호출, 메모리 관리, RAG 파이프라인 구축, 에이전트 생성

현재 프로젝트에는 미사용. QMS ML 파이프라인이나 APS 예측 엔진 구축 시 고려 대상.

---

### Evaluation Framework (평가 프레임워크)

LLM/RAG 시스템의 **품질을 자동으로 측정**하는 도구.

| 프레임워크 | 측정 항목 |
|-----------|----------|
| LangChain Evaluation | LLM 답변 정확도, 관련성, 일관성 |
| RAGAS | RAG 시스템 전용 — 검색 정확도(Precision), 답변 충실도(Faithfulness), 답변 관련성(Relevance) |
| DeepEval | 할루시네이션 감지, 독성 검사, 사실 확인 |

**핵심 개념:** "AI 시스템도 테스트해야 한다" — 소프트웨어 테스트(pytest, Vitest)처럼 AI 출력도 자동 평가 필요.

**점검 보고서 연계:** §2.6 "테스트 1/10" — 소프트웨어 테스트도 전무한 상태에서 AI Evaluation은 아직 먼 이야기. 소프트웨어 테스트 기반 → AI 테스트 순서.

---

### FDE

맥락 불명확. 가능한 의미:
- **Full-stack Data Engineer**: 데이터 파이프라인 전체(수집→가공→적재→시각화)를 담당하는 역할
- **Feedback-Driven Engineering**: 사용자 피드백 기반으로 개발 우선순위를 정하는 방법론
- 특정 유튜버/채널의 약어일 수도 있음

→ 영상 출처 확인되면 업데이트

---

## 4. 점검 보고서(2026-03-22) 주요 지적 vs 현재 진행 상황

| # | 점검 보고서 지적 사항 | 현재 상태 | 비고 |
|---|----------------------|----------|------|
| 1 | FK CASCADE 감사 + RESTRICT 전환 | ⏳ 미착수 | completion_status만 RESTRICT, 나머지 CASCADE |
| 2 | admin.py God Route 분리 | ⏳ 미착수 | 2,070줄 유지 중 |
| 3 | 참조 테이블 전환 (work_site, product_line) | ⏳ 미착수 | CHECK 제약 유지 중 |
| 4 | 트랜잭션 UnitOfWork 패턴 | ⏳ 미착수 | 부분 실패 위험 존재 |
| 5 | 테스트 기반 구축 | ⚠️ OPS만 부분 진행 | pytest 작성 중, VIEW 전무 |
| — | **CORS origins=\* 수정** | ⏳ 미착수 | 보안 이슈 — handoff.md에 기록됨 |
| — | **JWT_SECRET_KEY 환경변수 분리** | ⏳ 미착수 | 보안 이슈 — handoff.md에 기록됨 |

**현재 집중 방향:** 운영 안정화 (Sprint 41 릴레이 + Fix 41-A + Fix 48 + Sprint 51/52) → 점검 보고서 지적 사항은 운영 안정화 완료 후 순차 진행.

---

## 5. 용어 빠른 참조

| 용어 | 한줄 설명 | 카테고리 |
|------|----------|---------|
| MECE | 중복 없이 + 누락 없이 분류 | 설계 원칙 |
| 멱등성 | 같은 요청 N번 = 결과 동일 | 설계 원칙 |
| Linter | 코드 실행 전 자동 버그 감지 | 개발 도구 |
| C-P-S | Context → Problem → Solution 문서 구조 | 문서화 |
| PRD | 제품 요구사항 문서 | 문서화 |
| Blueprint | 시스템 전체 설계도 | 문서화 |
| 하네스 | 프롬프트를 감싸는 시스템 (입력/출력/에러) | AI 엔지니어링 |
| MCP | LLM ↔ 외부 도구 연결 프로토콜 | AI 엔지니어링 |
| RAG | 외부 문서 검색 + LLM 답변 생성 | AI 엔지니어링 |
| LangChain | LLM 앱 개발 프레임워크 | AI 엔지니어링 |
| Evaluation | AI 시스템 품질 자동 측정 | AI 엔지니어링 |
