from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import BlacklistCompany
from ..schemas import BlacklistCreate, BlacklistOut

router = APIRouter(prefix="/api/blacklist", tags=["blacklist"])


@router.get("", response_model=list[BlacklistOut])
def list_blacklist(db: Session = Depends(get_db)):
    return db.query(BlacklistCompany).order_by(BlacklistCompany.company.asc()).all()


@router.post("", response_model=BlacklistOut)
def add_blacklist(payload: BlacklistCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(BlacklistCompany)
        .filter(BlacklistCompany.company.ilike(payload.company.strip()))
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Already blacklisted.")
    row = BlacklistCompany(
        company=payload.company.strip(), reason=payload.reason,
        added_date=date.today().isoformat(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{blacklist_id}")
def remove_blacklist(blacklist_id: int, db: Session = Depends(get_db)):
    row = db.query(BlacklistCompany).filter(BlacklistCompany.id == blacklist_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(row)
    db.commit()
    return {"deleted": True}
