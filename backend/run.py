"""
Flask 앱 실행 엔트리 포인트
Sprint 1: 개발 서버 (0.0.0.0:5001)
"""

import os
from app import create_app, socketio

if __name__ == "__main__":
    app = create_app()

    # 환경변수에서 읽기 (fallback: 기본값)
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("FLASK_PORT", "5001")))
    debug = os.getenv("FLASK_DEBUG", "True").lower() == "true"

    print(f"Starting Flask server on {host}:{port} (debug={debug})")

    # SocketIO 개발 서버 실행
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
