from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import PortalProfile, JobMatch, MasterResume
from ..schemas import PortalProfileCreate, PortalProfileOut, ConnectorApplyRequest, ConnectorApplyResult
from ..services.connectors.registry import get_connector, active_connectors, apply_to_job, CONNECTORS

router = APIRouter(prefix="/api/portals", tags=["portals"])

# Default portals to seed on first load
DEFAULT_PORTALS = [
    {"portal_name": "linkedin",    "display_name": "LinkedIn"},
    {"portal_name": "naukri",      "display_name": "Naukri"},
    {"portal_name": "indeed",      "display_name": "Indeed"},
    {"portal_name": "instahyre",   "display_name": "Instahyre"},
    {"portal_name": "internshala", "display_name": "Internshala"},
    {"portal_name": "wellfound",   "display_name": "Wellfound"},
    {"portal_name": "hackerrank",  "display_name": "HackerRank Jobs"},
    {"portal_name": "unstop",      "display_name": "Unstop"},
    {"portal_name": "lever",       "display_name": "Lever ATS"},
    {"portal_name": "greenhouse",  "display_name": "Greenhouse ATS"},
]


def _seed_defaults(db: Session):
    """Create default portal entries if the table is empty."""
    if db.query(PortalProfile).count() == 0:
        today = date.today().isoformat()
        for p in DEFAULT_PORTALS:
            db.add(PortalProfile(
                portal_name=p["portal_name"],
                display_name=p["display_name"],
                created_date=today,
                updated_date=today,
            ))
        db.commit()


@router.get("", response_model=list[PortalProfileOut])
def list_portals(db: Session = Depends(get_db)):
    """Lists all job portal profiles. Seeds defaults on first access."""
    _seed_defaults(db)
    rows = db.query(PortalProfile).order_by(PortalProfile.display_name).all()
    return [PortalProfileOut(
        id=r.id, portal_name=r.portal_name, display_name=r.display_name,
        profile_url=r.profile_url or "", username=r.username or "",
        extra_fields=r.extra_fields or {}, is_connector_enabled=bool(r.is_connector_enabled),
        created_date=r.created_date or "", updated_date=r.updated_date or "",
    ) for r in rows]


@router.get("/{portal_name}", response_model=PortalProfileOut)
def get_portal(portal_name: str, db: Session = Depends(get_db)):
    row = db.query(PortalProfile).filter(PortalProfile.portal_name == portal_name).first()
    if not row:
        raise HTTPException(status_code=404, detail="Portal not found")
    return PortalProfileOut(
        id=row.id, portal_name=row.portal_name, display_name=row.display_name,
        profile_url=row.profile_url or "", username=row.username or "",
        extra_fields=row.extra_fields or {}, is_connector_enabled=bool(row.is_connector_enabled),
        created_date=row.created_date or "", updated_date=row.updated_date or "",
    )


@router.put("/{portal_name}", response_model=PortalProfileOut)
def upsert_portal(portal_name: str, payload: PortalProfileCreate, db: Session = Depends(get_db)):
    """Create or update a portal profile."""
    row = db.query(PortalProfile).filter(PortalProfile.portal_name == portal_name).first()
    today = date.today().isoformat()
    if row:
        row.display_name = payload.display_name or row.display_name
        row.profile_url = payload.profile_url
        row.username = payload.username
        row.extra_fields = payload.extra_fields
        row.is_connector_enabled = 1 if payload.is_connector_enabled else 0
        row.updated_date = today
    else:
        row = PortalProfile(
            portal_name=portal_name,
            display_name=payload.display_name or portal_name.title(),
            profile_url=payload.profile_url,
            username=payload.username,
            extra_fields=payload.extra_fields,
            is_connector_enabled=1 if payload.is_connector_enabled else 0,
            created_date=today,
            updated_date=today,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return PortalProfileOut(
        id=row.id, portal_name=row.portal_name, display_name=row.display_name,
        profile_url=row.profile_url or "", username=row.username or "",
        extra_fields=row.extra_fields or {}, is_connector_enabled=bool(row.is_connector_enabled),
        created_date=row.created_date or "", updated_date=row.updated_date or "",
    )


@router.delete("/{portal_name}")
def delete_portal(portal_name: str, db: Session = Depends(get_db)):
    row = db.query(PortalProfile).filter(PortalProfile.portal_name == portal_name).first()
    if not row:
        raise HTTPException(status_code=404, detail="Portal not found")
    db.delete(row)
    db.commit()
    return {"deleted": True}


@router.get("/{portal_name}/connector-status")
def connector_status(portal_name: str, db: Session = Depends(get_db)):
    """Check whether a connector is available and configured for this portal."""
    row = db.query(PortalProfile).filter(PortalProfile.portal_name == portal_name).first()
    mod = get_connector(portal_name)
    if not mod:
        return {"portal_name": portal_name, "has_connector": False, "configured": False,
                "can_auto_apply": False, "message": "No connector available for this portal."}
    profile = {
        "portal_name": portal_name,
        "profile_url": row.profile_url if row else "",
        "username": row.username if row else "",
        "extra_fields": row.extra_fields if row else {},
    }
    configured = mod.is_configured(profile)
    return {
        "portal_name": portal_name,
        "has_connector": True,
        "configured": configured,
        "can_auto_apply": mod.can_auto_apply(),
        "message": "Ready" if configured else "Fill in your profile to enable this connector.",
    }


@router.get("/connectors/active")
def list_active_connectors(db: Session = Depends(get_db)):
    """Lists all connectors that are fully configured and ready."""
    profiles = db.query(PortalProfile).all()
    profile_dicts = [
        {"portal_name": p.portal_name, "profile_url": p.profile_url or "",
         "username": p.username or "", "extra_fields": p.extra_fields or {}}
        for p in profiles
    ]
    return active_connectors(profile_dicts)


@router.post("/connectors/apply", response_model=ConnectorApplyResult)
def apply_via_connector(payload: ConnectorApplyRequest, db: Session = Depends(get_db)):
    """Attempts to apply to a job match using the specified portal's connector."""
    match = db.query(JobMatch).filter(JobMatch.id == payload.match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Job match not found")

    resume = db.query(MasterResume).filter(MasterResume.id == 1).first()
    if not resume:
        raise HTTPException(status_code=400, detail="Save your master resume first.")

    portal = db.query(PortalProfile).filter(
        PortalProfile.portal_name == payload.portal_name
    ).first()

    job = {
        "company": match.company, "title": match.title, "url": match.url,
        "jd": match.jd, "tailored_summary": match.tailored_summary,
    }
    master = {
        "name": resume.name, "email": resume.email, "phone": resume.phone,
        "summary": resume.summary, "skills": resume.skills,
        "education": resume.education, "linkedin_url": resume.linkedin_url,
        "github_url": resume.github_url, "portfolio_url": resume.portfolio_url,
    }
    profile = {
        "portal_name": payload.portal_name,
        "profile_url": portal.profile_url if portal else "",
        "username": portal.username if portal else "",
        "extra_fields": portal.extra_fields if portal else {},
    }

    result = apply_to_job(payload.portal_name, job, master, profile)
    return ConnectorApplyResult(**result)
