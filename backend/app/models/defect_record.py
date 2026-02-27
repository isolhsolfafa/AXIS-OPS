"""
defect.defect_record 모델
불량 기록 원본 데이터 (Teams Excel → ETL)
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional
import psycopg2.extras


@dataclass
class DefectRecord:
    """불량 기록 원본"""
    id: int
    serial_number: Optional[str]
    qr_doc_id: Optional[str]
    model_name: str
    component_name: str
    defect_detail: str
    defect_category_major: Optional[str]
    defect_category_minor: Optional[str]
    detection_stage: Optional[str]
    occurrence_date: date
    remarks: Optional[str]
    source_worksheet: Optional[str]
    source_file_name: Optional[str]
    etl_loaded_at: datetime
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db_row(cls, row: psycopg2.extras.DictRow) -> 'DefectRecord':
        """DB 행에서 DefectRecord 객체 생성"""
        return cls(
            id=row['id'],
            serial_number=row.get('serial_number'),
            qr_doc_id=row.get('qr_doc_id'),
            model_name=row['model_name'],
            component_name=row['component_name'],
            defect_detail=row['defect_detail'],
            defect_category_major=row.get('defect_category_major'),
            defect_category_minor=row.get('defect_category_minor'),
            detection_stage=row.get('detection_stage'),
            occurrence_date=row['occurrence_date'],
            remarks=row.get('remarks'),
            source_worksheet=row.get('source_worksheet'),
            source_file_name=row.get('source_file_name'),
            etl_loaded_at=row['etl_loaded_at'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    def to_dict(self) -> dict:
        """딕셔너리로 변환 (JSON 직렬화용)"""
        return {
            'id': self.id,
            'serial_number': self.serial_number,
            'qr_doc_id': self.qr_doc_id,
            'model_name': self.model_name,
            'component_name': self.component_name,
            'defect_detail': self.defect_detail,
            'defect_category_major': self.defect_category_major,
            'defect_category_minor': self.defect_category_minor,
            'detection_stage': self.detection_stage,
            'occurrence_date': self.occurrence_date.isoformat() if self.occurrence_date else None,
            'remarks': self.remarks,
            'source_worksheet': self.source_worksheet,
            'source_file_name': self.source_file_name,
            'etl_loaded_at': self.etl_loaded_at.isoformat() if self.etl_loaded_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# ============================================================
# CRUD 함수
# ============================================================

def create_defect_record(conn, data: dict) -> Optional[DefectRecord]:
    """불량 기록 생성 (ETL 전용)

    Args:
        conn: DB 연결 객체
        data: {
            'serial_number': str (optional),
            'qr_doc_id': str (optional),
            'model_name': str (required),
            'component_name': str (required),
            'defect_detail': str (required),
            'defect_category_major': str (optional),
            'defect_category_minor': str (optional),
            'detection_stage': str (optional),
            'occurrence_date': date (required),
            'remarks': str (optional),
            'source_worksheet': str (optional),
            'source_file_name': str (optional)
        }

    Returns:
        DefectRecord 객체 (생성 성공) or None (중복)
    """
    query = """
        INSERT INTO defect.defect_record (
            serial_number, qr_doc_id, model_name, component_name,
            defect_detail, defect_category_major, defect_category_minor,
            detection_stage, occurrence_date, remarks,
            source_worksheet, source_file_name
        )
        VALUES (%(serial_number)s, %(qr_doc_id)s, %(model_name)s, %(component_name)s,
                %(defect_detail)s, %(defect_category_major)s, %(defect_category_minor)s,
                %(detection_stage)s, %(occurrence_date)s, %(remarks)s,
                %(source_worksheet)s, %(source_file_name)s)
        ON CONFLICT (serial_number, component_name, occurrence_date, defect_detail) DO NOTHING
        RETURNING *;
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, data)
        row = cur.fetchone()
        if row:
            return DefectRecord.from_db_row(row)
        return None


