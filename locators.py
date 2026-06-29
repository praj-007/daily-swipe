"""Verified greytHR selectors. Update if greytHR changes its UI.

PLACEHOLDER VALUES — these must be replaced by running `python discover.py` with real
credentials and reading off the actual selectors before the automation will work.

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
