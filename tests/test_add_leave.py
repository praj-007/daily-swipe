from datetime import date
from pathlib import Path

import pytest

import add_leave as al


def test_resolve_blank_from_defaults_to_today():
    today = date(2026, 7, 1)
    assert al.resolve_dates("", "", today) == (today, today)


def test_resolve_blank_to_defaults_to_from():
    today = date(2026, 7, 1)
    assert al.resolve_dates("2026-07-10", "", today) == (date(2026, 7, 10), date(2026, 7, 10))


def test_resolve_explicit_range():
    today = date(2026, 7, 1)
    assert al.resolve_dates("2026-07-10", "2026-07-14", today) == (
        date(2026, 7, 10),
        date(2026, 7, 14),
    )


def test_resolve_to_before_from_raises():
    with pytest.raises(ValueError):
        al.resolve_dates("2026-07-14", "2026-07-10", date(2026, 7, 1))


def test_resolve_bad_format_raises():
    with pytest.raises(ValueError):
        al.resolve_dates("07/10/2026", "", date(2026, 7, 1))


def test_add_appends_new_range(tmp_path: Path):
    p = tmp_path / "leave.yaml"
    p.write_text("# header comment\n")
    added = al.add_leave_range(p, date(2026, 7, 10), date(2026, 7, 14))
    assert added is True
    text = p.read_text()
    assert "# header comment" in text  # preserved
    assert "- {from: 2026-07-10, to: 2026-07-14}" in text


def test_add_is_idempotent(tmp_path: Path):
    p = tmp_path / "leave.yaml"
    p.write_text("# header\n")
    assert al.add_leave_range(p, date(2026, 7, 10), date(2026, 7, 14)) is True
    before = p.read_text()
    assert al.add_leave_range(p, date(2026, 7, 10), date(2026, 7, 14)) is False
    assert p.read_text() == before  # no duplicate, unchanged


def test_add_to_missing_file(tmp_path: Path):
    p = tmp_path / "leave.yaml"  # does not exist
    assert al.add_leave_range(p, date(2026, 7, 1), date(2026, 7, 1)) is True
    assert "- {from: 2026-07-01, to: 2026-07-01}" in p.read_text()
