#!/usr/bin/env python3
from __future__ import annotations

import os, sys, argparse, json
from datetime import datetime, timezone, timedelta
from pathlib import Path

# --- Find project root so we can import pipeline/*
def _find_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(8):
        if (cur / "pipeline").is_dir():
            return cur
        cur = cur.parent
    return start.resolve()

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = _find_root(SCRIPT_DIR)
sys.path.insert(0, str(ROOT))

# Load .env if present
from dotenv import load_dotenv
env_path = ROOT / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

from notion_client import Client
from pipeline.enrichment.vibe import enrich_vibe

# ---- Notion helpers ----
def _kv_text(content: str) -> dict:
    return {"rich_text": [{"type": "text", "text": {"content": content}}]} if content else {"rich_text": []}

def _kv_links(urls: list[str]) -> dict:
    if not urls:
        return {"rich_text": []}
    rts = [{"type": "text", "text": {"content": u, "link": {"url": u}}} for u in urls[:6]]
    return {"rich_text": rts}

def _kv_multi(names: list[str]) -> dict:
    return {"multi_select": [{"name": n} for n in names[:10]]} if names else {"multi_select": []}

def _today_range_utc() -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start.isoformat(), end.isoformat()

def _query_today(n: Client, db_id: str, limit: int):
    start_iso, end_iso = _today_range_utc()
    # If you have a dedicated Date property (e.g., "Collected"), filter on that instead.
    # Here we use created_time so it works out of the box.
    payload = {
        "database_id": db_id,
        "filter": {
            "timestamp": "created_time",
            "created_time": {"on_or_after": start_iso}
        },
        "page_size": min(50, limit),
    }
    resp = n.databases.query(**payload)
    results = resp.get("results", [])
    while resp.get("has_more") and len(results) < limit:
        payload["start_cursor"] = resp.get("next_cursor")
        payload["page_size"] = min(50, limit - len(results))
        resp = n.databases.query(**payload)
        results.extend(resp.get("results", []))
    return results[:limit]

def _pluck_company(props: dict) -> str:
    # Prefer "Company" (rich_text or title), else title
    v = props.get("Company", {})
    if v.get("type") == "rich_text":
        return "".join(p.get("plain_text","") for p in v.get("rich_text") or []).strip()
    if v.get("type") == "title":
        return "".join(p.get("plain_text","") for p in v.get("title") or []).strip()
    # fallback: first title property
    for vv in props.values():
        if vv.get("type") == "title":
            return "".join(p.get("plain_text","") for p in vv.get("title") or []).strip()
    return ""

def _pluck_apply_url(props: dict) -> str:
    # Try "Apply URL", "URL", any rich_text link
    for name in ("Apply URL", "URL"):
        v = props.get(name, {})
        if v.get("type") == "url":
            return (v.get("url") or "").strip()
        if v.get("type") == "rich_text":
            for p in v.get("rich_text") or []:
                t = p.get("text") or {}
                link = t.get("link") or {}
                if link.get("url"):
                    return link["url"]
    # scan title/rich_text for a link
    for v in props.values():
        if v.get("type") in ("title","rich_text"):
            parts = (v.get("rich_text") or []) + (v.get("title") or [])
            for p in parts:
                t = p.get("text") or {}
                link = t.get("link") or {}
                if link.get("url"):
                    return link["url"]
    return ""

def main():
    ap = argparse.ArgumentParser(description="Enrich 'today's jobs' with Vibe fields and update Notion in-place.")
    ap.add_argument("--limit", type=int, default=50, help="Max pages to process (default 50).")
    ap.add_argument("--dry-run", action="store_true", help="Preview; do not write to Notion.")
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--company", type=str, default="", help="Only process rows where Company contains this string.")
    args = ap.parse_args()

    token = os.getenv("NOTION_TOKEN")
    db_id = os.getenv("NOTION_JOBS_DB_ID", "").strip('"').strip()
    if not token:
        raise SystemExit("ERROR: NOTION_TOKEN missing (set in .env).")
    if not db_id:
        raise SystemExit("ERROR: NOTION_JOBS_DB_ID missing (set in .env).")

    n = Client(auth=token)
    pages = _query_today(n, db_id, args.limit * 2)  # overfetch a bit
    if args.verbose:
        print(f"[info] fetched {len(pages)} pages created today (limit request: {args.limit})")

    processed = 0
    updates = 0
    sample = None

    for p in pages:
        props = p.get("properties", {})
        company = _pluck_company(props)
        if args.company and args.company.lower() not in company.lower():
            continue
        apply_url = _pluck_apply_url(props)
        job = {"company": company, "apply_url": apply_url, "notion_page_id": p["id"]}

        vibe = enrich_vibe(job)
        processed += 1

        # Build partial update (only vibe fields)
        patch = {
            "properties": {
                "Mission": _kv_text(vibe.get("vibe_mission") or ""),
                "Vibe": _kv_multi(vibe.get("vibe_keywords") or []),
                "BrandLinks": _kv_links(vibe.get("vibe_links") or []),
                "TalkingPoints": _kv_text(", ".join(vibe.get("vibe_talking_points") or [])),
            }
        }

        if args.dry_run:
            sample = sample or {"company": company, **vibe}
            continue

        # Update Notion page
        try:
            n.pages.update(page_id=p["id"], **patch)
            updates += 1
            if args.verbose:
                print(f"[ok] updated: {company[:60]}…  ({p['id']})")
        except Exception as e:
            print(f"[err] update failed for {company[:60]}…: {e}")

        if updates >= args.limit:
            break

    if args.dry_run:
        if args.verbose:
            print(f"[dry-run] would update up to {min(args.limit, processed)} pages")
        print(json.dumps(sample or {"note": "no sample found"}, indent=2)[:2000])
    else:
        print(f"[ok] processed={processed}  updated={updates}")

if __name__ == "__main__":
    main()
