"""Decide whether the attendance automation should run today (evaluated in IST)."""
from __future__ import annotations

import os
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

IST = ZoneInfo("Asia/Kolkata")
CONFIG_DIR = Path(__file__).resolve().parent


def today_ist() -> date:
    return datetime.now(IST).date()


def _as_date(value) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def load_holidays(path: Path) -> set[date]:
    if not path.exists():
        return set()
    data = yaml.safe_load(path.read_text()) or []
    return {_as_date(d) for d in data}


def load_leave_ranges(path: Path) -> list[tuple[date, date]]:
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text()) or []
    ranges: list[tuple[date, date]] = []
    for item in data:
        ranges.append((_as_date(item["from"]), _as_date(item["to"])))
    return ranges


def reason_to_skip(
    day: date, holidays: set[date], leave: list[tuple[date, date]]
) -> str | None:
    if day in holidays:
        return f"{day} is a public holiday"
    if day.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        return f"{day} is a weekend"
    for start, end in leave:
        if start <= day <= end:
            return f"{day} is within leave range {start}..{end}"
    return None


def _emit_github_output(should_run: bool) -> None:
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"should_run={'true' if should_run else 'false'}\n")


def main() -> int:
    day = today_ist()
    holidays = load_holidays(CONFIG_DIR / "holidays.yaml")
    leave = load_leave_ranges(CONFIG_DIR / "leave.yaml")
    skip = reason_to_skip(day, holidays, leave)
    if skip:
        print(f"SKIP: {skip}")
        _emit_github_output(False)
    else:
        print("RUN")
        _emit_github_output(True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
