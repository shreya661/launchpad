from . import adzuna, remotive, jooble, jsearch

# Add a new source here after writing its adapter file — nothing else in the
# app needs to change. "name" is what gets stored on JobMatch.source and
# shown as a pill in the UI.
SOURCES = [
    {"name": "Adzuna", "module": adzuna},
    {"name": "Remotive", "module": remotive},
    {"name": "Jooble", "module": jooble},
    {"name": "JSearch", "module": jsearch},
]


def active_sources() -> list[dict]:
    """Sources whose is_enabled() passes (i.e. their API key is set)."""
    return [s for s in SOURCES if s["module"].is_enabled()]


def search_all(keywords: str, results_per_source: int = 15) -> list[dict]:
    """Queries every enabled source and returns a combined, source-tagged list.
    One source failing/timing out never blocks the others."""
    combined = []
    for s in active_sources():
        try:
            jobs = s["module"].search_jobs(keywords, results_per_source)
        except Exception:
            jobs = []
        for job in jobs:
            job["source"] = s["name"]
            combined.append(job)
    return combined
