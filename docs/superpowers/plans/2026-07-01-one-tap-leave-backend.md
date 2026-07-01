# One-Tap Leave — Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `mark-leave.yml` workflow (triggered via the `workflow_dispatch` API) that records a leave date range in `leave.yaml`, so the existing sign-in/sign-out automation skips those days.

**Architecture:** A unit-tested `add_leave.py` resolves/validates a `from`/`to` range and appends it to `leave.yaml` (dedup-aware, preserving the file's comments). A `mark-leave.yml` workflow runs it on dispatch and commits the change with the built-in `GITHUB_TOKEN`. `should_run.py` (unchanged) already skips `leave.yaml` ranges for both sign-in and sign-out.

**Tech Stack:** Python 3.12, PyYAML, GitHub Actions (`workflow_dispatch`, `GITHUB_TOKEN`).

**Scope:** This is the backend subsystem only. The Android app that calls this workflow is a separate plan, written after this is merged.

## Global Constraints

- `mark-leave.yml` inputs: `from` (optional, `YYYY-MM-DD`, blank ⇒ today IST), `to` (optional, blank ⇒ equals `from`).
- All date defaulting is computed in `Asia/Kolkata` (IST), reusing `should_run.today_ist()`.
- Leave range stored as a line `- {from: YYYY-MM-DD, to: YYYY-MM-DD}` appended to `leave.yaml`; existing comments and entries preserved.
- Re-submitting an identical range is a clean no-op (dedupe; no duplicate line, no empty commit).
- Validation: dates must parse as ISO; `from <= to`; otherwise fail loudly (non-zero exit / red run).
- The workflow commits `leave.yaml` to `main` via `GITHUB_TOKEN` with `permissions: contents: write`. This is the feature's intended mechanism (leave must land on `main` for `should_run.py` to read it).
- `workflow_dispatch` inputs are passed into shell steps via `env:` (never interpolated directly into `run:` — avoids script injection).
- DRY: reuse `should_run.today_ist()` and `should_run.load_leave_ranges()`; do not re-implement IST or YAML parsing.

---

### Task 1: `add_leave.py` — date resolution, validation, dedup-append (TDD)

**Files:**
- Create: `add_leave.py`
- Test: `tests/test_add_leave.py`

**Interfaces:**
- Consumes: `should_run.today_ist() -> datetime.date`; `should_run.load_leave_ranges(path: Path) -> list[tuple[date, date]]` (existing).
- Produces:
  - `resolve_dates(from_str: str, to_str: str, today: date) -> tuple[date, date]`
  - `add_leave_range(path: Path, start: date, end: date) -> bool` (True if appended, False if already present)
  - CLI: `python add_leave.py --from <str> --to <str>` (both optional, default `""`), prints result, exit 0 on success / non-zero on invalid input.

- [ ] **Step 1: Write the failing tests**

`tests/test_add_leave.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd daily-swipe && source .venv/bin/activate && python -m pytest tests/test_add_leave.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'add_leave'`.

- [ ] **Step 3: Write `add_leave.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_add_leave.py -v`
Expected: PASS (8 passed).

- [ ] **Step 5: Run the full suite to confirm no regressions**

Run: `python -m pytest -v`
Expected: all tests pass (existing `test_should_run.py` + new `test_add_leave.py`), output pristine.

- [ ] **Step 6: Commit**

```bash
git add add_leave.py tests/test_add_leave.py
git commit -m "feat: add_leave.py — resolve/validate/dedup-append leave ranges"
```

---

### Task 2: `mark-leave.yml` workflow

**Files:**
- Create: `.github/workflows/mark-leave.yml`

**Interfaces:**
- Consumes: `add_leave.py` (CLI `--from`/`--to`); `leave.yaml`.
- Produces: a `workflow_dispatch` workflow `mark-leave.yml` that records a range and commits it. Dispatched via `POST /repos/AyushHarshit/daily-swipe/actions/workflows/mark-leave.yml/dispatches` with `{"ref":"main","inputs":{"from":"…","to":"…"}}`.

- [ ] **Step 1: Write `.github/workflows/mark-leave.yml`**

```yaml
name: Mark Leave
on:
  workflow_dispatch:
    inputs:
      from:
        description: "Start date YYYY-MM-DD (blank = today IST)"
        required: false
        default: ""
      to:
        description: "End date YYYY-MM-DD (blank = same as from)"
        required: false
        default: ""

permissions:
  contents: write

jobs:
  mark-leave:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Append leave range
        env:
          IN_FROM: ${{ inputs.from }}
          IN_TO: ${{ inputs.to }}
        run: python add_leave.py --from "$IN_FROM" --to "$IN_TO"
      - name: Commit if changed
        run: |
          if [[ -n "$(git status --porcelain leave.yaml)" ]]; then
            git config user.name "daily-swipe-bot"
            git config user.email "actions@users.noreply.github.com"
            git add leave.yaml
            git commit -m "chore: record leave via mark-leave [skip ci]"
            git push
          else
            echo "No change — range already present."
          fi
```

- [ ] **Step 2: Validate the YAML locally**

Run: `cd daily-swipe && source .venv/bin/activate && python -c "import yaml; d=yaml.safe_load(open('.github/workflows/mark-leave.yml')); print('triggers:', list((d.get('on') or d.get(True)).keys()), '| perms:', d['permissions'])"`
Expected: `triggers: ['workflow_dispatch'] | perms: {'contents': 'write'}`

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/mark-leave.yml
git commit -m "ci: mark-leave workflow — dispatch records a leave range in leave.yaml"
```

- [ ] **Step 4: End-to-end test (after the PR merges to main — dispatch only sees workflows on the default branch)**

> `workflow_dispatch` for a brand-new workflow only appears once the file is on the default branch. So this E2E step runs after merge.

Dispatch a test range via the API (token in a shell var; don't paste it raw):
```bash
read -rs GH_TOKEN
curl -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GH_TOKEN" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  -H "User-Agent: daily-swipe-cron" \
  https://api.github.com/repos/AyushHarshit/daily-swipe/actions/workflows/mark-leave.yml/dispatches \
  -d '{"ref":"main","inputs":{"from":"2026-12-25","to":"2026-12-25"}}' -i
```
Expected: `HTTP/2 204`. Then in the Actions tab the `Mark Leave` run is green, and a new commit adds `- {from: 2026-12-25, to: 2026-12-25}` to `leave.yaml`. Verify the skip logic locally after pulling:
```bash
git pull
python -c "import should_run as s, datetime as d; print(s.reason_to_skip(d.date(2026,12,25), s.load_holidays(s.CONFIG_DIR/'holidays.yaml'), s.load_leave_ranges(s.CONFIG_DIR/'leave.yaml')))"
```
Expected: prints a non-None reason mentioning the leave range. (Afterward, remove the test `2026-12-25` line from `leave.yaml` in a follow-up commit so it doesn't skip a real day.)

---

## Notes & risks

- **Commit to `main` from the workflow is intended** — `should_run.py` reads `leave.yaml` from the default branch, so leave must land there. `[skip ci]` + `GITHUB_TOKEN` commits don't retrigger workflows.
- **Script-injection safety:** dispatch inputs are passed via `env:` and quoted, never interpolated into a `run:` command.
- **Dedupe** prevents duplicate lines and empty commits on repeat submits.
- **E2E waits for merge** because `workflow_dispatch` on a new workflow requires the file on the default branch.
