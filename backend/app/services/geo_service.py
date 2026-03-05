"""
지오로케이션(GPS) 검증 서비스
Sprint 19-D: 출근 체크인 시 GPS 위치 검증

admin_settings 테이블에서 geo_check_enabled, geo_latitude, geo_longitude,
geo_radius_meters, geo_strict_mode 값을 읽어 클라이언트 위치가 허용 범위 내인지 검증한다.

Haversine 공식으로 두 좌표 간 거리(미터)를 계산.

work_site 예외: work_site='HQ'(협력사 본사)이면 GPS 검증 면제.
soft/strict 모드: strict=위치 미전송 시 거부, soft=경고만 (출근 허용).
"""

import logging
import math
from typing import Optional, Tuple

from app.models.admin_settings import get_setting


logger = logging.getLogger(__name__)

# 지구 평균 반지름 (미터)
_EARTH_RADIUS_M = 6_371_000


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Haversine 공식으로 두 좌표 간 거리(미터) 계산

    Args:
        lat1: 기준점 위도 (도)
        lon1: 기준점 경도 (도)
        lat2: 검증 대상 위도 (도)
        lon2: 검증 대상 경도 (도)

    Returns:
        두 점 사이의 거리 (미터)
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return _EARTH_RADIUS_M * c


def is_geo_check_enabled() -> bool:
    """
    위치 검증 기능 활성화 여부 조회

    Returns:
        True이면 위치 검증 활성화, False이면 비활성화
    """
    return bool(get_setting('geo_check_enabled', False))


def is_geo_strict_mode() -> bool:
    """
    위치 검증 엄격 모드 여부 조회

    Returns:
        True이면 strict (위치 미전송 시 거부), False이면 soft (경고만)
    """
    return bool(get_setting('geo_strict_mode', False))


def get_geo_config() -> Tuple[float, float, float]:
    """
    위치 검증 기준 설정 값 조회

    Returns:
        (위도, 경도, 허용 반경(m)) 튜플
        설정이 없을 경우 기본값 (GST 부산 공장 기준)
    """
    lat_raw = get_setting('geo_latitude', 35.1796)
    lon_raw = get_setting('geo_longitude', 129.0756)
    radius_raw = get_setting('geo_radius_meters', 200)

    try:
        latitude = float(lat_raw)
    except (TypeError, ValueError):
        logger.warning(f"geo_latitude 값 변환 실패: {lat_raw!r}, 기본값 35.1796 사용")
        latitude = 35.1796

    try:
        longitude = float(lon_raw)
    except (TypeError, ValueError):
        logger.warning(f"geo_longitude 값 변환 실패: {lon_raw!r}, 기본값 129.0756 사용")
        longitude = 129.0756

    try:
        radius = float(radius_raw)
    except (TypeError, ValueError):
        logger.warning(f"geo_radius_meters 값 변환 실패: {radius_raw!r}, 기본값 200 사용")
        radius = 200.0

    return latitude, longitude, radius


def verify_location(client_lat: float, client_lon: float) -> Tuple[bool, float]:
    """
    클라이언트 GPS 위치가 허용 범위(반경) 내에 있는지 검증

    위치 검증 기능이 비활성화된 경우 무조건 True 반환.

    Args:
        client_lat: 클라이언트 위도
        client_lon: 클라이언트 경도

    Returns:
        (허용 여부, 실제 거리(m)) 튜플
        geo_check_enabled=false 이면 (True, 0.0)
    """
    if not is_geo_check_enabled():
        return True, 0.0

    base_lat, base_lon, radius = get_geo_config()

    distance = _haversine_distance(base_lat, base_lon, client_lat, client_lon)
    allowed = distance <= radius

    if not allowed:
        logger.info(
            f"위치 검증 실패: 거리={distance:.1f}m, 허용반경={radius}m, "
            f"클라이언트=({client_lat},{client_lon}), 기준=({base_lat},{base_lon})"
        )

    return allowed, round(distance, 1)
