"""The Muse — tech company job board API.

Focused on company culture + tech roles. Works with or without an API key
(500 req/hour without key, 3600 req/hour with key).
Get a free key at: https://www.themuse.com/developers/api/v2

API: GET https://www.themuse.com/api/public/jobs
"""

import os
import re
import requests

THE_MUSE_API_KEY = os.getenv("THE_MUSE_API_KEY", "")
MUSE_URL = "https://www.themuse.com/api/public/jobs"

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(html: str) -> str:
    return _TAG_RE.sub(" ", html or "").replace("&nbsp;", " ").strip()


def is_enabled() -> bool:
    """Always enabled — works without an API key (lower rate limit)."""
    return True


def search_jobs(keywords: str, results: int = 15) -> list[dict]:
    """Returns tech job listings from The Muse, filtered by keyword."""
    try:
        params = {
            "page": 0,
            "descending": "true",
            "category": "Engineering",  # focus on engineering roles
        }
        if THE_MUSE_API_KEY:
            params["api_key"] = THE_MUSE_API_KEY

        resp = requests.get(MUSE_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        kw_lower = keywords.lower() if keywords else ""
        jobs = []
        for item in (data.get("results") or []):
            title = item.get("name", "")
            company = (item.get("company") or {}).get("name", "Unknown")
            # Filter by keyword in title or company name
            if kw_lower and kw_lower not in title.lower() and kw_lower not in company.lower():
                continue

            # Extract apply URL
            refs = item.get("refs") or {}
            url = refs.get("landing_page", "")

            # Extract location
            locs = item.get("locations") or []
            location = locs[0].get("name", "") if locs else "Unknown"

            # JD from HTML content
            jd = _strip_html(item.get("contents", ""))

            jobs.append({
                "company": company,
                "title": title,
                "url": url,
                "location": location,
                "jd": jd[:3000],
            })
            if len(jobs) >= results:
                break

        return jobs
    except Exception:
        return []
