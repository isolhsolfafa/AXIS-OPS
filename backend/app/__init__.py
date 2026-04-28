"""
Flask 앱 팩토리
Sprint 1: 인증 API + 에러 핸들러
Sprint 2: work, product blueprint 등록
Sprint 13: Flask-SocketIO → flask-sock 마이그레이션
"""

import logging
import os
import sys
from flask import Flask, jsonify, g, request
from flask_cors import CORS
from flask_sock import Sock

from app.config import Config


logger = logging.getLogger(__name__)

sock = Sock()


# FIX-WEBSOCKET-STOPITERATION-SENTRY-NOISE-20260428:
# flask-sock wsgi generator drain 시 발생하는 StopIteration 정상 종료 시그널을
# Sentry capture 에서 분리. 매칭 조건 3개 모두 성립 시만 drop 하므로 다른 곳의
# StopIteration 추적은 보존됨. 모듈 top-level 정의 (test 가 import 가능하도록).
def _sentry_before_send(event, hint):
    """
    Sentry event 필터.

    매칭 조건 (모두 성립 시 None 반환 → Sentry 미전송):
      - exception.values[0].type == 'StopIteration'
      - exception.values[0].mechanism.type == 'wsgi'
      - event.transaction == 'websocket_route'

    한 조건이라도 어긋나면 정상 capture (false negative 방지).
    필터 자체 실패 시에도 정상 capture (안전 fallback).
    """
    try:
        exc_info = event.get('exception', {}).get('values', [])
        if not exc_info:
            return event
        first = exc_info[0]
        exc_type = first.get('type', '')
        mechanism = first.get('mechanism', {}) or {}
        mechanism_type = mechanism.get('type', '')
        transaction = event.get('transaction', '')

        if (exc_type == 'StopIteration'
                and mechanism_type == 'wsgi'
                and transaction == 'websocket_route'):
            return None  # 잡음 → drop
    except Exception:
        pass  # 필터 자체 실패 시 정상 capture (안전 fallback)
    return event


# OBSERV-ALERT-SILENT-FAIL-20260427: Sentry 정식 연동
# DSN 환경변수 없으면 graceful skip (로컬/test 환경 호환).
# 4-22 알람 silent failure 5일 누적 사례 (HOTFIX-ALERT-SCHEDULER-DELIVERY) 의
# 외부 자동 감지 layer. migration 실패, scheduler 죽음, target_worker_id NULL
# 다발 등 ERROR/CRITICAL 자동 capture → Sentry alert rule 로 즉시 알림.
def _init_sentry() -> None:
    """Sentry SDK 초기화 — DSN 없으면 graceful skip."""
    dsn = os.environ.get('SENTRY_DSN', '').strip()
    if not dsn:
        logger.info("[sentry] SENTRY_DSN not set, skipping Sentry init (local/test env)")
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        environment = os.environ.get('SENTRY_ENVIRONMENT', 'production')
        # version.py 의 VERSION 가져오기 (release 추적)
        try:
            from version import VERSION as _release
        except Exception:
            _release = None

        sentry_sdk.init(
            dsn=dsn,
            integrations=[
                FlaskIntegration(),
                LoggingIntegration(
                    level=logging.INFO,        # breadcrumb 으로 INFO 까지 수집
                    event_level=logging.ERROR,  # ERROR 이상은 event 로 capture
                ),
            ],
            traces_sample_rate=float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '0.0')),
            environment=environment,
            release=_release,
            send_default_pii=False,  # PII 보호 (이메일/IP 등 자동 차단)
            before_send=_sentry_before_send,  # FIX-WEBSOCKET-STOPITERATION-SENTRY-NOISE-20260428
        )
        logger.info(f"[sentry] initialized (env={environment}, release={_release})")
    except ImportError:
        logger.warning("[sentry] sentry_sdk not installed, skipping init")
    except Exception as e:
        logger.error(f"[sentry] init failed (non-fatal): {e}")


