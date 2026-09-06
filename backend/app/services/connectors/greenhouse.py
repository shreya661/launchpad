"""Greenhouse ATS connector — many companies (Stripe, Airbnb, etc.) use Greenhouse.
Greenhouse hosted job boards accept applications via a public API endpoint.
This connector can auto-apply when the job URL is a Greenhouse posting."""

import requests


def can_auto_apply() -> bool:
    return True


def is_configured(portal_profile: dict) -> bool:
    return bool(portal_profile.get("profile_url") or portal_profile.get("username"))


def _extract_greenhouse_board_and_job(url: str) -> tuple:
    """Tries to extract board token and job ID from a Greenhouse URL like
    https://boards.greenhouse.io/company/jobs/123456"""
    if "greenhouse.io" not in url:
        return "", ""
    parts = url.rstrip("/").split("/")
    try:
        jobs_idx = parts.index("jobs")
        job_id = parts[jobs_idx + 1]
        # board token is typically 2 before "jobs"
        board_token = parts[jobs_idx - 1] if jobs_idx >= 1 else ""
        return board_token, job_id
    except (ValueError, IndexError):
        return "", ""


def apply(job: dict, master_resume: dict, portal_profile: dict) -> dict:
    url = job.get("url", "")
    board_token, job_id = _extract_greenhouse_board_and_job(url)

    if not board_token or not job_id:
        return {
            "applied": False,
            "method": "manual",
            "apply_url": url,
            "message": "Not a Greenhouse posting URL — open it manually.",
        }

    # Greenhouse public candidate application API
    apply_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}"

    form_data = {
        "first_name": master_resume.get("name", "").split()[0] if master_resume.get("name") else "",
        "last_name": " ".join(master_resume.get("name", "").split()[1:]) if master_resume.get("name") else "",
        "email": master_resume.get("email", ""),
        "phone": master_resume.get("phone", ""),
    }

    try:
        resp = requests.post(apply_url, json=form_data, timeout=30)
        if resp.status_code in (200, 201):
            return {
                "applied": True,
                "method": "auto",
                "apply_url": url,
                "message": "Applied via Greenhouse API successfully.",
            }
        else:
            return {
                "applied": False,
                "method": "manual",
                "apply_url": url,
                "message": f"Greenhouse API returned {resp.status_code}. Open and apply manually.",
            }
    except Exception as e:
        return {
            "applied": False,
            "method": "manual",
            "apply_url": url,
            "message": f"Greenhouse request failed: {str(e)}. Apply manually.",
        }
