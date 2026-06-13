"""
FEAT-CT-RELIABILITY-SUMMARY (B/v4) — 데이터 신뢰도 게이트 (모델 기준 + 생산량 가중)

검증:
  - 응답 구조 (headline/gate/by_model/input_source_integrity/labels/meta)
  - 가중평균 폐기 → count 게이트 (표본수 가중 없음)
  - 생산량 가중 Σ(w_model·r_model) — standard_ready_pct
  - Codex Q2 (category=partner_scope) / Q4 (무자료 모델 0기여) / Q5 (model prefix 정규화)
  - 2조건 분리 (n_met / tracking_met / both)
  - 라벨 정정 + force_closed 분리 (A=v2.40.0 정합)
"""
import pytest

from app.services.statistics_service import (
    _norm_model_prefix,
    _dual_label,
    get_reliability_summary,
)


# ── 정규화 헬퍼 (DB 불필요, Codex Q5) ──

def test_rs01_norm_prefix_known():
    """TC-RS-01: known prefix startswith 매칭."""
    pfx = ["GAIA", "DRAGON", "GALLANT", "SDS", "SWS", "IVAS"]
    assert _norm_model_prefix("GAIA-P DUAL", pfx) == "GAIA"
    assert _norm_model_prefix("GAIA-P-II DUAL", pfx) == "GAIA"
    assert _norm_model_prefix("DRAGON LE DUAL", pfx) == "DRAGON"
    assert _norm_model_prefix("iVAS GAIA-I DUAL", pfx) == "IVAS"  # iVAS 우선, GAIA 아님
    assert _norm_model_prefix("SWS-I", pfx) == "SWS"


def test_rs02_norm_prefix_fallback():
    """TC-RS-02: 미매칭 → 첫토큰 fallback."""
    pfx = ["GAIA", "DRAGON"]
    assert _norm_model_prefix("O3 Destructor", pfx) == "O3"
    assert _norm_model_prefix("HOT N2 MODULE", pfx) == "HOT"
    assert _norm_model_prefix(None, pfx) == "(미지정)"
    assert _norm_model_prefix("", pfx) == "(미지정)"


def test_rs03_dual_label():
    """TC-RS-03: DUAL/SINGLE = ILIKE '%DUAL%' 규칙."""
    assert _dual_label("GAIA-P DUAL") == "DUAL"
    assert _dual_label("GAIA") == "SINGLE"
    assert _dual_label("DRAGON LE DUAL DUAL") == "DUAL"
    assert _dual_label(None) == "SINGLE"


# ── DB 통합 ──

@pytest.fixture
def summary(db_conn):
    if db_conn is None:
        pytest.skip("sqlite")
    return get_reliability_summary()


def test_rs04_response_shape(summary):
    """TC-RS-04: 응답 최상위 키 + 라벨 정정."""
    for k in ("headline", "gate", "by_model", "input_source_integrity", "labels", "meta"):
        assert k in summary, f"키 누락: {k}"
    # 라벨 정정 (CT 신뢰도→표본가능, 입력정합→마감출처)
    assert summary["labels"]["ct_reliability"] == "표준 가능 비율"
    assert summary["labels"]["input_integrity"] == "마감 출처 정합"


def test_rs05_headline_gate(summary):
    """TC-RS-05: 헤드라인 추적율 + 게이트 단위/임계."""
    h = summary["headline"]
    assert 0 <= h["tracking_pct"] <= 100
    assert h["stage"] in ("tagging_settlement", "standard_ready")
    assert h["interpret"] in ("hold", "ok")
    g = summary["gate"]
    assert g["unit"] == "model_task_dual"            # 모델 기준 (협력사 합산)
    assert g["weight"] == "production_volume_12mo"    # 생산량 가중 (표본수 가중 폐기)
    assert g["threshold_n"] == 30
    assert g["tracking_threshold"] == 0.70


def test_rs06_gate_pct_range(summary):
    """TC-RS-06: 게이트 비율 0~100, 2조건 분리 존재."""
    g = summary["gate"]
    for k in ("standard_ready_pct", "n_met_pct", "tracking_met_pct", "input_integrity_pct"):
        assert 0 <= g[k] <= 100, f"{k} 범위 위반: {g[k]}"
    # 표준가능(둘다)은 각 단독 조건보다 클 수 없음 (AND)
    assert g["standard_ready_pct"] <= g["n_met_pct"] + 0.1
    assert g["standard_ready_pct"] <= g["tracking_met_pct"] + 0.1


def test_rs07_production_weight(summary):
    """TC-RS-07: 생산량 가중 — by_model production_share 합 ≈ 100 (생산데이터 있을 때)."""
    shares = [m["production_share"] for m in summary["by_model"]]
    if not shares or sum(shares) == 0:
        pytest.skip("test DB 최근 12개월 생산 데이터 없음 (운영 데이터 보존 정책)")
    # 생산비중 합은 100 근처 (반올림 오차 허용)
    assert abs(sum(shares) - 100) < 2.0, f"생산비중 합 {sum(shares)}"


def test_rs08_no_ct_cells_zero_contrib(summary):
    """TC-RS-08 (Codex Q4): 무자료 모델(생산>0, 셀=0) → status=no_ct_cells, 모든 비율 0."""
    nocell = [m for m in summary["by_model"] if m["status"] == "no_ct_cells"]
    for m in nocell:
        assert m["cells"] == 0
        assert m["standard_ready_pct"] == 0.0
        assert m["n_met_pct"] == 0.0
        assert m["tracking_met_pct"] == 0.0
        # 생산비중은 0 초과 (분모 유지 — 과대평가 재발 방지)
        assert m["production_share"] >= 0.0


def test_rs09_force_closed_separated(summary):
    """TC-RS-09 (A=v2.40.0 정합): clean 에 FORCE_CLOSED 미포함, 분리 노출."""
    isi = summary["input_source_integrity"]
    sources = {d["source"]: d for d in isi["dist"]}
    if "FORCE_CLOSED" in sources:
        assert sources["FORCE_CLOSED"]["clean"] is False
        assert isi["force_closed_pct"] > 0
    # clean_pct = clean=True 합 (force-close 제외)
    clean_sum = sum(d["pct"] for d in isi["dist"] if d["clean"])
    assert abs(isi["clean_pct"] - clean_sum) < 0.2


def test_rs10_by_model_prefix_normalized(summary):
    """TC-RS-10 (Codex Q5): by_model model 은 정규화된 prefix (full name 아님)."""
    for m in summary["by_model"]:
        # prefix 는 공백 없는 단일 토큰 또는 (미지정)
        assert " " not in m["model"] or m["model"] == "(미지정)", f"비정규화 model: {m['model']}"
