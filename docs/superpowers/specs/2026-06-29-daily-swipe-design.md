# daily-swipe — greytHR Attendance Automation

**Date:** 2026-06-29
**Status:** Approved design

## Overview

Automate daily attendance on the greytHR web portal (`satc.greythr.com`): sign in
each working morning and sign out each working evening, without manual effort. The
portal is a JavaScript single-page app with no employee-accessible developer API
(the official OAuth2 swipe API requires admin-generated keys we don't have), so the
automation drives the existing UI the same way a human does.

## Goals

- Sign in automatically on working-day mornings, sign out on working-day evenings.
- Run unattended in the cloud (no dependency on a personal laptop being awake).
- Keep credentials secure — never in code, repo, or chat history.
- Skip weekends and public holidays; fail loudly so a missed day is never silent.

## Non-Goals

- No use of the admin-only OAuth2 Attendance Swipe API.
- No automatic detection of personal leave (the user manually pauses for leave).
- No to-the-minute scheduling precision (GitHub cron drift of ~5–15 min is accepted).

## Constraints (confirmed with user)

- Login is **username + password only** — no OTP/2FA/SSO/captcha.
- **No IP or geo restriction** on web sign-in — a cloud datacenter IP works.
- Working days = **weekdays minus a user-supplied holiday list**; personal leave is
  handled by the user manually disabling the schedule.

## Architecture

A **private GitHub repository** (`daily-swipe`) containing a Python + Playwright
script driven by **two scheduled GitHub Actions workflows**:

- **Morning workflow** → runs the script with action `signin`.
- **Evening workflow** → runs the script with action `signout`.

Each run uses an ephemeral Ubuntu runner: launch headless Chromium → log in →
perform the action → verify → save a screenshot artifact → exit. Nothing runs
between jobs; there is no server to maintain.

**Language:** Python + Playwright (Playwright has first-class Python support and
installs cleanly on GitHub Actions runners).

## Components

- **`attendance.py`** — the Playwright script. Accepts an action argument
  (`signin` / `signout`); logs in, reads current swipe state, performs the action if
  needed, verifies the state flipped, and writes a screenshot.
- **`should_run.py`** — small helper that returns skip/run based on whether *today
  in IST* is a weekend or listed in `holidays.yaml`.
- **`holidays.yaml`** — user-editable list of public-holiday dates to skip.
- **`.github/workflows/signin.yml`** and **`signout.yml`** — the two cron schedules.
- **`requirements.txt`** — pinned dependencies (`playwright`, `pyyaml`).
- **`.gitignore`** — excludes the local git token file, `.env`, and any secrets
  (committed before anything else).
- **`README.md`** — setup steps (secrets, holiday editing, pausing for leave).

## Control flow (per run)

1. Workflow fires on cron → `should_run.py` checks weekday + not a holiday, computed
   in **IST**. If skip → exit 0 cleanly without touching greytHR.
2. Launch headless Chromium → open the portal → wait for the SPA to render →
   fill username + password (from secrets) → click Login → wait for the dashboard.
3. **Idempotency check:** read the dashboard's current swipe state. The portal shows
   a *Sign In* button when signed out and a *Sign Out* button when signed in.
   - `signin` run: if already signed in → log and skip (no double-swipe).
   - `signout` run: if already signed out → log and skip.
4. Otherwise click the correct button → wait for the status to flip → confirm.
5. Save a screenshot as a workflow artifact (proof of the run). Exit 0 on success,
   non-zero on failure.

## Scheduling & timezone

GitHub Actions cron runs in **UTC**. Conversion rule: `UTC = IST − 5:30`.

| Action | IST time | UTC cron |
|--------|----------|----------|
| Sign in | 09:30 IST | `00 04 * * 1-5` (04:00 UTC) |
| Sign out | 18:30 IST | `00 13 * * 1-5` (13:00 UTC) |

The `1-5` weekday filter in cron is a first pass; the authoritative weekday/holiday
decision is made by `should_run.py` **in IST**, because a UTC date can roll over and
misreport the day for early-IST times. Holiday skipping is therefore never dependent
on the cron clock.

**Accepted caveat:** GitHub's scheduled start can drift ~5–15 minutes under load.
Acceptable for attendance; if exact timing is ever required, migrate to a VM + cron.

## Security — credential handling

Two secret stores, kept strictly separate, neither ever passing through chat or code:

| Secret | Location | Purpose |
|--------|----------|---------|
| greytHR username + password (+ portal URL) | GitHub repo → Settings → Secrets (`GREYTHR_USERNAME`, `GREYTHR_PASSWORD`, `GREYTHR_URL`) | the Action logging in to swipe |
| Git access token | local token file, gitignored / kept outside the repo | authenticating `git push` to the personal repo |

Rules:
- Repo **must be private**.
- The script reads greytHR credentials only from environment variables injected from
  GitHub Secrets; GitHub masks them in logs automatically. Credentials are never
  committed, printed, or echoed.
- The local git token file is added to `.gitignore` **before the first commit** and
  is never read, opened, or echoed by the tooling. It is used only by the user's
  local git/`gh` auth to push.
- The push target is a **different git account** than the one linked to this
  environment; setup includes a `git remote -v` / identity check to avoid pushing
  under the wrong identity.

**User-acknowledged risk:** company portal credentials live in a personal GitHub
account's encrypted Secrets. Acceptable for personal attendance use; mitigated by a
private repo and GitHub secret encryption.

## Error handling & proof

- A screenshot artifact is saved on every run (success or failure) for an audit trail.
- On any failure (login change, button not found, network error) the job exits
  non-zero and **fails loudly** — GitHub emails the owner on workflow failure, so a
  missed swipe prompts a manual sign-in rather than a silent absence.
- All selectors are centralized in one place in `attendance.py` so a greytHR UI
  change is a one-spot fix.

## First implementation step (flagged risk)

The exact login field selectors and the signed-in/signed-out button labels are
unknown (JS-rendered SPA). **Task #1 is a discovery run**: point Playwright at the
site once, capture the real selectors and both swipe-button states, then build the
action logic on top. This de-risks the rest of the build.

## Open questions

None — all constraints confirmed.
