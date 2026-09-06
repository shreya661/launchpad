"""Zero-review auto-apply pipeline.

Scope, deliberately: this only ever touches portals whose connector reports
can_auto_apply() == True (currently Lever and Greenhouse — both have public,
legitimate hosted-apply APIs). LinkedIn/Naukri/Indeed and anything else stay
manual-only forever, regardless of this pipeline, because scripting those
logins risks the user's account.

Flow: for each undismissed JobMatch scoring >= AUTO_APPLY_MIN_SCORE, try to
resolve which connector (if any) owns that job's URL. If that connector is
configured and can auto-apply, submit immediately with no confirmation step,
then convert the match into a tracked Application and email a confirmation.
"""

import os
import logging
from datetime import date

logger = logging.getLogger("launchpad.auto_apply")

AUTO_APPLY_ENABLED = os.getenv("AUTO_APPLY_ENABLED", "false").lower() in ("1", "true", "yes")
AUTO_APPLY_MIN_SCORE = int(os.getenv("AUTO_APPLY_MIN_SCORE", "75"))

# Which connectors are even allowed to run through this zero-review pipeline.
# Deliberately excludes linkedin/naukri/indeed/generic/etc — those can_auto_apply() == False anyway,
# but this allowlist is a second, explicit gate so the pipeline can never silently
# start "auto-applying" through a portal that isn't truly API-based.
AUTO_APPLY_ALLOWED_PORTALS = {"lever", "greenhouse"}


def _resolve_portal_for_url(url: str) -> str:
    """Best-effort match of a job URL to a known auto-apply-capable portal."""
    if not url:
        return ""
    if "lever.co" in url:
        return "lever"
    if "greenhouse.io" in url:
        return "greenhouse"
    return ""


def run_auto_apply(db) -> dict:
    """Runs one pass of the auto-apply pipeline against stored JobMatches.
    Safe to call repeatedly — matches, once auto-applied or otherwise
    dismissed, are never revisited."""
    from ..models import JobMatch, Application, MasterResume, PortalProfile
    from ..services.connectors.registry import get_connector
    from ..services.emailer import send_application_email, EMAIL_ADDRESS

    if not AUTO_APPLY_ENABLED:
        return {"enabled": False, "applied": 0, "checked": 0}

    resume_row = db.query(MasterResume).filter(MasterResume.id == 1).first()
    if not resume_row:
        return {"enabled": True, "applied": 0, "checked": 0, "message": "No master resume saved."}

    master = {
        "name": resume_row.name, "email": resume_row.email, "phone": resume_row.phone,
        "summary": resume_row.summary, "skills": resume_row.skills,
        "education": resume_row.education, "linkedin_url": resume_row.linkedin_url,
        "github_url": resume_row.github_url, "portfolio_url": resume_row.portfolio_url,
    }

    portal_profiles = {p.portal_name: p for p in db.query(PortalProfile).all()}

    candidates = (
        db.query(JobMatch)
        .filter(JobMatch.dismissed == 0)
        .filter(JobMatch.match_score >= AUTO_APPLY_MIN_SCORE)
        .all()
    )

    checked = 0
    applied_count = 0
    results = []

    for match in candidates:
        portal_name = _resolve_portal_for_url(match.url)
        if portal_name not in AUTO_APPLY_ALLOWED_PORTALS:
            continue
        checked += 1

        mod = get_connector(portal_name)
        if not mod or not mod.can_auto_apply():
            continue

        profile_row = portal_profiles.get(portal_name)
        if not profile_row or not bool(profile_row.is_connector_enabled):
            continue  # user hasn't opted this portal in yet

        profile = {
            "portal_name": portal_name,
            "profile_url": profile_row.profile_url or "",
            "username": profile_row.username or "",
            "extra_fields": profile_row.extra_fields or {},
        }
        if not mod.is_configured(profile):
            continue

        job = {
            "company": match.company, "title": match.title, "url": match.url,
            "jd": match.jd, "tailored_summary": match.tailored_summary,
        }

        try:
            result = mod.apply(job, master, profile)
        except Exception as e:
            logger.warning(f"Auto-apply error for match {match.id} via {portal_name}: {e}")
            continue

        if not result.get("applied"):
            # Connector declined (e.g. couldn't parse a posting ID, API rejected it) —
            # leave the match as-is so it still shows up for manual review/apply.
            continue

        # Successful auto-apply — convert into a tracked Application, same as
        # the manual "promote" step, and stop revisiting this match.
        count = db.query(Application).count()
        code = f"APP-{count + 1:03d}"
        app_row = Application(
            code=code, company=match.company, title=match.title, source=match.source,
            url=match.url, deadline=None, applied_date=date.today().isoformat(),
            status="applied", match_score=match.match_score,
            company_snapshot="", tailored_summary=match.tailored_summary,
            tailored_bullets=match.tailored_bullets, missing_skills=match.missing_skills,
            jd=match.jd, auto_applied=1,
            status_note=f"Auto-applied via {portal_name} connector.",
        )
        db.add(app_row)
        match.dismissed = 1
        applied_count += 1
        results.append({"company": match.company, "title": match.title, "portal": portal_name})
        db.flush()

        if master.get("email") and EMAIL_ADDRESS:
            try:
                send_application_email(master["email"], {
                    "code": code, "company": match.company, "title": match.title,
                    "source": f"auto-apply/{portal_name}", "applied_date": app_row.applied_date,
                    "match_score": match.match_score, "deadline": None,
                    "url": match.url, "tailored_summary": match.tailored_summary,
                })
            except Exception as e:
                logger.warning(f"Auto-apply confirmation email failed for {code}: {e}")

    db.commit()
    return {"enabled": True, "checked": checked, "applied": applied_count, "results": results}
