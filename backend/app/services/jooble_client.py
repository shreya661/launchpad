import os
import requests

JOOBLE_API_KEY = os.getenv("JOOBLE_API_KEY", "")
JOOBLE_URL_TEMPLATE = "https://jooble.org/api/{key}"


def search_jobs(keywords: str, location: str = "India", results: int = 15) -> list[dict]:
    """Returns a list of {company, title, url, location, jd} dicts.
    Returns [] if no key is set or the request fails — get a free key at
    https://jooble.org/api/about and add it as JOOBLE_API_KEY in backend/.env."""
    if not JOOBLE_API_KEY:
        return []

    try:
        resp = requests.post(
            JOOBLE_URL_TEMPLATE.format(key=JOOBLE_API_KEY),
            json={"keywords": keywords, "location": location, "ResultOnPage": str(results)},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        jobs = []
        for r in data.get("jobs", [])[:results]:
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
