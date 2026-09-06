from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import GitHubRepo, MasterResume
from ..schemas import GitHubRepoOut
from ..services.github_monitor import (
    is_enabled, fetch_repos, fetch_repo_languages,
    fetch_readme_excerpt, generate_accept_token, generate_project_bullets,
)
from ..services.emailer import send_project_notification_email, EMAIL_ADDRESS

router = APIRouter(prefix="/api/github", tags=["github"])


@router.get("/status")
def github_status():
    """Check whether GitHub monitoring is configured."""
    return {
        "enabled": is_enabled(),
        "message": "GitHub monitoring is active." if is_enabled()
                   else "Set GITHUB_USERNAME (and optionally GITHUB_TOKEN) in .env to enable.",
    }


@router.post("/sync")
def sync_repos(db: Session = Depends(get_db)):
    """Manually trigger a GitHub repo sync — polls your repos, stores new ones,
    and sends email notifications for each new project detected."""
    if not is_enabled():
        raise HTTPException(
            status_code=400,
            detail="Set GITHUB_USERNAME in backend/.env to enable GitHub monitoring.",
        )

    existing_names = {r.repo_name for r in db.query(GitHubRepo.repo_name).all()}
    repos = fetch_repos()

    resume = db.query(MasterResume).filter(MasterResume.id == 1).first()
    user_email = resume.email if resume else EMAIL_ADDRESS

    added = 0
    emailed = 0
    for repo in repos:
        if repo["repo_name"] in existing_names:
            continue

        languages = fetch_repo_languages(repo["repo_name"])
        readme = fetch_readme_excerpt(repo["repo_name"])
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
        existing_names.add(repo["repo_name"])
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
                emailed += 1
            except Exception:
                pass

    db.commit()
    return {"found": len(repos), "added": added, "emailed": emailed}


@router.get("/repos", response_model=list[GitHubRepoOut])
def list_repos(db: Session = Depends(get_db)):
    """Lists all tracked GitHub repos with their status."""
    rows = db.query(GitHubRepo).order_by(GitHubRepo.id.desc()).all()
    return [GitHubRepoOut(
        id=r.id, repo_name=r.repo_name, repo_url=r.repo_url,
        description=r.description or "", languages=r.languages or [],
        stars=r.stars, last_pushed=r.last_pushed or "",
        status=r.status, auto_bullets=r.auto_bullets or [],
        created_date=r.created_date or "",
    ) for r in rows]


@router.get("/accept/{token}", response_class=HTMLResponse)
def accept_page(token: str, db: Session = Depends(get_db)):
    """HTML page served when user clicks the accept link in their email.
    Shows a preview of the project and a confirm button."""
    repo = db.query(GitHubRepo).filter(GitHubRepo.accept_token == token).first()
    if not repo:
        return HTMLResponse(
            "<html><body><h2>Link expired or invalid</h2>"
            "<p>This accept link is no longer valid. Manage your repos from the Launchpad dashboard.</p>"
            "</body></html>",
            status_code=404,
        )

    if repo.status == "accepted":
        return HTMLResponse(
            f"<html><body><h2>Already accepted ✅</h2>"
            f"<p><strong>{repo.repo_name}</strong> is already on your resume.</p>"
            f"</body></html>",
        )

    langs = ", ".join(repo.languages or [])
    bullets_html = "".join(f"<li>{b}</li>" for b in (repo.auto_bullets or []))

    html = f"""
    <html>
    <head><title>Accept project — Launchpad</title></head>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 40px auto; padding: 20px;">
      <h2>Add to your resume?</h2>
      <div style="background: #f8f9fa; border-radius: 8px; padding: 16px; margin: 20px 0;">
        <h3 style="margin: 0 0 8px;">
          <a href="{repo.repo_url}">{repo.repo_name}</a>
        </h3>
        <p>{repo.description or 'No description'}</p>
        <p><strong>Languages:</strong> {langs or 'N/A'} | <strong>Stars:</strong> ⭐ {repo.stars}</p>
      </div>
      <p><strong>These bullets will be added to your resume:</strong></p>
      <ul>{bullets_html}</ul>
      <p style="color:#666; font-size:13px;">You can edit them later from the Master Resume page.</p>
      <div style="display:flex; gap:12px; margin-top:16px;">
        <form method="POST" action="/api/github/repos/{repo.id}/accept?token={token}">
          <button type="submit" style="background:#22c55e; color:#fff; padding:12px 28px;
            border:none; border-radius:8px; font-size:15px; font-weight:600; cursor:pointer;">
            ✅ Accept — add to my resume
          </button>
        </form>
        <a href="/api/github/decline/{token}">
          <button type="button" style="background:#f3f4f6; color:#374151; padding:12px 28px;
            border:1px solid #d1d5db; border-radius:8px; font-size:15px; font-weight:600; cursor:pointer;">
            ✖ Decline
          </button>
        </a>
      </div>
    </body>
    </html>
    """
    return HTMLResponse(html)


