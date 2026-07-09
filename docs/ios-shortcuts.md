# Mark leave from an iPhone (iOS Shortcuts)

No app needed on iOS — the built-in **Shortcuts** app can call the `mark-leave.yml`
workflow directly. You'll create two shortcuts: **🤒 Sick** (one date, defaults to
today) and **🏖️ Vacation** (a from/to range). Both add the dates to `leave.yaml`,
so sign-in and sign-out skip those days.

**You need:** your fine-grained GitHub token with **Actions: Read and write** on this
repo (the same one used by cron-job.org).

---

## Shortcut 1 — 🤒 Sick (single day)

Open **Shortcuts** → **+** (new shortcut), then add these actions in order:

1. **Date** — set to *Ask Each Time*. When you run the shortcut, iOS shows a date
   picker prefilled with today; keep it or pick another day.
2. **Format Date** — input: the Date from step 1. Set *Date Format* → **Custom** →
   format string exactly: `yyyy-MM-dd`
3. **Get Contents of URL** — expand *Show More* and configure:
   - **URL:**
     `https://api.github.com/repos/AyushHarshit/daily-swipe/actions/workflows/mark-leave.yml/dispatches`
   - **Method:** `POST`
   - **Headers** (add each):
     | Key | Value |
     |-----|-------|
     | `Accept` | `application/vnd.github+json` |
     | `Authorization` | `Bearer <YOUR_TOKEN>` |
     | `X-GitHub-Api-Version` | `2022-11-28` |
     | `User-Agent` | `daily-swipe-ios` |
     | `Content-Type` | `application/json` |
   - **Request Body:** `JSON` → add a text field is fiddly, so choose **File** →
     switch body type to *Text* if offered, or use JSON fields:
     - `ref` (Text) = `main`
     - `inputs` (Dictionary) → `from` (Text) = *Formatted Date* (the variable from
       step 2), `to` (Text) = *Formatted Date*
4. Name it **Sick**, pick an icon, and **Add to Home Screen** (Share sheet → Add to
   Home Screen). You can also run it by voice: "Hey Siri, Sick".

## Shortcut 2 — 🏖️ Vacation (date range)

Same as above, but with two date prompts:

1. **Date** (*Ask Each Time*) — the first prompt is the **start** date.
2. **Format Date** → `yyyy-MM-dd` → rename the result variable to *FromDate*
   (tap the variable → Rename).
3. **Date** (*Ask Each Time*) — the second prompt is the **end** date.
4. **Format Date** → `yyyy-MM-dd` → rename to *ToDate*.
5. **Get Contents of URL** — identical to Sick, except the JSON `inputs` dictionary
   uses `from` = *FromDate* and `to` = *ToDate*.
6. Name it **Vacation**, add to Home Screen.

---

## Verify it works

Run the shortcut. Success is **silent** (the API returns HTTP 204 with no body).
To confirm:

1. Repo → **Actions** → a **Mark Leave** run appears within seconds and turns green.
2. `leave.yaml` on `main` gets a new commit with your date(s).

If the shortcut shows an error:
- **401** — the token is wrong/expired. Re-paste it in the `Authorization` header
  (format: `Bearer github_pat_…`, one space after Bearer).
- **404** — the token lacks access to this repo, or the URL has a typo.
- **422** — the body/JSON is malformed; re-check step 3's fields and that the dates
  are `yyyy-MM-dd`.

## Notes

- The token lives only inside your shortcuts on your device (synced by iCloud).
  Don't share the shortcut with anyone — sharing includes the token.
- Marking a day that's already recorded is harmless (the workflow de-duplicates).
- If you mark **today** after the morning sign-in already ran, the record stays —
  trigger a manual sign-out from the Actions tab if needed.
