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
