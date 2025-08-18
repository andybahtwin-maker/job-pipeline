
# Online Job Pipeline (Cloud-First, No Local Heavy Lifting)

This repo is a **hands-off job aggregator** you can edit in VS Code but run **online** on GitHub Actions.
It:
- Scrapes two public job sources (RemoteOK & Remotive) asynchronously
- Normalizes & filters by **your keywords**
- Writes a fresh CSV to `output/latest.csv`
- (Optional) pushes results to **Google Sheets** if you add credentials
- Runs **every 2 hours** automatically via GitHub Actions

> Goal: Flip the ATS game. You get a steady stream of relevant roles without touching your old machine.

---

## Quick Start (Fastest Path)

1. **Create a new private GitHub repo** named anything you like.
2. **Upload** all files from this folder into that repo (or just upload the ZIP below).
3. Go to **Settings → Actions → General** → set “Workflow permissions” to **Read and write**.
4. Go to **Settings → Secrets and variables → Actions → New repository secret** and add:
   - `GROQ_API_KEY` (optional for enrichment/ranking)
5. Commit & push. The workflow will run every **2 hours** automatically.

You can trigger manually via: **Actions → Scrape Jobs → Run workflow**.

---

## Optional: Google Sheets push

If you want results in a Google Sheet instead of CSV-only:

1. Create a Google Cloud Service Account with **“Editor”** on Sheets.
2. Share your target Google Sheet with the service account email.
3. Add these repo secrets:
   - `GOOGLE_SERVICE_ACCOUNT_JSON` → **the raw JSON** of the service account key
   - `GOOGLE_SHEET_ID` → the Sheet ID from the URL
   - `GOOGLE_SHEET_TAB` → tab name (default: `Jobs`)

The workflow detects these and pushes rows after each scrape.

---

## Tuning relevance

Edit `KEYWORDS_ANY` in `src/config.py` to match your current focus (e.g., `design`, `automation`, `fabrication`, `OSINT`, `investigator`, `remote`).

---

## Next (Phase 2): Auto-draft emails / drafts in Gmail

- Add a step to create **Gmail drafts** for any rows that include a contact email.
- We’ll store a long-lived OAuth refresh token as a GitHub secret and call Gmail API `users.drafts.create`.
- You approve/send on your phone; no local work needed.

(We can wire this once you’re happy with the feed quality.)

