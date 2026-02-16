"""
Flask 애플리케이션 설정
TODO: 환경변수에서 설정값 읽기
TODO: staging/production 환경 분리
"""

import os
from datetime import timedelta


class Config:
    """기본 설정"""
    
    # 데이터베이스
    # Staging DB (Railway)
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:aemQKKvZhddWGlLUsAghiWAlzFkoWugL@maglev.proxy.rlwy.net:38813/railway"
    )
    
    # JWT 설정
    # TODO: 환경변수에서 읽기, production은 강력한 secret 사용
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    
    # SQLAlchemy 설정
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # SocketIO 설정
    # TODO: redis/rabbitmq 메시지 큐 설정
    SOCKETIO_MESSAGE_QUEUE = None
    
    # 보안
    # TODO: production 환경에서 설정값 검증
    DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    TESTING = False
