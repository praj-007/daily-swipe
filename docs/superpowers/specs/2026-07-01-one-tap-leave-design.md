# One-Tap Leave — Design

**Date:** 2026-07-01
**Status:** Approved design

## Overview

Add a way to mark ad-hoc leave (sick day) or planned vacation from a phone, so the
daily greytHR automation skips signing in/out on those days. A small native Android
app lets the user pick dates and fires the GitHub API, which triggers a new
`mark-leave` workflow that records the dates in `leave.yaml`. The existing
`should_run.py` already reads `leave.yaml`, so both sign-in and sign-out skip those
days automatically.

## Goals

- One-tap "Sick today" from the phone (date defaults to today, editable).
- "Vacation" mode to mark a start–end range from the phone.
- Marked leave skips **both** sign-in and sign-out for those days.
- Nothing publicly reachable; no server to maintain; no local Android Studio.
- Credentials never committed or exposed in app/source.

## Non-Goals

- No greytHR-side leave application (this only controls the local automation).
- No editing/removing existing leave from the app (edit `leave.yaml` directly for that).
- No release signing / Play Store — a debug-signed APK, sideloaded, is sufficient.

## Constraints (confirmed with user)

- Front end is a **native Android APK**, built in the cloud via **GitHub Actions**
  (no local Android Studio); downloaded as a build artifact and sideloaded.
- Nothing may be publicly reachable (rules out public web hosting).
- Reuse the existing fine-grained token (Actions: read/write on `daily-swipe`).
- greytHR sign-in runs ~09:30 IST, sign-out ~18:30 IST, triggered by cron-job.org
  via the `workflow_dispatch` API (GitHub `schedule:` is disabled).

## Architecture

Two components across two repos:

1. **Backend — `mark-leave.yml`** in the existing `daily-swipe` repo. A
   `workflow_dispatch` workflow that appends leave dates to `leave.yaml` and commits
   them, using the built-in `GITHUB_TOKEN`.
2. **Front end — a native Android app** in a new repo (e.g. `daily-swipe-leave-app`,
   private). Single screen: Sick (one date) / Vacation (range). It calls the GitHub
   API to dispatch `mark-leave.yml`. The APK is built by a GitHub Actions workflow in
   that repo and downloaded as an artifact.

The existing `should_run.py` in `daily-swipe` already skips weekends, `holidays.yaml`,
and `leave.yaml` ranges (in IST) — no change needed there.

## Component A — `mark-leave.yml` (backend)

**Trigger:** `workflow_dispatch` with two optional string inputs:
- `from` — start date `YYYY-MM-DD`. Blank ⇒ today in IST.
- `to` — end date `YYYY-MM-DD`. Blank ⇒ equal to `from`.

**Permissions:** `contents: write` (to commit `leave.yaml` via `GITHUB_TOKEN`).

**Logic** (in a new, unit-tested `add_leave.py`):
- Resolve `from` (default today IST) and `to` (default = `from`).
- Validate: both parse as ISO dates; `from <= to`.
- Load existing ranges from `leave.yaml`; append `- {from: F, to: T}` **only if that
  exact range is not already present** (dedupe).
- Write `leave.yaml` back (preserving existing entries and the file's comment header).

**Workflow steps:** checkout → setup-python → `pip install pyyaml` → run
`add_leave.py` with inputs → if the file changed, `git commit` + `git push` (author =
a bot identity; `GITHUB_TOKEN` auth). No-op cleanly if the range already existed.

**Effect:** the next scheduled sign-in and sign-out call `should_run.py`, which sees
the new range and skips.

## Component B — Android app (front end)

**Stack:** Kotlin + Jetpack Compose, single screen (single Activity). Minimal
dependencies (Compose + an HTTP client — `HttpURLConnection` or OkHttp).

**UI:**
- A mode toggle: **Sick** and **Vacation**.
- Sick: one date field, prefilled with today, editable via a date picker.
- Vacation: two date fields (start, end) via date pickers; validated start ≤ end.
- A **Submit** button; a status line showing the result (e.g. "Recorded ✓ (204)" or
  the error).
- A settings field to paste the API token once.

**Token storage:** the fine-grained token is stored on-device in
`EncryptedSharedPreferences`. It is never in the app source or committed anywhere.

**Network call:** on Submit, POST to
`https://api.github.com/repos/AyushHarshit/daily-swipe/actions/workflows/mark-leave.yml/dispatches`
with headers `Accept: application/vnd.github+json`,
`Authorization: Bearer <token>`, `X-GitHub-Api-Version: 2022-11-28`,
`User-Agent: daily-swipe-leave`, `Content-Type: application/json`, and body
`{"ref":"main","inputs":{"from":"<from>","to":"<to>"}}`. Success = HTTP 204.

**Build & distribution:** a GitHub Actions workflow (`build-apk.yml`) in the app repo
runs `./gradlew assembleDebug`, then uploads `app-debug.apk` as an artifact. The user
downloads it from the run and sideloads it (enable "install unknown apps"). The APK is
debug-signed — fine for personal sideloading. The cloud build is also the compile
verification; build failures are fixed from the Actions log.

## Data flow

phone (pick dates, Submit) → GitHub API dispatch of `mark-leave.yml` →
`add_leave.py` appends range to `leave.yaml` → workflow commits + pushes →
next `should_run.py` (sign-in and sign-out) sees the range → skips those days.

## Security

- App source (in a possibly-public build repo) contains **no token**. The token lives
  only in the phone's `EncryptedSharedPreferences`.
- The token is the existing **fine-grained, Actions:read/write, `daily-swipe`-only**
  PAT — it can only trigger workflows on that one repo.
- The `leave.yaml` commit is made by the workflow's **`GITHUB_TOKEN`**, so the phone
  token never needs `contents` write.
- The build repo needs no secrets (debug build).

## Error handling & edge cases

- **Client-side validation:** the app checks date format and start ≤ end before
  sending; disables Submit otherwise.
- **Server-side validation:** `add_leave.py` re-validates and the workflow fails
  visibly (red run) on bad input.
- **Dedupe:** re-submitting the same range is a clean no-op (no duplicate lines, no
  empty commit).
- **Race window:** if leave is marked after the ~09:30 sign-in already ran, the range
  still records (so sign-out skips), and the user can fire a one-off sign-out to undo
  the sign-in. Documented; mark leave before ~09:25 to avoid it.
- **Network/API failure:** the app surfaces the HTTP status / error text so the user
  knows it did not register.

## Testing

- **Unit tests** for `add_leave.py`: today-default for `from`; `to` defaults to
  `from`; range validation (`from <= to`, bad format rejected); dedupe (no duplicate
  append); existing entries preserved.
- **APK build workflow** is the app's compile verification.
- **Manual end-to-end:** Sick and Vacation submissions each return 204, produce a
  `mark-leave` run, commit the expected `leave.yaml` entry, and cause `should_run.py`
  to report SKIP for those dates.

## Build sequence

Build and verify the **backend first** (`mark-leave.yml` + `add_leave.py`) — it is
independently testable with a `curl` dispatch and immediately usable. Then build the
**Android app + build workflow** on top of that proven contract.

## Open questions

None — all decisions confirmed (native APK, GitHub Actions build, own repo, reuse
existing token, MVP confirmation = show HTTP status).
