"""
공지사항 라우트
엔드포인트: /api/notices/*, /api/admin/notices/*
Sprint 20-B: 공지사항 CRUD API
"""

import logging
from flask import Blueprint, request, jsonify, g
from typing import Tuple, Dict, Any

from app.middleware.jwt_auth import jwt_required, admin_required
from app.models.worker import get_db_connection
from psycopg2 import Error as PsycopgError


logger = logging.getLogger(__name__)

notices_bp = Blueprint("notices", __name__)


# ──────────────────────────────────────────────────
# 공개 API (로그인 사용자 전체)
# ──────────────────────────────────────────────────

@notices_bp.route("/api/notices", methods=["GET"])
@jwt_required
def get_notices() -> Tuple[Dict[str, Any], int]:
    """
    공지 목록 조회 (최신순, 고정 공지 상단)

    Query Parameters:
        page: int (default: 1)
        limit: int (default: 10)
        version: str (optional, 특정 버전 필터)

    Returns:
        200: {"notices": [...], "total": int, "page": int, "limit": int}
    """
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    version = request.args.get('version')

    if page < 1:
        page = 1
    if limit < 1 or limit > 50:
        limit = 10

    offset = (page - 1) * limit

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        where_clauses = []
        params = []

        if version:
            where_clauses.append("n.version = %s")
            params.append(version)

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        # 전체 건수
        cur.execute(f"SELECT COUNT(*) AS cnt FROM notices n {where_sql}", tuple(params))
        total = cur.fetchone()['cnt']

        # 목록 (고정 공지 상단, 최신순)
        cur.execute(f"""
            SELECT n.id, n.title, n.content, n.version, n.is_pinned,
                   n.created_by, w.name AS author_name,
                   n.created_at, n.updated_at
            FROM notices n
            LEFT JOIN workers w ON n.created_by = w.id
            {where_sql}
            ORDER BY n.is_pinned DESC, n.created_at DESC
            LIMIT %s OFFSET %s
        """, tuple(params) + (limit, offset))

        rows = cur.fetchall()
        notices = [
            {
                'id': row['id'],
                'title': row['title'],
                'content': row['content'],
                'version': row['version'],
                'is_pinned': row['is_pinned'],
                'author_name': row['author_name'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
            }
            for row in rows
        ]

        return jsonify({
            'notices': notices,
            'total': total,
            'page': page,
            'limit': limit,
        }), 200

    except PsycopgError as e:
        logger.error(f"Failed to get notices: {e}")
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': '공지사항 조회에 실패했습니다.'
        }), 500
    finally:
        if conn:
            conn.close()


@notices_bp.route("/api/notices/<int:notice_id>", methods=["GET"])
@jwt_required
def get_notice_detail(notice_id: int) -> Tuple[Dict[str, Any], int]:
    """
    공지 상세 조회

    Returns:
        200: {"id", "title", "content", "version", ...}
        404: {"error": "NOT_FOUND"}
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT n.id, n.title, n.content, n.version, n.is_pinned,
                   n.created_by, w.name AS author_name,
                   n.created_at, n.updated_at
            FROM notices n
            LEFT JOIN workers w ON n.created_by = w.id
            WHERE n.id = %s
        """, (notice_id,))

        row = cur.fetchone()
        if not row:
            return jsonify({
                'error': 'NOT_FOUND',
                'message': '공지사항을 찾을 수 없습니다.'
            }), 404

        return jsonify({
            'id': row['id'],
            'title': row['title'],
            'content': row['content'],
            'version': row['version'],
            'is_pinned': row['is_pinned'],
            'author_name': row['author_name'],
            'created_at': row['created_at'].isoformat() if row['created_at'] else None,
            'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
        }), 200

    except PsycopgError as e:
        logger.error(f"Failed to get notice detail: {e}")
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': '공지사항 조회에 실패했습니다.'
        }), 500
    finally:
        if conn:
            conn.close()


# ──────────────────────────────────────────────────
# Admin API (관리자 전용)
# ──────────────────────────────────────────────────

