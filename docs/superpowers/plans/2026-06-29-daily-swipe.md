# daily-swipe — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically sign in and sign out of the greytHR portal (`satc.greythr.com`) on working days via a Python + Playwright script driven by two scheduled GitHub Actions workflows.

**Architecture:** A private GitHub repo holds the script and two cron workflows. Each run checks (in IST) whether today is a working day, then drives headless Chromium through the real login + swipe UI, verifies the state changed, and saves a screenshot artifact. No persistent server.

**Tech Stack:** Python 3.12, Playwright (sync API, Chromium), PyYAML, python-dotenv (local dev only), GitHub Actions.

## Global Constraints

- Login is username + password only — no OTP/2FA/SSO/captcha handling.
- greytHR credentials come ONLY from env vars (`GREYTHR_URL`, `GREYTHR_USERNAME`, `GREYTHR_PASSWORD`), injected from GitHub Secrets in CI or a gitignored `.env` locally. Never hardcode, print, or commit them.
- All working-day / holiday / leave decisions are computed in `Asia/Kolkata` (IST), never from the UTC cron clock.
- Schedule: sign in `0 4 * * 1-5` (09:30 IST), sign out `0 13 * * 1-5` (18:30 IST). UTC = IST − 5:30.
- Idempotent: never double-swipe. Read current state before acting.
- Fail loudly on errors (non-zero exit) so GitHub emails a failure notice; a clean skip exits 0.
- Repo stays private. `.token`, `.env`, `screenshots/`, `.DS_Store` stay gitignored.
- Python style: standard library + the listed deps only; selectors centralized in one module.

---

### Task 1: Project setup & dependencies

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Modify: `.gitignore` (confirm `.env` already ignored — added during scaffolding)
- Create: `README.md` (skeleton; finalized in Task 6)

**Interfaces:**
- Consumes: nothing.
- Produces: a working Python env with Playwright Chromium installed; `.env.example` documenting the three required env vars.

- [ ] **Step 1: Write `requirements.txt`**

```
playwright==1.49.1
pyyaml==6.0.2
python-dotenv==1.0.1
```

- [ ] **Step 2: Write `.env.example`**

```
# Copy to .env (gitignored) for local runs. Never commit the real .env.
GREYTHR_URL=https://satc.greythr.com/
GREYTHR_USERNAME=your-employee-id-or-email
GREYTHR_PASSWORD=your-password
```

- [ ] **Step 3: Write `README.md` skeleton**

```markdown
# daily-swipe

Automated greytHR sign in / sign out via Playwright + GitHub Actions.
See `docs/superpowers/specs/2026-06-29-daily-swipe-design.md` for the design.

## Local setup
1. `python -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `python -m playwright install chromium`
4. `cp .env.example .env` and fill in your greytHR credentials.

(Full usage, secrets, and pause instructions added in Task 6.)
```

- [ ] **Step 4: Create venv and install**

Run:
```bash
cd daily-swipe
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```
Expected: installs succeed; `python -c "import playwright, yaml, dotenv; print('ok')"` prints `ok`.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .env.example README.md .gitignore
git commit -m "chore: project dependencies and dev scaffolding"
```

---

### Task 2: Working-day decision logic (`should_run.py`) — TDD

**Files:**
- Create: `should_run.py`
- Create: `holidays.yaml`
- Create: `leave.yaml`
- Test: `tests/test_should_run.py`

**Interfaces:**
- Consumes: `holidays.yaml`, `leave.yaml`.
- Produces:
  - `reason_to_skip(day: date, holidays: set[date], leave: list[tuple[date, date]]) -> str | None`
  - `load_holidays(path: Path) -> set[date]`
  - `load_leave_ranges(path: Path) -> list[tuple[date, date]]`
  - `today_ist() -> date`
  - CLI: prints `RUN` or `SKIP: <reason>`, exits 0, and writes `should_run=true|false` to `$GITHUB_OUTPUT` when set. The workflows gate the swipe step on this output.

- [ ] **Step 1: Write the failing tests**

`tests/test_should_run.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd daily-swipe && python -m pytest tests/test_should_run.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'should_run'` (or attribute errors).

- [ ] **Step 3: Write `should_run.py`**

```python
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
    if day.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        return f"{day} is a weekend"
    if day in holidays:
        return f"{day} is a public holiday"
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
```

- [ ] **Step 4: Create config files**

