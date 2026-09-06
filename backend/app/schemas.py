from typing import List, Optional
from pydantic import BaseModel


class ExperienceBlock(BaseModel):
    heading: str
    bullets: List[str] = []
    project_url: str = ""  # optional GitHub/live link for this project


class MasterResumeSchema(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    summary: str = ""
    skills: str = ""
    education: str = ""
    certs: str = ""
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""
    cgpa: str = ""
    has_backlogs: bool = False
    batch_year: str = ""
    experience: List[ExperienceBlock] = []

    class Config:
        from_attributes = True


class TailorRequest(BaseModel):
    company: str
    title: str
    jd: str


class TailorResult(BaseModel):
    companySnapshot: str = ""
    matchScore: int = 0
    matchedKeywords: List[str] = []
    missingSkills: List[str] = []
    tailoredSummary: str = ""
    tailoredBullets: List[str] = []
    suggestedFocus: str = ""


class ApplicationCreate(BaseModel):
    company: str
    title: str
    source: str
    url: Optional[str] = None
    deadline: Optional[str] = None
    jd: str = ""
    matchScore: int = 0
    companySnapshot: str = ""
    tailoredSummary: str = ""
    tailoredBullets: List[str] = []
    missingSkills: List[str] = []


class ApplicationStatusUpdate(BaseModel):
    status: str


class AssessmentDateUpdate(BaseModel):
    assessment_date: Optional[str] = None  # ISO date string, or null to clear


class ApplicationOut(BaseModel):
    id: int
    code: str
    company: str
    title: str
    source: str
    url: Optional[str]
    deadline: Optional[str]
    applied_date: str
    status: str
    match_score: int
    company_snapshot: str
    tailored_summary: str
    tailored_bullets: List[str]
    missing_skills: List[str]
    jd: str
    assessment_date: Optional[str] = None
    auto_applied: bool = False
    status_note: str = ""

    class Config:
        from_attributes = True


class BlacklistCreate(BaseModel):
    company: str
    reason: str = ""


class BlacklistOut(BaseModel):
    id: int
    company: str
    reason: str
    added_date: str

    class Config:
        from_attributes = True


class ReferralCreate(BaseModel):
    name: str
    company: str
    role_title: str = ""
    linkedin_url: str = ""
    target_job_title: str = ""
    notes: str = ""


class ReferralUpdate(BaseModel):
    status: Optional[str] = None
    message_draft: Optional[str] = None
    message_sent_date: Optional[str] = None
    notes: Optional[str] = None


class ReferralDraftRequest(BaseModel):
    name: str
    company: str
    role_title: str = ""
    target_job_title: str = ""
    jd: str = ""  # optional JD text to make the message more specific


class BulkReferralItem(BaseModel):
    name: str
    company: str
    role_title: str = ""
    linkedin_url: str = ""
    target_job_title: str = ""


class BulkReferralDraftRequest(BaseModel):
    contacts: List[BulkReferralItem]
    jd: str = ""  # optional, applied to every contact in the batch


class ReferralOut(BaseModel):
    id: int
    name: str
    company: str
    role_title: str
    linkedin_url: str
    target_job_title: str
    message_draft: str
    message_sent_date: Optional[str]
    status: str
    notes: str
    created_date: str

    class Config:
        from_attributes = True


class BulkReferralResultItem(BaseModel):
    name: str
    company: str
    ok: bool
    referral: Optional[ReferralOut] = None
    error: str = ""


# --- Portal profiles ---

class PortalProfileCreate(BaseModel):
    portal_name: str
    display_name: str = ""
    profile_url: str = ""
    username: str = ""
    extra_fields: dict = {}
    is_connector_enabled: bool = False


class PortalProfileOut(BaseModel):
    id: int
    portal_name: str
    display_name: str
    profile_url: str
    username: str
    extra_fields: dict
    is_connector_enabled: bool
    created_date: str
    updated_date: str

    class Config:
        from_attributes = True


class ConnectorApplyRequest(BaseModel):
    match_id: int
    portal_name: str


class ConnectorApplyResult(BaseModel):
    applied: bool = False
    method: str = "manual"    # "auto" or "manual"
    apply_url: str = ""
    message: str = ""


# --- GitHub repos ---

class GitHubRepoOut(BaseModel):
    id: int
    repo_name: str
    repo_url: str
    description: str
    languages: list
    stars: int
    last_pushed: str
    status: str
    auto_bullets: list
    created_date: str

    class Config:
        from_attributes = True
