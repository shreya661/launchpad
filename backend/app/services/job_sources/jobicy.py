"""Jobicy — free, keyless remote jobs API.

Focuses on remote engineering, developer, DevOps roles from
US/EU companies that hire internationally (including India).

API: GET https://jobicy.com/api/v2/remote-jobs
Docs: https://jobicy.com/api
"""

import requests

JOBICY_URL = "https://jobicy.com/api/v2/remote-jobs"


def is_enabled() -> bool:
    """Always on — no key required."""
    return True


def search_jobs(keywords: str, results: int = 15) -> list[dict]:
    """Returns remote engineering jobs from Jobicy, filtered by keyword."""
    try:
        params = {
            "count": min(results * 3, 50),  # over-fetch and filter
            "industry": "engineering",       # focus on tech/engineering roles
        }
        if keywords:
            params["tag"] = keywords[:50]   # API limit: 3-50 chars

        resp = requests.get(JOBICY_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        jobs = []
        for item in (data.get("jobs") or [])[:results]:
            jd = item.get("jobDescription", "") or item.get("jobExcerpt", "")
            jobs.append({
                "company": item.get("companyName", "Unknown"),
                "title": item.get("jobTitle", ""),
                "url": item.get("url", ""),
                "location": item.get("jobGeo", "Remote"),
                "jd": jd[:3000],
            })
        return jobs
    except Exception:
        return []
