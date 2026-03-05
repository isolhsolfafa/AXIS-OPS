-- Sprint 19-D: Geolocation 접속 보안 설정
-- admin_settings에 위치 보안 관련 설정 추가

-- 위치 검증 활성화 여부 (기본값: false — 첫 배포는 비활성화)
INSERT INTO admin_settings (setting_key, setting_value, description)
VALUES ('geo_check_enabled', 'false', '출근 체크인 시 GPS 위치 검증 활성화 여부')
ON CONFLICT (setting_key) DO NOTHING;

-- 허용 위도 (GST 공장 기준)
INSERT INTO admin_settings (setting_key, setting_value, description)
VALUES ('geo_latitude', '35.1796', 'GPS 검증 기준 위도 (GST 공장)')
ON CONFLICT (setting_key) DO NOTHING;

-- 허용 경도 (GST 공장 기준)
INSERT INTO admin_settings (setting_key, setting_value, description)
VALUES ('geo_longitude', '129.0756', 'GPS 검증 기준 경도 (GST 공장)')
ON CONFLICT (setting_key) DO NOTHING;

-- 허용 반경 (미터 단위, 기본값: 200m)
INSERT INTO admin_settings (setting_key, setting_value, description)
VALUES ('geo_radius_meters', '200', 'GPS 검증 허용 반경 (미터)')
ON CONFLICT (setting_key) DO NOTHING;

-- 엄격 모드 (기본값: false — soft 모드: 위치 미전송 시 경고만, strict: 거부)
INSERT INTO admin_settings (setting_key, setting_value, description)
VALUES ('geo_strict_mode', 'false', 'GPS 위치 검증 엄격 모드 (true: 위치 없으면 거부, false: 경고만)')
ON CONFLICT (setting_key) DO NOTHING;
