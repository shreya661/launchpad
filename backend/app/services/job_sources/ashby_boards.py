"""Ashby ATS — direct board crawl.

Ashby is a modern ATS adopted by many funded startups (Notion-era companies,
AI startups, Series A/B/C tech companies). It exposes a public GraphQL endpoint
for job listings — no auth required.

Jobs are posted here first, before they reach LinkedIn or job boards.

GraphQL endpoint: https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams
"""

import requests

# Curated list of companies using Ashby ATS.
# Format: (ashby_slug, display_name)
ASHBY_COMPANIES = [
    # AI / ML companies
    ("openai", "OpenAI"),
    ("anthropic", "Anthropic"),
    ("cohere", "Cohere"),
    ("mistral", "Mistral AI"),
    ("perplexity", "Perplexity AI"),
    ("qdrant", "Qdrant"),
    ("weaviate", "Weaviate"),
    ("chroma", "Chroma"),
    ("replicate", "Replicate"),
    ("together", "Together AI"),
    ("anyscale", "Anyscale"),
    ("modal", "Modal"),
    ("weights-biases", "Weights & Biases"),
    ("runway", "Runway"),
    ("elevenlabs", "ElevenLabs"),
    ("pika", "Pika"),
    # Product / Dev tools
    ("linear", "Linear"),
    ("raycast", "Raycast"),
    ("craft", "Craft"),
    ("codeium", "Codeium"),
    ("cursor", "Cursor"),
    ("sourcegraph", "Sourcegraph"),
    ("gitpod", "Gitpod"),
    ("railway", "Railway"),
    ("render", "Render"),
    ("fly", "Fly.io"),
    ("turso", "Turso"),
    ("neon", "Neon"),
    ("xata", "Xata"),
    ("convex", "Convex"),
    # Fintech / Infra
    ("mercury", "Mercury"),
    ("ramp", "Ramp"),
    ("arc", "Arc"),
    ("brex", "Brex"),
    ("deel", "Deel"),
    ("remote", "Remote"),
    ("rippling", "Rippling"),
    ("gusto", "Gusto"),
]

ASHBY_GRAPHQL_URL = "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams"

ASHBY_QUERY = """
query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) {
  jobBoard: jobBoardWithTeams(
    organizationHostedJobsPageName: $organizationHostedJobsPageName
  ) {
    teams {
      id
      name
      parentTeamId
    }
    jobPostings {
      id
      title
      teamId
      locationId
      locationName
      employmentType
      descriptionSocial
      descriptionParts {
        descriptionHtml
      }
      externalLink
      applyLink
    }
  }
}
"""


def is_enabled() -> bool:
    """Always on — Ashby's board API is fully public."""
    return True


def _fetch_company_jobs(slug: str, company_name: str, results: int) -> list[dict]:
    """Fetches live job postings for a single Ashby company slug."""
    try:
        resp = requests.post(
            ASHBY_GRAPHQL_URL,
            json={
                "operationName": "ApiJobBoardWithTeams",
                "query": ASHBY_QUERY,
                "variables": {"organizationHostedJobsPageName": slug},
            },
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        if resp.status_code in (404, 400):
            return []
        resp.raise_for_status()
        data = resp.json()
        board = (data.get("data") or {}).get("jobBoard") or {}
        postings = board.get("jobPostings") or []

        import re

        jobs = []
        for item in postings[:results]:
            # Extract JD from descriptionParts HTML
            jd_html = ""
            for part in (item.get("descriptionParts") or []):
                jd_html += part.get("descriptionHtml", "")
            jd = re.sub(r"<[^>]+>", " ", jd_html).strip() or item.get("descriptionSocial", "")

            url = item.get("applyLink") or item.get("externalLink") or \
                  f"https://jobs.ashbyhq.com/{slug}/{item.get('id', '')}"

            jobs.append({
                "company": company_name,
                "title": item.get("title", ""),
                "url": url,
                "location": item.get("locationName", "Remote"),
                "jd": jd[:3000],
            })
        return jobs
    except Exception:
        return []


def search_jobs(keywords: str, results: int = 15) -> list[dict]:
    """Fetches jobs from curated Ashby companies and filters by keyword."""
    kw_lower = keywords.lower() if keywords else ""
    all_jobs = []
    per_company = max(3, results // 5)

    for slug, company_name in ASHBY_COMPANIES:
        if len(all_jobs) >= results * 4:
            break
        company_jobs = _fetch_company_jobs(slug, company_name, per_company)
        all_jobs.extend(company_jobs)

    if kw_lower:
        filtered = [
            j for j in all_jobs
            if kw_lower in j["title"].lower() or kw_lower in j["jd"].lower()
        ]
        return (filtered or all_jobs)[:results]
    return all_jobs[:results]