`holidays.yaml`:
```yaml
# Public holidays to skip (YYYY-MM-DD). Edit and push to update.
# - 2026-08-15
# - 2026-10-02
```

`leave.yaml`:
```yaml
# Personal leave ranges to skip (inclusive). Auto-resumes after `to`.
# - {from: 2026-07-10, to: 2026-07-14}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_should_run.py -v`
Expected: PASS (9 passed).

- [ ] **Step 6: Commit**

```bash
git add should_run.py holidays.yaml leave.yaml tests/test_should_run.py
git commit -m "feat: working-day/holiday/leave skip logic in IST"
```

---

### Task 3: Login & selector discovery (`discover.py` → `locators.py`)

> This task is exploratory because greytHR is a JS-rendered SPA (possibly with web-component shadow DOM) whose exact selectors are unknown. Its deliverable is a verified `locators.py`. Run it locally with real credentials in `.env`; do NOT commit any captured credentials or full-page HTML containing personal data.
>
> Note: the module is named `locators.py`, NOT `selectors.py`, to avoid shadowing Python's stdlib `selectors` module (used by `asyncio`, which Playwright relies on).

**Files:**
- Create: `discover.py` (one-off helper; kept in repo for future re-discovery)
- Create: `locators.py` (the verified output — constants consumed by Task 4)

**Interfaces:**
- Consumes: `GREYTHR_URL`, `GREYTHR_USERNAME`, `GREYTHR_PASSWORD` from env/`.env`.
- Produces: `locators.py` exposing these module-level string constants used by `attendance.py`:
  - `USERNAME` — locator for the username/employee-id field
  - `PASSWORD` — locator for the password field
  - `LOGIN_BUTTON` — locator for the submit button
  - `DASHBOARD_READY` — a locator that exists only once login succeeds (landing/home)
  - `SIGN_IN_BUTTON` — the "Sign In" swipe button (present when signed OUT)
  - `SIGN_OUT_BUTTON` — the "Sign Out" swipe button (present when signed IN)

- [ ] **Step 1: Write `discover.py`**

```python
"""One-off: log in to greytHR and print candidate selectors for the login + swipe UI.

Run headed so you can watch it: `python discover.py`.
Prints role/label/text candidates and saves a screenshot to screenshots/discover.png.
"""
from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import sync_playwright

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

URL = os.environ["GREYTHR_URL"]
USER = os.environ["GREYTHR_USERNAME"]
PW = os.environ["GREYTHR_PASSWORD"]


def main() -> None:
    Path("screenshots").mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        page = browser.new_context().new_page()
        page.goto(URL, wait_until="networkidle")
        page.wait_for_timeout(2000)

        print("\n=== INPUTS ON LOGIN PAGE ===")
        for el in page.locator("input").all():
            print(
                "input:",
                {
                    "type": el.get_attribute("type"),
                    "name": el.get_attribute("name"),
                    "id": el.get_attribute("id"),
                    "placeholder": el.get_attribute("placeholder"),
                },
            )
        print("\n=== BUTTONS ON LOGIN PAGE ===")
        for el in page.get_by_role("button").all():
            print("button text:", repr(el.inner_text()))

        # >>> After inspecting the prints, fill the real fields, e.g.:
        # page.get_by_label("Username").fill(USER)
        # page.get_by_label("Password").fill(PW)
        # page.get_by_role("button", name="Log in").click()
        input("\nLog in manually in the browser if needed, then press Enter here...")

        page.wait_for_timeout(2000)
        print("\n=== POST-LOGIN BUTTONS (look for Sign In / Sign Out) ===")
        for el in page.get_by_role("button").all():
            print("button text:", repr(el.inner_text()))
        page.screenshot(path="screenshots/discover.png", full_page=True)
        print("\nSaved screenshots/discover.png")
        input("Press Enter to close...")
        browser.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run discovery and record findings**

Run: `cd daily-swipe && source .venv/bin/activate && python discover.py`
Expected: a visible browser opens; the console lists input fields and button texts. Note the working locators for username, password, login button, the dashboard-ready element, and the Sign In vs Sign Out button. Confirm the button text toggles between "Sign In" and "Sign Out" by signing in/out manually once.

> If fields are inside shadow DOM, prefer Playwright's `get_by_role` / `get_by_label` / `get_by_text` (they pierce open shadow roots) over raw CSS. Record the exact accessible names observed.

- [ ] **Step 3: Write `locators.py` from the findings**

Fill each constant with the verified locator string discovered in Step 2. Use Playwright locator syntax. Example shape (replace values with what you actually observed):
```python
"""Verified greytHR selectors. Update if greytHR changes its UI.

Each value is passed to Playwright via page.locator(...). For accessible-name
based locators we store a CSS/text selector that page.locator supports, e.g.
'role=button[name="Sign In"]' or 'text=Sign In' or '#username'.
"""

