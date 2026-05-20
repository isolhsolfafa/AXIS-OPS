# GCP Migration — Standby 상태 기록

> **마지막 업데이트**: 2026-05-20 KST
> **목적**: GCP migration 준비 100% 완료 + 비용 협의로 hold. 재오픈 시 이 문서만 보면 30분 내 cutover 가능하도록 컨텍스트 보존.

---

## 1. 현재 상태 요약 (2026-05-20)

| 환경 | 상태 | 비고 |
|------|------|-----|
| **Railway BE + DB** | ✅ 운영 중 (prod, 사용자 150명) | Auto Deploys **ON 복원** (2026-05-20 stop 후 재활성화) |
| **Netlify FE** | ✅ Railway URL 가리킴 | `https://gaxis-ops.co.kr` |
| **GCP Cloud SQL** | ⏸️ **STOPPED** (activation policy=NEVER) | data + schema + 운영 데이터 dump 보존 |
| **GCP Cloud Run** | 🗑️ **DELETED** (2026-05-20 Sentry 폭주 차단) | service 자체 삭제 — 재오픈 시 재생성 |
| **GCP Cloud Build trigger** | 🗑️ **DELETED** (2026-05-20) | GitHub push 자동 빌드 차단 — 재오픈 시 재생성 |
| **GCP Artifact Registry** | ✅ 이미지 보존 (`cloud-run-source-deploy`) | 재오픈 시 push 안 해도 됨 (이미지 재사용 가능) |

**hold 이유**: GCP 운영 비용 (Cloud SQL Enterprise Plus ~$300/월 다운사이즈 후) Railway 대비 10배+ 증가 → 비용 협의 후 재개 결정.

**재오픈 트리거**:
- Railway 장애 재발 시 (2026-05-19 Railway 부분 장애로 migration 시작했던 배경)
- 또는 비용 협의 완료 후 정식 cutover 결정 시

---

## 2. GCP 자원 식별자 (재오픈 시 그대로 사용)

| 자원 | 값 | 비고 |
|------|---|-----|
| **GCP 프로젝트 ID** | `g-axis-prod` | |
| **계정** | `angdredong@gmail.com` | gcloud auth login |
| **Cloud SQL 인스턴스** | `g-axis-core` | PostgreSQL 18, asia-northeast3 |
| **Cloud SQL 연결 이름** | `g-axis-prod:asia-northeast3:g-axis-core` | Unix socket path |
| **Cloud SQL Edition** | `ENTERPRISE_PLUS` (다운그레이드 직접 불가) | 변경 시 새 인스턴스 |
| **Cloud SQL Tier** | `db-perf-optimized-N-2` (2 vCPU/16 GB, ~$300/월) | 다운사이즈 완료 (8/64 → 2/16) |
| **Cloud SQL availability** | `ZONAL` (HA OFF) | 비용 절감 |
| **Cloud SQL 백업** | enabled, 15개 보관, 02:00~06:00 KST | |
| **Cloud SQL PITR** | enabled, 7일 보관 | |
| **Cloud SQL Public IP** | `34.64.46.218` / outgoing `34.50.33.199` | 참고용 |
| **DB 이름** | `axis-core` | |
| **DB 사용자** | `axis_core_app` | |
| **DB 비밀번호** | (Secret Manager로 migration 권장. 평문 기록 X) | 현재 Cloud Run env 평문 — 추후 회전 |
| **Cloud Run 서비스** | `axis-core-api` (🗑️ 삭제됨, 재오픈 시 재생성) | asia-northeast3 |
| **Cloud Run URL (이전)** | `https://axis-core-api-239127335594.asia-northeast3.run.app` | 재생성 시 같은 이름 → 같은 URL 가능성 높음 (project number 239127335594 고정) |
| **Cloud Run 권장 설정** | 2 GiB / 1 vCPU / CPU 항상 할당 / 시작 부스트 ON / concurrency 40 / min=1 / max=1 | 재오픈 시 재적용 |
| **Cloud Build trigger** | GitHub `isolhsolfafa/AXIS-OPS` main 브랜치 자동 빌드 (🗑️ 삭제됨, 재오픈 시 재생성) | `backend/Dockerfile` 경로 |
| **Artifact Registry 이미지** | `asia-northeast3-docker.pkg.dev/g-axis-prod/cloud-run-source-deploy/axis-ops/axis-core-api` | |

