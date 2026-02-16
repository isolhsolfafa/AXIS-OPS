"""
제품 정보 모델 및 CRUD 함수
테이블: product_info
Sprint 2: QR 기반 제품 조회 + Location 업데이트 + TMS 분기 지원
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, Dict, Any

from psycopg2 import Error as PsycopgError

from .worker import get_db_connection


logger = logging.getLogger(__name__)


@dataclass
class ProductInfo:
    """
    제품 정보 모델

    Attributes:
        id: 제품 ID
        qr_doc_id: QR 문서 ID (DOC_{serial_number})
        serial_number: 시리얼 번호
        model: 모델명
        production_date: 생산 날짜
        location_qr_id: Location QR ID
        mech_partner: 기구 협력사 (TMS 분기용)
        module_outsourcing: 모듈 외주처 (TMS 분기용)
        created_at: 생성 시간
        updated_at: 수정 시간
    """

    id: int
    qr_doc_id: str
    serial_number: str
    model: str
    production_date: date
    location_qr_id: Optional[str]
    mech_partner: Optional[str]
    module_outsourcing: Optional[str]
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_db_row(row: Dict[str, Any]) -> "ProductInfo":
        """
        데이터베이스 행에서 ProductInfo 객체 생성

        Args:
            row: RealDictCursor로 조회한 dict 형태의 행

        Returns:
            ProductInfo 객체
        """
        return ProductInfo(
            id=row['id'],
            qr_doc_id=row['qr_doc_id'],
            serial_number=row['serial_number'],
            model=row['model'],
            production_date=row['production_date'],
            location_qr_id=row.get('location_qr_id'),
            mech_partner=row.get('mech_partner'),
            module_outsourcing=row.get('module_outsourcing'),
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )


def get_product_by_qr_doc_id(qr_doc_id: str) -> Optional[ProductInfo]:
    """
    QR 문서 ID로 제품 조회

    Args:
        qr_doc_id: QR 문서 ID (예: DOC_GBWS-6408)

    Returns:
        ProductInfo 객체, 없으면 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM product_info WHERE qr_doc_id = %s",
            (qr_doc_id,)
        )

        row = cur.fetchone()
        if row:
            return ProductInfo.from_db_row(row)
        return None

    except PsycopgError as e:
        logger.error(f"Failed to get product by qr_doc_id={qr_doc_id}: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_product_by_serial_number(serial_number: str) -> Optional[ProductInfo]:
    """
    시리얼 번호로 제품 조회

    Args:
        serial_number: 시리얼 번호 (예: GBWS-6408)

    Returns:
        ProductInfo 객체, 없으면 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM product_info WHERE serial_number = %s",
            (serial_number,)
        )

        row = cur.fetchone()
        if row:
            return ProductInfo.from_db_row(row)
        return None

    except PsycopgError as e:
        logger.error(f"Failed to get product by serial_number={serial_number}: {e}")
        return None
    finally:
        if conn:
            conn.close()


def update_location_qr(qr_doc_id: str, location_qr_id: str) -> bool:
    """
    제품의 Location QR 업데이트

    Args:
        qr_doc_id: QR 문서 ID
        location_qr_id: Location QR ID

    Returns:
        성공 시 True, 실패 시 False
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "UPDATE product_info SET location_qr_id = %s WHERE qr_doc_id = %s",
            (location_qr_id, qr_doc_id)
        )

        updated = cur.rowcount > 0
        conn.commit()

        if updated:
            logger.info(f"Location QR updated: qr_doc_id={qr_doc_id}, location_qr_id={location_qr_id}")
        return updated

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to update location QR: {e}")
        return False
    finally:
        if conn:
            conn.close()


def is_tms_product(product: ProductInfo) -> bool:
    """
    TMS 제품 여부 확인 (TMS 분기 로직)

    Args:
        product: ProductInfo 객체

    Returns:
        TMS 제품이면 True, 아니면 False
    """
    return (
        product.mech_partner == "TMS" and
        product.module_outsourcing == "TMS"
    )
