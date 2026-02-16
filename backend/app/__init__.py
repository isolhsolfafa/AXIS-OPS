"""
Flask 앱 팩토리
Sprint 1: 인증 API + 에러 핸들러
Sprint 2: work, product blueprint 등록
"""

import logging
from flask import Flask, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO

from app.config import Config


logger = logging.getLogger(__name__)

socketio = SocketIO(cors_allowed_origins="*")


def create_app(config_class: type = Config) -> Flask:
    """
    Flask 애플리케이션 팩토리

    Args:
        config_class: 설정 클래스

    Returns:
        Flask 애플리케이션 인스턴스
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 로깅 설정
    logging.basicConfig(
        level=logging.DEBUG if app.config['DEBUG'] else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # CORS 설정
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    logger.info("CORS configured for /api/*")

    # SocketIO 초기화 (Sprint 3)
    socketio.init_app(app)

    # WebSocket 이벤트 핸들러 등록 (Sprint 3)
    from app.websocket.events import register_events
    register_events(socketio)
    logger.info("WebSocket events registered")

    # 블루프린트 등록
    from app.routes.auth import auth_bp
    from app.routes.work import work_bp
    from app.routes.product import product_bp
    from app.routes.alert import alert_bp  # Sprint 3

    app.register_blueprint(auth_bp)
    app.register_blueprint(work_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(alert_bp)
    logger.info("Blueprints registered: auth, work, product, alert")

    # Sprint 4+에서 추가 예정:
    # from app.routes.admin import admin_bp
    # from app.routes.sync import sync_bp

    # 헬스 체크 엔드포인트
    @app.route("/health", methods=["GET"])
    def health_check():
        """헬스 체크"""
        return jsonify({"status": "ok", "message": "Server is running"}), 200

    # 404 에러 핸들러
    @app.errorhandler(404)
    def not_found(error):
        """404 Not Found 에러 핸들러"""
        return jsonify({
            "error": "NOT_FOUND",
            "message": "요청한 리소스를 찾을 수 없습니다."
        }), 404

    # 500 에러 핸들러
    @app.errorhandler(500)
    def internal_error(error):
        """500 Internal Server Error 에러 핸들러"""
        logger.error(f"Internal server error: {error}")
        return jsonify({
            "error": "INTERNAL_SERVER_ERROR",
            "message": "서버 내부 오류가 발생했습니다."
        }), 500

    # 일반 예외 핸들러
    @app.errorhandler(Exception)
    def handle_exception(error):
        """일반 예외 핸들러"""
        logger.error(f"Unhandled exception: {error}", exc_info=True)
        return jsonify({
            "error": "INTERNAL_SERVER_ERROR",
            "message": "서버 내부 오류가 발생했습니다."
        }), 500

    logger.info("Flask app created successfully")
    return app