@router.get("/decline/{token}", response_class=HTMLResponse)
def decline_repo_by_token(token: str, db: Session = Depends(get_db)):
    """Called when the user clicks 'Decline' either from the email or the
    preview page. Marks the repo as ignored — nothing is changed on the
    resume. Won't be suggested again unless reset from the dashboard."""
    repo = db.query(GitHubRepo).filter(GitHubRepo.accept_token == token).first()
    if not repo:
        return HTMLResponse(
            "<html><body><h2>Link expired or invalid</h2>"
            "<p>This link is no longer valid. Manage your repos from the Launchpad dashboard.</p>"
            "</body></html>",
            status_code=404,
        )

    if repo.status != "accepted":
        repo.status = "ignored"
        db.commit()

    return HTMLResponse(
        f"<html><body style='font-family: Arial, sans-serif; max-width:600px; margin:40px auto; text-align:center;'>"
        f"<h2>Declined</h2>"
        f"<p><strong>{repo.repo_name}</strong> will not be added to your resume. "
        f"Your resume was not changed.</p>"
        f"<p style='color:#666; font-size:13px;'>Changed your mind? You can bring it back "
        f"from the GitHub sync page in Launchpad.</p>"
        f"<a href='http://localhost:5500' style='display:inline-block; margin-top:20px; "
        f"background:#6b7280; color:#fff; padding:10px 24px; border-radius:8px; "
        f"text-decoration:none; font-weight:600;'>Open Launchpad →</a>"
        f"</body></html>",
    )


@router.post("/repos/{repo_id}/accept")
def accept_repo(repo_id: int, token: str = "", db: Session = Depends(get_db)):
    """Accepts a repo — adds it as a new Experience entry on the master resume.
    Called from the email accept page or the dashboard UI."""
    repo = db.query(GitHubRepo).filter(GitHubRepo.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repo not found")

    # Validate token if provided (from email link)
    if token and repo.accept_token and token != repo.accept_token:
        raise HTTPException(status_code=403, detail="Invalid accept token")

    if repo.status == "accepted":
        return HTMLResponse(
            f"<html><body><h2>Already accepted ✅</h2>"
            f"<p><strong>{repo.repo_name}</strong> is already on your resume.</p>"
            f"<p><a href='http://localhost:5500'>Go to Launchpad</a></p>"
            f"</body></html>",
        )

    # Add to master resume as a new experience block
    resume = db.query(MasterResume).filter(MasterResume.id == 1).first()
    if not resume:
        raise HTTPException(status_code=400, detail="Save your master resume first.")

    experience = list(resume.experience or [])
    project_name = repo.repo_name.split("/")[-1].replace("-", " ").replace("_", " ").title()

    experience.append({
        "heading": project_name,
        "bullets": repo.auto_bullets or [f"Developed {project_name} project"],
        "project_url": repo.repo_url,
    })

    resume.experience = experience
    repo.status = "accepted"
    db.commit()

    # Return a nice HTML page if accessed from browser (email link)
    return HTMLResponse(
        f"<html><body style='font-family: Arial, sans-serif; max-width:600px; margin:40px auto; text-align:center;'>"
        f"<h2>✅ Project added!</h2>"
        f"<p><strong>{repo.repo_name}</strong> has been added to your master resume.</p>"
        f"<p>Open Launchpad to review and edit the entry.</p>"
        f"<a href='http://localhost:5500' style='display:inline-block; margin-top:20px; "
        f"background:#3b82f6; color:#fff; padding:10px 24px; border-radius:8px; "
        f"text-decoration:none; font-weight:600;'>Open Launchpad →</a>"
        f"</body></html>",
    )


@router.post("/repos/{repo_id}/ignore")
def ignore_repo(repo_id: int, db: Session = Depends(get_db)):
    """Marks a repo as ignored — won't be suggested again."""
    repo = db.query(GitHubRepo).filter(GitHubRepo.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repo not found")
    repo.status = "ignored"
    db.commit()
    return {"ignored": True}


@router.post("/repos/{repo_id}/reset")
def reset_repo(repo_id: int, db: Session = Depends(get_db)):
    """Resets a repo back to pending status."""
    repo = db.query(GitHubRepo).filter(GitHubRepo.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repo not found")
    repo.status = "pending"
    db.commit()
    return {"status": "pending"}
