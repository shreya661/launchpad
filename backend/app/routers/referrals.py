from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ReferralContact, MasterResume
from ..schemas import (
    ReferralCreate, ReferralUpdate, ReferralOut, ReferralDraftRequest,
    BulkReferralDraftRequest, BulkReferralResultItem,
)
from ..services.groq_client import draft_cold_message

router = APIRouter(prefix="/api/referrals", tags=["referrals"])

FOLLOW_UP_AFTER_DAYS = 7  # nudge if a "sent" reach-out has been quiet this long


@router.get("", response_model=list[ReferralOut])
def list_referrals(db: Session = Depends(get_db)):
    return db.query(ReferralContact).order_by(ReferralContact.id.desc()).all()


@router.get("/follow-ups")
def follow_ups_due(days: int = FOLLOW_UP_AFTER_DAYS, db: Session = Depends(get_db)):
    """Reach-outs marked 'sent' with no reply logged, sent >= `days` ago —
    a nudge list, not an auto-send: you still decide whether/how to follow up."""
    cutoff = date.today() - timedelta(days=days)
    rows = db.query(ReferralContact).filter(ReferralContact.status == "sent").all()
    due = []
    for r in rows:
        if not r.message_sent_date:
            continue
        try:
            sent = datetime.strptime(r.message_sent_date, "%Y-%m-%d").date()
        except ValueError:
            continue
        if sent <= cutoff:
            due.append({
                "id": r.id, "name": r.name, "company": r.company,
                "linkedin_url": r.linkedin_url, "message_sent_date": r.message_sent_date,
                "daysSinceSent": (date.today() - sent).days,
            })
    due.sort(key=lambda x: -x["daysSinceSent"])
    return {"count": len(due), "followUps": due}


@router.post("", response_model=ReferralOut)
def create_referral(payload: ReferralCreate, db: Session = Depends(get_db)):
    row = ReferralContact(
        name=payload.name, company=payload.company, role_title=payload.role_title,
        linkedin_url=payload.linkedin_url, target_job_title=payload.target_job_title,
        notes=payload.notes, status="not_sent", created_date=date.today().isoformat(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.post("/draft-message")
def draft_message(payload: ReferralDraftRequest, db: Session = Depends(get_db)):
    """Generates a short, personalized cold-reachout message for the person to review,
    edit, and send themselves — Launchpad never messages anyone on your behalf."""
    resume = db.query(MasterResume).filter(MasterResume.id == 1).first()
    if not resume:
        raise HTTPException(status_code=400, detail="Save your master resume first.")
    master = {
        "name": resume.name, "summary": resume.summary, "skills": resume.skills,
        "education": resume.education, "experience": resume.experience or [],
    }
    try:
        message = draft_cold_message(
            master, payload.name, payload.company, payload.role_title,
            payload.target_job_title, payload.jd,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Drafting failed: {e}")
    return {"message": message}


@router.post("/draft-message-bulk")
def draft_message_bulk(payload: BulkReferralDraftRequest, db: Session = Depends(get_db)):
    """Drafts and saves a personalized message for each contact in the list —
    still one message per person from your real resume, just queued up in one go
    instead of one at a time. Nothing is sent; each row lands as status 'not_sent'
    for you to review, edit, and send yourself."""
    resume = db.query(MasterResume).filter(MasterResume.id == 1).first()
    if not resume:
        raise HTTPException(status_code=400, detail="Save your master resume first.")
    if not payload.contacts:
        raise HTTPException(status_code=400, detail="Add at least one contact.")
    master = {
        "name": resume.name, "summary": resume.summary, "skills": resume.skills,
        "education": resume.education, "experience": resume.experience or [],
    }
    results = []
    for c in payload.contacts:
        try:
            message = draft_cold_message(
                master, c.name, c.company, c.role_title, c.target_job_title, payload.jd,
            )
            row = ReferralContact(
                name=c.name, company=c.company, role_title=c.role_title,
                linkedin_url=c.linkedin_url, target_job_title=c.target_job_title,
                message_draft=message, status="not_sent",
                created_date=date.today().isoformat(),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            results.append(BulkReferralResultItem(name=c.name, company=c.company, ok=True, referral=row))
        except Exception as e:
            db.rollback()
            results.append(BulkReferralResultItem(name=c.name, company=c.company, ok=False, error=str(e)))
    return {"results": results}


@router.patch("/{referral_id}", response_model=ReferralOut)
def update_referral(referral_id: int, payload: ReferralUpdate, db: Session = Depends(get_db)):
    row = db.query(ReferralContact).filter(ReferralContact.id == referral_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    if payload.status is not None:
        row.status = payload.status
        if payload.status == "sent" and not row.message_sent_date:
            row.message_sent_date = date.today().isoformat()
    if payload.message_draft is not None:
        row.message_draft = payload.message_draft
    if payload.message_sent_date is not None:
        row.message_sent_date = payload.message_sent_date
    if payload.notes is not None:
        row.notes = payload.notes
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{referral_id}")
def delete_referral(referral_id: int, db: Session = Depends(get_db)):
    row = db.query(ReferralContact).filter(ReferralContact.id == referral_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(row)
    db.commit()
    return {"deleted": True}
