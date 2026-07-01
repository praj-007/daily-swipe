"""Append a leave date range to leave.yaml (dedup-aware). Used by mark-leave.yml."""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from should_run import load_leave_ranges, today_ist

CONFIG_DIR = Path(__file__).resolve().parent
LEAVE_FILE = CONFIG_DIR / "leave.yaml"


def resolve_dates(from_str: str, to_str: str, today: date) -> tuple[date, date]:
    start = date.fromisoformat(from_str) if from_str else today
    end = date.fromisoformat(to_str) if to_str else start
    if end < start:
        raise ValueError(f"'to' ({end}) is before 'from' ({start})")
    return start, end


def add_leave_range(path: Path, start: date, end: date) -> bool:
    if (start, end) in load_leave_ranges(path):
        return False
    line = f"- {{from: {start.isoformat()}, to: {end.isoformat()}}}\n"
    text = path.read_text() if path.exists() else ""
    if text and not text.endswith("\n"):
        text += "\n"
    path.write_text(text + line)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Append a leave range to leave.yaml")
    parser.add_argument("--from", dest="from_", default="")
    parser.add_argument("--to", default="")
    args = parser.parse_args()

    start, end = resolve_dates(args.from_, args.to, today_ist())
    added = add_leave_range(LEAVE_FILE, start, end)
    print(f"{'Added' if added else 'Already present'}: {start.isoformat()}..{end.isoformat()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
