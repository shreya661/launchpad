import csv
import io
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Application, MasterResume
from ..schemas import ApplicationCreate, ApplicationOut, ApplicationStatusUpdate, AssessmentDateUpdate
from ..services.resume_export import build_resume_docx

router = APIRouter(prefix="/api/applications", tags=["applications"])


@router.get("", response_model=list[ApplicationOut])
def list_applications(db: Session = Depends(get_db)):
    return db.query(Application).order_by(Application.id.desc()).all()


@router.post("", response_model=ApplicationOut)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db)):
    count = db.query(Application).count()
    code = f"APP-{count + 1:03d}"
    row = Application(
        code=code,
        company=payload.company,
        title=payload.title,
        source=payload.source,
        url=payload.url,
        deadline=payload.deadline,
        applied_date=date.today().isoformat(),
        status="applied",
        match_score=payload.matchScore,
        company_snapshot=payload.companySnapshot,
        tailored_summary=payload.tailoredSummary,
        tailored_bullets=payload.tailoredBullets,
        missing_skills=payload.missingSkills,
        jd=payload.jd,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/{app_id}/status", response_model=ApplicationOut)
def update_status(app_id: int, payload: ApplicationStatusUpdate, db: Session = Depends(get_db)):
    row = db.query(Application).filter(Application.id == app_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")
    row.status = payload.status
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{app_id}")
def delete_application(app_id: int, db: Session = Depends(get_db)):
    row = db.query(Application).filter(Application.id == app_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")
    db.delete(row)
    db.commit()
    return {"deleted": True}


@router.patch("/{app_id}/assessment", response_model=ApplicationOut)
def update_assessment_date(app_id: int, payload: AssessmentDateUpdate, db: Session = Depends(get_db)):
    """Sets/clears the OA / aptitude-test date for TCS/Infosys/Wipro-style fixed-date drives."""
    row = db.query(Application).filter(Application.id == app_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")
    row.assessment_date = payload.assessment_date
    db.commit()
    db.refresh(row)
    return row


@router.get("/export.csv")
def export_applications_csv(db: Session = Depends(get_db)):
    rows = db.query(Application).order_by(Application.id.asc()).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "code", "company", "title", "source", "url", "status", "match_score",
        "applied_date", "deadline", "assessment_date", "missing_skills",
    ])
    for r in rows:
        writer.writerow([
            r.code, r.company, r.title, r.source, r.url or "", r.status, r.match_score,
            r.applied_date, r.deadline or "", r.assessment_date or "",
            "; ".join(r.missing_skills or []),
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="applications.csv"'},
    )


@router.get("/{app_id}/resume.docx")
def download_application_resume(app_id: int, db: Session = Depends(get_db)):
    """ATS-friendly .docx tailored to this specific application's JD — reuses the
    tailored summary/bullets already stored when it was scored, so nothing is re-invented."""
    app_row = db.query(Application).filter(Application.id == app_id).first()
    if not app_row:
        raise HTTPException(status_code=404, detail="Application not found")
    resume = db.query(MasterResume).filter(MasterResume.id == 1).first()
    if not resume:
        raise HTTPException(status_code=400, detail="Save your master resume first.")
    master = {
        "name": resume.name, "email": resume.email, "phone": resume.phone,
        "linkedin_url": resume.linkedin_url, "github_url": resume.github_url,
        "portfolio_url": resume.portfolio_url, "summary": resume.summary, "skills": resume.skills,
        "education": resume.education, "certs": resume.certs, "cgpa": resume.cgpa,
        "experience": resume.experience or [],
    }
    buf = build_resume_docx(master, app_row.tailored_summary, app_row.tailored_bullets)
    filename = f"{app_row.code}_{app_row.company.replace(' ', '_')}_resume.docx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