_init_sentry()


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

    # 로깅 설정 (OBSERV-RAILWAY-LOG-LEVEL-MAPPING-20260427)
    # stream=sys.stdout 명시 — 기본 stderr 출력 시 Railway 가 'error' level 로 잘못 태깅
    # → Sentry alert rule 의 level=error 필터 정확 작동 위한 선행 조건
    # force=True — gunicorn master 가 fork 전에 basicConfig 호출했을 수 있어 재설정 보장
    logging.basicConfig(
        level=logging.DEBUG if app.config['DEBUG'] else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout,
        force=True,
    )

    # CORS 설정 (/api/* + /health)
    CORS(app, resources={
        r"/api/*": {"origins": "*"},
        r"/health": {"origins": "*"},
    })
    logger.info("CORS configured for /api/* and /health")

    # flask-sock 초기화 (Sprint 13)
    sock.init_app(app)

    # WebSocket 라우트 등록 (Sprint 13)
    from app.websocket.events import ws_handler

    @sock.route('/ws')
    def websocket_route(ws):
        ws_handler(ws)

    logger.info("WebSocket route /ws registered (flask-sock)")

    # DB Connection Pool 초기화 (Sprint 30)
    if not app.config.get('TESTING', False):
        from app.db_pool import init_pool, close_pool
        init_pool()

        import atexit
        atexit.register(close_pool)

    # 스케줄러 초기화 및 시작 (Sprint 4) — 테스트 환경에서는 비활성화
    # Sprint 30-B: Gunicorn multi-worker 에서 스케줄러 중복 실행 방지 (env guard)
    # HOTFIX-SCHEDULER-DUP-20260422: env guard 는 fork 이후 COW semantics 로 worker 간
    #   전파되지 않아 중복 실행 발생 (R1 실측 37.5% 중복, GPWS-0773 3중복).
    #   fcntl.flock 기반 OS 레벨 lock 으로 교체 — 1 worker 만 scheduler 시작 허용.
    #   Phase 0 Pre-flight Check (2026-04-22) 로 단일 컨테이너 확정 → /tmp 공유 전제 성립.
    import os
    import fcntl
    if not app.config.get('TESTING', False):
        _lock_path = '/tmp/axis_ops_scheduler.lock'
        try:
            _lock_fd = os.open(_lock_path, os.O_CREAT | os.O_WRONLY, 0o644)
            fcntl.flock(_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Lock 획득 성공 — 이 worker 가 scheduler owner
            from app.services.scheduler_service import init_scheduler, start_scheduler
            init_scheduler()
            start_scheduler()
            # env guard 는 보조 방어로 유지 (같은 worker 내 재진입 방지)
            os.environ['_SCHEDULER_STARTED'] = '1'
            # GC 방지 참조 — 모듈 전역으로 프로세스 수명 동안 fd 유지
            import app.services.scheduler_service as _sched_mod
            _sched_mod._scheduler_lock_fd = _lock_fd
            logger.info(f"Scheduler initialized and started (file lock acquired, fd={_lock_fd}, pid={os.getpid()})")
        except BlockingIOError:
            # 다른 worker 가 이미 lock 보유 — scheduler 시작 skip
            logger.info(f"Scheduler already running in another worker (file lock held, pid={os.getpid()})")
        except Exception as e:
            # 예상외 예외 (FS 문제 등) — 스케줄러 skip 하되 앱은 기동
            logger.error(f"Scheduler file lock acquisition failed: {e}", exc_info=True)

    # DB 스키마 자동 검증 (BUG-24: migration 누락 방지)
    if not app.config.get('TESTING', False):
        from app.schema_check import ensure_schema
        ensure_schema()

    # Migration 자동 실행 — 미실행 migration 순차 적용
    if not app.config.get('TESTING', False):
        from app.migration_runner import run_migrations, assert_migrations_in_sync
        run_migrations()
        # OBSERV-MIGRATION-RUNNER-STARTUP-ASSERTION-20260427:
        # 4-22 049 미적용 사례 재발 방지 — disk vs DB sync 검증, gap 시 Sentry alert
        assert_migrations_in_sync()

    # 블루프린트 등록
    from app.routes.auth import auth_bp
    from app.routes.work import work_bp
    from app.routes.product import product_bp
    from app.routes.alert import alert_bp      # Sprint 3
    from app.routes.admin import admin_bp      # Sprint 4
    from app.routes.sync import sync_bp        # Sprint 4
    from app.routes.gst import gst_bp          # Sprint 11: GST 검사 공정
    from app.routes.checklist import checklist_bp  # Sprint 11: 체크리스트
    from app.routes.hr import hr_bp            # Sprint 12: 협력사 출퇴근 관리
    from app.routes.notices import notices_bp  # Sprint 20-B: 공지사항
    from app.routes.qr import qr_bp            # Sprint 21: QR 관리
    from app.routes.factory import factory_bp  # Sprint 29: 공장 API
    from app.routes.analytics import analytics_bp  # Sprint 32: 사용자 분석
    from app.routes.production import production_bp  # Sprint 33: 생산실적

    app.register_blueprint(auth_bp)
    app.register_blueprint(work_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(alert_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(sync_bp)
    app.register_blueprint(gst_bp)
    app.register_blueprint(checklist_bp)
    app.register_blueprint(hr_bp)
    app.register_blueprint(notices_bp)
    app.register_blueprint(qr_bp)
    app.register_blueprint(factory_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(production_bp)
    logger.info("Blueprints registered: auth, work, product, alert, admin, sync, gst, checklist, hr, notices, qr, factory, analytics, production")

    # Sprint 32: 사용자 행위 트래킹 (access log)
    import time as _time
    from app.db_pool import get_conn as _get_conn, put_conn as _put_conn

    @app.after_request
    def log_access(response):
        worker_id = getattr(g, 'worker_id', None)
        if worker_id is None:
            return response
        start = getattr(g, 'request_start_time', None)
        duration_ms = int((_time.time() - start) * 1000) if start else None
        try:
            conn = _get_conn()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO app_access_log
                    (worker_id, worker_email, worker_role, endpoint, method,
                     status_code, duration_ms, ip_address, user_agent, request_path)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                worker_id,
                getattr(g, 'worker_email', None),
                getattr(g, 'worker_role', None),
                request.endpoint or request.path,
                request.method,
                response.status_code,
                duration_ms,
                request.remote_addr,
                str(request.user_agent)[:500] if request.user_agent else None,
                request.full_path[:500],
            ))
            conn.commit()
            _put_conn(conn)
        except Exception as e:
            logger.warning(f"Access log failed: {e}")
        return response

    # 헬스 체크 엔드포인트
    from version import VERSION, BUILD_DATE

    @app.route("/health", methods=["GET"])
    def health_check():
        """헬스 체크 + 버전 정보"""
        return jsonify({
            "status": "ok",
            "version": VERSION,
            "build_date": BUILD_DATE,
        }), 200

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
