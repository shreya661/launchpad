"""Unstop (formerly Dare2Compete) connector — CANNOT auto-submit (no public
apply API, and scripting a login risks the account). This connector prepares
everything and gives you a one-click URL to the job or a search page."""

import urllib.parse


def can_auto_apply() -> bool:
    return False


def is_configured(portal_profile: dict) -> bool:
    return bool(portal_profile.get("profile_url") or portal_profile.get("username"))


def apply(job: dict, master_resume: dict, portal_profile: dict) -> dict:
    url = job.get("url", "")

    if "unstop.com" in url:
        apply_url = url
    else:
        query = urllib.parse.quote(f"{job.get('title', '')} {job.get('company', '')}")
        apply_url = f"https://unstop.com/jobs?searchTerm={query}"

    return {
        "applied": False,
        "method": "manual",
        "apply_url": apply_url,
        "message": (
            "Unstop doesn't allow automated applications — your tailored resume "
            "is ready. Click the link to open the posting, then apply with your "
            "downloaded resume."
        ),
    }