---

## 3. 환경변수 12개 (Cloud Run에 등록됨)

```
DATABASE_URL=postgresql://axis_core_app:<URL-encoded-password>@/axis-core?host=/cloudsql/g-axis-prod:asia-northeast3:g-axis-core
JWT_SECRET_KEY=<Railway 값과 동일 — 로그인 토큰 유지>
JWT_REFRESH_SECRET_KEY=<Railway 값과 동일>
SMTP_HOST=jmp.ktbizoffice.com
SMTP_PORT=465
SMTP_USER=dkkim1@gst-in.com
SMTP_PASSWORD=<KT 그룹웨어 비밀번호>
SMTP_FROM_NAME=G-AXIS
SMTP_FROM_EMAIL=dkkim1@gst-in.com
SENTRY_DSN=https://...@o4511292278046720.ingest.us.sentry.io/4511292281389056
DB_POOL_MAX=30
DB_POOL_MIN=5
```

⚠️ **DATABASE_URL typo 주의**: 이전 catch — `asia-northe   ast3` 공백 typo로 BE가 Unix socket 못 찾던 사고. paste 시 한 줄로 정확히 입력 필수.

⚠️ **보안**: 위 값들 평문 채팅 노출됨. cutover 안정화 후 회전 + Secret Manager 마이그레이션 권고.

---

## 4. 재오픈 절차 — 30분 안에 cutover

### Step 1: Cloud SQL 시작 (~5분)

```bash
gcloud sql instances patch g-axis-core --activation-policy=ALWAYS

# 또는 콘솔: Cloud SQL → g-axis-core → "시작" 버튼
# 상태가 RUNNABLE 될 때까지 대기 (~3~5분)
gcloud sql instances describe g-axis-core --format="value(state)"
```

### Step 2: Cloud Run service 재생성 (~5분, 2026-05-20 service 삭제됨)

Cloud Build trigger도 함께 삭제됐으므로 GCP 콘솔에서 재생성:

```
GCP 콘솔 → Cloud Run → "서비스 만들기"
  - 소스 저장소에서 지속적 배포 선택
  - GitHub repo: isolhsolfafa/AXIS-OPS / branch: ^main$
  - 빌드 유형: Dockerfile / 소스 위치: /backend/Dockerfile
  - 서비스 이름: axis-core-api / 리전: asia-northeast3
  - 인증: 공개 액세스 허용
  - 자동 확장: min=1, max=1 (또는 2)
  - 컨테이너: 메모리 2 GiB / CPU 1 / 시작 부스트 ON / CPU 항상 할당
  - Cloud SQL 연결: g-axis-prod:asia-northeast3:g-axis-core 추가
  - 환경변수 12개 등록 (Section 3 참조) — DATABASE_URL typo (공백) 주의
  - "만들기" → Cloud Build 자동 실행 + 첫 revision 배포

또는 Artifact Registry에 이미지 보존돼 있으므로:
gcloud run deploy axis-core-api \
  --image=asia-northeast3-docker.pkg.dev/g-axis-prod/cloud-run-source-deploy/axis-ops/axis-core-api:latest \
  --region=asia-northeast3 \
  --add-cloudsql-instances=g-axis-prod:asia-northeast3:g-axis-core \
  --memory=2Gi --cpu=1 --min-instances=1 --max-instances=1 \
  --set-env-vars="DATABASE_URL=...,JWT_SECRET_KEY=...,..."
```

→ Cloud Run URL 새로 생성됨. project number `239127335594` 고정이므로 **같은 이름으로 만들면 URL 동일할 가능성 높음**: `https://axis-core-api-239127335594.asia-northeast3.run.app`

### Step 3: Cloud SQL DB 초기화 + Railway 최신 dump → restore (~10분)

