"""SerpAPI — Google Jobs search (India-focused + international remote).

Uses SerpAPI's Google Jobs engine to surface listings from Naukri,
LinkedIn India, Instahyre, Cutshort, Wellfound, and direct company sites
through Google's job index. This is the best single source for Indian
tech job market coverage.

Free tier: 100 searches/month.
Get a key at: https://serpapi.com/

API: GET https://serpapi.com/search?engine=google_jobs
"""

import os
import requests

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
SERPAPI_URL = "https://serpapi.com/search"


def is_enabled() -> bool:
    return bool(SERPAPI_KEY)


def search_jobs(keywords: str, results: int = 15) -> list[dict]:
    """Searches Google Jobs India via SerpAPI and returns structured listings.
    Covers Naukri, LinkedIn, Instahyre, Cutshort, Wellfound, and company career pages."""
    if not SERPAPI_KEY:
        return []
    try:
        # Build query: keywords targeted at India + optionally remote
        query = f"{keywords} India OR remote"

        resp = requests.get(
            SERPAPI_URL,
            params={
                "engine": "google_jobs",
                "q": query,
                "api_key": SERPAPI_KEY,
                "gl": "in",       # Country: India
                "hl": "en",       # Language: English
                "chips": "date_posted:week",  # Recent postings only
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        jobs = []
        for item in (data.get("jobs_results") or [])[:results]:
            # Best available apply URL
            apply_options = item.get("apply_options") or []
            url = apply_options[0].get("link", "") if apply_options else item.get("share_link", "")

            # Build JD from highlights + description
            highlights = item.get("job_highlights") or []
            jd_parts = [item.get("description", "")]
            for h in highlights:
                title_h = h.get("title", "")
                items_h = h.get("items") or []
                jd_parts.append(f"{title_h}: {' '.join(items_h)}")
            jd = " ".join(jd_parts).strip()

            jobs.append({
                "company": item.get("company_name", "Unknown"),
                "title": item.get("title", ""),
                "url": url,
                "location": item.get("location", "India"),
                "jd": jd[:3000],
            })
        return jobs
    except Exception:
        return []
