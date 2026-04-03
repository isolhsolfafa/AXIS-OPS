"""
Sprint 31C-A: PI 위임 모델별 옵션 — pi_delegate_models 테스트
White-box: get_task_categories_for_worker 단위 테스트 (admin_settings mock)

TC-31CA-01: GAIA + mech=TMS → PI 위임 (GAIA ∈ pi_delegate_models)
TC-31CA-02: DRAGON + mech=TMS → PI 위임 (DRAGON ∈ pi_delegate_models)
TC-31CA-03: SWS + mech=TMS → GST PI 직접 (SWS ∉ pi_delegate_models)
TC-31CA-04: GAIA + mech=BAT → GST PI (BAT ∉ pi_capable, 위임 무관)
TC-31CA-05: GAIA JP라인 + mech=TMS → GST PI (override_lines 체크)
TC-31CA-06: 신규 모델 NEWMODEL + mech=TMS → GST PI (미등록 = 안전)
TC-31CA-07: pi_delegate_models에 "SWS" 추가 → SWS도 위임 복원
"""

import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, 'backend')
from app.services.task_seed import get_task_categories_for_worker


def _mock_settings(
    pi_capable=None,
    override_lines=None,
    delegate_models=None,
):
    """admin_settings mock 헬퍼 — pi_delegate_models 포함."""
    if pi_capable is None:
        pi_capable = ['TMS']
    if override_lines is None:
        override_lines = ['JP']
    if delegate_models is None:
        delegate_models = ['GAIA', 'DRAGON']

    def side_effect(key, default=None):
        return {
            'pi_capable_mech_partners': pi_capable,
            'pi_gst_override_lines': override_lines,
            'pi_delegate_models': delegate_models,
        }.get(key, default)

    return side_effect


