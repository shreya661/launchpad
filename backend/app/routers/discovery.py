from collections import Counter
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import MasterResume, JobMatch, Application, BlacklistCompany
from ..services.job_sources.registry import search_all, SOURCES
from ..services.groq_client import tailor_resume
from ..services.eligibility import check_eligibility
from ..services.resume_export import build_resume_docx

router = APIRouter(prefix="/api/discover", tags=["discover"])


@router.post("/run")
def run_discovery(db: Session = Depends(get_db)):
    """Pulls fresh job postings matching your resume's skills/title from every
    enabled source (see GET /sources for what's active), skips blacklisted
    companies and clearly-ineligible JDs, dedups against what's already
    stored, scores the rest against your master resume, and stores the
    results as candidate matches. Does not apply to anything itself — you
    review and promote, UNLESS auto-apply is enabled (see /api/discover/auto-apply/status),
    in which case eligible Lever/Greenhouse matches get submitted right after this call."""
    resume = db.query(MasterResume).filter(MasterResume.id == 1).first()
    if not resume:
        raise HTTPException(status_code=400, detail="Save your master resume first.")

    top_skills = ", ".join([s.strip() for s in (resume.skills or "").split(",")[:6]])
    keywords = top_skills or "software engineer fresher"

    postings = search_all(keywords, results_per_source=15)

    if not postings:
        return {"found": 0, "message": "No results — no job sources are configured yet. Add ADZUNA_APP_ID/ADZUNA_APP_KEY (Remotive needs no key), or check GET /api/discover/sources for what's active."}

    existing_urls = {m.url for m in db.query(JobMatch.url).all()}
    existing_pairs = {
        (c.strip().lower(), t.strip().lower())
        for c, t in db.query(JobMatch.company, JobMatch.title).all()
    }
    blacklisted = {b.company.strip().lower() for b in db.query(BlacklistCompany).all()}

    master_resume_dict = {
        "name": resume.name, "email": resume.email, "phone": resume.phone,
        "summary": resume.summary, "skills": resume.skills,
        "education": resume.education, "certs": resume.certs,
        "cgpa": resume.cgpa, "has_backlogs": bool(resume.has_backlogs),
        "experience": resume.experience or [],
    }

    added = 0
    skipped_blacklist = 0
    skipped_ineligible = 0
    skipped_duplicate = 0
    for job in postings:
        if not job["url"] or job["url"] in existing_urls:
            continue
        pair_key = (job["company"].strip().lower(), job["title"].strip().lower())
        if pair_key in existing_pairs:
            skipped_duplicate += 1
            continue
        if job["company"].strip().lower() in blacklisted:
            skipped_blacklist += 1
            continue
        eligible, _reason = check_eligibility(job["jd"], master_resume_dict)
        if not eligible:
            skipped_ineligible += 1
            continue
        try:
            scored = tailor_resume(master_resume_dict, job["jd"])
        except Exception:
            continue
        row = JobMatch(
            source=job["source"], company=job["company"], title=job["title"],
            url=job["url"], location=job["location"], jd=job["jd"],
            match_score=scored.get("matchScore", 0),
            matched_keywords=scored.get("matchedKeywords", []),
            missing_skills=scored.get("missingSkills", []),
            key_skills=scored.get("keySkills", []),
            tailored_summary=scored.get("tailoredSummary", ""),
            tailored_bullets=scored.get("tailoredBullets", []),
            discovered_date=date.today().isoformat(),
        )
        db.add(row)
        existing_urls.add(job["url"])
        existing_pairs.add(pair_key)
        added += 1
    db.commit()

    from ..services.auto_apply import run_auto_apply
    auto_apply_result = run_auto_apply(db)

    return {
        "found": len(postings), "added": added,
        "skippedDuplicate": skipped_duplicate,
        "skippedBlacklist": skipped_blacklist,
        "skippedIneligible": skipped_ineligible,
        "autoApply": auto_apply_result,
    }


@router.get("/auto-apply/status")
def auto_apply_status():
    """Whether the zero-review auto-apply pipeline is on, and its current
    settings. Auto-apply only ever runs for Lever/Greenhouse (the only
    portals with legitimate public apply APIs) and only once you've filled
    in that portal's profile and enabled its connector on the Job Portals page."""
    from ..services.auto_apply import AUTO_APPLY_ENABLED, AUTO_APPLY_MIN_SCORE, AUTO_APPLY_ALLOWED_PORTALS
    return {
        "enabled": AUTO_APPLY_ENABLED,
        "minScore": AUTO_APPLY_MIN_SCORE,
        "allowedPortals": sorted(AUTO_APPLY_ALLOWED_PORTALS),
        "message": (
            "Auto-apply is ON. Matches scoring >= {}% from Lever/Greenhouse postings "
            "will be submitted automatically with no review step, provided that "
            "portal's connector is configured and enabled.".format(AUTO_APPLY_MIN_SCORE)
            if AUTO_APPLY_ENABLED else
            "Auto-apply is OFF. Set AUTO_APPLY_ENABLED=true in backend/.env to turn it on."
        ),
    }


