"""
Flask 애플리케이션 설정
Sprint 5: python-dotenv 적용, SMTP 설정 추가, Refresh Token 만료 설정
"""

import os
from datetime import timedelta, timezone

from dotenv import load_dotenv


# backend/.env 파일 로드 (파일이 없어도 오류 없음)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))


class Config:
    """기본 설정 — 모든 값은 .env에서 읽고 기본값 fallback"""

    # --- 데이터베이스 ---
    # Staging DB (Railway) — 운영은 .env에서 반드시 덮어쓸 것
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:aemQKKvZhddWGlLUsAghiWAlzFkoWugL@maglev.proxy.rlwy.net:38813/railway"
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
    KST = timezone(timedelta(hours=9))  # Asia/Seoul (UTC+9)

    # --- Flask ---
    DEBUG: bool = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    TESTING: bool = False
