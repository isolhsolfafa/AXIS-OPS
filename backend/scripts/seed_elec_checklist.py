"""
ELEC 체크리스트 마스터 데이터 시드 (Sprint 57-C)
3개 그룹, 31항목 (24 WORKER + 7 QI) — 전장외주검사성적서 양식 기준

실행: cd backend && python -m scripts.seed_elec_checklist
"""

import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models.worker import get_db_connection
from app.db_pool import put_conn

# (item_group, item_name, description, item_order, checker_role, phase1_applicable, qi_check_required, select_options, remarks)
# Sprint 60-BE: phase1_na → phase1_applicable (의미 반전), qi_check_required 신규, remarks 신규
ELEC_CHECKLIST_ITEMS = [
    # Group 1: PANEL 검사 (11항목)
    ('PANEL 검사', '파트 사양확인 (라벨 포함)', 'Part 및 Duct Label 도면상의 사양 일치', 1, 'WORKER', False, None),
    ('PANEL 검사', '파트 고정위치', '도면상의 위치 일치', 2, 'WORKER', False, None),
    ('PANEL 검사', '파트 고정상태', '유동 없을것', 3, 'WORKER', False, None),
    ('PANEL 검사', 'NUMBERING 상태', '표기오류 및 누락 없을것', 4, 'WORKER', False, None),
    ('PANEL 검사', 'LOADLOCK 와셔', 'ELCB, NFB, N/F-비스프링, M/C, T/B등 AC Line', 5, 'WORKER', False, None),
    ('PANEL 검사', 'TUBE 종류 / 색상 (R, S, T, PE)', 'TUBE 색상 조합 선택 후 판정', 6, 'WORKER', False,
     ['비가역 EYE CAP(갈, 검, 회, 녹)', '비가역 EYE CAP(적, 황, 청, 녹)', '비가역 EYE CAP(황, 녹, 적, 흑)']),
    ('PANEL 검사', 'Connector (JST / MOLEX 외), Penhole 작업 상태 검사', 'LUG 압착부 끝단 1±1mm 노출', 7, 'WORKER', False, None),
    ('PANEL 검사', 'MFC CONNECTOR확인', '아날로그 모듈부 넘버링 확인 (D-SUB 쪽은 제외)', 8, 'WORKER', False, None),
    ('PANEL 검사', 'FLOW SENSOR확인', 'PIN번호, 색상, 넘버링 작업 후 즉시 1차 육안 확인', 9, 'WORKER', False, None),
    ('PANEL 검사', 'I-Marking 상태 확인', 'I-Marking 기준에 따른 작업 확인', 10, 'WORKER', False, None),
    ('PANEL 검사', 'CLEANING 상태', '제품 內 이물질 없을것', 11, 'WORKER', False, None),

    # Group 2: 조립 검사 (6항목)
    ('조립 검사', 'Surge Protector 장착 상태', '지정 위치 정상 장착', 1, 'WORKER', False, None),
    ('조립 검사', 'BOLT 체결상태', '풀림 및 유동 없을것', 2, 'WORKER', False, None),
    ('조립 검사', '버너 위 배선상태', '탄화방지 작업 확인', 3, 'WORKER', True, None),  # 1차 N.A
    ('조립 검사', '3M CONECTOR 압착상태', '압착이 덜 되어 있거나 PIN이 빠지지 않을 것', 4, 'WORKER', False, None),
    ('조립 검사', 'E CONECTOR 체결상태', '케이블 두께 기준 체결 정상 확인 및 도면 확인', 5, 'WORKER', False, None),
    ('조립 검사', '당김 검사', '커넥터, WIRE 빠짐 없을것', 6, 'WORKER', False, None),

    # Group 3: JIG 검사 및 특별관리 POINT — WORKER (7항목)
    ('JIG 검사 및 특별관리 POINT', 'PUMP 배선 상태 CHECK', 'PUMP 배선 체결 순서 및 상태 1차 작업 시 육안 확인', 1, 'WORKER', False, None),
    ('JIG 검사 및 특별관리 POINT', 'MFC 배선 상태 CHECK', '아날로그모듈로 들어가는 배선만 체결 순서 및 상태 확인', 2, 'WORKER', False, None),
    ('JIG 검사 및 특별관리 POINT', 'IGNITION 및 M/T스크래퍼 CONECTOR 배선 CHECK', 'CONECTOR 배선만 순서 확인', 3, 'WORKER', False, None),
    ('JIG 검사 및 특별관리 POINT', 'AC LINE SHORT 검사', 'AC LINE SHORT 확인', 4, 'WORKER', False, None),
    ('JIG 검사 및 특별관리 POINT', 'DC LINE SHORT 검사', 'DC LINE SHORT 및 체결 상태 확인', 5, 'WORKER', False, None),
    ('JIG 검사 및 특별관리 POINT', 'MUX (ANALOG MODULE) ↔ PLC 배선 CHECK', 'PIN번호 육안 확인', 6, 'WORKER', False, None),
    ('JIG 검사 및 특별관리 POINT', 'DC SOL VALVE 다이오드 체결 상태 확인', '체결 방법 및 CABLE 간섭 유/무 확인', 7, 'WORKER', False, None),

    # Group 3: GST 담당자 전용 (QI) — 동일 7항목
    ('JIG 검사 및 특별관리 POINT', 'PUMP 배선 상태 CHECK (GST)', 'PUMP 배선 체결 순서 및 상태 — GST 검증', 8, 'QI', False, None),
    ('JIG 검사 및 특별관리 POINT', 'MFC 배선 상태 CHECK (GST)', '아날로그모듈 배선 체결 — GST 검증', 9, 'QI', False, None),
    ('JIG 검사 및 특별관리 POINT', 'IGNITION 및 M/T스크래퍼 CONECTOR (GST)', 'CONECTOR 배선 순서 — GST 검증', 10, 'QI', False, None),
    ('JIG 검사 및 특별관리 POINT', 'AC LINE SHORT 검사 (GST)', 'AC LINE SHORT — GST 검증', 11, 'QI', False, None),
    ('JIG 검사 및 특별관리 POINT', 'DC LINE SHORT 검사 (GST)', 'DC LINE SHORT — GST 검증', 12, 'QI', False, None),
    ('JIG 검사 및 특별관리 POINT', 'MUX (ANALOG MODULE) ↔ PLC (GST)', 'PIN번호 — GST 검증', 13, 'QI', False, None),
    ('JIG 검사 및 특별관리 POINT', 'DC SOL VALVE 다이오드 (GST)', '체결 방법 및 CABLE 간섭 — GST 검증', 14, 'QI', False, None),
]


def seed():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        inserted = 0
        for item_group, item_name, description, item_order, checker_role, phase1_na, select_options in ELEC_CHECKLIST_ITEMS:
            item_type = 'SELECT' if select_options else 'CHECK'
            options_json = json.dumps(select_options) if select_options else None

            cur.execute("""
                INSERT INTO checklist.checklist_master
                    (product_code, category, item_group, item_name, item_order,
                     description, is_active, checker_role, phase1_na,
                     item_type, select_options)
                VALUES ('COMMON', 'ELEC', %s, %s, %s, %s, TRUE, %s, %s, %s, %s)
                ON CONFLICT (product_code, category, item_group, item_name) DO NOTHING
            """, (item_group, item_name, item_order, description,
                  checker_role, phase1_na, item_type, options_json))
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
