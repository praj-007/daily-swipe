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
