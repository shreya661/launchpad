from . import (
    adzuna, remotive, jooble, jsearch, arbeitnow,
    greenhouse_boards, lever_boards, ashby_boards,
    jobicy, remoteok, findwork, themuse, serpapi_jobs,
)

# Add a new source here after writing its adapter file — nothing else in the
# app needs to change. "name" is what gets stored on JobMatch.source and
# shown as a pill in the UI.
SOURCES = [
    # Direct ATS boards — jobs appear here BEFORE aggregators pick them up
    {"name": "Greenhouse",     "module": greenhouse_boards},
    {"name": "Lever",          "module": lever_boards},
    {"name": "Ashby",          "module": ashby_boards},
    # Aggregators with India coverage (covers Naukri/LinkedIn/Instahyre/Wellfound)
    {"name": "SerpAPI/Google Jobs", "module": serpapi_jobs},
    {"name": "JSearch",        "module": jsearch},
    {"name": "Adzuna",         "module": adzuna},
    {"name": "Jooble",         "module": jooble},
    # Remote-first boards (US/EU companies hiring remote in India)
    {"name": "Remotive",       "module": remotive},
    {"name": "Jobicy",         "module": jobicy},
    {"name": "RemoteOK",       "module": remoteok},
    {"name": "Arbeitnow",      "module": arbeitnow},
    # Developer-specific boards
    {"name": "Findwork",       "module": findwork},
    {"name": "The Muse",       "module": themuse},
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
