# daily-swipe

Automated greytHR **sign in / sign out** (and leave) using GitHub Actions, triggered
on schedule by [cron-job.org](https://cron-job.org). A headless browser logs in and
clicks Sign In / Sign Out for you on working days; a phone app (optional) marks sick
or vacation days.

## How it works

- **`signin.yml` / `signout.yml`** — run `attendance.py`, which drives headless
  Chromium (Playwright) to log in and click Sign In / Sign Out.
- **`mark-leave.yml`** — runs `add_leave.py` to record a date range in `leave.yaml`
  and commit it, so sign-in/out skip those days.
- **`should_run.py`** — skips weekends, dates in `holidays.yaml`, and ranges in
  `leave.yaml` (all evaluated in IST).
- **Scheduling** — the workflows are triggered by cron-job.org calling the GitHub
  `workflow_dispatch` API at your chosen times. (GitHub's own `schedule:` is
  best-effort and was delaying runs by hours, so it isn't used.)
- **Randomized swipe time** — each run sleeps a random delay before swiping, so the
  recorded time isn't identical every day: sign-in lands **09:30–09:45**, sign-out
  **18:45–19:15** (windows start at the cron trigger time; tweak the `Random delay`
  step in the workflows to change them).

---

## Set it up for yourself

### 1. Clone / fork the repo
Fork this repo (or clone and push it to a **private** repo) under your own GitHub
account. Everything below happens on your copy.

### 2. Set up cron-job.org (the scheduler)
Create a free [cron-job.org](https://cron-job.org) account and add **two jobs**, each
with **timezone `Asia/Kolkata`**:

| Job | Cron (IST) | Method + URL |
|-----|-----------|--------------|
| Sign in | `30 9 * * 1-5` | `POST https://api.github.com/repos/<you>/<repo>/actions/workflows/signin.yml/dispatches` |
| Sign out | `45 18 * * 1-5` | `POST https://api.github.com/repos/<you>/<repo>/actions/workflows/signout.yml/dispatches` |

The cron time is the **start of the window** — the workflow adds a random delay, so
the actual swipe lands 09:30–09:45 / 18:45–19:15.

Each job's **headers**:
```
Accept: application/vnd.github+json
Authorization: Bearer <YOUR_TOKEN>        # from step 4
X-GitHub-Api-Version: 2022-11-28
User-Agent: daily-swipe
Content-Type: application/json
```
Request **body**: `{"ref":"main"}` — a successful trigger returns HTTP `204`.

### 3. Add your greytHR credentials as GitHub Secrets
Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value |
|--------|-------|
| `GREYTHR_URL` | your portal, e.g. `https://satc.greythr.com/` |
| `GREYTHR_USERNAME` | your greytHR username |
| `GREYTHR_PASSWORD` | your greytHR password |

### 4. Create a token
Create a **fine-grained personal access token** with **Actions: Read and write** on
your repo (and an expiry you'll remember to rotate). This token triggers the
workflows — paste it into the cron-job.org jobs (step 2) and, optionally, the app
(step 5). Store it only in those places; never commit it.

### 5. Point it at your portal's selectors
greytHR instances can differ, so capture your own login / Sign In / Sign Out
selectors:
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env          # fill in your greytHR credentials for local runs
python discover.py            # log in; note the field/button selectors it prints
```
Put the values you observe into **`locators.py`**, then verify without swiping:
```bash
python attendance.py signin --dry-run
```

### 6. (Optional) Mark sick / vacation from your phone
Both options dispatch `mark-leave.yml` to add a date range to `leave.yaml` (so
sign-in/out skip it), reusing the **same token** from step 4:

- **iPhone** — no app needed: two iOS Shortcuts (Sick / Vacation with date prompts).
  Full recipe: [docs/ios-shortcuts.md](docs/ios-shortcuts.md).
- **Android** — a small app in a separate repo (`daily-swipe-leave-app`). Build it
  via its GitHub Actions workflow and sideload the APK.

---

## Day-to-day

- **Take leave** — add a range to `leave.yaml` (`- {from: 2026-07-10, to: 2026-07-14}`)
  and push, or use the app. Both sign-in and sign-out skip those days.
- **Holidays** — add dates to `holidays.yaml` (`- 2026-08-15`) and push.
- **Pause entirely** — disable the cron-job.org jobs.
- **Push changes** — `./push.sh main` (pushes using the token in a local, gitignored
  `.token` file).

## Files

| File | Purpose |
|------|---------|
| `attendance.py` | Logs in and clicks Sign In / Sign Out (Playwright). |
| `should_run.py` | Decides if today is a working day (weekend / holiday / leave, IST). |
| `add_leave.py` | Appends a leave range to `leave.yaml` (used by `mark-leave.yml`). |
| `discover.py` | One-off helper to capture your portal's selectors. |
| `locators.py` | The login / Sign In / Sign Out selectors. |
| `holidays.yaml` / `leave.yaml` | Dates to skip. |
| `.github/workflows/*.yml` | signin, signout, mark-leave (triggered via the API). |
