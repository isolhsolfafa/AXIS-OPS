"""
Sprint 95 / FEAT-SHIPMENT-DAILY-COMPLETED-LIST — 출하 일일 알림 완료 리스트 추가

검증 (단위 — DB 불필요):
  - _render_completed_section: 완료 N건 섹션 + S/N 표시 / 0건 표시(health check)
  - _render_shipment_overdue_html: completed_items=None 하위호환 + 완료 섹션 포함
  - send 시그니처 completed_items default (하위호환)
  - TEST 제외 보강(serial NOT LIKE 'TEST%') 소스 검증
"""
from datetime import date
import inspect

from app.services.notification_service import (
    _render_completed_section,
    _render_shipment_overdue_html,
    send_shipment_overdue_alert,
)


def _item(sn, so="6672", model="GAIA"):
    return {"serial_number": sn, "sales_order": so, "model": model, "customer": "C",
            "mech_partner": "BAT", "elec_partner": "P&S", "actual_date": "2026-06-11"}


def test_s95_01_completed_section_with_items():
    """TC-S95-01: 완료 N건 섹션 — 건수 + S/N 표시."""
    html = _render_completed_section([_item("GBWS-1"), _item("GBWS-2")])
    assert "✅ 어제 출하 완료 — 2건" in html
    assert "GBWS-1" in html and "GBWS-2" in html


def test_s95_02_completed_section_zero():
    """TC-S95-02: 완료 0건 — health check 표시(없음)."""
    html = _render_completed_section([])
    assert "✅ 어제 출하 완료 — 0건" in html
    assert "어제 출하 완료된 건이 없습니다" in html
    # None 도 동일
    assert "0건" in _render_completed_section(None)


def test_s95_03_render_backcompat_no_completed():
    """TC-S95-03: completed_items 미지정 하위호환 — 완료 0건 섹션 자동."""
    html = _render_shipment_overdue_html([], date(2026, 6, 11))  # completed 생략
    assert "✅ 어제 출하 완료 — 0건" in html  # default None → 0건 섹션


def test_s95_04_render_overdue_plus_completed():
    """TC-S95-04: 미처리>0 + 완료 둘 다 섹션 포함."""
    overdue = [_item("GBWS-OV", model="DRAGON")]
    completed = [_item("GBWS-CO")]
    html = _render_shipment_overdue_html(overdue, date(2026, 6, 11), completed)
    assert "⚠️ 출하 미처리 알림" in html       # 미처리 섹션
    assert "GBWS-OV" in html
    assert "✅ 어제 출하 완료 — 1건" in html    # 완료 섹션
    assert "GBWS-CO" in html


def test_s95_05_send_signature_backcompat():
    """TC-S95-05: send_shipment_overdue_alert completed_items default (하위호환)."""
    sig = inspect.signature(send_shipment_overdue_alert)
    assert "completed_items" in sig.parameters
    assert sig.parameters["completed_items"].default is None


def test_s95_06_test_exclusion_source():
    """TC-S95-06 (Codex M-Q4): get_overdue/completed_shipments 둘 다 serial NOT LIKE 'TEST%' 보강."""
    import app.services.shipment_flow_service as sf
    src = open(sf.__file__).read()
    # 두 함수 모두 serial TEST 제외 + customer TEST 제외
    assert src.count("serial_number NOT LIKE 'TEST%%'") >= 2
    assert "def get_completed_shipments" in src
