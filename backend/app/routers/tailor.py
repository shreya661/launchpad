from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import MasterResume
from ..schemas import TailorRequest, TailorResult
from ..services.groq_client import tailor_resume
from ..services.tavily_client import research_company

router = APIRouter(prefix="/api/tailor", tags=["tailor"])


@router.post("", response_model=TailorResult)
def tailor(payload: TailorRequest, db: Session = Depends(get_db)):
    row = db.query(MasterResume).filter(MasterResume.id == 1).first()
    if not row:
        raise HTTPException(status_code=400, detail="Save your master resume first.")

    master_resume = {
        "name": row.name, "email": row.email, "phone": row.phone,
        "summary": row.summary, "skills": row.skills,
        "education": row.education, "certs": row.certs,
        "experience": row.experience or [],
    }

    company_notes = research_company(payload.company)

    try:
        result = tailor_resume(master_resume, payload.jd, company_notes)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Tailoring failed: {e}")

    return TailorResult(
        companySnapshot=company_notes[:600] if company_notes else "No reliable company info found.",
        matchScore=result.get("matchScore", 0),
        matchedKeywords=result.get("matchedKeywords", []),
        missingSkills=result.get("missingSkills", []),
        tailoredSummary=result.get("tailoredSummary", ""),
        tailoredBullets=result.get("tailoredBullets", []),
        suggestedFocus=result.get("suggestedFocus", ""),
    )