USERNAME = "#username"                 # e.g. "#username" or 'input[name="username"]'
PASSWORD = "#password"
LOGIN_BUTTON = 'role=button[name="Log in"]'
DASHBOARD_READY = 'text=Sign Out, text=Sign In'  # an element present only post-login
SIGN_IN_BUTTON = 'role=button[name="Sign In"]'
SIGN_OUT_BUTTON = 'role=button[name="Sign Out"]'
```
> `DASHBOARD_READY` must match an element that appears ONLY after successful login (the attendance card is a good choice, since either Sign In or Sign Out will be present). Pick whichever single stable selector you confirmed.

- [ ] **Step 4: Verify locators load**

Run: `python -c "import locators as l; print(l.USERNAME, l.SIGN_IN_BUTTON, l.SIGN_OUT_BUTTON)"`
Expected: prints the three values without error.

- [ ] **Step 5: Commit (no credentials, no full-page HTML)**

```bash
git add discover.py locators.py
git commit -m "feat: capture verified greytHR login + swipe selectors"
```

---

### Task 4: Attendance script (`attendance.py`)

**Files:**
- Create: `attendance.py`

**Interfaces:**
- Consumes: `locators.py` constants; `GREYTHR_*` env vars.
- Produces: CLI `python attendance.py {signin|signout} [--dry-run]`. Logs in, reads current swipe state, performs the action only if needed (idempotent), verifies the state flipped, saves `screenshots/<action>-<ist-timestamp>.png`. Exit 0 on success/skip; exit non-zero on any failure.

- [ ] **Step 1: Write `attendance.py`**

```python
"""greytHR attendance automation: sign in / sign out via headless Chromium."""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.sync_api import TimeoutError as PWTimeout, sync_playwright

import locators as S

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

IST = ZoneInfo("Asia/Kolkata")
SCREENSHOT_DIR = Path("screenshots")
NAV_TIMEOUT_MS = 45_000
ACTION_TIMEOUT_MS = 20_000


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"ERROR: required environment variable {name} is not set", file=sys.stderr)
        sys.exit(2)
    return value


def _timestamp() -> str:
    return datetime.now(IST).strftime("%Y%m%d-%H%M%S")


