import os
import requests

ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")
ADZUNA_URL = "https://api.adzuna.com/v1/api/jobs/in/search/1"
# ^ "in" = India. Adzuna's free tier covers a limited set of countries — check
# https://developer.adzuna.com/docs/search for the current list if you're outside India.


def is_enabled() -> bool:
    return bool(ADZUNA_APP_ID and ADZUNA_APP_KEY)


def search_jobs(keywords: str, results: int = 15) -> list[dict]:
    """Returns a list of {company, title, url, location, jd} dicts.
    Returns [] if no key is set or the request fails."""
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        return []

    try:
        resp = requests.get(
            ADZUNA_URL,
            params={
                "app_id": ADZUNA_APP_ID,
                "app_key": ADZUNA_APP_KEY,
                "results_per_page": results,
                "what": keywords,
                "max_days_old": 21,
                "sort_by": "date",
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        jobs = []
        for r in data.get("results", []):
            jobs.append({
                "company": (r.get("company") or {}).get("display_name", "Unknown"),
                "title": r.get("title", ""),
                "url": r.get("redirect_url", ""),
                "location": (r.get("location") or {}).get("display_name", ""),
                "jd": r.get("description", ""),
            })
        return jobs
    except Exception:
        return []
