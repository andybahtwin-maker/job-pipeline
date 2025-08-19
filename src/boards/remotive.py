
import httpx
from datetime import datetime
from ..normalize import Job

API = "https://remotive.com/api/remote-jobs"

async def fetch_remotive(client: httpx.AsyncClient):
    jobs = []
    r = await client.get(API, timeout=30)
    r.raise_for_status()
    data = r.json()
    for item in data.get("jobs", []):
        jobs.append(Job(
            source="remotive",
            job_id=str(item.get("id")),
            title=item.get("title",""),
            company=item.get("company_name",""),
            location=item.get("candidate_required_location",""),
            url=item.get("url",""),
            tags=[t for t in item.get("tags",[]) if t],
            description=item.get("description","")[:4000],
            posted_at=datetime.fromisoformat(item.get("publication_date","").replace("Z","+00:00")) if item.get("publication_date") else None,
        ))
    return jobs
