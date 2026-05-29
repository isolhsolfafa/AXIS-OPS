"""
Flask 애플리케이션 설정
Sprint 5: python-dotenv 적용, SMTP 설정 추가, Refresh Token 만료 설정
"""

import os
from datetime import timedelta, timezone
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


# backend/.env 파일 로드 (파일이 없어도 오류 없음)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))


class Config:
    """기본 설정 — 모든 값은 .env에서 읽고 기본값 fallback"""

    # --- 데이터베이스 ---
    # v2.18.3 (2026-05-20, GCP migration): hardcoded Railway DB URL fallback 제거.
    # 사고: Cloud Run 첫 부팅 시 env DATABASE_URL 누락 → fallback 으로 Railway DB 에
    # 의도치 않게 연결되던 catch (2026-05-20 cutover 준비 중 발견).
    # 현재: env 필수 — Cloud Run/Railway 환경변수 등록 또는 backend/.env 파일 필수.
    # 테스트: conftest.py 가 TEST_DATABASE_URL → DATABASE_URL 으로 import 전 셋팅.
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL 환경변수 미설정 — Cloud Run/Railway env 등록 필수. "
            "테스트는 TEST_DATABASE_URL 셋팅 후 conftest.py 가 자동 매핑."
        )

    # --- JWT ---
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        "dev-secret-key-change-in-production"
    )
    # Refresh Token 전용 시크릿 (Access Token과 분리)
    JWT_REFRESH_SECRET_KEY: str = os.getenv(
        "JWT_REFRESH_SECRET_KEY",
        "dev-refresh-secret-key-change-in-production"
    )
    JWT_ACCESS_TOKEN_EXPIRES: timedelta = timedelta(hours=2)
    JWT_REFRESH_TOKEN_EXPIRES: timedelta = timedelta(days=30)

    # --- SMTP ---
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "G-AXIS")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "noreply@gst-in.com")

    # --- SQLAlchemy (미사용, 하위 호환용) ---
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # --- SocketIO ---
    SOCKETIO_MESSAGE_QUEUE = None

    # --- Timezone ---
    # v2.20.3 fix (2026-05-29): APScheduler CronTrigger 가 stdlib `timezone(timedelta)`
    # 를 KST 로 정확히 인식 못해 시간 단위 cron 이 UTC 로 해석됨 (07:30 KST → 16:30 KST 로 9h 지연 fire).
    # IANA tz (ZoneInfo) 로 변경하면 APScheduler 가 KST 로 정확히 인식.
    # 이전: timezone(timedelta(hours=9))  # 시간 단위 cron 9시간 지연 버그
    KST = ZoneInfo('Asia/Seoul')  # Asia/Seoul (UTC+9)

    # --- Flask ---
    DEBUG: bool = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    TESTING: bool = False
