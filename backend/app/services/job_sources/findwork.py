"""Findwork.dev — developer-focused job board API.

Focuses on software engineering, DevOps, ML, and product roles.
Requires a free API key (50 requests/day on free tier).
Get your key at: https://findwork.dev/developers/

API: GET https://findwork.dev/api/jobs/
Auth: Authorization: Token <FINDWORK_API_KEY>
"""

import os
import requests

FINDWORK_API_KEY = os.getenv("FINDWORK_API_KEY", "")
FINDWORK_URL = "https://findwork.dev/api/jobs/"


def is_enabled() -> bool:
    return bool(FINDWORK_API_KEY)


def search_jobs(keywords: str, results: int = 15) -> list[dict]:
    """Returns developer-focused jobs from Findwork, filtered by keyword."""
    if not FINDWORK_API_KEY:
        return []
    try:
        params = {
            "limit": results,
            "sort_by": "relevance",
        }
        if keywords:
            params["search"] = keywords

        resp = requests.get(
            FINDWORK_URL,
            headers={"Authorization": f"Token {FINDWORK_API_KEY}"},
            params=params,
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()

        jobs = []
        for item in (data.get("results") or [])[:results]:
            # Build JD from available text fields
            jd_parts = []
            if item.get("text"):
                jd_parts.append(item["text"])
            if item.get("role"):
                jd_parts.append(f"Role: {item['role']}")
            if item.get("keywords"):
                jd_parts.append(f"Skills: {', '.join(item['keywords'])}")

            jobs.append({
                "company": item.get("company_name", "Unknown"),
                "title": item.get("role", ""),
                "url": item.get("url", ""),
                "location": item.get("location", "Remote"),
                "jd": " ".join(jd_parts)[:3000],
            })
        return jobs
    except Exception:
        return []