```bash
# 3-1. Cloud SQL Auth Proxy 시작 (백그라운드)
cloud-sql-proxy g-axis-prod:asia-northeast3:g-axis-core --port=5433 &

# 3-2. Cloud SQL axis-core DB 비우기 (이전 dump + Cloud Run cron noise 정리)
# 옵션 A: 모든 테이블 drop (스키마는 새로 만들어짐)
/opt/homebrew/opt/postgresql@18/bin/psql "postgresql://axis_core_app:<PW>@127.0.0.1:5433/axis-core" -c "
  DROP SCHEMA IF EXISTS public CASCADE;
  DROP SCHEMA IF EXISTS plan CASCADE;
  DROP SCHEMA IF EXISTS hr CASCADE;
  DROP SCHEMA IF EXISTS checklist CASCADE;
  DROP SCHEMA IF EXISTS defect CASCADE;
  DROP SCHEMA IF EXISTS auth CASCADE;
  DROP SCHEMA IF EXISTS analytics CASCADE;
  DROP SCHEMA IF EXISTS etl CASCADE;
  CREATE SCHEMA public;
"

# 3-3. Railway DB 최신 dump
RAILWAY_URL="postgresql://postgres:<RW_PW>@maglev.proxy.rlwy.net:38813/railway?sslmode=require"
/opt/homebrew/opt/postgresql@18/bin/pg_dump "$RAILWAY_URL" \
  --no-owner --no-acl --no-publications --no-subscriptions \
  -f /tmp/railway-dump-cutover.sql

# 3-4. Cloud SQL에 restore
/opt/homebrew/opt/postgresql@18/bin/psql \
  "postgresql://axis_core_app:<PW>@127.0.0.1:5433/axis-core" \
  -f /tmp/railway-dump-cutover.sql

# 3-5. 검증
/opt/homebrew/opt/postgresql@18/bin/psql "postgresql://axis_core_app:<PW>@127.0.0.1:5433/axis-core" \
  -c "SELECT COUNT(*) FROM workers; SELECT COUNT(*) FROM qr_registry;"
# 기대: workers 200+, qr_registry 2800+
```

### Step 4: FE API_BASE_URL 변경 + Netlify 배포 (~10분)

```dart
// frontend/lib/utils/constants.dart
// 변경 전 (Railway):
// const String API_BASE_URL = 'https://axis-ops-api.up.railway.app';
// 변경 후 (Cloud Run):
const String API_BASE_URL = 'https://axis-core-api-239127335594.asia-northeast3.run.app';
```

```bash
cd frontend
flutter build web --release
npx netlify-cli deploy --prod \
  --dir=build/web \
  --site=ab8041c3-dc51-40c6-96e4-9966222aeda3
```

### Step 5: curl 검증

```bash
URL="https://axis-core-api-239127335594.asia-northeast3.run.app"
curl -sS "$URL/health"
# 기대: {"version":"2.18.x","status":"ok",...}

curl -sS -X POST -H "Content-Type: application/json" \
  -d '{"email":"dkkim1@gst-in.com","password":"wrong"}' \
  "$URL/api/auth/login"
# 기대: INVALID_PASSWORD (admin 발견 = DB 정상)
```

### Step 6: Cutover 후 모니터링 (~30분)

- Sentry 새 ERROR 0 확인
- 실 사용자 로그인 1건 테스트
- 1주 hot standby로 Railway 유지 → 안정화 확인 후 Railway 폐기

---

## 5. 코드 변경 trail (재오픈 시 이미 적용됨)

| 변경 | commit | 내용 |
|------|--------|-----|
| `backend/Dockerfile` 신규 | `affea54` | Cloud Run 배포용. gunicorn `-w 1 --timeout 0`, Python 3.11.11-slim, PORT=8080 |
| `backend/.dockerignore` 신규 | `affea54` | 빌드 context 최적화 |
| `CLAUDE.md` Codex 채널 정정 | `9b43e66` | brew → npm `@openai/codex` (2026-05-20 VIEW catch) |
| `backend/app/config.py` fallback 제거 (v2.18.3) | `3fb98cd` | Railway DB URL 하드코딩 제거, `RuntimeError` fail-fast |

→ Railway 영향: Auto Deploys ON 복원으로 다음 push 시 자동 배포. 코드 변경은 모두 호환 (Railway env에 DATABASE_URL 이미 설정됨).

---

## 6. 비용 추적 + 알림 가이드

### 현재 burn rate (standby)

| 자원 | 일일 | 월간 |
|------|------|------|
| Cloud SQL stopped (storage 100GB) | ~$0.62 | ~$18.7 |
| Cloud Run min=0 idle | ~$0 | <$1 |
| **Total** | **~$0.6/일** | **~$20/월** |

→ free trial $300 으로 **약 500일** 유지 가능 (사실상 무한).

### 재오픈 시 burn rate (운영)

