"""Greenhouse ATS — direct board crawl.

Greenhouse is an enterprise ATS used by hundreds of tech companies worldwide
(Google, Stripe, Airbnb, Razorpay, CRED, etc.). Every company hosted on Greenhouse
exposes a fully public JSON jobs API — no key, no auth, no scraping.

This adapter queries a curated list of tech company board tokens and returns
their live postings. Jobs appear here the moment the company creates them —
typically 1-3 days BEFORE aggregators like Naukri/Indeed pick them up.

API docs: https://developers.greenhouse.io/job-board.html
Endpoint: GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
"""

import requests

# Curated list of tech companies on Greenhouse.
# India-founded / India-hiring companies + global remote-friendly companies.
# Format: (board_token, display_company_name)
GREENHOUSE_COMPANIES = [
    # Indian tech companies / MNCs hiring in India
    ("razorpay", "Razorpay"),
    ("cred", "CRED"),
    ("meesho", "Meesho"),
    ("groww", "Groww"),
    ("zerodha", "Zerodha"),
    ("slice", "Slice"),
    ("setu", "Setu"),
    ("postman", "Postman"),
    ("browserstack", "BrowserStack"),
    ("freshworks", "Freshworks"),
    ("hasura", "Hasura"),
    ("chargebee", "Chargebee"),
    ("clevertap", "CleverTap"),
    ("moengage", "MoEngage"),
    ("druva", "Druva"),
    ("ninjacart", "Ninjacart"),
    ("darwinbox", "Darwinbox"),
    ("leadsquared", "LeadSquared"),
    # Global remote-friendly tech companies
    ("stripe", "Stripe"),
    ("notion", "Notion"),
    ("airbnb", "Airbnb"),
    ("pinterest", "Pinterest"),
    ("coinbase", "Coinbase"),
    ("dropbox", "Dropbox"),
    ("twilio", "Twilio"),
    ("sendgrid", "SendGrid"),
    ("datadog", "Datadog"),
    ("mongodb", "MongoDB"),
    ("elastic", "Elastic"),
    ("hashicorp", "HashiCorp"),
    ("cloudflare", "Cloudflare"),
    ("figma", "Figma"),
    ("vercel", "Vercel"),
    ("planetscale", "PlanetScale"),
    ("supabase", "Supabase"),
    ("linear", "Linear"),
    ("retool", "Retool"),
    ("dbt", "dbt Labs"),
    ("cockroachlabs", "CockroachDB"),
    ("temporal", "Temporal"),
    ("confluent", "Confluent"),
    ("grafana", "Grafana Labs"),
    ("sentry", "Sentry"),
    ("posthog", "PostHog"),
    ("loom", "Loom"),
    ("miro", "Miro"),
    ("contentful", "Contentful"),
    ("algolia", "Algolia"),
    ("segment", "Segment"),
    ("amplitude", "Amplitude"),
    ("mixpanel", "Mixpanel"),
    ("intercom", "Intercom"),
    ("zendesk", "Zendesk"),
    ("hubspot", "HubSpot"),
    ("netlify", "Netlify"),
    ("fastly", "Fastly"),
    ("auth0", "Auth0"),
    ("okta", "Okta"),
]

GREENHOUSE_BASE = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


def is_enabled() -> bool:
    """Always on — no key needed. Greenhouse is a fully public API."""
    return True


def _fetch_company_jobs(token: str, company_name: str, results: int) -> list[dict]:
    """Fetches live job postings for a single Greenhouse board token."""
    try:
        resp = requests.get(
            GREENHOUSE_BASE.format(token=token),
            params={"content": "true"},
            timeout=15,
        )
        if resp.status_code == 404:
            return []  # Company may have left Greenhouse
        resp.raise_for_status()
        data = resp.json()
        jobs = []
        for item in (data.get("jobs") or [])[:results]:
            # Extract location
            location = ""
            if item.get("location"):
                location = item["location"].get("name", "")
            # Extract JD from content blob
            jd = item.get("content", "") or ""
            # Strip basic HTML tags
            import re
            jd = re.sub(r"<[^>]+>", " ", jd).strip()
            jobs.append({
                "company": company_name,
                "title": item.get("title", ""),
                "url": item.get("absolute_url", ""),
                "location": location,
                "jd": jd[:3000],  # trim very long JDs
            })
        return jobs
    except Exception:
        return []


def search_jobs(keywords: str, results: int = 15) -> list[dict]:
    """Fetches jobs from all curated Greenhouse companies and filters by keyword.
    Each company is queried independently so one failure never blocks others."""
    kw_lower = keywords.lower() if keywords else ""
    all_jobs = []

    # Spread results evenly — we don't want to exhaust the limit on first company
    per_company = max(3, results // 5)

    for token, company_name in GREENHOUSE_COMPANIES:
        if len(all_jobs) >= results * 4:  # collect 4x and keyword-filter down
            break
        company_jobs = _fetch_company_jobs(token, company_name, per_company)
        all_jobs.extend(company_jobs)

    # Keyword filter
    if kw_lower:
        filtered = [
            j for j in all_jobs
            if kw_lower in j["title"].lower() or kw_lower in j["jd"].lower()
        ]
        # Fall back to unfiltered if keyword is too strict
        return (filtered or all_jobs)[:results]
    return all_jobs[:results]
