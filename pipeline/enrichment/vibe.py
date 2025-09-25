#!/usr/bin/env python3
from __future__ import annotations

import re
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import tldextract
from collections import Counter
from readability import Document

STOPWORDS = set("""
a an and are as at be by for from has have i in is it its of on or our that the their them there they this to was we with you your
solutions platform products services team global customer customers enterprise trusted leading innovation innovative enable empowering empower secure
""".split())

CANDIDATE_PATHS = ["", "about", "company", "careers", "values", "mission", "brand", "press", "blog", "design", "design-system"]

DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
}

def _client(timeout=12.0) -> httpx.Client:
    return httpx.Client(follow_redirects=True, timeout=timeout, headers=DEFAULT_HEADERS)

def _domain(url: str) -> str:
    p = tldextract.extract(url)
    return f"{p.domain}.{p.suffix}" if p.suffix else p.domain

def _is_same_domain(a: str, b: str) -> bool:
    try:
        return _domain(a) == _domain(b)
    except Exception:
        return False

def _textify(html: str) -> str:
    try:
        doc = Document(html)
        html = doc.summary()
    except Exception:
        pass
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text(" ", strip=True)

def _extract_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    out = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
            continue
        absu = urljoin(base_url, href)
        out.append(absu)
    return out

def _pick_company_root_from_ats(apply_url: str, html: str) -> str | None:
    # Heuristic: external links not on the ATS domain are likely the company site.
    ats_dom = _domain(apply_url)
    candidates = []
    for link in _extract_links(html, apply_url):
        if not link.startswith("http"):
            continue
        dom = _domain(link)
        if dom and dom != ats_dom:
            candidates.append(dom)
    if not candidates:
        return None
    target_dom, _ = Counter(candidates).most_common(1)[0]
    scheme = urlparse(apply_url).scheme or "https"
    return f"{scheme}://{target_dom}"

def _keywords_from_text(text: str, k: int = 8) -> list[str]:
    words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z\-\+]{2,}", text)]
    words = [w for w in words if w not in STOPWORDS and not w.isdigit() and len(w) <= 24]
    counts = Counter(words)
    return [w for (w, _) in counts.most_common(k)]

MISSION_PATTERNS = [
    r"\bour mission is\b.+?[\.\!\?]",
    r"\bmission\b.+?[\.\!\?]",
    r"\bour purpose\b.+?[\.\!\?]",
    r"\bwe (?:exist|aim|strive|work) to\b.+?[\.\!\?]",
    r"\bwhat we (?:do|believe)\b.+?[\.\!\?]"
]

def _extract_mission(text: str) -> str | None:
    for pat in MISSION_PATTERNS:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            s = m.group(0)
            return re.sub(r"\s+", " ", s).strip()
    # fallback: first concise sentence mentioning customers/users
    m = re.search(r".{20,180}?(customers?|users?|developers?)\. ", text, flags=re.IGNORECASE)
    if m:
        return re.sub(r"\s+", " ", m.group(0)).strip()
    return None

def _brandish_links(root: str, htmls: dict[str, str]) -> list[str]:
    keep = []
    seen = set()
    for path, html in htmls.items():
        for link in _extract_links(html, urljoin(root, path)):
            if _is_same_domain(link, root):
                lower = link.lower()
                if any(x in lower for x in ["/brand", "/press", "/media", "/blog", "/news", "/design", "design-system", "/careers", "/values", "/mission"]):
                    if link not in seen:
                        seen.add(link)
                        keep.append(link)
    # Dedup to 6 max
    return keep[:6]

def enrich_vibe(job: dict) -> dict:
    """
    Returns a dict with:
      - vibe_mission: str | None
      - vibe_keywords: list[str]
      - vibe_links: list[str]
      - vibe_talking_points: list[str]
    Uses job['apply_url'] when available; optionally job['company_url'] if present.
    """
    apply_url = job.get("apply_url") or job.get("url") or ""
    company_hint = job.get("company_url") or ""

    vibe = {"vibe_mission": None, "vibe_keywords": [], "vibe_links": [], "vibe_talking_points": []}
    if not (apply_url or company_hint):
        return vibe

    with _client() as client:
        root = None
        htmls = {}

        # Step 1: if we have a direct company hint, use it as root
        if company_hint:
            root = company_hint.rstrip("/")
        else:
            # Fetch the ATS page and try to discover the company root site
            try:
                r = client.get(apply_url)
                if r.status_code < 400 and (r.headers.get("content-type","").startswith("text/")):
                    html = r.text
                    root = _pick_company_root_from_ats(apply_url, html)
            except Exception:
                root = None

        if not root:
            return vibe

        # Step 2: fetch candidate pages
        for p in CANDIDATE_PATHS:
            url = root if p == "" else urljoin(root + "/", p)
            try:
                res = client.get(url)
                if res.status_code < 400 and ("text/html" in res.headers.get("content-type", "")):
                    htmls[p] = res.text
            except Exception:
                continue

        if not htmls:
            return vibe

        # Step 3: extract mission + keywords
        joined_text = " ".join(_textify(h) for h in htmls.values())
        mission = _extract_mission(joined_text)
        keywords = _keywords_from_text(joined_text, k=8)
        links = _brandish_links(root, htmls)

        # Talking points – keep it short and usable
        tps = []
        if mission:
            tps.append("Mission fit: " + mission[:120].rstrip())
        if keywords:
            tps.append("Themes: " + ", ".join(keywords[:6]))
        if any("careers" in l.lower() for l in links):
            tps.append("Recent roles & teams on Careers page")
        if any("blog" in l.lower() or "news" in l.lower() for l in links):
            tps.append("Pull a recent blog/news win")

        vibe["vibe_mission"] = mission
        vibe["vibe_keywords"] = keywords
        vibe["vibe_links"] = links
        vibe["vibe_talking_points"] = tps[:4]
        return vibe
