from . import (
    lever, greenhouse, linkedin, naukri, indeed,
    instahyre, internshala, wellfound, hackerrank, unstop, generic,
)

# Register connectors here — portal_name must match what's stored in the
# portal_profiles table.  The module must expose can_auto_apply(),
# is_configured(profile), and apply(job, resume, profile).
CONNECTORS = [
    {"portal_name": "lever",        "display": "Lever ATS",       "module": lever},
    {"portal_name": "greenhouse",   "display": "Greenhouse ATS",  "module": greenhouse},
    {"portal_name": "linkedin",     "display": "LinkedIn",        "module": linkedin},
    {"portal_name": "naukri",       "display": "Naukri",          "module": naukri},
    {"portal_name": "indeed",       "display": "Indeed",          "module": indeed},
    {"portal_name": "instahyre",    "display": "Instahyre",       "module": instahyre},
    {"portal_name": "internshala", "display": "Internshala",     "module": internshala},
    {"portal_name": "wellfound",   "display": "Wellfound",       "module": wellfound},
    {"portal_name": "hackerrank",  "display": "HackerRank Jobs", "module": hackerrank},
    {"portal_name": "unstop",      "display": "Unstop",          "module": unstop},
    {"portal_name": "generic",      "display": "Generic",         "module": generic},
]


def get_connector(portal_name: str):
    """Returns the connector module for a portal, or None."""
    for c in CONNECTORS:
        if c["portal_name"] == portal_name:
            return c["module"]
    return None


def active_connectors(portal_profiles: list[dict]) -> list[dict]:
    """Returns connectors whose profile is configured."""
    profile_map = {p["portal_name"]: p for p in portal_profiles}
    result = []
    for c in CONNECTORS:
        prof = profile_map.get(c["portal_name"])
        if prof and c["module"].is_configured(prof):
            result.append({
                "portal_name": c["portal_name"],
                "display": c["display"],
                "can_auto_apply": c["module"].can_auto_apply(),
            })
    return result


def apply_to_job(portal_name: str, job: dict, master_resume: dict, portal_profile: dict) -> dict:
    """Delegates to the right connector.  Returns a result dict."""
    mod = get_connector(portal_name)
    if not mod:
        return {"applied": False, "method": "manual", "apply_url": job.get("url", ""),
                "message": f"No connector found for '{portal_name}'."}
    if not mod.is_configured(portal_profile):
        return {"applied": False, "method": "manual", "apply_url": job.get("url", ""),
                "message": f"Connector for '{portal_name}' is not configured — fill in your profile first."}
    try:
        return mod.apply(job, master_resume, portal_profile)
    except Exception as e:
        return {"applied": False, "method": "manual", "apply_url": job.get("url", ""),
                "message": f"Connector error: {str(e)}"}
