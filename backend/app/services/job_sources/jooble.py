import os
import requests

JOOBLE_API_KEY = os.getenv("JOOBLE_API_KEY", "")
JOOBLE_URL_TEMPLATE = "https://jooble.org/api/{key}"
# Jooble aggregates postings from many boards (including some sourced from
# LinkedIn/Indeed via their own licensed feeds) — free API key, see jooble.org/api/about


def is_enabled() -> bool:
    return bool(JOOBLE_API_KEY)


def search_jobs(keywords: str, results: int = 15) -> list[dict]:
    """Returns a list of {company, title, url, location, jd} dicts.
    Returns [] if no key is set or the request fails."""
    if not JOOBLE_API_KEY:
        return []
    try:
        resp = requests.post(
            JOOBLE_URL_TEMPLATE.format(key=JOOBLE_API_KEY),
            json={"keywords": keywords, "location": "India"},
            headers={"Content-Type": "application/json"},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        jobs = []
        for r in (data.get("jobs") or [])[:results]:
            jobs.append({
                "company": r.get("company") or "Unknown",
                "title": r.get("title", ""),
                "url": r.get("link", ""),
                "location": r.get("location", ""),
                "jd": r.get("snippet", ""),
            })
        return jobs
    except Exception:
        return []
