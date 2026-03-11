"""
제품 정보 모델 및 CRUD 함수

DB 스키마:
  plan.product_info  — 생산 메타데이터 (S/N, model, 일정, 협력사...)
  public.qr_registry — QR ↔ 제품 매핑 (qr_doc_id, serial_number, status)

조회 흐름:
  QR 스캔 → qr_registry(qr_doc_id) → serial_number → plan.product_info JOIN
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
    제품 정보 모델 (qr_registry + plan.product_info JOIN 결과)

    Attributes:
        id: plan.product_info PK
        qr_doc_id: QR 문서 ID (DOC_{serial_number})
        serial_number: 시리얼 번호
        model: 모델명
        prod_date: 생산 날짜
        location_qr_id: Location QR ID
        mech_partner: 기구 협력사 (TMS 분기용)
        elec_partner: 전장 협력사
        module_outsourcing: 모듈 외주처 (TMS 분기용)
        title_number: 도면 번호
        product_code: 제품 코드
        sales_order: 수주 번호
        customer: 고객사
        line: 라인 정보
        quantity: 수량 (VARCHAR)
        mech_start: 기구 시작일
        mech_end: 기구 종료일
        elec_start: 전장 시작일
        elec_end: 전장 종료일
        module_start: 모듈 시작일
        pi_start: PI 시작일
        qi_start: QI 시작일
        si_start: SI 시작일
        ship_plan_date: 출하 예정일
        created_at: 생성 시간
        updated_at: 수정 시간
    """

    # 필수 필드 (기본값 없음)
    id: int
    qr_doc_id: str
    serial_number: str
    model: str
    prod_date: date
    created_at: datetime
    updated_at: datetime

    # Optional 필드 (기본값 = None)
    location_qr_id: Optional[str] = None
    mech_partner: Optional[str] = None
    elec_partner: Optional[str] = None
    module_outsourcing: Optional[str] = None
    title_number: Optional[str] = None
    product_code: Optional[str] = None
    sales_order: Optional[str] = None
    customer: Optional[str] = None
    line: Optional[str] = None
    quantity: Optional[str] = None
    mech_start: Optional[date] = None
    mech_end: Optional[date] = None
    elec_start: Optional[date] = None
    elec_end: Optional[date] = None
    module_start: Optional[date] = None
    pi_start: Optional[date] = None
    qi_start: Optional[date] = None
    si_start: Optional[date] = None
    ship_plan_date: Optional[date] = None

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
            prod_date=row['prod_date'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            location_qr_id=row.get('location_qr_id'),
            mech_partner=row.get('mech_partner'),
            elec_partner=row.get('elec_partner'),
            module_outsourcing=row.get('module_outsourcing'),
            title_number=row.get('title_number'),
            product_code=row.get('product_code'),
            sales_order=row.get('sales_order'),
            customer=row.get('customer'),
            line=row.get('line'),
            quantity=row.get('quantity'),
            mech_start=row.get('mech_start'),
            mech_end=row.get('mech_end'),
            elec_start=row.get('elec_start'),
            elec_end=row.get('elec_end'),
            module_start=row.get('module_start'),
            pi_start=row.get('pi_start'),
            qi_start=row.get('qi_start'),
            si_start=row.get('si_start'),
            ship_plan_date=row.get('ship_plan_date'),
        )


# JOIN 쿼리: qr_registry + plan.product_info
_BASE_JOIN_QUERY = """
    SELECT pi.id, qr.qr_doc_id, pi.serial_number,
           pi.model, pi.prod_date, pi.location_qr_id,
           pi.mech_partner, pi.elec_partner, pi.module_outsourcing,
           pi.title_number, pi.product_code, pi.sales_order,
           pi.customer, pi.line, pi.quantity,
           pi.mech_start, pi.mech_end,
           pi.elec_start, pi.elec_end,
           pi.module_start, pi.pi_start, pi.qi_start, pi.si_start,
           pi.ship_plan_date,
           pi.created_at, pi.updated_at
    FROM public.qr_registry qr
    JOIN plan.product_info pi ON qr.serial_number = pi.serial_number
"""


def get_product_by_qr_doc_id(qr_doc_id: str, include_shipped: bool = False) -> Optional[ProductInfo]:
    """
    QR 문서 ID로 제품 조회
    qr_registry → plan.product_info JOIN

    Args:
        qr_doc_id: QR 문서 ID (예: DOC_GBWS-6408)
        include_shipped: True면 shipped 상태도 포함 (Admin용)

    Returns:
        ProductInfo 객체, 없으면 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        if include_shipped:
            status_filter = "qr.status IN ('active', 'shipped')"
        else:
            status_filter = "qr.status = 'active'"

        cur.execute(
            _BASE_JOIN_QUERY + " WHERE qr.qr_doc_id = %s AND " + status_filter,
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
    qr_registry → plan.product_info JOIN

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
            _BASE_JOIN_QUERY + " WHERE pi.serial_number = %s AND qr.status = 'active'",
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
    qr_doc_id → serial_number 조회 → plan.product_info 업데이트

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

        # qr_registry에서 serial_number 조회
        cur.execute(
            "SELECT serial_number FROM public.qr_registry WHERE qr_doc_id = %s AND status = 'active'",
            (qr_doc_id,)
        )
        row = cur.fetchone()
        if not row:
            logger.warning(f"QR not found or inactive: qr_doc_id={qr_doc_id}")
            return False

        # plan.product_info 업데이트
        cur.execute(
            "UPDATE plan.product_info SET location_qr_id = %s WHERE serial_number = %s",
            (location_qr_id, row['serial_number'])
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
