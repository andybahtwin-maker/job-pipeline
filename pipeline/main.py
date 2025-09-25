from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict
import os

from .config import load
from .io_utils import read_ndjson, write_ndjson, archive_path_for
from .transform import normalize
from .dedupe import merge
from .stats import compute_dashboard, render_dashboard_md
from .notion_sync import upsert_jobs, update_portfolio_blocks
from notion_client import Client

def run():
    cfg = load()

    # 1) Read incoming (one JSON per line)
    incoming = Path("sources/incoming.ndjson")
    raw_rows: List[Dict] = read_ndjson(incoming)

    # 2) Normalize
    normalized = [normalize(r) for r in raw_rows]
    normalized = [r for r in normalized if r]

    # 3) Archive (idempotent per-day)
    today_path = archive_path_for(datetime.now(timezone.utc))
    existing = read_ndjson(today_path)
    merged = merge(existing, normalized)
    write_ndjson(today_path, merged)

    # 4) Stats across ALL history
    all_rows: List[Dict] = []
    for p in Path("data").rglob("jobs.ndjson"):
        all_rows.extend(read_ndjson(p))
    stats = compute_dashboard(all_rows)

    links = {
        "today": os.environ.get("NOTION_TODAY_LINK",""),
        "all": os.environ.get("NOTION_DB_LINK",""),
    }
    markdown = render_dashboard_md(stats, links)

    # 5) Notion: upsert DB + infographic blocks
    notion = Client(auth=cfg.notion_token)
    upsert_jobs(notion, cfg.notion_db_id, merged)

    # "today's list" = items harvested today; each line shows the listing's Posted date
    today_iso = datetime.now(timezone.utc).date().isoformat()
    todays_jobs = [r for r in merged if str(r.get("first_seen",""))[:10] == today_iso]

    update_portfolio_blocks(notion, cfg.notion_portfolio_page_id, markdown, todays_jobs)

    print("[ok] Pipeline finished.")

if __name__ == "__main__":
    run()
