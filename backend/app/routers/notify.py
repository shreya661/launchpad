from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Application, MasterResume
from ..services.emailer import send_application_email

router = APIRouter(prefix="/api/notify", tags=["notify"])


@router.post("/email/{app_id}")
def email_application(app_id: int, db: Session = Depends(get_db)):
    app_row = db.query(Application).filter(Application.id == app_id).first()
    if not app_row:
        raise HTTPException(status_code=404, detail="Application not found")
    resume = db.query(MasterResume).filter(MasterResume.id == 1).first()
    to_address = resume.email if resume else ""

    try:
        send_application_email(to_address, {
            "code": app_row.code, "company": app_row.company, "title": app_row.title,
            "source": app_row.source, "applied_date": app_row.applied_date,
            "match_score": app_row.match_score, "deadline": app_row.deadline,
            "url": app_row.url, "tailored_summary": app_row.tailored_summary,
        })
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"sent": True}


@router.get("/inbox-scan/status")
def inbox_scan_status():
    """Whether inbox status-scanning is configured. Uses the same Gmail app
    password already set up for sending — no separate credential needed."""
    from ..services.email_monitor import is_enabled, INBOX_SCAN_MAX_EMAILS
    return {
        "enabled": is_enabled(),
        "maxEmailsPerPass": INBOX_SCAN_MAX_EMAILS,
        "message": (
            "Inbox scanning is active — checking for interview/offer/rejection replies."
            if is_enabled() else
            "Set EMAIL_ADDRESS and EMAIL_APP_PASSWORD in backend/.env to enable inbox scanning."
        ),
    }


@router.post("/inbox-scan/run")
def inbox_scan_run(db: Session = Depends(get_db)):
    """Manually triggers one pass of the inbox scanner right now, instead of
    waiting for the next scheduled run."""
    from ..services.email_monitor import scan_inbox
    return scan_inbox(db)
