import os
import requests

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
JSEARCH_URL = "https://jsearch.p.rapidapi.com/search"
JSEARCH_HOST = "jsearch.p.rapidapi.com"
# JSearch aggregates Google for Jobs results, which pulls in postings originally
# listed on LinkedIn, Indeed, Naukri, and many company sites — licensed aggregation,
# not scraping those sites directly. Free tier is small; paid tiers scale up.
# Get a key at rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch


def is_enabled() -> bool:
    return bool(RAPIDAPI_KEY)


def search_jobs(keywords: str, results: int = 15) -> list[dict]:
    """Returns a list of {company, title, url, location, jd} dicts.
    Returns [] if no key is set or the request fails."""
    if not RAPIDAPI_KEY:
        return []
    try:
        resp = requests.get(
            JSEARCH_URL,
            headers={
                "X-RapidAPI-Key": RAPIDAPI_KEY,
                "X-RapidAPI-Host": JSEARCH_HOST,
            },
            params={
                "query": f"{keywords} in India",
                "page": "1",
                "num_pages": "1",
                "date_posted": "month",
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        jobs = []
        for r in (data.get("data") or [])[:results]:
            jobs.append({
                "company": r.get("employer_name") or "Unknown",
                "title": r.get("job_title", ""),
                "url": r.get("job_apply_link") or r.get("job_google_link", ""),
                "location": r.get("job_city") or r.get("job_country", ""),
                "jd": r.get("job_description", ""),
            })
        return jobs
    except Exception:
        return []
