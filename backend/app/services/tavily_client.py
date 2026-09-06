import os
import requests

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_URL = "https://api.tavily.com/search"


def research_company(company: str) -> str:
    """Returns a short plain-text digest of search snippets about the company.
    Falls back to an empty string if no key is set or the request fails —
    tailoring still works without this, just without company context."""
    if not TAVILY_API_KEY:
        return ""

    try:
        resp = requests.post(
            TAVILY_URL,
            json={
                "api_key": TAVILY_API_KEY,
                "query": f"{company} company overview size funding recent news",
                "search_depth": "basic",
                "max_results": 5,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        snippets = []
        for r in data.get("results", [])[:5]:
            title = r.get("title", "")
            content = (r.get("content", "") or "")[:300]
            snippets.append(f"- {title}: {content}")
        return "\n".join(snippets)
    except Exception:
        return ""
