"""Every job source is a small adapter with two things:

  1. A `search_jobs(keywords, results) -> list[dict]` function returning
     dicts shaped like {company, title, url, location, jd}. Return []
     on any failure — a down/misconfigured source must never break
     discovery for the others.
  2. An `is_enabled() -> bool` function — usually "do I have an API key".

To add a new job site:
  1. Drop a new file in this folder (e.g. `mycompany.py`) with those two
     functions, following adzuna.py or jooble.py as a template.
  2. Register it in `registry.py`'s SOURCES list with a display name.
That's it — dedup, blacklist filtering, eligibility filtering, LLM
scoring, storage, and the frontend all work off the registry and never
need to change again.
"""
