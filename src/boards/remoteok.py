
import httpx
from datetime import datetime
from .normalize import Job

API = "https://remoteok.com/api"  # public JSON feed

async def fetch_remoteok(client: httpx.AsyncClient):
    jobs = []
    r = await client.get(API, headers={"User-Agent":"Mozilla/5.0"}, timeout=30)
    r.raise_for_status()
    data = r.json()
    # first element is usually metadata; skip non-job entries
    for item in data:
        if not isinstance(item, dict): continue
        if "id" not in item or "position" not in item: continue
        url = item.get("url") or (f"https://remoteok.com/l/{item.get('id')}" if item.get("id") else "")
        posted = item.get("date") or item.get("epoch")
        try:
            posted_at = datetime.fromisoformat(posted.replace("Z","+00:00")) if isinstance(posted,str) else None
        except Exception:
            posted_at = None
        jobs.append(Job(
            source="remoteok",
            job_id=str(item.get("id")),
            title=item.get("position","") or item.get("title",""),
            company=item.get("company",""),
            location=item.get("location","") or "",
            url=url,
            tags=[t for t in (item.get("tags") or []) if t],
            description=(item.get("description","") or "")[:4000],
            posted_at=posted_at,
        ))
    return jobs
