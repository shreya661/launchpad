"""Generic connector — fallback for any portal without a dedicated connector.
Opens the job posting URL in the browser. No automation possible."""


def can_auto_apply() -> bool:
    return False


def is_configured(portal_profile: dict) -> bool:
    # Generic connector always works — no specific config needed.
    return True


def apply(job: dict, master_resume: dict, portal_profile: dict) -> dict:
    url = job.get("url", "")
    return {
        "applied": False,
        "method": "manual",
        "apply_url": url,
        "message": (
            "No dedicated connector for this portal. Your tailored resume is ready — "
            "open the posting link and apply manually."
        ),
    }
