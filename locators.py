"""Verified greytHR selectors for the satc.greythr.com portal.

Confirmed working via `attendance.py --dry-run` on 2026-06-29: login (the OIDC
redirect through idp-coral.greythr.com), dashboard render, and state detection
all succeed with these values. Re-run `python discover.py` and update here if
greytHR changes its UI.

Each value is passed to Playwright via page.locator(...). For accessible-name
based locators we store a selector page.locator supports, e.g.
'role=button[name="Sign In"]' or '#username'.
"""

USERNAME = "#username"                 # e.g. "#username" or 'input[name="username"]'
PASSWORD = "#password"
LOGIN_BUTTON = 'role=button[name="Login"]'
SIGN_IN_BUTTON = 'role=button[name="Sign In"]'
SIGN_OUT_BUTTON = 'role=button[name="Sign Out"]'
