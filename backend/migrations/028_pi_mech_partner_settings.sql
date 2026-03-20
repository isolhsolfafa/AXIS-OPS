-- Migration 028: PI 검사 협력사 위임 설정 (Sprint 31C)
-- mech_partner 기준 PI 가시성 분기 + DRAGON model_config PI 활성화
BEGIN;

-- 1. PI 검사 가능 협력사 목록
INSERT INTO admin_settings (setting_key, setting_value, description)
VALUES (
    'pi_capable_mech_partners',
    '["TMS"]',
    'PI 검사 가능 협력사 목록 (mech_partner 매칭 시 PI 태스크 위임)'
)
ON CONFLICT (setting_key) DO NOTHING;

-- 2. GST PI 유지 라인 prefix 목록
INSERT INTO admin_settings (setting_key, setting_value, description)
VALUES (
    'pi_gst_override_lines',
    '["JP"]',
    'GST PI 유지 라인 prefix (이 라인은 협력사 위임 제외, GST PI 직접 검사)'
)
ON CONFLICT (setting_key) DO NOTHING;

-- 3. DRAGON model_config: PI 활성화
UPDATE model_config
SET pi_lng_util = TRUE,
    pi_chamber = TRUE,
    updated_at = CURRENT_TIMESTAMP
WHERE model_prefix = 'DRAGON';

-- 4. 기존 DRAGON 제품: PI 태스크 활성화
UPDATE app_task_details
SET is_applicable = TRUE, updated_at = CURRENT_TIMESTAMP
WHERE task_category = 'PI' AND is_applicable = FALSE
  AND serial_number IN (
      SELECT serial_number FROM plan.product_info WHERE model ILIKE 'DRAGON%'
  );

-- 5. 기존 DRAGON 제품: MECH PRESSURE_TEST 비활성화 (PI로 이관)
UPDATE app_task_details
SET is_applicable = FALSE, updated_at = CURRENT_TIMESTAMP
WHERE task_category = 'MECH' AND task_id = 'PRESSURE_TEST'
  AND serial_number IN (
      SELECT serial_number FROM plan.product_info WHERE model ILIKE 'DRAGON%'
  );

COMMIT;
