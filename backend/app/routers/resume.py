from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import MasterResume
from ..schemas import MasterResumeSchema
from ..services.resume_export import build_resume_docx

router = APIRouter(prefix="/api/resume", tags=["resume"])


def _get_or_create(db: Session) -> MasterResume:
    row = db.query(MasterResume).filter(MasterResume.id == 1).first()
    if not row:
        row = MasterResume(id=1)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("", response_model=MasterResumeSchema)
def get_resume(db: Session = Depends(get_db)):
    row = _get_or_create(db)
    return MasterResumeSchema(
        name=row.name, email=row.email, phone=row.phone, summary=row.summary,
        skills=row.skills, education=row.education, certs=row.certs,
        linkedin_url=row.linkedin_url, github_url=row.github_url, portfolio_url=row.portfolio_url,
        cgpa=row.cgpa, has_backlogs=bool(row.has_backlogs), batch_year=row.batch_year,
        experience=row.experience or [],
    )


@router.put("", response_model=MasterResumeSchema)
def update_resume(payload: MasterResumeSchema, db: Session = Depends(get_db)):
    row = _get_or_create(db)
    row.name = payload.name
    row.email = payload.email
    row.phone = payload.phone
    row.summary = payload.summary
    row.skills = payload.skills
    row.education = payload.education
    row.certs = payload.certs
    row.linkedin_url = payload.linkedin_url
    row.github_url = payload.github_url
    row.portfolio_url = payload.portfolio_url
    row.cgpa = payload.cgpa
    row.has_backlogs = 1 if payload.has_backlogs else 0
    row.batch_year = payload.batch_year
    row.experience = [e.dict() for e in payload.experience]
    db.commit()
    db.refresh(row)
    return payload


@router.get("/download")
def download_resume(db: Session = Depends(get_db)):
    """ATS-friendly .docx of your master resume as-is (no JD tailoring)."""
    row = _get_or_create(db)
    if not row.name:
        raise HTTPException(status_code=400, detail="Save your master resume first.")
    master = {
        "name": row.name, "email": row.email, "phone": row.phone,
        "linkedin_url": row.linkedin_url, "github_url": row.github_url,
        "portfolio_url": row.portfolio_url, "summary": row.summary, "skills": row.skills,
        "education": row.education, "certs": row.certs, "cgpa": row.cgpa,
        "experience": row.experience or [],
    }
    buf = build_resume_docx(master)
    filename = f"{(row.name or 'resume').replace(' ', '_')}_resume.docx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
