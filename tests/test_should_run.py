from datetime import date
from pathlib import Path
import should_run as sr


def test_weekday_not_holiday_not_leave_runs():
    # 2026-06-29 is a Monday
    assert sr.reason_to_skip(date(2026, 6, 29), set(), []) is None


def test_saturday_skips():
    assert "weekend" in sr.reason_to_skip(date(2026, 7, 4), set(), [])


def test_sunday_skips():
    assert "weekend" in sr.reason_to_skip(date(2026, 7, 5), set(), [])


def test_holiday_skips():
    holidays = {date(2026, 8, 15)}
    assert "holiday" in sr.reason_to_skip(date(2026, 8, 15), holidays, [])


def test_leave_range_inclusive_skips():
    leave = [(date(2026, 7, 10), date(2026, 7, 14))]
    assert sr.reason_to_skip(date(2026, 7, 10), set(), leave) is not None  # start
    assert sr.reason_to_skip(date(2026, 7, 14), set(), leave) is not None  # end
    assert sr.reason_to_skip(date(2026, 7, 13), set(), leave) is not None  # middle


def test_day_after_leave_runs():
    leave = [(date(2026, 7, 10), date(2026, 7, 14))]
    # 2026-07-15 is a Wednesday, just after the range
    assert sr.reason_to_skip(date(2026, 7, 15), set(), leave) is None


def test_load_holidays_parses_yaml(tmp_path: Path):
    p = tmp_path / "holidays.yaml"
    p.write_text("- 2026-08-15\n- 2026-10-02\n")
    assert sr.load_holidays(p) == {date(2026, 8, 15), date(2026, 10, 2)}


def test_load_holidays_missing_file_is_empty(tmp_path: Path):
    assert sr.load_holidays(tmp_path / "nope.yaml") == set()


def test_load_leave_ranges_parses_yaml(tmp_path: Path):
    p = tmp_path / "leave.yaml"
    p.write_text("- {from: 2026-07-10, to: 2026-07-14}\n")
    assert sr.load_leave_ranges(p) == [(date(2026, 7, 10), date(2026, 7, 14))]