| 자원 | 일일 | 월간 |
|------|------|------|
| Cloud SQL N-2 (Enterprise Plus 2vCPU/16GB) | ~$10 | ~$300 |
| Cloud Run min=1 (CPU 항상 할당) | ~$0.7 | ~$21 |
| Storage + 기타 | ~$0.7 | ~$20 |
| **Total** | **~$11.5/일** | **~$340/월** |

### 추가 다운사이즈 (안정화 후)

- Enterprise Plus → Enterprise (Standard): 새 인스턴스 필요. 월 ~$150 (50% 절감)
- HA OFF 유지 + 가장 작은 머신: 월 ~$100

### 예산 알림 권고

```
GCP 콘솔 → 결제 → "예산 및 알림" → 새 예산
  이름: g-axis-prod-trial
  금액: $300 (free trial 한도)
  알림: 50% / 75% / 90% / 100%
  → 이메일 angdredong@gmail.com
```

---

## 7. Free Trial 만료 알림 (~2026-06-19)

GCP free trial 30일이라 만료 시점 도래:
- 정확한 날짜: GCP 콘솔 → 결제 → "체험판" 섹션
- 만료 후 stopped 상태라도 storage 비용 ~$20/월 자동 청구 시작
- 신용카드 등록 안 했으면 GCP 자동 모든 자원 일시정지 가능

**만료 전 결정 트리거**:
- A) cutover 진행 → 월 ~$340 운영 비용 수용
- B) 모든 GCP 자원 delete (Cloud SQL + Cloud Run) → 월 $0, 다음에 처음부터 재구축
- C) 신용카드 등록 + standby 유지 → 월 ~$20

---

## 8. pytest 환경 — Railway 폐기 시 마이그레이션 필요

```
현재: TEST_DATABASE_URL = postgresql://postgres:***@centerbeam.proxy.rlwy.net:20196/railway
                                            ↑ Railway 별도 staging DB (Sprint 39, 2026-03-26)
```

Railway 완전 폐기 시 pytest 환경도 옮겨야 함. 옵션:
- **옵션 A** (recommended): Cloud SQL `g-axis-core` 인스턴스 안에 `axis-core-test` DB 추가 생성 (월 비용 0, 같은 인스턴스 내)
- 옵션 B: 별도 작은 Cloud SQL 인스턴스 (월 ~$10)
- 옵션 C: GitHub Actions service container PostgreSQL

→ cutover 안정화 후 별 sprint로 처리.

---

## 9. 잠재 catch + 별 sprint

| 항목 | 우선순위 | 비고 |
|------|---------|-----|
| APScheduler `/tmp/axis_ops_scheduler.lock` multi-instance 한계 | 🟡 LOW | max_instances=10 + scale-out 시 cron 중복 fire. 트래픽 낮아 실 발생 가능성 낮음. PostgreSQL advisory lock 도입은 별 sprint |
| Dockerfile JSON CMD 형태 (linter 경고) | 🟢 advisory | shell `exec gunicorn` 이라 signal 전파 정상. 별 sprint로 JSON array 변경 권고 |
| Cloud Run non-root user | 🟢 advisory | 보안 강화, ~5줄 추가 |
| Cloud Run에 stop된 동안 cron이 쌓은 noise (alert_logs 등) | 🟢 cleanup 시 처리 | restore 시 `DROP SCHEMA ... CASCADE` 또는 `pg_restore --clean` 으로 자동 정리 |
| 평문 비밀번호 회전 (Railway DB, JWT keys, SMTP) | 🟠 MEDIUM | cutover 안정화 후 Secret Manager 마이그레이션 시 함께 |
| Codex CLI 채널 (npm vs brew) | ✅ 처리됨 | 2026-05-20 CLAUDE.md 정정 |

---

## 10. 컨텍스트 요약 — 한 줄

> Railway prod 운영 중 + GCP standby (stopped) + 재오픈 30분 + 모든 코드/이미지/env 준비 완료. 비용 협의 결과 또는 Railway 장애 재발 시 즉시 재오픈 가능.

---

**문서 작성일**: 2026-05-20 KST
**작성 트리거**: 사용자 hold 결정 + 비용 협의 시간 확보
**다음 검토 시점**: 비용 협의 완료 OR free trial 만료 (~2026-06-19) OR Railway 장애 재발
