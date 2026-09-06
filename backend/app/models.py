from sqlalchemy import Column, Integer, String, Text, JSON
from .database import Base


class MasterResume(Base):
    __tablename__ = "master_resume"

    id = Column(Integer, primary_key=True, default=1)
    name = Column(String, default="")
    email = Column(String, default="")
    phone = Column(String, default="")
    summary = Column(Text, default="")
    skills = Column(Text, default="")
    education = Column(String, default="")
    certs = Column(String, default="")
    linkedin_url = Column(String, default="")
    github_url = Column(String, default="")
    portfolio_url = Column(String, default="")
    cgpa = Column(String, default="")
    has_backlogs = Column(Integer, default=0)  # 0/1 boolean flag
    batch_year = Column(String, default="")
    experience = Column(JSON, default=list)  # [{heading, bullets: [], project_url: ""}]


class JobMatch(Base):
    __tablename__ = "job_matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String)  # Adzuna, RemoteOK, etc.
    company = Column(String)
    title = Column(String)
    url = Column(String)
    location = Column(String, default="")
    jd = Column(Text, default="")
    match_score = Column(Integer, default=0)
    matched_keywords = Column(JSON, default=list)
    missing_skills = Column(JSON, default=list)
    key_skills = Column(JSON, default=list)     # top skills from JD for interview prep
    tailored_summary = Column(Text, default="")
    tailored_bullets = Column(JSON, default=list)
    discovered_date = Column(String)
    dismissed = Column(Integer, default=0)  # 0/1 boolean flag


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, unique=True, index=True)
    company = Column(String)
    title = Column(String)
    source = Column(String)
    url = Column(String, nullable=True)
    deadline = Column(String, nullable=True)  # ISO date string
    applied_date = Column(String)  # ISO date string
    status = Column(String, default="applied")  # applied/screen/interview/offer/rejected
    match_score = Column(Integer, default=0)
    company_snapshot = Column(Text, default="")
    tailored_summary = Column(Text, default="")
    tailored_bullets = Column(JSON, default=list)
    missing_skills = Column(JSON, default=list)
    key_skills = Column(JSON, default=list)           # top skills from JD for interview prep
    jd = Column(Text, default="")
    assessment_date = Column(String, nullable=True)  # ISO date string, for OA/aptitude test tracking
    auto_applied = Column(Integer, default=0)         # 0/1 — was this submitted by the auto-apply pipeline?
    status_note = Column(Text, default="")            # last detected status-change snippet from inbox scan


class BlacklistCompany(Base):
    __tablename__ = "blacklist_companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company = Column(String, unique=True, index=True)
    reason = Column(String, default="")
    added_date = Column(String)


class ReferralContact(Base):
    __tablename__ = "referral_contacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    company = Column(String)
    role_title = Column(String, default="")  # their role, e.g. "Engineering Manager"
    linkedin_url = Column(String, default="")
    target_job_title = Column(String, default="")  # the role you're reaching out about
    message_draft = Column(Text, default="")
    message_sent_date = Column(String, nullable=True)
    status = Column(String, default="not_sent")  # not_sent/sent/replied/no_response
    notes = Column(Text, default="")
    created_date = Column(String)


class PortalProfile(Base):
    __tablename__ = "portal_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portal_name = Column(String, unique=True, index=True)   # "linkedin", "naukri", etc.
    display_name = Column(String, default="")                # "LinkedIn", "Naukri"
    profile_url = Column(String, default="")                 # your profile link on that portal
    username = Column(String, default="")                    # login email/username
    extra_fields = Column(JSON, default=dict)                # portal-specific fields
    is_connector_enabled = Column(Integer, default=0)        # 0/1 boolean flag
    created_date = Column(String)
    updated_date = Column(String)


class GitHubRepo(Base):
    __tablename__ = "github_repos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo_name = Column(String, unique=True, index=True)      # "user/repo-name"
    repo_url = Column(String, default="")
    description = Column(Text, default="")
    languages = Column(JSON, default=list)                   # ["Python", "JavaScript"]
    stars = Column(Integer, default=0)
    last_pushed = Column(String, default="")                 # ISO date
    status = Column(String, default="pending")               # pending/accepted/ignored
    accept_token = Column(String, default="")                # unique token for email accept link
    auto_bullets = Column(JSON, default=list)                # LLM-generated ATS bullets
    created_date = Column(String)


class ScannedEmail(Base):
    """Tracks which inbox messages the status-scanner has already processed,
    so the same email never triggers a duplicate status update/notification."""
    __tablename__ = "scanned_emails"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String, unique=True, index=True)   # IMAP Message-ID header
    application_id = Column(Integer, nullable=True)         # matched Application, if any
    detected_status = Column(String, default="")            # status the scan inferred, if any
    subject = Column(String, default="")
    from_address = Column(String, default="")
    scanned_date = Column(String, default="")
