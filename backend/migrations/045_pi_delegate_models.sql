-- Sprint 31C-A: PI 위임 모델별 옵션
-- pi_delegate_models: PI 위임 대상 모델 prefix 목록
-- 이 목록에 있는 모델만 mech_partner 기반 PI 위임 적용

INSERT INTO admin_settings (setting_key, setting_value, description)
VALUES (
    'pi_delegate_models',
    '["GAIA", "DRAGON"]',
    'PI 위임 대상 모델 prefix 목록 (이 목록에 있는 모델만 mech_partner 기반 PI 위임 적용)'
)
ON CONFLICT (setting_key) DO NOTHING;
