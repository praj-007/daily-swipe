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
