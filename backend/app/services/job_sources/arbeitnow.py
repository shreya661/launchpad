"""Arbeitnow job source — free public API, no key required.

Provides remote-friendly tech, engineering, and dev jobs.
API docs: https://www.arbeitnow.com/api
"""

import requests

ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"


def is_enabled() -> bool:
    """Always on — no key needed."""
    return True


def search_jobs(keywords: str, results: int = 15) -> list[dict]:
    """Returns a list of {company, title, url, location, jd} dicts.
    Filters by keyword match in title or description since the API
    returns a feed rather than a search endpoint."""
    try:
        resp = requests.get(ARBEITNOW_URL, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("data", [])

        kw_lower = keywords.lower() if keywords else ""
        matched = []
        for item in data:
            title = item.get("title", "")
            description = item.get("description", "")
            if kw_lower and not (
                kw_lower in title.lower() or kw_lower in description.lower()
            ):
                continue
            matched.append({
                "company": item.get("company_name", ""),
                "title": title,
                "url": item.get("url", ""),
                "location": item.get("location", "Remote"),
                "jd": description,
            })
            if len(matched) >= results:
                break

        # If keyword filter was too strict, return first N unfiltered
        if not matched and data:
            for item in data[:results]:
                matched.append({
                    "company": item.get("company_name", ""),
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "location": item.get("location", "Remote"),
                    "jd": item.get("description", ""),
                })
        return matched
    except Exception:
        return []