class TestPIDelegateModels(unittest.TestCase):
    """pi_delegate_models 설정에 따른 PI 위임 분기 테스트"""

    # ── TC-31CA-01 ─────────────────────────────────────────────
    @patch('app.services.task_seed.get_setting')
    def test_tc31ca_01_gaia_tms_worker_sees_pi(self, mock):
        """TC-31CA-01: GAIA + mech=TMS + TMS(M) 작업자 → PI 위임됨 (GAIA ∈ pi_delegate_models)"""
        mock.side_effect = _mock_settings()
        cats = get_task_categories_for_worker(
            worker_company='TMS(M)',
            worker_role='MECH',
            product_mech_partner='TMS',
            product_elec_partner=None,
            product_module_outsourcing='TMS',
            product_line='P4-D',
            product_model='GAIA-1234',
        )
        self.assertIn('PI', cats, "GAIA 모델에서 TMS(M) 작업자는 PI를 볼 수 있어야 합니다")
        self.assertIn('MECH', cats)
        self.assertIn('TMS', cats)

    # ── TC-31CA-01 (GST PI 관점) ────────────────────────────────
    @patch('app.services.task_seed.get_setting')
    def test_tc31ca_01_gaia_gst_pi_excluded(self, mock):
        """TC-31CA-01: GAIA + mech=TMS + GST PI → PI 제외 (위임됨)"""
        mock.side_effect = _mock_settings()
        cats = get_task_categories_for_worker(
            worker_company='GST',
            worker_role='PI',
            product_mech_partner='TMS',
            product_elec_partner=None,
            product_module_outsourcing=None,
            product_line='P4-D',
            product_model='GAIA-1234',
        )
        self.assertNotIn('PI', cats, "GAIA 모델에서 GST PI는 PI를 볼 수 없어야 합니다 (위임)")

    # ── TC-31CA-02 ─────────────────────────────────────────────
    @patch('app.services.task_seed.get_setting')
    def test_tc31ca_02_dragon_tms_worker_sees_pi(self, mock):
        """TC-31CA-02: DRAGON + mech=TMS + TMS(M) 작업자 → PI 위임됨 (DRAGON ∈ pi_delegate_models)"""
        mock.side_effect = _mock_settings()
        cats = get_task_categories_for_worker(
            worker_company='TMS(M)',
            worker_role='MECH',
            product_mech_partner='TMS',
            product_elec_partner=None,
            product_module_outsourcing='TMS',
            product_line='P4-D',
            product_model='DRAGON LE',
        )
        self.assertIn('PI', cats, "DRAGON 모델에서 TMS(M) 작업자는 PI를 볼 수 있어야 합니다")

    @patch('app.services.task_seed.get_setting')
    def test_tc31ca_02_dragon_gst_pi_excluded(self, mock):
        """TC-31CA-02: DRAGON + mech=TMS + GST PI → PI 제외 (위임됨)"""
        mock.side_effect = _mock_settings()
        cats = get_task_categories_for_worker(
            worker_company='GST',
            worker_role='PI',
            product_mech_partner='TMS',
            product_elec_partner=None,
            product_module_outsourcing=None,
            product_line='P4-D',
            product_model='DRAGON LE',
        )
        self.assertNotIn('PI', cats, "DRAGON 모델에서 GST PI는 PI를 볼 수 없어야 합니다 (위임)")

    # ── TC-31CA-03 ─────────────────────────────────────────────
    @patch('app.services.task_seed.get_setting')
    def test_tc31ca_03_sws_gst_pi_direct(self, mock):
        """TC-31CA-03: SWS + mech=TMS + GST PI → PI 유지 (SWS ∉ pi_delegate_models)"""
        mock.side_effect = _mock_settings()  # delegate_models=['GAIA','DRAGON'], SWS 없음
        cats = get_task_categories_for_worker(
            worker_company='GST',
            worker_role='PI',
            product_mech_partner='TMS',
            product_elec_partner=None,
            product_module_outsourcing=None,
            product_line='P4-D',
            product_model='SWS-500',
        )
        self.assertIn('PI', cats, "SWS 모델은 pi_delegate_models에 없으므로 GST PI가 PI를 직접 담당해야 합니다")

    @patch('app.services.task_seed.get_setting')
    def test_tc31ca_03_sws_tms_worker_no_pi(self, mock):
        """TC-31CA-03: SWS + mech=TMS + TMS(M) 작업자 → PI 없음 (위임 안 됨)"""
        mock.side_effect = _mock_settings()
        cats = get_task_categories_for_worker(
            worker_company='TMS(M)',
            worker_role='MECH',
            product_mech_partner='TMS',
            product_elec_partner=None,
            product_module_outsourcing='TMS',
            product_line='P4-D',
            product_model='SWS-500',
        )
        self.assertNotIn('PI', cats, "SWS 모델에서 TMS(M) 작업자는 PI를 볼 수 없어야 합니다 (비위임 모델)")

    # ── TC-31CA-04 ─────────────────────────────────────────────
    @patch('app.services.task_seed.get_setting')
    def test_tc31ca_04_gaia_bat_mech_gst_pi_direct(self, mock):
        """TC-31CA-04: GAIA + mech=BAT + GST PI → PI 유지 (BAT ∉ pi_capable)"""
        mock.side_effect = _mock_settings()  # pi_capable=['TMS'], BAT 없음
        cats = get_task_categories_for_worker(
            worker_company='GST',
            worker_role='PI',
            product_mech_partner='BAT',
            product_elec_partner=None,
            product_module_outsourcing=None,
            product_line='P4-D',
            product_model='GAIA-1234',
        )
        self.assertIn('PI', cats, "BAT는 pi_capable이 아니므로 위임 모델이어도 GST PI가 담당해야 합니다")

    # ── TC-31CA-05 ─────────────────────────────────────────────
    @patch('app.services.task_seed.get_setting')
    def test_tc31ca_05_gaia_jp_line_gst_pi_override(self, mock):
        """TC-31CA-05: GAIA JP라인 + mech=TMS + GST PI → PI 유지 (override_lines 체크)"""
        mock.side_effect = _mock_settings()  # override_lines=['JP']
        cats = get_task_categories_for_worker(
            worker_company='GST',
            worker_role='PI',
            product_mech_partner='TMS',
            product_elec_partner=None,
            product_module_outsourcing=None,
            product_line='JP(F15)',
            product_model='GAIA-1234',
        )
        self.assertIn('PI', cats, "GAIA + JP 라인은 override_lines에 해당하므로 GST PI가 담당해야 합니다")

    @patch('app.services.task_seed.get_setting')
    def test_tc31ca_05_gaia_jp_line_tms_worker_no_pi(self, mock):
        """TC-31CA-05: GAIA JP라인 + mech=TMS + TMS(M) 작업자 → PI 없음 (override)"""
        mock.side_effect = _mock_settings()
        cats = get_task_categories_for_worker(
            worker_company='TMS(M)',
            worker_role='MECH',
            product_mech_partner='TMS',
            product_elec_partner=None,
            product_module_outsourcing='TMS',
            product_line='JP(F15)',
            product_model='GAIA-1234',
        )
        self.assertNotIn('PI', cats, "GAIA + JP 라인 + override → TMS(M) PI 없음")

    # ── TC-31CA-06 ─────────────────────────────────────────────
    @patch('app.services.task_seed.get_setting')
    def test_tc31ca_06_newmodel_gst_pi_direct(self, mock):
        """TC-31CA-06: 미등록 모델 NEWMODEL + mech=TMS + GST PI → PI 유지 (안전 기본값)"""
        mock.side_effect = _mock_settings()  # delegate_models=['GAIA','DRAGON']
        cats = get_task_categories_for_worker(
            worker_company='GST',
            worker_role='PI',
            product_mech_partner='TMS',
            product_elec_partner=None,
            product_module_outsourcing=None,
            product_line='P4-D',
            product_model='NEWMODEL-001',
        )
        self.assertIn('PI', cats, "미등록 모델은 기본적으로 GST PI가 담당해야 합니다 (fail-safe)")

    @patch('app.services.task_seed.get_setting')
    def test_tc31ca_06_none_model_gst_pi_direct(self, mock):
        """TC-31CA-06: product_model=None → PI 위임 안 됨 (안전 기본값)"""
        mock.side_effect = _mock_settings()
        cats = get_task_categories_for_worker(
            worker_company='GST',
            worker_role='PI',
            product_mech_partner='TMS',
            product_elec_partner=None,
            product_module_outsourcing=None,
            product_line='P4-D',
            product_model=None,
        )
        self.assertIn('PI', cats, "product_model=None 이면 기본적으로 GST PI가 담당해야 합니다")

    # ── TC-31CA-07 ─────────────────────────────────────────────
    @patch('app.services.task_seed.get_setting')
    def test_tc31ca_07_sws_added_to_delegate_sees_pi(self, mock):
        """TC-31CA-07: pi_delegate_models에 SWS 추가 → SWS도 위임 복원 (TMS(M) PI 보임)"""
        mock.side_effect = _mock_settings(delegate_models=['GAIA', 'DRAGON', 'SWS'])
        cats = get_task_categories_for_worker(
            worker_company='TMS(M)',
            worker_role='MECH',
            product_mech_partner='TMS',
            product_elec_partner=None,
            product_module_outsourcing='TMS',
            product_line='P4-D',
            product_model='SWS-500',
        )
        self.assertIn('PI', cats, "SWS를 pi_delegate_models에 추가하면 TMS(M) 작업자가 PI를 볼 수 있어야 합니다")

    @patch('app.services.task_seed.get_setting')
    def test_tc31ca_07_sws_added_gst_pi_excluded(self, mock):
        """TC-31CA-07: pi_delegate_models에 SWS 추가 → GST PI 제외"""
        mock.side_effect = _mock_settings(delegate_models=['GAIA', 'DRAGON', 'SWS'])
        cats = get_task_categories_for_worker(
            worker_company='GST',
            worker_role='PI',
            product_mech_partner='TMS',
            product_elec_partner=None,
            product_module_outsourcing=None,
            product_line='P4-D',
            product_model='SWS-500',
        )
        self.assertNotIn('PI', cats, "SWS를 pi_delegate_models에 추가하면 GST PI는 PI를 볼 수 없어야 합니다")