def run(action: str, dry_run: bool) -> None:
    url = _require_env("GREYTHR_URL")
    username = _require_env("GREYTHR_USERNAME")
    password = _require_env("GREYTHR_PASSWORD")
    SCREENSHOT_DIR.mkdir(exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(ACTION_TIMEOUT_MS)
        try:
            page.goto(url, wait_until="networkidle", timeout=NAV_TIMEOUT_MS)
            page.locator(S.USERNAME).fill(username)
            page.locator(S.PASSWORD).fill(password)
            page.locator(S.LOGIN_BUTTON).click()
            page.wait_for_selector(S.DASHBOARD_READY, timeout=NAV_TIMEOUT_MS)

            signed_in = page.locator(S.SIGN_OUT_BUTTON).count() > 0
            print(f"Current state: {'SIGNED IN' if signed_in else 'SIGNED OUT'}")

            shot = SCREENSHOT_DIR / f"{action}-{_timestamp()}.png"

            if action == "signin":
                if signed_in:
                    print("Already signed in; nothing to do.")
                elif dry_run:
                    print("DRY-RUN: would click Sign In.")
                else:
                    page.locator(S.SIGN_IN_BUTTON).click()
                    page.wait_for_selector(S.SIGN_OUT_BUTTON, timeout=ACTION_TIMEOUT_MS)
                    print("Signed in.")
            elif action == "signout":
                if not signed_in:
                    print("Already signed out; nothing to do.")
                elif dry_run:
                    print("DRY-RUN: would click Sign Out.")
                else:
                    page.locator(S.SIGN_OUT_BUTTON).click()
                    page.wait_for_selector(S.SIGN_IN_BUTTON, timeout=ACTION_TIMEOUT_MS)
                    print("Signed out.")

            page.screenshot(path=str(shot))
            print(f"Screenshot saved: {shot}")
        except PWTimeout as exc:
            fail_shot = SCREENSHOT_DIR / f"FAILED-{action}-{_timestamp()}.png"
            try:
                page.screenshot(path=str(fail_shot))
                print(f"Failure screenshot: {fail_shot}", file=sys.stderr)
            except Exception:
                pass
            print(f"ERROR: timed out during {action}: {exc}", file=sys.stderr)
            sys.exit(1)
        finally:
            browser.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="greytHR attendance automation")
    parser.add_argument("action", choices=["signin", "signout"])
    parser.add_argument("--dry-run", action="store_true", help="log in and report state without swiping")
    args = parser.parse_args()
    run(args.action, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Verify login + state detection without swiping (dry run)**

Run: `cd daily-swipe && source .venv/bin/activate && python attendance.py signin --dry-run`
Expected: prints `Current state: SIGNED IN` or `SIGNED OUT`, then `DRY-RUN: would click Sign In.` (or `Already signed in`), and saves a screenshot. No actual swipe occurs. This confirms login + selectors work end-to-end.

- [ ] **Step 3: Verify a real sign-in, then sign-out (only when you actually want to swipe)**

Run (e.g. at the start of your workday):
```bash
python attendance.py signin
```
Expected: `Signed in.` and the greytHR card now shows Sign Out (confirm in the screenshot). Run `python attendance.py signin` again → `Already signed in; nothing to do.` (idempotency). At end of day: `python attendance.py signout` → `Signed out.`

- [ ] **Step 4: Commit**

```bash
git add attendance.py
git commit -m "feat: idempotent sign in/out script with dry-run and screenshots"
```

---

### Task 5: GitHub Actions workflows + secrets

**Files:**
- Create: `.github/workflows/signin.yml`
- Create: `.github/workflows/signout.yml`

**Interfaces:**
- Consumes: repo secrets `GREYTHR_URL`, `GREYTHR_USERNAME`, `GREYTHR_PASSWORD`; `should_run.py` output `should_run`; `attendance.py`.
- Produces: two scheduled jobs that skip non-working days and upload screenshot artifacts.

- [ ] **Step 1: Add the three repo secrets (manual, in GitHub UI)**

In `github.com/AyushHarshit/daily-swipe` → Settings → Secrets and variables → Actions → New repository secret. Add `GREYTHR_URL` = `https://satc.greythr.com/`, `GREYTHR_USERNAME`, `GREYTHR_PASSWORD`. (Do this in the browser; never put them in code.)

- [ ] **Step 2: Write `.github/workflows/signin.yml`**

```yaml
name: greytHR Sign In
on:
  schedule:
    - cron: "0 4 * * 1-5"   # 09:30 IST (UTC = IST - 5:30)
  workflow_dispatch:        # allow manual runs for testing

jobs:
  signin:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Decide whether today is a working day (IST)
        id: check
        run: python should_run.py
      - name: Install dependencies
        if: steps.check.outputs.should_run == 'true'
        run: |
          pip install -r requirements.txt
          python -m playwright install --with-deps chromium
      - name: Sign in
        if: steps.check.outputs.should_run == 'true'
        env:
          GREYTHR_URL: ${{ secrets.GREYTHR_URL }}
          GREYTHR_USERNAME: ${{ secrets.GREYTHR_USERNAME }}
          GREYTHR_PASSWORD: ${{ secrets.GREYTHR_PASSWORD }}
        run: python attendance.py signin
      - name: Upload screenshot
        if: always() && steps.check.outputs.should_run == 'true'
        uses: actions/upload-artifact@v4
        with:
          name: signin-screenshot
          path: screenshots/
          if-no-files-found: ignore
```

- [ ] **Step 3: Write `.github/workflows/signout.yml`**

```yaml
name: greytHR Sign Out
on:
  schedule:
    - cron: "0 13 * * 1-5"  # 18:30 IST (UTC = IST - 5:30)
  workflow_dispatch:

jobs:
  signout:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Decide whether today is a working day (IST)
        id: check
        run: python should_run.py
      - name: Install dependencies
        if: steps.check.outputs.should_run == 'true'
        run: |
          pip install -r requirements.txt
          python -m playwright install --with-deps chromium
      - name: Sign out
        if: steps.check.outputs.should_run == 'true'
        env:
          GREYTHR_URL: ${{ secrets.GREYTHR_URL }}
          GREYTHR_USERNAME: ${{ secrets.GREYTHR_USERNAME }}
          GREYTHR_PASSWORD: ${{ secrets.GREYTHR_PASSWORD }}
        run: python attendance.py signout
      - name: Upload screenshot
        if: always() && steps.check.outputs.should_run == 'true'
        uses: actions/upload-artifact@v4
        with:
          name: signout-screenshot
          path: screenshots/
          if-no-files-found: ignore
```

- [ ] **Step 4: Push and trigger a manual test run**

```bash
git add .github/workflows/signin.yml .github/workflows/signout.yml
git commit -m "ci: scheduled sign in/out workflows with working-day gate"
./push.sh main
```
Then in GitHub → Actions → "greytHR Sign In" → Run workflow (workflow_dispatch). On a weekday it should install, run, and upload a `signin-screenshot` artifact showing your signed-in state. Download the artifact and verify. (Run on a real working day, or temporarily test logic with `--dry-run` by editing the run step on a branch.)
Expected: green run; artifact contains a screenshot proving the swipe (or a clean "already signed in").

---

### Task 6: README finalization & end-to-end verification

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: everything above.
- Produces: complete operator docs.

- [ ] **Step 1: Finalize `README.md`**

```markdown
# daily-swipe

Automated greytHR (`satc.greythr.com`) sign in / sign out on working days,
via Playwright + scheduled GitHub Actions. Design:
`docs/superpowers/specs/2026-06-29-daily-swipe-design.md`.

## How it works
- `signin.yml` runs 09:30 IST, `signout.yml` runs 18:30 IST (Mon–Fri).
- `should_run.py` skips weekends, `holidays.yaml`, and `leave.yaml` ranges (in IST).
- `attendance.py` logs in, checks current state, swipes only if needed, screenshots.

## Local setup
1. `python -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `python -m playwright install chromium`
4. `cp .env.example .env` and fill credentials.
5. Dry run: `python attendance.py signin --dry-run`

## Cloud setup (GitHub Actions)
Repo → Settings → Secrets and variables → Actions → add:
`GREYTHR_URL`, `GREYTHR_USERNAME`, `GREYTHR_PASSWORD`.

## Pausing for time off
- **Planned leave:** add a range to `leave.yaml`
  (`- {from: 2026-07-10, to: 2026-07-14}`), then `./push.sh`. Auto-resumes.
- **Ad-hoc day off:** Actions tab → the workflow → ⋯ → Disable workflow.
  Re-enable on return.

## Adding holidays
Edit `holidays.yaml` (one `- YYYY-MM-DD` per line), then `./push.sh`.

## Pushing changes
`./push.sh main` — pushes via the PAT in `.token` (gitignored, never committed).

## Maintenance
If greytHR changes its login/swipe UI, re-run `python discover.py` and update
`locators.py`. Failures email you automatically (GitHub Actions failure notice).
```

- [ ] **Step 2: Run the full local test suite**

Run: `cd daily-swipe && source .venv/bin/activate && python -m pytest -v`
Expected: all `should_run` tests pass.

- [ ] **Step 3: Commit and push**

```bash
git add README.md
git commit -m "docs: complete operator README"
./push.sh main
```

- [ ] **Step 4: Final end-to-end confirmation**

On a real working day: confirm the 09:30 IST run signs you in (check the Actions run + artifact), and the 18:30 IST run signs you out. After this passes once, the automation is live.

---

## Notes & risks

- **Selectors are the fragile part.** Task 3 de-risks by capturing them from the live site; `locators.py` is the single place to fix if greytHR changes its UI.
- **Shadow DOM:** if greytHR uses web components, prefer `get_by_role`/`get_by_label`/`get_by_text` locators (they pierce open shadow roots).
- **Cron drift:** GitHub scheduled runs may start 5–15 min late under load — acceptable for attendance.
- **Credential safety:** secrets live only in GitHub Secrets (CI) / `.env` (local, gitignored). The PAT lives only in `.token` (gitignored). Neither is ever printed or committed.
- **Wrong-day safety:** `should_run.py` is authoritative in IST; the cron `1-5` filter is a secondary guard.
