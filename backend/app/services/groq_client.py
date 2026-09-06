import os
import json
import requests

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
# Groq's free tier — see https://console.groq.com for current model list/limits.
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

SYSTEM_PROMPT = """You are a resume-tailoring assistant for an Indian CS fresher (0-2 years experience) job search.
You will be given the candidate's master resume (JSON, ground truth), a job description, and optionally a
short block of company research notes.

Respond with ONLY a JSON object, no preamble, no markdown fences, matching exactly this shape:
{
  "matchScore": <integer 0-100>,
  "matchedKeywords": [<strings, up to 8>],
  "missingSkills": [<strings, up to 6, skills in the JD not present in the resume>],
  "tailoredSummary": "<2-3 sentence resume summary tailored to this JD, using ONLY facts present in the master resume>",
  "tailoredBullets": [<3-5 rewritten bullet points pulled from the candidate's real experience/projects, reworded to mirror JD keywords, each starting with an action verb, NEVER inventing metrics or skills not in the master resume>],
  "suggestedFocus": "<one sentence on which existing project or experience to lead with for this JD>"
}
Rules: never invent companies, skills, metrics, or years of experience beyond what's in the master resume.
If the JD wants something the candidate lacks, list it in missingSkills instead of fabricating it."""


def tailor_resume(master_resume: dict, jd: str, company_notes: str = "") -> dict:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set. Add it to backend/.env")

    user_content = (
        f"MASTER RESUME:\n{json.dumps(master_resume)}\n\n"
        f"COMPANY RESEARCH NOTES:\n{company_notes or 'none available'}\n\n"
        f"JOB DESCRIPTION:\n{jd}"
    )

    resp = requests.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    raw = data["choices"][0]["message"]["content"]
    return json.loads(raw)


REACHOUT_SYSTEM_PROMPT = """You draft short, warm, non-cringey LinkedIn cold-reachout messages for an
Indian CS fresher (0-2 years experience) job search. You will be given the candidate's master resume
(JSON, ground truth), the name/role of the person they're messaging, the target company, and optionally
a job title or JD excerpt.

Respond with ONLY the message text — no preamble, no markdown, no subject line, no quotation marks around it.
Rules:
- Under 100 words. LinkedIn connection notes and InMail both read best short.
- Mention ONE concrete, true detail from the master resume (a real project or skill) — never invent one.
- Ask for something small and specific (a referral, 15 minutes, or to keep them in mind) — never ask them
  to "give a job."
- Warm and human tone, not a form letter. No emojis. No exclamation-point stacking.
- Never fabricate a shared connection, mutual acquaintance, or prior interaction that wasn't stated."""


def draft_cold_message(master_resume: dict, contact_name: str, company: str,
                        role_title: str = "", target_job_title: str = "", jd: str = "") -> str:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set. Add it to backend/.env")

    user_content = (
        f"MASTER RESUME:\n{json.dumps(master_resume)}\n\n"
        f"CONTACT: {contact_name}, {role_title or 'unknown role'} at {company}\n"
        f"TARGET ROLE: {target_job_title or 'not specified'}\n"
        f"JD EXCERPT (optional): {jd[:1500] if jd else 'none provided'}"
    )

    resp = requests.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": REACHOUT_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.5,
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()
