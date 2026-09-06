import re
import requests

REMOTIVE_URL = "https://remotive.com/api/remote-jobs"

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(html: str) -> str:
    return _TAG_RE.sub(" ", html or "").replace("&nbsp;", " ").strip()


def is_enabled() -> bool:
    return True  # free, keyless public API — always on


def search_jobs(keywords: str, results: int = 15) -> list[dict]:
    """Returns a list of {company, title, url, location, jd} dicts.
    Remotive's public API needs no key; returns [] on any failure so a
    down/rate-limited source never breaks discovery."""
    try:
        resp = requests.get(
            REMOTIVE_URL,
            params={"search": keywords, "limit": results},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        jobs = []
        for r in data.get("jobs", [])[:results]:
            jobs.append({
                "company": r.get("company_name", "Unknown"),
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "location": r.get("candidate_required_location", "Remote"),
                "jd": _strip_html(r.get("description", "")),
            })
        return jobs
    except Exception:
        return []
