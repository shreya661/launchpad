"""RemoteOK — free, keyless remote developer jobs API.

Popular remote-first job board heavily used by startups and tech companies
hiring engineers worldwide, including India. No key required.

API: GET https://remoteok.com/api?tags=dev
Docs: https://remoteok.com/api
"""

import requests

REMOTEOK_URL = "https://remoteok.com/api"


def is_enabled() -> bool:
    """Always on — no key required."""
    return True


def search_jobs(keywords: str, results: int = 15) -> list[dict]:
    """Returns remote developer jobs from RemoteOK, filtered by keyword."""
    try:
        params = {"tags": "dev"}
        resp = requests.get(
            REMOTEOK_URL,
            params=params,
            headers={"User-Agent": "Launchpad Job Search Bot/1.0"},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()

        # RemoteOK prepends a legal notice dict as the first item — skip it
        items = [item for item in data if isinstance(item, dict) and item.get("id")]

        kw_lower = keywords.lower() if keywords else ""
        matched = []
        for item in items:
            title = item.get("position", "")
            description = item.get("description", "")
            tags = " ".join(item.get("tags") or [])
            if kw_lower and not (
                kw_lower in title.lower()
                or kw_lower in description.lower()
                or kw_lower in tags.lower()
            ):
                continue
            matched.append({
                "company": item.get("company", "Unknown"),
                "title": title,
                "url": item.get("url", "") or f"https://remoteok.com/l/{item.get('id', '')}",
                "location": "Remote",
                "jd": (description or "")[:3000],
            })
            if len(matched) >= results:
                break

        # Fall back to unfiltered if keyword was too strict
        if not matched and items:
            for item in items[:results]:
                matched.append({
                    "company": item.get("company", "Unknown"),
                    "title": item.get("position", ""),
                    "url": item.get("url", "") or f"https://remoteok.com/l/{item.get('id', '')}",
                    "location": "Remote",
                    "jd": (item.get("description", "") or "")[:3000],
                })
        return matched
    except Exception:
        return []
