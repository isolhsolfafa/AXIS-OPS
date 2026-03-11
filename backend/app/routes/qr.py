"""
QR 관리 라우트
엔드포인트: /api/admin/qr/*
Sprint 21: QR Registry + Product Info 조회 API
"""

import logging
from flask import Blueprint, request, jsonify
from typing import Tuple, Dict, Any

from flask import g
from app.middleware.jwt_auth import jwt_required, manager_or_admin_required
from app.models.worker import get_db_connection, get_worker_by_id

logger = logging.getLogger(__name__)

qr_bp = Blueprint("qr", __name__, url_prefix="/api/admin/qr")


@qr_bp.route("/list", methods=["GET"])
@jwt_required
@manager_or_admin_required
def get_qr_list() -> Tuple[Dict[str, Any], int]:
    """
    QR 목록 조회 (qr_registry JOIN product_info)

    Query Params:
        search: S/N 또는 qr_doc_id 부분검색 (optional)
        model: 모델명 필터 (optional)
        status: active/revoked 필터 (optional, default: all)
        page: 페이지 번호 (default: 1)
        per_page: 페이지당 건수 (default: 50, max: 200)
        sort_by: 정렬 기준 (default: qr.created_at)
        sort_order: asc/desc (default: desc)

    Returns:
        200: { items: [...], total: int, page: int, per_page: int, total_pages: int }
    """
    try:
        search = request.args.get("search", "").strip()
        model_filter = request.args.get("model", "").strip()
        status_filter = request.args.get("status", "").strip()
        date_field = request.args.get("date_field", "").strip()
        date_from = request.args.get("date_from", "").strip()
        date_to = request.args.get("date_to", "").strip()
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(200, max(1, int(request.args.get("per_page", 50))))
        sort_by = request.args.get("sort_by", "qr.created_at")
        sort_order = request.args.get("sort_order", "desc").lower()

        # 허용된 정렬 컬럼
        allowed_sorts = {
            "qr.created_at": "qr.created_at",
            "serial_number": "p.serial_number",
            "model": "p.model",
            "mech_start": "p.mech_start",
            "module_start": "p.module_start",
            "sales_order": "p.sales_order",
        }
        sort_col = allowed_sorts.get(sort_by, "qr.created_at")
        sort_dir = "ASC" if sort_order == "asc" else "DESC"

        conn = get_db_connection()
        cursor = conn.cursor()

        # WHERE 조건 빌드
        conditions = []
        params = []

        # Manager: 자사 제품만 필터
        current_worker = get_worker_by_id(g.worker_id)
        if current_worker and current_worker.is_manager and not current_worker.is_admin:
            manager_company = current_worker.company
            conditions.append("(p.mech_partner = %s OR p.elec_partner = %s)")
            params.extend([manager_company, manager_company])

        if search:
            conditions.append("(p.serial_number ILIKE %s OR qr.qr_doc_id ILIKE %s)")
            params.extend([f"%{search}%", f"%{search}%"])

        if model_filter:
            conditions.append("p.model = %s")
            params.append(model_filter)

        if status_filter in ("active", "shipped", "revoked"):
            conditions.append("qr.status = %s")
            params.append(status_filter)

        # 날짜 범위 필터
        allowed_date_fields = {"mech_start": "p.mech_start", "module_start": "p.module_start"}
        if date_field in allowed_date_fields:
            col = allowed_date_fields[date_field]
            if date_from:
                conditions.append(f"{col} >= %s")
                params.append(date_from)
            if date_to:
                conditions.append(f"{col} <= %s")
                params.append(date_to)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # COUNT 쿼리
        count_sql = f"""
            SELECT COUNT(*) AS cnt
            FROM public.qr_registry qr
            JOIN plan.product_info p ON qr.serial_number = p.serial_number
            {where_clause}
        """
        cursor.execute(count_sql, params)
        total = cursor.fetchone()['cnt']

        # 데이터 쿼리
        offset = (page - 1) * per_page
        data_sql = f"""
            SELECT
                qr.id AS qr_id,
                qr.qr_doc_id,
                qr.serial_number,
                qr.status,
                qr.created_at AS qr_created_at,
                p.model,
                p.sales_order,
                p.customer,
                p.mech_partner,
                p.elec_partner,
                p.mech_start,
                p.module_start,
                p.ship_plan_date,
                p.prod_date,
                p.actual_ship_date
            FROM public.qr_registry qr
            JOIN plan.product_info p ON qr.serial_number = p.serial_number
            {where_clause}
            ORDER BY {sort_col} {sort_dir}
            LIMIT %s OFFSET %s
        """
        cursor.execute(data_sql, params + [per_page, offset])
        rows = cursor.fetchall()

        # 모델 목록 (필터용)
        cursor.execute("""
            SELECT DISTINCT p.model
            FROM public.qr_registry qr
            JOIN plan.product_info p ON qr.serial_number = p.serial_number
            ORDER BY p.model
        """)
        models = [row['model'] for row in cursor.fetchall() if row['model']]

        # 통계 (Manager: 자사 필터 적용)
        stats_conditions = []
        stats_params = []
        if current_worker and current_worker.is_manager and not current_worker.is_admin:
            stats_conditions.append("(p.mech_partner = %s OR p.elec_partner = %s)")
            stats_params.extend([manager_company, manager_company])
        stats_where = f"WHERE {' AND '.join(stats_conditions)}" if stats_conditions else ""

        cursor.execute(f"""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE qr.status = 'active') AS active_count,
                COUNT(*) FILTER (WHERE qr.status = 'shipped') AS shipped_count,
                COUNT(*) FILTER (WHERE qr.status = 'revoked') AS revoked_count
            FROM public.qr_registry qr
            JOIN plan.product_info p ON qr.serial_number = p.serial_number
            {stats_where}
        """, stats_params)
        stats_row = cursor.fetchone()

        conn.close()

        # 응답 빌드
        items = []
        for row in rows:
            items.append({
                "qr_id": row['qr_id'],
                "qr_doc_id": row['qr_doc_id'],
                "serial_number": row['serial_number'],
                "status": row['status'],
                "qr_created_at": row['qr_created_at'].isoformat() if row['qr_created_at'] else None,
                "model": row['model'],
                "sales_order": row['sales_order'],
                "customer": row['customer'],
                "mech_partner": row['mech_partner'],
                "elec_partner": row['elec_partner'],
                "mech_start": row['mech_start'].isoformat() if row['mech_start'] else None,
                "module_start": row['module_start'].isoformat() if row['module_start'] else None,
                "ship_plan_date": row['ship_plan_date'].isoformat() if row['ship_plan_date'] else None,
                "prod_date": row['prod_date'].isoformat() if row['prod_date'] else None,
                "actual_ship_date": row['actual_ship_date'].isoformat() if row.get('actual_ship_date') else None,
            })

        total_pages = (total + per_page - 1) // per_page

        return jsonify({
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "models": models,
            "stats": {
                "total": stats_row['total'],
                "active": stats_row['active_count'],
                "shipped": stats_row['shipped_count'],
                "revoked": stats_row['revoked_count'],
            },
        }), 200

    except Exception as e:
        logger.error(f"QR 목록 조회 실패: {e}", exc_info=True)
        return jsonify({
            "error": "INTERNAL_ERROR",
            "message": "QR 목록 조회 중 오류가 발생했습니다."
        }), 500
