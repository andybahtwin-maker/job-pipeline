#!/usr/bin/env python3
from __future__ import annotations

import sys, json, glob
from pathlib import Path

# --- Find project root (walk up until we see ./pipeline)
def _find_project_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(8):
        if (cur / "pipeline").is_dir():
            return cur
        cur = cur.parent
    return start.resolve()

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = _find_project_root(SCRIPT_DIR)
sys.path.insert(0, str(ROOT))

# --- Now safe to import project modules
from pipeline.enrichment.vibe import enrich_vibe
import pipeline.notion_sync as notion_sync

# --- Resolve a usable push function regardless of its name
def _resolve_push(ns):
    for name in (
        "push_jobs_to_notion",
        "sync_jobs_to_notion",
        "upsert_jobs_to_notion",
        "create_or_update_jobs",
        "write_jobs_to_notion",
        "push",
    ):
        fn = getattr(ns, name, None)
        if callable(fn):
            return fn
    raise ImportError(
        "No Notion push function found. Define one of: "
        "push_jobs_to_notion / sync_jobs_to_notion / upsert_jobs_to_notion / "
        "create_or_update_jobs / write_jobs_to_notion / push"
    )

def iter_jobs():
    for path in glob.glob(str(ROOT / "data/*.jsonl")):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    yield json.loads(line)
                except Exception:
                    continue

def main():
    push = _resolve_push(notion_sync)
    jobs = []
    for job in iter_jobs():
        try:
            job.update(enrich_vibe(job))
        except Exception as e:
            job.setdefault("enrichment_errors", []).append(f"vibe:{e.__class__.__name__}")
        jobs.append(job)
    if jobs:
        push(jobs)

if __name__ == "__main__":
    main()
