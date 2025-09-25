from __future__ import annotations
import re
import yaml
from pathlib import Path
from typing import Dict, Any

VIBES_PATH = Path("data/enrichment/company_vibes.yaml")

def _norm_company(name: str) -> str:
    return re.sub(r"\s+", " ", name or "").strip().lower()

def load_vibes(path: Path = VIBES_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    # Build a lowercase lookup for case-insensitive matching
    return {k.lower(): v for k, v in data.items()}

def enrich_job_with_vibe(job: Dict[str, Any], vibes_idx: Dict[str, Any]) -> Dict[str, Any]:
    company = _norm_company(job.get("company", ""))
    if not company:
        return job
    # Try exact, then fuzzy by removing Inc./Ltd./Corp etc.
    hit = vibes_idx.get(company)
    if not hit:
        company2 = re.sub(r"\b(inc\.?|corp\.?|ltd\.?|llc)\b", "", company).strip()
        hit = vibes_idx.get(company2)
    if hit:
        job["vibe_mission"] = hit.get("mission")
        job["vibe_keywords"] = hit.get("vibe", [])
        job["vibe_talking_points"] = hit.get("talking_points", [])
        job["vibe_links"] = hit.get("links", [])
    return job
