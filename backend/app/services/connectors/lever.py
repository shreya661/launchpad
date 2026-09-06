"""Lever ATS connector — many startups use Lever's hosted apply forms.
Lever's apply endpoint accepts a multipart POST with resume + candidate fields.
This connector can fully auto-apply when the job URL is a Lever posting."""

import os
import requests

LEVER_APPLY_TEMPLATE = "https://api.lever.co/v0/postings/{posting_id}/apply"


def can_auto_apply() -> bool:
    return True


def is_configured(portal_profile: dict) -> bool:
    # Lever doesn't need login creds — it uses public apply endpoints.
    # Just need the user's basic info from the master resume.
    return bool(portal_profile.get("profile_url") or portal_profile.get("username"))


def _extract_lever_posting_id(url: str) -> str:
    """Tries to extract a Lever posting ID from a URL like
    https://jobs.lever.co/company/posting-uuid"""
    if "lever.co" not in url:
        return ""
    parts = url.rstrip("/").split("/")
    if len(parts) >= 2:
        return parts[-1]
    return ""


def apply(job: dict, master_resume: dict, portal_profile: dict) -> dict:
    url = job.get("url", "")
    posting_id = _extract_lever_posting_id(url)

    if not posting_id:
        return {
            "applied": False,
            "method": "manual",
            "apply_url": url,
            "message": "Not a Lever posting URL — open it manually.",
        }

    # Lever's public apply endpoint
    apply_url = LEVER_APPLY_TEMPLATE.format(posting_id=posting_id)

    form_data = {
        "name": master_resume.get("name", ""),
        "email": master_resume.get("email", ""),
        "phone": master_resume.get("phone", ""),
        "org": master_resume.get("education", ""),
        "urls[LinkedIn]": master_resume.get("linkedin_url", ""),
        "urls[GitHub]": master_resume.get("github_url", ""),
        "urls[Portfolio]": master_resume.get("portfolio_url", ""),
        "comments": job.get("tailored_summary", master_resume.get("summary", "")),
    }

    try:
        resp = requests.post(apply_url, data=form_data, timeout=30)
        if resp.status_code in (200, 201):
            return {
                "applied": True,
                "method": "auto",
                "apply_url": url,
                "message": "Applied via Lever API successfully.",
            }
        else:
            return {
                "applied": False,
                "method": "manual",
                "apply_url": url,
                "message": f"Lever API returned {resp.status_code}. Open the posting and apply manually.",
            }
    except Exception as e:
        return {
            "applied": False,
            "method": "manual",
            "apply_url": url,
            "message": f"Lever request failed: {str(e)}. Apply manually.",
        }
