from typing import List, Dict
from collections import Counter
from statistics import mean
from datetime import datetime, timezone, timedelta

def compute_dashboard(rows: List[Dict]) -> Dict:
    now = datetime.now(timezone.utc)
    today = now.date()
    last7 = now - timedelta(days=7)

    total = len(rows)
    # first_seen is stored as ISO string by our I/O helpers; handle both str/datetime
    def iso_date(v):
        if not v: return ""
        if isinstance(v, str): return v[:10]
        try: return v.date().isoformat()
        except Exception: return ""
    today_count = sum(1 for r in rows if iso_date(r.get("first_seen")) == str(today))
    last7_rows = [r for r in rows if iso_date(r.get("first_seen")) >= str(last7.date())]

    companies = Counter([r.get("company") for r in last7_rows if r.get("company")]).most_common(5)
    titles = Counter([r.get("title") for r in last7_rows if r.get("title")]).most_common(5)
    keywords = Counter([kw for r in last7_rows for kw in (r.get("keywords") or [])]).most_common(10)

    remotes = sum(1 for r in rows if r.get("remote") is True)
    onsite  = sum(1 for r in rows if r.get("remote") is False)

    pays = []
    for r in rows:
        lo = r.get("salary_min"); hi = r.get("salary_max")
        if lo and hi: pays.append((float(lo)+float(hi))/2.0)
        elif lo: pays.append(float(lo))
        elif hi: pays.append(float(hi))
    avg_pay = round(mean(pays), 2) if pays else None

    return {
        "total_roles": total,
        "today_count": today_count,
        "remote_count": remotes,
        "onsite_count": onsite,
        "top_companies": companies,
        "top_titles": titles,
        "top_keywords": keywords,
        "avg_salary": avg_pay,
        "today_date": str(today),
    }

def _pairs_to_text(pairs):
    if not pairs: return "—"
    return ", ".join([f"{k} ({v})" for k, v in pairs])

def render_dashboard_md(stats: Dict, links: Dict[str,str]) -> str:
    lines = []
    lines.append("## 📊 Jobs Dashboard (auto-updated)")
    lines.append("")
    lines.append(f"- **Today’s jobs ({stats['today_date']}):** {stats['today_count']}")
    lines.append(f"- **All-time collected:** {stats['total_roles']}")
    lines.append(f"- **Remote vs On-site:** {stats['remote_count']} remote / {stats['onsite_count']} on-site")
    if stats['avg_salary'] is not None:
        lines.append(f"- **Avg salary midpoint:** {stats['avg_salary']}")
    lines.append("")
    lines.append(f"**Top companies (last 7d):** {_pairs_to_text(stats['top_companies'])}")
    lines.append(f"**Top titles (last 7d):** {_pairs_to_text(stats['top_titles'])}")
    lines.append(f"**Top keywords (last 7d):** {_pairs_to_text(stats['top_keywords'])}")
    lines.append("")
    lines.append(f"🔗 [Today’s jobs]({links.get('today','')})")
    lines.append(f"🔗 [Full database]({links.get('all','')})")
    return "\\n".join(lines)
