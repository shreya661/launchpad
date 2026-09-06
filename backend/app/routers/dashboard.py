from collections import Counter
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Application

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    apps = db.query(Application).all()
    counts = Counter(a.status for a in apps)
    return {
        "total": len(apps),
        "applied": len(apps),
        "screen": counts.get("screen", 0),
        "interview": counts.get("interview", 0),
        "offer": counts.get("offer", 0),
        "rejected": counts.get("rejected", 0),
    }


@router.get("/timeline")
def timeline(db: Session = Depends(get_db)):
    apps = db.query(Application).all()
    by_date = Counter(a.applied_date for a in apps if a.applied_date)
    return [{"date": d, "count": c} for d, c in sorted(by_date.items())]


@router.get("/deadlines")
def deadlines(db: Session = Depends(get_db)):
    apps = (
        db.query(Application)
        .filter(Application.deadline.isnot(None))
        .order_by(Application.deadline.asc())
        .limit(5)
        .all()
    )
    return [
        {"code": a.code, "company": a.company, "title": a.title, "deadline": a.deadline}
        for a in apps
    ]
