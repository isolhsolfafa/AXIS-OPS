"""
Sprint 88-BE step② (#86) — checkout_status + 미체크률 검증.

대상: app.services.hr_attendance_service
  - get_checkout_status_map(target_date, company_filter) — worker_id → checkout_status
  - get_attendance_data_with_checkout(...) — records 병합 + summary miss_rate

설계(Codex 라운드2 GO): day-row, check_in=MIN(in), cutoff=LEAST(익일이후 첫 in, D+1 02:00 KST),
check_out=check_in<t<cutoff MAX(out)+orphan 가드, 상태 not_started/done/working/missed,
미체크률 missed/checked_in(CASE NULL), work_site 분리.

운영 데이터 보존: 테스트 생성 worker + 그 worker 의 attendance 만 seed (cleanup_hr_attendance autouse).
get_checkout_status_map 은 seed 한 날짜에 출근한 worker 만 반환 → per-worker 단정으로 격리.
"""
from datetime import datetime, timedelta, timezone, date

import pytest

from app.services.hr_attendance_service import (
    get_checkout_status_map,
    get_attendance_data_with_checkout,
    kst_date_range,
)

KST = timezone(timedelta(hours=9))
_PW = "Test1234!"


def _has_schema(db_conn) -> bool:
    if db_conn is None:
        return False
    cur = db_conn.cursor()
    cur.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_schema='hr' AND table_name='partner_attendance'"
    )
    return cur.fetchone() is not None


def _ins(db_conn, worker_id, check_type, dt_kst, work_site='GST'):
    """attendance 1행 삽입 (dt_kst = KST aware datetime)."""
    cur = db_conn.cursor()
    cur.execute(
        "INSERT INTO hr.partner_attendance (worker_id, check_type, check_time, method, work_site) "
        "VALUES (%s, %s, %s, 'button', %s)",
        (worker_id, check_type, dt_kst, work_site),
    )
    db_conn.commit()


@pytest.mark.skipif(
    "config.getoption('--no-db', default=False)", reason="DB 필요"
)
class TestCheckoutStatusMap:
    """get_checkout_status_map 4-state + cutoff 경계 (격리 past date 사용)."""

    PAST = date(2026, 2, 17)  # 충분히 과거 → cutoff 확정 경과 (done/missed 결정적)

    def _worker(self, create_test_worker, suffix, company='C&A'):
        return create_test_worker(
            email=f"cs_{suffix}@test.com", password=_PW,
            name=f"CS {suffix}", role='ELEC', is_manager=False, company=company,
        )

    def test_done(self, create_test_worker, db_conn):
        if not _has_schema(db_conn):
            pytest.skip("hr schema 없음")
        wid = self._worker(create_test_worker, "done")
        D = self.PAST
        _ins(db_conn, wid, 'in', datetime(D.year, D.month, D.day, 8, 0, tzinfo=KST))
        _ins(db_conn, wid, 'out', datetime(D.year, D.month, D.day, 17, 0, tzinfo=KST))
        cmap = get_checkout_status_map(D)
        assert cmap[wid] == 'done'

    def test_missed(self, create_test_worker, db_conn):
        if not _has_schema(db_conn):
            pytest.skip("hr schema 없음")
        wid = self._worker(create_test_worker, "missed")
        D = self.PAST
        _ins(db_conn, wid, 'in', datetime(D.year, D.month, D.day, 8, 0, tzinfo=KST))
        # 퇴근 없음 + 과거 → cutoff 경과 → missed
        cmap = get_checkout_status_map(D)
        assert cmap[wid] == 'missed'

    def test_working_today_future_cutoff(self, create_test_worker, db_conn):
        if not _has_schema(db_conn):
            pytest.skip("hr schema 없음")
        wid = self._worker(create_test_worker, "working")
        today = datetime.now(KST).date()
        # 오늘 출근 + 퇴근 없음 → cutoff(내일 02:00) 미래 → working
        _ins(db_conn, wid, 'in', datetime.now(KST) - timedelta(hours=1))
        cmap = get_checkout_status_map(today)
        assert cmap[wid] == 'working'

    def test_orphan_out_before_checkin_is_not_done(self, create_test_worker, db_conn):
        if not _has_schema(db_conn):
            pytest.skip("hr schema 없음")
        wid = self._worker(create_test_worker, "orphan")
        D = self.PAST
        # out 이 in 보다 빠름 → 가드(check_time > check_in)로 제외 → done 아님(missed)
        _ins(db_conn, wid, 'out', datetime(D.year, D.month, D.day, 7, 0, tzinfo=KST))
        _ins(db_conn, wid, 'in', datetime(D.year, D.month, D.day, 8, 0, tzinfo=KST))
        cmap = get_checkout_status_map(D)
        assert cmap[wid] == 'missed'

    def test_cutoff_boundary_0159_done_0201_missed(self, create_test_worker, db_conn):
        if not _has_schema(db_conn):
            pytest.skip("hr schema 없음")
        D = self.PAST
        # 익일 01:59 퇴근 → cutoff(02:00) 이전 → done
        w1 = self._worker(create_test_worker, "b0159")
        _ins(db_conn, w1, 'in', datetime(D.year, D.month, D.day, 23, 0, tzinfo=KST))
        _ins(db_conn, w1, 'out', datetime(D.year, D.month, D.day, 23, 0, tzinfo=KST) + timedelta(hours=2, minutes=59))
        # 익일 02:01 퇴근 → cutoff 이후 → 제외 → missed
        w2 = self._worker(create_test_worker, "b0201")
        _ins(db_conn, w2, 'in', datetime(D.year, D.month, D.day, 23, 0, tzinfo=KST))
        _ins(db_conn, w2, 'out', datetime(D.year, D.month, D.day, 23, 0, tzinfo=KST) + timedelta(hours=3, minutes=1))
        cmap = get_checkout_status_map(D)
        assert cmap[w1] == 'done'
        assert cmap[w2] == 'missed'

    def test_next_day_in_caps_cutoff(self, create_test_worker, db_conn):
        if not _has_schema(db_conn):
            pytest.skip("hr schema 없음")
        D = self.PAST
        wid = self._worker(create_test_worker, "nextin")
        _ins(db_conn, wid, 'in', datetime(D.year, D.month, D.day, 9, 0, tzinfo=KST))
        # 익일 00:30 재출근(다음근무) → cutoff=00:30 으로 당겨짐
        _ins(db_conn, wid, 'in', datetime(D.year, D.month, D.day, 9, 0, tzinfo=KST) + timedelta(hours=15, minutes=30))
        # 익일 01:00 퇴근 → cutoff(00:30) 이후 → 제외 → missed
        _ins(db_conn, wid, 'out', datetime(D.year, D.month, D.day, 9, 0, tzinfo=KST) + timedelta(hours=16))
        cmap = get_checkout_status_map(D)
        assert cmap[wid] == 'missed'

    def test_not_started_absent_from_map(self, create_test_worker, db_conn):
        if not _has_schema(db_conn):
            pytest.skip("hr schema 없음")
        wid = self._worker(create_test_worker, "absent")
        # 출근 기록 없음 → 맵 미포함 (호출부에서 not_started 기본)
        cmap = get_checkout_status_map(self.PAST)
        assert wid not in cmap

    def test_company_scope_excludes_other(self, create_test_worker, db_conn):
        if not _has_schema(db_conn):
            pytest.skip("hr schema 없음")
        D = self.PAST
        ca = self._worker(create_test_worker, "scope_ca", company='C&A')
        fni = self._worker(create_test_worker, "scope_fni", company='FNI')
        _ins(db_conn, ca, 'in', datetime(D.year, D.month, D.day, 8, 0, tzinfo=KST))
        _ins(db_conn, fni, 'in', datetime(D.year, D.month, D.day, 8, 0, tzinfo=KST))
        cmap = get_checkout_status_map(D, company_filter='C&A')
        assert ca in cmap            # 자사 포함
        assert fni not in cmap       # 타사 제외 (scope 누수 차단)


