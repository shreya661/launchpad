"""Lever ATS — direct board crawl.

Lever is an ATS used by many startups and mid-size tech companies.
Every company on Lever exposes a fully public JSON postings API.
No key, no auth, no scraping required.

Jobs appear here the moment the company publishes them — often 2-5 days
before they surface on Naukri / LinkedIn.

API: GET https://api.lever.co/v0/postings/{company}?mode=json
Docs: https://hire.lever.co/developer/postings
"""

import requests

# Curated list of companies using Lever ATS.
# Format: (lever_slug, display_name)
LEVER_COMPANIES = [
    # India-founded / India-hiring
    ("razorpay", "Razorpay"),
    ("phonepe", "PhonePe"),
    ("paytm", "Paytm"),
    ("ola", "Ola"),
    ("oyo", "OYO"),
    ("byju-s", "BYJU'S"),
    ("swiggy", "Swiggy"),
    ("zomato", "Zomato"),
    ("flipkart", "Flipkart"),
    ("myntra", "Myntra"),
    ("urbancompany", "Urban Company"),
    ("navi", "Navi"),
    ("smallcase", "Smallcase"),
    ("jupiter", "Jupiter"),
    ("khatabook", "Khatabook"),
    ("plum", "Plum"),
    ("setu", "Setu"),
    ("recko", "Recko"),
    ("voicebpe", "Voice"),
    # Global / remote-friendly
    ("netflix", "Netflix"),
    ("reddit", "Reddit"),
    ("figma", "Figma"),
    ("canva", "Canva"),
    ("airtable", "Airtable"),
    ("asana", "Asana"),
    ("notion", "Notion"),
    ("clickup", "ClickUp"),
    ("linear", "Linear"),
    ("webflow", "Webflow"),
    ("loom", "Loom"),
    ("typeform", "Typeform"),
    ("hotjar", "Hotjar"),
    ("segment", "Segment"),
    ("brex", "Brex"),
    ("rippling", "Rippling"),
    ("deel", "Deel"),
    ("remote", "Remote"),
    ("gusto", "Gusto"),
    ("carta", "Carta"),
    ("mercury", "Mercury"),
    ("ramp", "Ramp"),
    ("scale-ai", "Scale AI"),
    ("cohere", "Cohere"),
    ("huggingface", "Hugging Face"),
    ("qdrant", "Qdrant"),
    ("weaviate", "Weaviate"),
    ("pinecone", "Pinecone"),
    ("anthropic", "Anthropic"),
    ("mistral", "Mistral AI"),
    ("perplexity-ai", "Perplexity AI"),
    ("openai", "OpenAI"),
]

LEVER_BASE = "https://api.lever.co/v0/postings/{slug}?mode=json"


def is_enabled() -> bool:
    """Always on — Lever postings API is fully public."""
    return True


def _fetch_company_jobs(slug: str, company_name: str, results: int) -> list[dict]:
    """Fetches live postings for a single Lever company slug."""
    try:
        resp = requests.get(
            LEVER_BASE.format(slug=slug),
            timeout=15,
        )
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        data = resp.json()
        jobs = []
        for item in data[:results]:
            # Build JD from lists block
            jd_parts = []
            for block in (item.get("lists") or []):
                jd_parts.append(block.get("text", "") + ": " + " ".join(
                    block.get("content", [])
                ))
            jd = " ".join(jd_parts) or item.get("descriptionPlain", "")
            location = ""
            cats = item.get("categories") or {}
            location = cats.get("location", "") or cats.get("commitment", "")
            jobs.append({
                "company": company_name,
                "title": item.get("text", ""),
                "url": item.get("hostedUrl", ""),
                "location": location,
                "jd": jd[:3000],
            })
        return jobs
    except Exception:
        return []


def search_jobs(keywords: str, results: int = 15) -> list[dict]:
    """Fetches jobs from all curated Lever companies and filters by keyword."""
    kw_lower = keywords.lower() if keywords else ""
    all_jobs = []
    per_company = max(3, results // 5)

    for slug, company_name in LEVER_COMPANIES:
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