@router.post("/auto-apply/run")
def auto_apply_run_now(db: Session = Depends(get_db)):
    """Manually triggers one pass of the auto-apply pipeline against
    already-discovered matches, without waiting for the next scheduled run."""
    from ..services.auto_apply import run_auto_apply
    return run_auto_apply(db)


@router.get("/sources")
def list_sources():
    """Shows every registered job source and whether it's currently active
    (i.e. its API key is set in .env). Add a new source by dropping an
    adapter file in app/services/job_sources/ and registering it in
    registry.py — no other code needs to change."""
    return [
        {"name": s["name"], "enabled": s["module"].is_enabled()}
        for s in SOURCES
    ]


@router.get("/matches")
def list_matches(db: Session = Depends(get_db)):
    rows = (
        db.query(JobMatch)
        .filter(JobMatch.dismissed == 0)
        .order_by(JobMatch.match_score.desc())
        .all()
    )
    return [
        {
            "id": r.id, "source": r.source, "company": r.company, "title": r.title,
            "url": r.url, "location": r.location, "matchScore": r.match_score,
            "matchedKeywords": r.matched_keywords, "missingSkills": r.missing_skills,
            "keySkills": r.key_skills or [],
            "tailoredSummary": r.tailored_summary, "tailoredBullets": r.tailored_bullets,
            "discoveredDate": r.discovered_date,
        }
        for r in rows
    ]


@router.get("/skill-gaps")
def skill_gaps(db: Session = Depends(get_db)):
    """Aggregates missingSkills across all non-dismissed matches into a ranked
    'what to learn next' list."""
    rows = db.query(JobMatch).filter(JobMatch.dismissed == 0).all()
    counter = Counter()
    for r in rows:
        for skill in (r.missing_skills or []):
            counter[skill.strip()] += 1
    ranked = [{"skill": s, "count": c} for s, c in counter.most_common(25)]
    return {"totalMatches": len(rows), "gaps": ranked}


@router.get("/matches/{match_id}/resume.docx")
def download_match_resume(match_id: int, db: Session = Depends(get_db)):
    """ATS-friendly .docx tailored to this discovered match's JD, before you even apply."""
    m = db.query(JobMatch).filter(JobMatch.id == match_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Match not found")
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
    buf = build_resume_docx(master, m.tailored_summary, m.tailored_bullets)
    filename = f"{m.company.replace(' ', '_')}_{m.title.replace(' ', '_')}_resume.docx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/matches/{match_id}/dismiss")
def dismiss_match(match_id: int, db: Session = Depends(get_db)):
    row = db.query(JobMatch).filter(JobMatch.id == match_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Match not found")
    row.dismissed = 1
    db.commit()
    return {"dismissed": True}


@router.post("/matches/{match_id}/promote")
def promote_match(match_id: int, db: Session = Depends(get_db)):
    """Turns a discovered match into a tracked application. This is the
    'apply' step — it hands you the real posting URL; it does not submit
    anything on your behalf."""
    m = db.query(JobMatch).filter(JobMatch.id == match_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Match not found")

    count = db.query(Application).count()
    code = f"APP-{count + 1:03d}"
    app_row = Application(
        code=code, company=m.company, title=m.title, source=m.source, url=m.url,
        deadline=None, applied_date=date.today().isoformat(), status="applied",
        match_score=m.match_score, company_snapshot="",
        tailored_summary=m.tailored_summary, tailored_bullets=m.tailored_bullets,
        missing_skills=m.missing_skills, key_skills=m.key_skills or [], jd=m.jd,
    )
    db.add(app_row)
    m.dismissed = 1
    db.commit()
    db.refresh(app_row)
    return {"applicationId": app_row.id, "code": app_row.code}


@router.get("/matches/{match_id}/interview-prep")
def interview_prep(match_id: int, db: Session = Depends(get_db)):
    """Returns everything you need to prepare for the interview for this job:
    - keySkills:        top 10 technical skills this role demands (study guide)
    - matchedKeywords:  skills from the JD you already have
    - missingSkills:    skills the JD wants that you currently lack
    - suggestedFocus:   which of your existing projects to lead with
    - tailoredBullets:  ATS-ready bullets to use in your resume for this role
    """
    m = db.query(JobMatch).filter(JobMatch.id == match_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Match not found")
    return {
        "id": m.id,
        "company": m.company,
        "title": m.title,
        "url": m.url,
        "matchScore": m.match_score,
        "keySkills": m.key_skills or [],
        "matchedKeywords": m.matched_keywords or [],
        "missingSkills": m.missing_skills or [],
        "tailoredBullets": m.tailored_bullets or [],
        "tailoredSummary": m.tailored_summary or "",
        "jdExcerpt": (m.jd or "")[:500],   # first 500 chars of JD as context
    }
