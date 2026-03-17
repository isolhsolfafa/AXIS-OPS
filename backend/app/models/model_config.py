"""
모델 설정(model_config) 모델 및 CRUD 함수
테이블: model_config
Sprint 6: 제품 모델별 Task 분기 설정 (has_docking, is_tms, tank_in_mech)
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List

from psycopg2 import Error as PsycopgError

from .worker import get_db_connection
from app.db_pool import put_conn


logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """
    제품 모델 설정 모델

    Attributes:
        id: 설정 ID
        model_prefix: 모델명 접두어 (GAIA, DRAGON, GALLANT, MITHAS, SDS, SWS)
        has_docking: 도킹 공정 존재 여부 (GAIA: True)
        is_tms: TMS 모듈 사용 여부 (GAIA: True)
        tank_in_mech: 탱크가 MECH 협력사 담당 여부 (DRAGON: True)
        description: 설명
        created_at: 생성 시간
        updated_at: 수정 시간
    """

    id: int
    model_prefix: str
    has_docking: bool
    is_tms: bool
    tank_in_mech: bool
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_db_row(row: Dict[str, Any]) -> "ModelConfig":
        """
        데이터베이스 행에서 ModelConfig 객체 생성

        Args:
            row: RealDictCursor로 조회한 dict 형태의 행

        Returns:
            ModelConfig 객체
        """
        return ModelConfig(
            id=row['id'],
            model_prefix=row['model_prefix'],
            has_docking=row['has_docking'],
            is_tms=row['is_tms'],
            tank_in_mech=row['tank_in_mech'],
            description=row.get('description'),
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    def to_dict(self) -> Dict[str, Any]:
        """API 응답용 dict 변환"""
        return {
            'id': self.id,
            'model_prefix': self.model_prefix,
            'has_docking': self.has_docking,
            'is_tms': self.is_tms,
            'tank_in_mech': self.tank_in_mech,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


def get_all_model_configs() -> List[ModelConfig]:
    """
    모든 모델 설정 조회

    Returns:
        ModelConfig 객체 리스트
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT * FROM model_config
            ORDER BY model_prefix
            """
        )

        rows = cur.fetchall()
        return [ModelConfig.from_db_row(row) for row in rows]

    except PsycopgError as e:
        logger.error(f"Failed to get all model configs: {e}")
        return []
    finally:
        if conn:
            put_conn(conn)


def get_model_config_by_prefix(model_prefix: str) -> Optional[ModelConfig]:
    """
    model_prefix로 모델 설정 조회 (정확한 일치)

    Args:
        model_prefix: 모델명 접두어 (예: 'GAIA', 'DRAGON')

    Returns:
        ModelConfig 객체, 없으면 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM model_config WHERE model_prefix = %s",
            (model_prefix.upper(),)
        )

        row = cur.fetchone()
        if row:
            return ModelConfig.from_db_row(row)
        return None

    except PsycopgError as e:
        logger.error(f"Failed to get model config by prefix={model_prefix}: {e}")
        return None
    finally:
        if conn:
            put_conn(conn)


def get_model_config_for_product(model_name: str) -> Optional[ModelConfig]:
    """
    제품 모델명에서 model_config 조회 (접두어 매칭)

    product_info.model 값에서 model_prefix를 추출하여 설정 조회.
    예: 'GAIA-1234' → 'GAIA', 'DRAGON-456' → 'DRAGON'

    Args:
        model_name: 제품 모델명 (plan.product_info.model)

    Returns:
        ModelConfig 객체, 매칭 없으면 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 접두어 매칭: model_name이 model_prefix로 시작하는 설정 조회
        cur.execute(
            """
            SELECT * FROM model_config
            WHERE %s ILIKE model_prefix || '%%'
            ORDER BY LENGTH(model_prefix) DESC
            LIMIT 1
            """,
            (model_name,)
        )

        row = cur.fetchone()
        if row:
            return ModelConfig.from_db_row(row)
        return None

    except PsycopgError as e:
        logger.error(f"Failed to get model config for model_name={model_name}: {e}")
        return None
    finally:
        if conn:
            put_conn(conn)
