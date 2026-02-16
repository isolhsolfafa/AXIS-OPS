"""
라우트 모듈
TODO: 라우트 에러 핸들러
TODO: 요청 검증 미들웨어
"""

from flask import Blueprint
from app.routes.auth import auth_bp
from app.routes.work import work_bp
from app.routes.product import product_bp
from app.routes.alert import alert_bp
from app.routes.admin import admin_bp
from app.routes.sync import sync_bp

__all__ = [
    "auth_bp",
    "work_bp",
    "product_bp",
    "alert_bp",
    "admin_bp",
    "sync_bp",
]
