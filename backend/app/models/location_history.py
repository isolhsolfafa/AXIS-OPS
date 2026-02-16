"""
위치 기록 모델
테이블: location_history
TODO: 위치 정확도 검증
TODO: 위치 데이터 암호화
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class LocationHistory:
    """
    위치 기록 모델
    
    Attributes:
        id: 기록 ID
        worker_id: 작업자 ID
        latitude: 위도
        longitude: 경도
        recorded_at: 기록 시간
    """
    
    id: int
    worker_id: int
    latitude: float
    longitude: float
    recorded_at: datetime
    
    @staticmethod
    def from_db_row(row: tuple) -> "LocationHistory":
        """
        데이터베이스 행에서 LocationHistory 객체 생성
        
        Args:
            row: (id, worker_id, latitude, longitude, recorded_at)
            
        Returns:
            LocationHistory 객체
        """
        # TODO: 행 구조에 맞게 파싱
        pass
