"""
관리자 설정(admin_settings) 모델 및 CRUD 함수
테이블: admin_settings
Sprint 6: key-value 구조의 시스템 옵션 설정
  - heating_jacket_enabled: Heating Jacket task 활성화 여부
  - phase_block_enabled: Tank Docking 전 POST_DOCKING task 차단 여부
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List

from psycopg2 import Error as PsycopgError

from .worker import get_db_connection
from app.db_pool import put_conn


logger = logging.getLogger(__name__)


@dataclass
class AdminSettings:
    """
    관리자 설정 모델

    Attributes:
        id: 설정 ID
        setting_key: 설정 키 (unique)
        setting_value: 설정 값 (JSONB — bool, str, int 등)
        description: 설정 설명
        updated_by: 마지막 수정한 관리자 worker_id
        updated_at: 마지막 수정 시간
    """

    id: int
    setting_key: str
    setting_value: Any  # JSONB → Python Any (bool, str, dict, list 등)
    description: Optional[str]
    updated_by: Optional[int]
    updated_at: datetime

    @staticmethod
    def from_db_row(row: Dict[str, Any]) -> "AdminSettings":
        """
        데이터베이스 행에서 AdminSettings 객체 생성

        Args:
            row: RealDictCursor로 조회한 dict 형태의 행

        Returns:
            AdminSettings 객체
        """
        return AdminSettings(
            id=row['id'],
            setting_key=row['setting_key'],
            setting_value=row['setting_value'],  # psycopg2가 JSONB를 Python 타입으로 자동 변환
            description=row.get('description'),
            updated_by=row.get('updated_by'),
            updated_at=row['updated_at']
        )

    def to_dict(self) -> Dict[str, Any]:
        """API 응답용 dict 변환"""
        return {
            'id': self.id,
            'setting_key': self.setting_key,
            'setting_value': self.setting_value,
            'description': self.description,
            'updated_by': self.updated_by,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


def get_setting(setting_key: str, default: Any = None) -> Any:
    """
    설정 값 조회 (값만 반환)

    Args:
        setting_key: 설정 키
        default: 설정이 없을 때 반환할 기본값

    Returns:
        설정 값 (JSONB가 Python 타입으로 변환됨), 없으면 default
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT setting_value FROM admin_settings WHERE setting_key = %s",
            (setting_key,)
        )

        row = cur.fetchone()
        if row:
            return row['setting_value']
        return default

    except PsycopgError as e:
        logger.error(f"Failed to get setting key={setting_key}: {e}")
        return default
    finally:
        if conn:
            put_conn(conn)


def get_setting_obj(setting_key: str) -> Optional[AdminSettings]:
    """
    설정 전체 객체 조회

    Args:
        setting_key: 설정 키

    Returns:
        AdminSettings 객체, 없으면 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM admin_settings WHERE setting_key = %s",
            (setting_key,)
        )

        row = cur.fetchone()
        if row:
            return AdminSettings.from_db_row(row)
        return None

    except PsycopgError as e:
        logger.error(f"Failed to get setting obj key={setting_key}: {e}")
        return None
    finally:
        if conn:
            put_conn(conn)


def get_all_settings() -> List[AdminSettings]:
    """
    모든 관리자 설정 조회

    Returns:
        AdminSettings 객체 리스트
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM admin_settings ORDER BY setting_key")

        rows = cur.fetchall()
        return [AdminSettings.from_db_row(row) for row in rows]

    except PsycopgError as e:
        logger.error(f"Failed to get all settings: {e}")
        return []
    finally:
        if conn:
            put_conn(conn)


def update_setting(setting_key: str, setting_value: Any, updated_by: Optional[int] = None) -> bool:
    """
    설정 값 업데이트 (없으면 INSERT, 있으면 UPDATE)

    Args:
        setting_key: 설정 키
        setting_value: 새 설정 값 (Python 타입 — bool, str, dict 등)
        updated_by: 수정한 관리자 worker_id

    Returns:
        성공 시 True, 실패 시 False
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # JSONB 직렬화 (Python → JSON 문자열)
        json_value = json.dumps(setting_value)

        cur.execute(
            """
            INSERT INTO admin_settings (setting_key, setting_value, updated_by, updated_at)
            VALUES (%s, %s::jsonb, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (setting_key) DO UPDATE
                SET setting_value = EXCLUDED.setting_value,
                    updated_by = EXCLUDED.updated_by,
                    updated_at = CURRENT_TIMESTAMP
            """,
            (setting_key, json_value, updated_by)
        )

        conn.commit()
        logger.info(f"Admin setting updated: key={setting_key}, value={setting_value}, by={updated_by}")
        return True

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to update setting key={setting_key}: {e}")
        return False
    finally:
        if conn:
            put_conn(conn)
