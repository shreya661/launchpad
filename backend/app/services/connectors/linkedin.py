"""LinkedIn connector — CANNOT auto-submit (scripting LinkedIn logins risks
your account getting banned). This connector prepares everything and gives
you a one-click URL to the apply page."""

import os
import urllib.parse


def can_auto_apply() -> bool:
    return False


def is_configured(portal_profile: dict) -> bool:
    return bool(portal_profile.get("profile_url") or portal_profile.get("username"))


def apply(job: dict, master_resume: dict, portal_profile: dict) -> dict:
    url = job.get("url", "")

    # If the URL is a direct LinkedIn job posting, use it.
    # Otherwise construct a search-like URL.
    if "linkedin.com" in url:
        apply_url = url
    else:
        # Construct a LinkedIn job search URL with the title + company
        query = urllib.parse.quote(f"{job.get('title', '')} {job.get('company', '')}")
        apply_url = f"https://www.linkedin.com/jobs/search/?keywords={query}"

    return {
        "applied": False,
        "method": "manual",
        "apply_url": apply_url,
        "message": (
            "LinkedIn doesn't allow automated applications — your tailored resume "
            "is ready. Click the link to open the posting, then apply with your "
            "downloaded resume."
        ),
    }
