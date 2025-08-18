
import asyncio, os, csv, time
from datetime import datetime, timezone
import httpx
import pandas as pd

from .config import KEYWORDS_ANY, MIN_DESCRIPTION_LEN, GOOGLE_SHEET_ID, GOOGLE_SHEET_TAB, GOOGLE_SERVICE_ACCOUNT_JSON
from .boards.remotive import fetch_remotive
from .boards.remoteok import fetch_remoteok
from .normalize import Job

def is_relevant(job: Job) -> bool:
    text = f"{job.title} {job.company} {job.location} {' '.join(job.tags)} {job.description}".lower()
    if len(job.description or "") < MIN_DESCRIPTION_LEN:
        return False
    return any(k.lower() in text for k in KEYWORDS_ANY)

async def gather_all():
    async with httpx.AsyncClient() as client:
        remotive, remoteok = await asyncio.gather(
            fetch_remotive(client),
            fetch_remoteok(client),
        )
    jobs = remotive + remoteok
    # de-dup by URL or (source,id)
    seen = set()
    unique = []
    for j in jobs:
        key = j.url or f"{j.source}:{j.job_id}"
        if key in seen: continue
        seen.add(key); unique.append(j)
    return unique

def write_csv(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source","job_id","title","company","location","url","tags","description","posted_at"])
        for j in rows:
            w.writerow([
                j.source, j.job_id, j.title, j.company, j.location, j.url,
                "|".join(j.tags), (j.description or "").replace("\n"," ")[:1000],
                j.posted_at.isoformat() if j.posted_at else ""
            ])

def main():
    jobs = asyncio.run(gather_all())
    relevant = [j for j in jobs if is_relevant(j)]
    relevant.sort(key=lambda j: (j.posted_at or datetime(1970,1,1, tzinfo=timezone.utc)), reverse=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    latest = "output/latest.csv"
    snapshot = f"output/jobs_{ts}.csv"

    write_csv(relevant, latest)
    write_csv(relevant, snapshot)

    # Optional: push to Google Sheets if configured
    if GOOGLE_SHEET_ID and GOOGLE_SERVICE_ACCOUNT_JSON:
        from .sheets import push_to_sheet
        push_to_sheet(GOOGLE_SHEET_ID, GOOGLE_SHEET_TAB, relevant, GOOGLE_SERVICE_ACCOUNT_JSON)

    print(f"Wrote {len(relevant)} jobs to {latest}")

if __name__ == "__main__":
    main()