@pytest.mark.skipif(
    "config.getoption('--no-db', default=False)", reason="DB 필요"
)
class TestAttendanceDataWithCheckout:
    """get_attendance_data_with_checkout 병합 + 미체크률."""

    PAST = date(2026, 2, 18)

    def test_miss_rate_and_by_work_site(self, create_test_worker, db_conn):
        if not _has_schema(db_conn):
            pytest.skip("hr schema 없음")
        D = self.PAST
        # C&A 2명: 1 done + 1 missed (GST work_site)
        done = create_test_worker(email="wc_done@test.com", password=_PW, name="WC done",
                                  role='ELEC', company='C&A')
        miss = create_test_worker(email="wc_miss@test.com", password=_PW, name="WC miss",
                                  role='ELEC', company='C&A')
        _ins(db_conn, done, 'in', datetime(D.year, D.month, D.day, 8, 0, tzinfo=KST), work_site='GST')
        _ins(db_conn, done, 'out', datetime(D.year, D.month, D.day, 17, 0, tzinfo=KST), work_site='GST')
        _ins(db_conn, miss, 'in', datetime(D.year, D.month, D.day, 8, 0, tzinfo=KST), work_site='GST')
        start, end = kst_date_range(D)
        records, summary = get_attendance_data_with_checkout(start, end, D, company_filter='C&A')
        recs = {r['worker_id']: r for r in records}
        assert recs[done]['checkout_status'] == 'done'
        assert recs[miss]['checkout_status'] == 'missed'
        # 기존 status 키 보존 (불변)
        assert 'status' in recs[done]
        # by_work_site GST: checked_in>=2, missed>=1, miss_rate not None
        gst = summary['by_work_site'].get('GST')
        assert gst is not None and gst['checked_in'] >= 2 and gst['missed'] >= 1
        assert gst['miss_rate'] is not None
        # 합계 정합: by_work_site missed 합 == summary.missed
        assert sum(v['missed'] for v in summary['by_work_site'].values()) == summary['missed']