def get_defect_records_by_serial(conn, serial_number: str) -> list[DefectRecord]:
    """S/N 기준으로 불량 기록 조회"""
    query = """
        SELECT * FROM defect.defect_record
        WHERE serial_number = %s
        ORDER BY occurrence_date DESC, created_at DESC;
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, (serial_number,))
        return [DefectRecord.from_db_row(row) for row in cur.fetchall()]


def get_defect_records_by_model(conn, model_name: str, limit: int = 100) -> list[DefectRecord]:
    """모델명 기준으로 불량 기록 조회"""
    query = """
        SELECT * FROM defect.defect_record
        WHERE model_name = %s
        ORDER BY occurrence_date DESC, created_at DESC
        LIMIT %s;
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, (model_name, limit))
        return [DefectRecord.from_db_row(row) for row in cur.fetchall()]


def get_defect_records_by_component(conn, component_name: str, limit: int = 100) -> list[DefectRecord]:
    """부품명 기준으로 불량 기록 조회"""
    query = """
        SELECT * FROM defect.defect_record
        WHERE component_name = %s
        ORDER BY occurrence_date DESC, created_at DESC
        LIMIT %s;
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, (component_name, limit))
        return [DefectRecord.from_db_row(row) for row in cur.fetchall()]


def get_defect_records_by_date_range(
    conn,
    start_date: date,
    end_date: date,
    model_name: Optional[str] = None,
    component_name: Optional[str] = None
) -> list[DefectRecord]:
    """날짜 범위 + 필터 조건으로 불량 기록 조회"""
    query = """
        SELECT * FROM defect.defect_record
        WHERE occurrence_date BETWEEN %s AND %s
    """
    params = [start_date, end_date]

    if model_name:
        query += " AND model_name = %s"
        params.append(model_name)

    if component_name:
        query += " AND component_name = %s"
        params.append(component_name)

    query += " ORDER BY occurrence_date DESC, created_at DESC;"

    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, params)
        return [DefectRecord.from_db_row(row) for row in cur.fetchall()]


def get_recent_defect_records(conn, days: int = 30, limit: int = 100) -> list[DefectRecord]:
    """최근 N일 불량 기록 조회"""
    query = """
        SELECT * FROM defect.defect_record
        WHERE occurrence_date >= CURRENT_DATE - INTERVAL '%s days'
        ORDER BY occurrence_date DESC, created_at DESC
        LIMIT %s;
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, (days, limit))
        return [DefectRecord.from_db_row(row) for row in cur.fetchall()]


def count_defects_by_model(conn, start_date: Optional[date] = None, end_date: Optional[date] = None) -> dict:
    """모델별 불량 건수 집계"""
    query = """
        SELECT model_name, COUNT(*) as defect_count
        FROM defect.defect_record
    """
    params = []

    if start_date and end_date:
        query += " WHERE occurrence_date BETWEEN %s AND %s"
        params = [start_date, end_date]
    elif start_date:
        query += " WHERE occurrence_date >= %s"
        params = [start_date]

    query += " GROUP BY model_name ORDER BY defect_count DESC;"

    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, params)
        return {row['model_name']: row['defect_count'] for row in cur.fetchall()}


def count_defects_by_component(conn, start_date: Optional[date] = None, end_date: Optional[date] = None) -> dict:
    """부품별 불량 건수 집계"""
    query = """
        SELECT component_name, COUNT(*) as defect_count
        FROM defect.defect_record
    """
    params = []

    if start_date and end_date:
        query += " WHERE occurrence_date BETWEEN %s AND %s"
        params = [start_date, end_date]
    elif start_date:
        query += " WHERE occurrence_date >= %s"
        params = [start_date]

    query += " GROUP BY component_name ORDER BY defect_count DESC;"

    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, params)
        return {row['component_name']: row['defect_count'] for row in cur.fetchall()}