@notices_bp.route("/api/admin/notices", methods=["POST"])
@jwt_required
@admin_required
def create_notice() -> Tuple[Dict[str, Any], int]:
    """
    공지 작성

    Request Body:
        {"title": str, "content": str, "version": str (optional), "is_pinned": bool (optional)}

    Returns:
        201: {"message": str, "notice": {...}}
    """
    data = request.get_json()

    if not data or not all(k in data for k in ['title', 'content']):
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'title과 content 필드가 필요합니다.'
        }), 400

    title = data['title'].strip()
    content = data['content'].strip()
    version = data.get('version')
    is_pinned = data.get('is_pinned', False)

    if not title:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': '제목을 입력해주세요.'
        }), 400

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO notices (title, content, version, is_pinned, created_by)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, title, content, version, is_pinned, created_by, created_at, updated_at
        """, (title, content, version, is_pinned, g.worker_id))

        row = cur.fetchone()
        conn.commit()

        logger.info(f"Notice created: id={row['id']}, by={g.worker_id}")

        return jsonify({
            'message': '공지사항이 등록되었습니다.',
            'notice': {
                'id': row['id'],
                'title': row['title'],
                'content': row['content'],
                'version': row['version'],
                'is_pinned': row['is_pinned'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
            }
        }), 201

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to create notice: {e}")
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': '공지사항 등록에 실패했습니다.'
        }), 500
    finally:
        if conn:
            conn.close()


@notices_bp.route("/api/admin/notices/<int:notice_id>", methods=["PUT"])
@jwt_required
@admin_required
def update_notice(notice_id: int) -> Tuple[Dict[str, Any], int]:
    """
    공지 수정

    Request Body:
        {"title": str (optional), "content": str (optional),
         "version": str (optional), "is_pinned": bool (optional)}

    Returns:
        200: {"message": str, "notice_id": int}
        404: {"error": "NOT_FOUND"}
    """
    data = request.get_json(silent=True) or {}

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 존재 확인
        cur.execute("SELECT id FROM notices WHERE id = %s", (notice_id,))
        if not cur.fetchone():
            return jsonify({
                'error': 'NOT_FOUND',
                'message': '공지사항을 찾을 수 없습니다.'
            }), 404

        updates = []
        params = []
        for field in ('title', 'content', 'version', 'is_pinned'):
            if field in data:
                updates.append(f"{field} = %s")
                params.append(data[field])

        if not updates:
            return jsonify({
                'error': 'INVALID_REQUEST',
                'message': '수정할 필드가 없습니다.'
            }), 400

        params.append(notice_id)
        cur.execute(
            f"UPDATE notices SET {', '.join(updates)} WHERE id = %s",
            tuple(params)
        )
        conn.commit()

        logger.info(f"Notice updated: id={notice_id}, by={g.worker_id}")

        return jsonify({
            'message': '공지사항이 수정되었습니다.',
            'notice_id': notice_id,
        }), 200

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to update notice: {e}")
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': '공지사항 수정에 실패했습니다.'
        }), 500
    finally:
        if conn:
            conn.close()


@notices_bp.route("/api/admin/notices/<int:notice_id>", methods=["DELETE"])
@jwt_required
@admin_required
def delete_notice(notice_id: int) -> Tuple[Dict[str, Any], int]:
    """
    공지 삭제

    Returns:
        200: {"message": str, "notice_id": int}
        404: {"error": "NOT_FOUND"}
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("DELETE FROM notices WHERE id = %s RETURNING id", (notice_id,))
        deleted = cur.fetchone()

        if not deleted:
            return jsonify({
                'error': 'NOT_FOUND',
                'message': '공지사항을 찾을 수 없습니다.'
            }), 404

        conn.commit()
        logger.info(f"Notice deleted: id={notice_id}, by={g.worker_id}")

        return jsonify({
            'message': '공지사항이 삭제되었습니다.',
            'notice_id': notice_id,
        }), 200

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to delete notice: {e}")
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': '공지사항 삭제에 실패했습니다.'
        }), 500
    finally:
        if conn:
            conn.close()
