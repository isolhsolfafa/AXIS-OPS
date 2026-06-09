"""
협력사 근태(hr.partner_attendance) 조회 서비스.

Sprint 88-BE (#86) step① [REFACTOR]: admin.py(god route)에 있던 근태 조회 로직을
동작 100% 동일하게 추출. 라우트(admin.py)는 본 서비스 함수를 호출만 한다.
step②에서 checkout_status / 미체크률(additive)을 본 서비스에 추가한다.

⚠️ 추출 원칙(CLAUDE.md 리팩토링 7원칙): 본 단계는 구조 이동만, 기능 변경 0.
"""

from datetime import datetime, timedelta, timezone, date
from typing import Any, Dict, List, Optional, Tuple

from app.models.worker import get_db_connection, put_conn


# admin.py 의 _KST 와 동일 (KST = UTC+9). 추출 후에도 동작 동일 보장.
KST = timezone(timedelta(hours=9))


def kst_date_range(target_date: Optional[date] = None) -> Tuple[datetime, datetime]:
    """KST 기준 날짜의 시작/끝 범위 반환 (target_date=None이면 오늘)"""
    if target_date is None:
        now_kst = datetime.now(KST)
        target_date = now_kst.date()
    start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=KST)
    end = start + timedelta(days=1)
    return start, end


def get_attendance_data(
    target_start_kst: datetime,
    target_end_kst: datetime,
    company_filter: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """출퇴근 데이터 조회 공통 함수 — records + summary 반환

    Args:
        target_start_kst: KST 기준 조회 시작 시간
        target_end_kst: KST 기준 조회 종료 시간
        company_filter: Manager 자사 필터 (None이면 전체)
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = """
            SELECT
              w.id AS worker_id,
              w.name AS worker_name,
              w.company,
              w.role,
              MAX(CASE WHEN pa.check_type = 'in'  THEN pa.check_time END) AS check_in_time,
              MAX(CASE WHEN pa.check_type = 'out' THEN pa.check_time END) AS check_out_time,
              MAX(CASE WHEN pa.check_type = 'in'  THEN pa.work_site END) AS work_site,
              MAX(CASE WHEN pa.check_type = 'in'  THEN pa.product_line END) AS product_line
            FROM workers w
            LEFT JOIN hr.partner_attendance pa
              ON w.id = pa.worker_id
              AND pa.check_time >= %s
              AND pa.check_time <  %s
            WHERE w.company != 'GST'
              AND w.approval_status = 'approved'
              AND w.is_active = TRUE
        """
        params = [target_start_kst, target_end_kst]

        if company_filter:
            query += " AND w.company = %s"
            params.append(company_filter)

        query += """
            GROUP BY w.id, w.name, w.company, w.role
            ORDER BY w.company, w.name
        """
        cur.execute(query, params)

        rows = cur.fetchall()

        records = []
        summary = {
            'total_registered': 0,
            'checked_in': 0,
            'checked_out': 0,
            'currently_working': 0,
            'not_checked': 0,
        }

        for row in rows:
            check_in = row['check_in_time']
            check_out = row['check_out_time']

            if check_in is None:
                status = 'not_checked'
            elif check_out is None:
                status = 'working'
            else:
                status = 'left'

            records.append({
                'worker_id': row['worker_id'],
                'worker_name': row['worker_name'],
                'company': row['company'],
                'role': row['role'],
                'check_in_time': check_in.isoformat() if check_in else None,
                'check_out_time': check_out.isoformat() if check_out else None,
                'status': status,
                'work_site': row['work_site'],
                'product_line': row['product_line'],
            })

            summary['total_registered'] += 1
            if status == 'not_checked':
                summary['not_checked'] += 1
            else:
                summary['checked_in'] += 1
                if status == 'left':
                    summary['checked_out'] += 1
                else:
                    summary['currently_working'] += 1

        return records, summary

    finally:
        if conn:
            put_conn(conn)


def get_attendance_trend_data(
    date_from: date,
    date_to: date,
    company_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """기간별 일별 출입 집계 — 단일 SQL"""
    range_start = datetime(date_from.year, date_from.month, date_from.day, tzinfo=KST)
    range_end = datetime(date_to.year, date_to.month, date_to.day, tzinfo=KST) + timedelta(days=1)

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 일별 출근 집계
        checkin_query = """
            SELECT
                DATE(pa.check_time AT TIME ZONE 'Asia/Seoul') AS check_date,
                COUNT(DISTINCT pa.worker_id) AS checked_in,
                COUNT(DISTINCT CASE WHEN pa.work_site = 'HQ' THEN pa.worker_id END) AS hq_count,
                COUNT(DISTINCT CASE WHEN pa.work_site != 'HQ' THEN pa.worker_id END) AS site_count
            FROM hr.partner_attendance pa
            INNER JOIN workers w ON w.id = pa.worker_id
            WHERE pa.check_type = 'in'
              AND pa.check_time >= %s AND pa.check_time < %s
              AND w.company != 'GST'
              AND w.approval_status = 'approved'
              AND w.is_active = TRUE
        """
        params: List[Any] = [range_start, range_end]
        if company_filter:
            checkin_query += " AND w.company = %s"
            params.append(company_filter)
        checkin_query += " GROUP BY check_date ORDER BY check_date"

        cur.execute(checkin_query, params)
        checkin_rows = {row['check_date']: row for row in cur.fetchall()}

        # 전체 등록 인원
        reg_query = "SELECT COUNT(*) AS cnt FROM workers WHERE company != 'GST' AND approval_status = 'approved' AND is_active = TRUE"
        reg_params: List[Any] = []
        if company_filter:
            reg_query += " AND company = %s"
            reg_params.append(company_filter)
        cur.execute(reg_query, reg_params)
        total_registered = cur.fetchone()['cnt']

        # 빈 날짜 채우기
        trend = []
        current = date_from
        while current <= date_to:
            row = checkin_rows.get(current)
            trend.append({
                'date': current.strftime('%Y-%m-%d'),
                'total_registered': total_registered,
                'checked_in': row['checked_in'] if row else 0,
                'hq_count': row['hq_count'] if row else 0,
                'site_count': row['site_count'] if row else 0,
            })
            current += timedelta(days=1)
        return trend
    finally:
        if conn:
            put_conn(conn)