class TestPIDelegateModelsRegression(unittest.TestCase):
    """pi_delegate_models 추가 후 기존 동작 regression 검증"""

    @patch('app.services.task_seed.get_setting')
    def test_admin_still_sees_all(self, mock):
        """ADMIN은 pi_delegate_models와 무관하게 전체 조회"""
        mock.side_effect = _mock_settings()
        cats = get_task_categories_for_worker(
            worker_company='GST',
            worker_role='ADMIN',
            product_mech_partner='TMS',
            product_elec_partner=None,
            product_module_outsourcing=None,
            product_line='P4-D',
            product_model='GAIA-1234',
        )
        self.assertIsNone(cats)

    @patch('app.services.task_seed.get_setting')
    def test_qi_unchanged(self, mock):
        """QI 작업자는 pi_delegate_models와 무관"""
        mock.side_effect = _mock_settings()
        cats = get_task_categories_for_worker(
            worker_company='GST',
            worker_role='QI',
            product_mech_partner='TMS',
            product_elec_partner=None,
            product_module_outsourcing=None,
            product_line='P4-D',
            product_model='GAIA-1234',
        )
        self.assertIn('QI', cats)
        self.assertNotIn('PI', cats)

    @patch('app.services.task_seed.get_setting')
    def test_elec_partner_unchanged(self, mock):
        """ELEC 협력사는 pi_delegate_models와 무관"""
        mock.side_effect = _mock_settings()
        cats = get_task_categories_for_worker(
            worker_company='TMS(E)',
            worker_role='ELEC',
            product_mech_partner='TMS',
            product_elec_partner='TMS',
            product_module_outsourcing=None,
            product_line='P4-D',
            product_model='GAIA-1234',
        )
        self.assertIn('ELEC', cats)
        self.assertNotIn('PI', cats)

    @patch('app.services.task_seed.get_setting')
    def test_prefix_case_insensitive(self, mock):
        """모델 prefix 대소문자 비교 무관 — 'gaia-1234' → GAIA 매칭"""
        mock.side_effect = _mock_settings(delegate_models=['GAIA', 'DRAGON'])
        cats = get_task_categories_for_worker(
            worker_company='GST',
            worker_role='PI',
            product_mech_partner='TMS',
            product_elec_partner=None,
            product_module_outsourcing=None,
            product_line='P4-D',
            product_model='gaia-1234',  # 소문자
        )
        self.assertNotIn('PI', cats, "소문자 모델명도 GAIA로 인식해 위임 처리되어야 합니다")

    @patch('app.services.task_seed.get_setting')
    def test_empty_delegate_models_no_delegation(self, mock):
        """pi_delegate_models=[] → 모든 모델 GST PI 직접 담당"""
        mock.side_effect = _mock_settings(delegate_models=[])
        cats = get_task_categories_for_worker(
            worker_company='GST',
            worker_role='PI',
            product_mech_partner='TMS',
            product_elec_partner=None,
            product_module_outsourcing=None,
            product_line='P4-D',
            product_model='GAIA-1234',
        )
        self.assertIn('PI', cats, "pi_delegate_models가 비어 있으면 위임 없이 GST PI가 담당해야 합니다")


if __name__ == '__main__':
    unittest.main()
