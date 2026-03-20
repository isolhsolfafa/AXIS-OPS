"""
Sprint 31C: PI 검사 협력사 위임 — 가시성 분기 테스트
White-box: get_task_categories_for_worker 단위 테스트 (admin_settings mock)
"""

import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, 'backend')
from app.services.task_seed import get_task_categories_for_worker


def _mock_settings(pi_capable=None, override_lines=None):
    """admin_settings mock 헬퍼"""
    if pi_capable is None:
        pi_capable = ['TMS']
    if override_lines is None:
        override_lines = ['JP']

    def side_effect(key, default=None):
        return {
            'pi_capable_mech_partners': pi_capable,
            'pi_gst_override_lines': override_lines,
        }.get(key, default)
    return side_effect


class TestPIVisibilityTMS(unittest.TestCase):
    """TMS(M) 작업자의 PI 가시성"""

    @patch('app.services.task_seed.get_setting')
    def test_tms_sees_pi_when_capable(self, mock):
        """TMS(M) + mech=TMS + line=P4-D → PI 보임"""
        mock.side_effect = _mock_settings()
        cats = get_task_categories_for_worker(
            'TMS(M)', 'MECH', 'TMS', None, 'TMS', product_line='P4-D')
        self.assertIn('PI', cats)
        self.assertIn('TMS', cats)
        self.assertIn('MECH', cats)

    @patch('app.services.task_seed.get_setting')
    def test_tms_no_pi_on_jp_line(self, mock):
        """TMS(M) + mech=TMS + line=JP(F15) → PI 안 보임"""
        mock.side_effect = _mock_settings()
        cats = get_task_categories_for_worker(
            'TMS(M)', 'MECH', 'TMS', None, 'TMS', product_line='JP(F15)')
        self.assertNotIn('PI', cats)
        self.assertIn('MECH', cats)

    @patch('app.services.task_seed.get_setting')
    def test_tms_no_pi_when_not_capable(self, mock):
        """pi_capable 빈 리스트 → PI 없음"""
        mock.side_effect = _mock_settings(pi_capable=[])
        cats = get_task_categories_for_worker(
            'TMS(M)', 'MECH', 'TMS', None, 'TMS', product_line='P4-D')
        self.assertNotIn('PI', cats)

    @patch('app.services.task_seed.get_setting')
    def test_tms_no_pi_when_mech_not_tms(self, mock):
        """mech_partner=FNI → MECH 없음, PI도 없음"""
        mock.side_effect = _mock_settings()
        cats = get_task_categories_for_worker(
            'TMS(M)', 'MECH', 'FNI', None, 'TMS', product_line='P4-D')
        self.assertNotIn('PI', cats)
        self.assertNotIn('MECH', cats)


class TestPIVisibilityGST(unittest.TestCase):
    """GST PI 작업자의 PI 가시성"""

    @patch('app.services.task_seed.get_setting')
    def test_gst_pi_no_pi_when_delegated(self, mock):
        """mech=TMS + line=P4-D → GST PI에서 PI 제외"""
        mock.side_effect = _mock_settings()
        cats = get_task_categories_for_worker(
            'GST', 'PI', 'TMS', None, None, product_line='P4-D')
        self.assertNotIn('PI', cats)

    @patch('app.services.task_seed.get_setting')
    def test_gst_pi_keeps_on_jp(self, mock):
        """mech=TMS + line=JP → GST PI 유지"""
        mock.side_effect = _mock_settings()
        cats = get_task_categories_for_worker(
            'GST', 'PI', 'TMS', None, None, product_line='JP(F15)')
        self.assertIn('PI', cats)

    @patch('app.services.task_seed.get_setting')
    def test_gst_pi_keeps_when_mech_not_capable(self, mock):
        """mech=FNI (pi_capable 아님) → GST PI 유지"""
        mock.side_effect = _mock_settings()
        cats = get_task_categories_for_worker(
            'GST', 'PI', 'FNI', None, None, product_line='P4-D')
        self.assertIn('PI', cats)

    @patch('app.services.task_seed.get_setting')
    def test_gst_pi_keeps_when_no_mech(self, mock):
        """mech=NULL → GST PI 유지"""
        mock.side_effect = _mock_settings()
        cats = get_task_categories_for_worker(
            'GST', 'PI', None, None, None, product_line='P4-D')
        self.assertIn('PI', cats)

    @patch('app.services.task_seed.get_setting')
    def test_gst_pi_active_role_override(self, mock):
        """active_role=PI + 위임 대상 → GST PI 제외"""
        mock.side_effect = _mock_settings()
        cats = get_task_categories_for_worker(
            'GST', 'QI', 'TMS', None, None,
            worker_active_role='PI', product_line='P4-D')
        self.assertNotIn('PI', cats)


class TestPIVisibilityFNI(unittest.TestCase):
    """FNI/BAT 확장 대비"""

    @patch('app.services.task_seed.get_setting')
    def test_fni_no_pi_by_default(self, mock):
        """FNI → pi_capable 아님 → PI 없음"""
        mock.side_effect = _mock_settings()
        cats = get_task_categories_for_worker(
            'FNI', 'MECH', 'FNI', None, None, product_line='P4-D')
        self.assertIn('MECH', cats)
        self.assertNotIn('PI', cats)

    @patch('app.services.task_seed.get_setting')
    def test_fni_sees_pi_when_added(self, mock):
        """FNI를 pi_capable에 추가 → PI 보임"""
        mock.side_effect = _mock_settings(pi_capable=['TMS', 'FNI'])
        cats = get_task_categories_for_worker(
            'FNI', 'MECH', 'FNI', None, None, product_line='P4-D')
        self.assertIn('MECH', cats)
        self.assertIn('PI', cats)


class TestPIVisibilityRegression(unittest.TestCase):
    """기존 동작 유지"""

    @patch('app.services.task_seed.get_setting')
    def test_admin_sees_all(self, mock):
        cats = get_task_categories_for_worker(
            'GST', 'ADMIN', 'TMS', None, None, product_line='P4-D')
        self.assertIsNone(cats)

    @patch('app.services.task_seed.get_setting')
    def test_gst_qi_unchanged(self, mock):
        cats = get_task_categories_for_worker(
            'GST', 'QI', 'TMS', None, None, product_line='P4-D')
        self.assertIn('QI', cats)
        self.assertNotIn('PI', cats)

    @patch('app.services.task_seed.get_setting')
    def test_gst_si_unchanged(self, mock):
        cats = get_task_categories_for_worker(
            'GST', 'SI', 'TMS', None, None, product_line='P4-D')
        self.assertIn('SI', cats)

    @patch('app.services.task_seed.get_setting')
    def test_elec_partner_unchanged(self, mock):
        cats = get_task_categories_for_worker(
            'TMS(E)', 'ELEC', 'TMS', 'TMS', None, product_line='P4-D')
        self.assertIn('ELEC', cats)
        self.assertNotIn('PI', cats)

    @patch('app.services.task_seed.get_setting')
    def test_multiple_override_lines(self, mock):
        """복수 override prefix"""
        mock.side_effect = _mock_settings(override_lines=['JP', 'FAB2', 'AUSTRIA'])
        # FAB2 → GST PI 유지
        cats = get_task_categories_for_worker(
            'GST', 'PI', 'TMS', None, None, product_line='FAB2')
        self.assertIn('PI', cats)
        # P4-D → 위임
        cats2 = get_task_categories_for_worker(
            'GST', 'PI', 'TMS', None, None, product_line='P4-D')
        self.assertNotIn('PI', cats2)
