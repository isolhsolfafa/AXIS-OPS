"""
ELEC 체크리스트 마스터 데이터 시드 (Sprint 57)
3개 그룹, 31항목 (24 WORKER + 7 QI) — 전장외주검사성적서 양식 기준

실행: cd backend && python -m scripts.seed_elec_checklist
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models.worker import get_db_connection
from app.db_pool import put_conn

# (item_group, item_name, description, item_order, checker_role, phase1_na)
ELEC_CHECKLIST_ITEMS = [
    # Group 1: PANEL 검사 (11항목)
    ('PANEL 검사', 'SUS Fitting 조임 상태', 'GAP GAUGE / 측수 검사', 1, 'WORKER', False),
    ('PANEL 검사', 'Gas Nozzle Cover 힘 여부', 'Jig 활용 Center 확인 / 육안 검사', 2, 'WORKER', False),
    ('PANEL 검사', '클램프 체결', '조립 유동 여부 / 측수 검사', 3, 'WORKER', False),
    ('PANEL 검사', 'Packing 조립 확인', '적용 여부 / 육안 검사', 4, 'WORKER', False),
    ('PANEL 검사', 'Packing Guide 고정 확인', '유동 여부 / 육안 검사', 5, 'WORKER', False),
    ('PANEL 검사', 'SUS Fitting 조임 상태 (EXHAUST)', 'GAP GAUGE / 측수 검사', 6, 'WORKER', False),
    ('PANEL 검사', 'BCW Nozzle Spray 방향', '아래 방향 / 육안 검사', 7, 'WORKER', False),
    ('PANEL 검사', 'Fitting 조임 상태', '조립 유동 여부 / 측수 검사', 8, 'WORKER', False),
    ('PANEL 검사', 'Tube 조임 상태', '조립 유동 여부 / 측수 검사', 9, 'WORKER', False),
    ('PANEL 검사', '클램프 체결 (REACTOR)', '조립 유동 여부 / 측수 검사', 10, 'WORKER', False),
    ('PANEL 검사', 'Cir Line Tubing', '조립 유동 여부 / 측수 검사', 11, 'WORKER', False),

    # Group 2: 조립 검사 (6항목)
    ('조립 검사', 'Cir Pump Spec 확인', '조립 도면과 현물 1:1 확인 / 육안 검사', 1, 'WORKER', False),
    ('조립 검사', 'Flow Sensor Swirl Orifice', 'Swirl Orifice 적용 조립 / 육안 검사', 2, 'WORKER', False),
    ('조립 검사', 'Tank 내부 이물질 확인', 'Tank 투시창 이용 확인 / 육안 검사', 3, 'WORKER', False),
    ('조립 검사', '열교환기 Spec 확인', '조립 도면과 현물 1:1 확인 / 육안 검사', 4, 'WORKER', False),
    ('조립 검사', '버너 위 배선 상태', '현장 조립 후 확인 / 육안 검사', 5, 'WORKER', True),  # 1차 N.A
    ('조립 검사', '전장 BOX 내부 배선 상태', '배선 정리 상태 / 육안 검사', 6, 'WORKER', False),

    # Group 3: JIG 검사 및 특별관리 POINT — WORKER (7항목)
    ('JIG 검사 및 특별관리 POINT', 'Jig 검사 항목 1', '특별관리 / 육안 검사', 1, 'WORKER', False),
    ('JIG 검사 및 특별관리 POINT', 'Jig 검사 항목 2', '특별관리 / 육안 검사', 2, 'WORKER', False),
    ('JIG 검사 및 특별관리 POINT', 'Jig 검사 항목 3', '특별관리 / 육안 검사', 3, 'WORKER', False),
    ('JIG 검사 및 특별관리 POINT', 'Jig 검사 항목 4', '특별관리 / 육안 검사', 4, 'WORKER', False),
    ('JIG 검사 및 특별관리 POINT', 'Jig 검사 항목 5', '특별관리 / 육안 검사', 5, 'WORKER', False),
    ('JIG 검사 및 특별관리 POINT', 'Jig 검사 항목 6', '특별관리 / 육안 검사', 6, 'WORKER', False),
    ('JIG 검사 및 특별관리 POINT', 'Jig 검사 항목 7', '특별관리 / 육안 검사', 7, 'WORKER', False),

    # Group 3: GST 담당자 전용 (QI) — 동일 7항목
    ('JIG 검사 및 특별관리 POINT', 'Jig 검사 항목 1 (GST)', '특별관리 — GST 검증 / 육안 검사', 8, 'QI', False),
    ('JIG 검사 및 특별관리 POINT', 'Jig 검사 항목 2 (GST)', '특별관리 — GST 검증 / 육안 검사', 9, 'QI', False),
    ('JIG 검사 및 특별관리 POINT', 'Jig 검사 항목 3 (GST)', '특별관리 — GST 검증 / 육안 검사', 10, 'QI', False),
    ('JIG 검사 및 특별관리 POINT', 'Jig 검사 항목 4 (GST)', '특별관리 — GST 검증 / 육안 검사', 11, 'QI', False),
    ('JIG 검사 및 특별관리 POINT', 'Jig 검사 항목 5 (GST)', '특별관리 — GST 검증 / 육안 검사', 12, 'QI', False),
    ('JIG 검사 및 특별관리 POINT', 'Jig 검사 항목 6 (GST)', '특별관리 — GST 검증 / 육안 검사', 13, 'QI', False),
    ('JIG 검사 및 특별관리 POINT', 'Jig 검사 항목 7 (GST)', '특별관리 — GST 검증 / 육안 검사', 14, 'QI', False),
]


def seed():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        inserted = 0
        for item_group, item_name, description, item_order, checker_role, phase1_na in ELEC_CHECKLIST_ITEMS:
            cur.execute("""
                INSERT INTO checklist.checklist_master
                    (product_code, category, item_group, item_name, item_order,
                     description, is_active, checker_role, phase1_na)
                VALUES ('COMMON', 'ELEC', %s, %s, %s, %s, TRUE, %s, %s)
                ON CONFLICT (product_code, category, item_group, item_name) DO NOTHING
            """, (item_group, item_name, item_order, description, checker_role, phase1_na))
            if cur.rowcount > 0:
                inserted += 1

        conn.commit()
        print(f"[seed_elec_checklist] Inserted {inserted}/{len(ELEC_CHECKLIST_ITEMS)} items")
        cur.close()

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[seed_elec_checklist] Error: {e}")
        raise
    finally:
        if conn:
            put_conn(conn)


if __name__ == '__main__':
    seed()
