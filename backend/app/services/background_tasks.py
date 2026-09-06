"""Background task scheduler — runs periodic jobs like GitHub repo polling.
Uses APScheduler for reliable cron-like scheduling within the FastAPI process."""

import os
import logging
from datetime import date
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger("launchpad.background")

GITHUB_POLL_MINUTES = int(os.getenv("GITHUB_POLL_INTERVAL_MINUTES", "30"))
DISCOVERY_POLL_MINUTES = int(os.getenv("DISCOVERY_POLL_INTERVAL_MINUTES", "60"))
INBOX_SCAN_MINUTES = int(os.getenv("INBOX_SCAN_INTERVAL_MINUTES", "20"))

scheduler = BackgroundScheduler()


def sync_github_repos():
    """Background job: polls GitHub repos, stores new ones, emails notifications."""
    from .github_monitor import is_enabled, fetch_repos, fetch_repo_languages, \
        fetch_readme_excerpt, generate_accept_token, generate_project_bullets
    from .emailer import send_project_notification_email, EMAIL_ADDRESS

    if not is_enabled():
        return

    # Import DB inside the function to avoid circular imports at module level
    from ..database import SessionLocal
    from ..models import GitHubRepo, MasterResume

    db = SessionLocal()
    try:
        existing_names = {r.repo_name for r in db.query(GitHubRepo.repo_name).all()}
        repos = fetch_repos()
        added = 0

        # Get user email for notifications
        resume = db.query(MasterResume).filter(MasterResume.id == 1).first()
        user_email = resume.email if resume else EMAIL_ADDRESS

        for repo in repos:
            if repo["repo_name"] in existing_names:
                continue

            # Fetch extra metadata
            languages = fetch_repo_languages(repo["repo_name"])
            readme = fetch_readme_excerpt(repo["repo_name"])

            # Generate ATS bullets
            bullets = generate_project_bullets(
                repo["repo_name"], repo["description"], languages, readme
            )

            token = generate_accept_token()

            row = GitHubRepo(
                repo_name=repo["repo_name"],
                repo_url=repo["repo_url"],
                description=repo["description"],
                languages=languages or ([repo["language"]] if repo.get("language") else []),
                stars=repo["stars"],
                last_pushed=repo["last_pushed"],
                status="pending",
                accept_token=token,
                auto_bullets=bullets,
                created_date=date.today().isoformat(),
            )
            db.add(row)
            added += 1

            # Send email notification
            if user_email and EMAIL_ADDRESS:
                try:
                    send_project_notification_email(
                        to_address=user_email,
                        repo_name=repo["repo_name"],
                        repo_url=repo["repo_url"],
                        description=repo["description"],
                        languages=languages,
                        stars=repo["stars"],
                        bullets=bullets,
                        accept_token=token,
                    )
                except Exception as e:
                    logger.warning(f"Failed to send email for {repo['repo_name']}: {e}")

        if added:
            db.commit()
            logger.info(f"GitHub sync: added {added} new repo(s)")
        else:
            logger.info("GitHub sync: no new repos found")

    except Exception as e:
        logger.error(f"GitHub sync failed: {e}")
        db.rollback()
    finally:
        db.close()


def run_discovery_and_auto_apply():
    """Background job: pulls fresh postings and, if AUTO_APPLY_ENABLED, submits
    to eligible Lever/Greenhouse matches immediately, with zero manual review.
    Everything else (LinkedIn/Naukri/Indeed/etc) still just gets prepared and
    left for you to open and apply manually."""
    from .auto_apply import AUTO_APPLY_ENABLED

    from ..database import SessionLocal
    db = SessionLocal()
    try:
        from ..routers.discovery import run_discovery
        result = run_discovery(db=db)
        if AUTO_APPLY_ENABLED:
            applied = result.get("autoApply", {}).get("applied", 0)
            logger.info(f"Scheduled discovery: {result.get('added', 0)} new matches, "
                        f"{applied} auto-applied.")
        else:
            logger.info(f"Scheduled discovery: {result.get('added', 0)} new matches "
                        f"(auto-apply is off).")
    except Exception as e:
        logger.error(f"Scheduled discovery/auto-apply failed: {e}")
        db.rollback()
    finally:
        db.close()


def run_inbox_scan():
    """Background job: scans the inbox for replies about tracked applications
    and updates status + notifies the user on a confident match."""
    from .email_monitor import is_enabled, scan_inbox

    if not is_enabled():
        return

    from ..database import SessionLocal
    db = SessionLocal()
    try:
        result = scan_inbox(db)
        logger.info(f"Inbox scan: {result.get('scanned', 0)} emails checked, "
                    f"{result.get('matched', 0)} status update(s) detected.")
    except Exception as e:
        logger.error(f"Inbox scan failed: {e}")
        db.rollback()
    finally:
        db.close()


def start_scheduler():
    """Call this on app startup to begin background polling."""
    from .github_monitor import is_enabled
    from .email_monitor import is_enabled as email_scan_enabled

    if is_enabled() and GITHUB_POLL_MINUTES > 0:
        scheduler.add_job(
            sync_github_repos,
            trigger=IntervalTrigger(minutes=GITHUB_POLL_MINUTES),
            id="github_sync",
            replace_existing=True,
        )
        logger.info(f"GitHub polling started: every {GITHUB_POLL_MINUTES} minutes")

    if DISCOVERY_POLL_MINUTES > 0:
        scheduler.add_job(
            run_discovery_and_auto_apply,
            trigger=IntervalTrigger(minutes=DISCOVERY_POLL_MINUTES),
            id="discovery_and_auto_apply",
            replace_existing=True,
        )
        logger.info(f"Discovery + auto-apply polling started: every {DISCOVERY_POLL_MINUTES} minutes")

    if email_scan_enabled() and INBOX_SCAN_MINUTES > 0:
        scheduler.add_job(
            run_inbox_scan,
            trigger=IntervalTrigger(minutes=INBOX_SCAN_MINUTES),
            id="inbox_scan",
            replace_existing=True,
        )
        logger.info(f"Inbox status scan started: every {INBOX_SCAN_MINUTES} minutes")

    if not scheduler.running:
        scheduler.start()
        logger.info("Background scheduler started")


def stop_scheduler():
    """Call this on app shutdown."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")
