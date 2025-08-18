
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class Job(BaseModel):
    source: str
    job_id: str = Field(..., description="Source-specific unique id")
    title: str
    company: str
    location: str = ""
    url: str
    tags: List[str] = []
    description: str = ""
    posted_at: Optional[datetime] = None
