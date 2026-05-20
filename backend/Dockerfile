# syntax=docker/dockerfile:1
# AXIS-OPS BE — Cloud Run 배포용 (GCP migration, 2026-05-20)
#
# 이 파일은 backend/ 안에 위치합니다. 이유:
# - 루트에 두면 Railway nixpacks 가 우선 사용해 Railway 빌드 영향 발생
# - backend/ 안에 두면 Railway nixpacks 는 루트 Procfile/requirements.txt 그대로 사용 (영향 0)
# - Cloud Build 콘솔에서 "소스 위치 = /backend/Dockerfile" 로 지정
#
FROM python:3.11.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# psycopg2-binary 는 self-contained 이지만 SSL/CA 정합을 위해 ca-certificates 추가
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# build context = backend/ — 따라서 requirements.txt 는 그대로
# Layer 캐싱 최적화 (코드 변경 시 deps 재설치 회피)
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# 애플리케이션 코드 (backend/ 전체를 /app 으로)
COPY . ./

# Cloud Run 은 $PORT 환경변수 주입 (기본 8080)
ENV PORT=8080
EXPOSE 8080

# gunicorn — Cloud Run 권장 설정
#  -w 1            : 인스턴스당 1 worker (APScheduler in-process 중복 fire 방지)
#  --threads 8     : I/O 동시성 (flask-sock + DB 호출)
#  --timeout 0     : Cloud Run request timeout(300s)에 맡김
#  --graceful-timeout 30 : SIGTERM 시 in-flight 요청 마감 시간
CMD exec gunicorn --bind 0.0.0.0:$PORT \
    --worker-class gthread --threads 8 -w 1 \
    --timeout 0 --graceful-timeout 30 \
    --access-logfile=- --log-level=info \
    "app:create_app()"
