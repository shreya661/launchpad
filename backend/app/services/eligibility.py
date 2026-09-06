import re

# Phrases that signal a posting wants someone well beyond a fresher / 0-2 yr candidate,
# or has hard requirements a fresher with no backlogs still can't satisfy.
# Kept deliberately narrow — a false "ineligible" silently hides a job, so only match
# on fairly unambiguous language.
_EXPERIENCE_PATTERNS = [
    r"\b([3-9]|1[0-9])\s*\+?\s*-?\s*(?:to\s*\d+\s*)?years?\s*(?:of\s*)?experience\b",
    r"\bminimum\s+(?:of\s+)?([3-9]|1[0-9])\s*\+?\s*years?\b",
    r"\bat\s+least\s+([3-9]|1[0-9])\s*\+?\s*years?\b",
    r"\b([3-9]|1[0-9])\s*-\s*\d+\s*years?\s*experience\b",
]

_IMMEDIATE_JOINER_PATTERNS = [
    r"\bimmediate\s+joiners?\s+only\b",
    r"\bonly\s+immediate\s+joiners?\b",
]

_SENIOR_TITLE_PATTERNS = [
    r"\bsenior\b", r"\bstaff\s+engineer\b", r"\bprincipal\s+engineer\b",
    r"\blead\s+engineer\b", r"\barchitect\b",
]

_NO_BACKLOG_PATTERNS = [
    r"\bno\s+active\s+backlogs?\b", r"\bno\s+standing\s+backlogs?\b",
    r"\bwithout\s+(?:any\s+)?backlogs?\b",
]

_MIN_CGPA_PATTERN = re.compile(r"\bminimum\s+cgpa\s*(?:of\s*)?([\d.]+)", re.IGNORECASE)


def check_eligibility(jd_text: str, resume: dict) -> tuple[bool, str]:
    """Returns (eligible, reason). reason is empty when eligible.
    Conservative on purpose — only flags JDs with fairly explicit disqualifying language,
    since a fresher's own title rarely appears verbatim in a posting."""
    if not jd_text:
        return True, ""
    text = jd_text.lower()

    for pat in _EXPERIENCE_PATTERNS:
        if re.search(pat, text):
            return False, "Requires more experience than a fresher profile (years-of-experience line in JD)."

    for pat in _IMMEDIATE_JOINER_PATTERNS:
        if re.search(pat, text):
            return False, "Posting requires immediate joiners only."

    for pat in _SENIOR_TITLE_PATTERNS:
        if re.search(pat, text):
            return False, "Posting is titled for a senior/lead-level role."

    has_backlogs = bool(resume.get("has_backlogs"))
    if has_backlogs:
        for pat in _NO_BACKLOG_PATTERNS:
            if re.search(pat, text):
                return False, "Posting requires no active backlogs."

    cgpa_str = str(resume.get("cgpa") or "").strip()
    if cgpa_str:
        try:
            candidate_cgpa = float(cgpa_str)
            m = _MIN_CGPA_PATTERN.search(text)
            if m:
                required = float(m.group(1))
                if candidate_cgpa < required:
                    return False, f"Posting requires minimum CGPA {required}, below your {candidate_cgpa}."
        except ValueError:
            pass

    return True, ""
