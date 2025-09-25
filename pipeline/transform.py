from datetime import datetime, timezone
from typing import Dict, Any, List
from .schema import Job
import yaml, re
from dateutil import parser as dateparse

NOW = datetime.now(timezone.utc)

# Optional keyword rules for tagging (keywords.yml)
try:
    with open("keywords.yml","r",encoding="utf-8") as f:
        RULES = yaml.safe_load(f) or []
except Exception:
    RULES = []

def tag_keywords(text: str) -> List[str]:
    if not text: return []
    t = text.lower()
    tags = []
    for r in RULES:
        name = r.get("name"); terms = r.get("match") or []
        if any(re.search(r"\b"+re.escape(term.lower())+r"\b", t) for term in terms):
            tags.append(name)
    seen=set(); out=[]
    for k in tags:
        if k not in seen:
            seen.add(k); out.append(k)
    return out

def _parse_posted_at(value) -> datetime | None:
    if not value:
        return None
    # accept ISO strings, RFC, simple dates, or epoch seconds
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        if isinstance(value, str):
            return dateparse.parse(value).astimezone(timezone.utc)
    except Exception:
        return None
    return None

def normalize(raw: Dict[str, Any]) -> Dict[str, Any]:
    external_id = (
        raw.get("external_id") or raw.get("id") or raw.get("leverId")
        or raw.get("greenhouseId") or raw.get("url")
    )
    title = raw.get("title") or raw.get("position") or ""
    company = raw.get("company") or raw.get("organization") or ""
    url = raw.get("url") or raw.get("applyUrl") or raw.get("postingUrl")
    posted_at = raw.get("posted_at") or raw.get("createdAt") or raw.get("datePosted")
    location = raw.get("location") or raw.get("city") or raw.get("region")
    remote = raw.get("remote")
    salary_min = raw.get("salary_min") or raw.get("minSalary")
    salary_max = raw.get("salary_max") or raw.get("maxSalary")
    currency = raw.get("currency") or raw.get("compCurrency")

    if not external_id or not title or not company:
        return {}

    # Build a text blob for tagging
    desc = raw.get("description") or raw.get("body") or ""
    blob = " ".join([str(title), str(company), str(location or ""), str(desc or "")])

    job = Job(
        external_id=str(external_id),
        title=str(title).strip(),
        company=str(company).strip(),
        location=(str(location).strip() if location else None),
        remote=bool(remote) if remote is not None else None,
        url=url,
        posted_at=_parse_posted_at(posted_at),
        salary_min=float(salary_min) if salary_min not in (None, "") else None,
        salary_max=float(salary_max) if salary_max not in (None, "") else None,
        currency=currency,
        keywords=tag_keywords(blob),
        source=raw.get("source"),
        first_seen=NOW,   # harvest date
        last_seen=NOW,
    )
    return job.model_dump()
