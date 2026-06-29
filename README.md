# daily-swipe

Automated greytHR sign in / sign out via Playwright + GitHub Actions.
See `docs/superpowers/specs/2026-06-29-daily-swipe-design.md` for the design.

## Local setup
1. `python -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `python -m playwright install chromium`
4. `cp .env.example .env` and fill in your greytHR credentials.

(Full usage, secrets, and pause instructions added in Task 6.)
