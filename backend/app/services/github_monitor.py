"""GitHub repo monitoring — polls your GitHub repos periodically, detects new ones,
generates ATS-friendly bullet points via the LLM, and sends an email notification
with an accept/ignore link."""

import os
import uuid
import json
import requests
from datetime import date

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "")
GITHUB_API = "https://api.github.com"


def is_enabled() -> bool:
    return bool(GITHUB_USERNAME)


def fetch_repos() -> list[dict]:
    """Fetches all repos for the configured GitHub user.
    Uses token auth if available (sees private repos), falls back to public."""
    if not GITHUB_USERNAME:
        return []

    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    repos = []
    page = 1
    while True:
        try:
            if GITHUB_TOKEN:
                # Authenticated — gets all repos (public + private)
                url = f"{GITHUB_API}/user/repos?per_page=100&page={page}&sort=pushed"
            else:
                # Public only
                url = f"{GITHUB_API}/users/{GITHUB_USERNAME}/repos?per_page=100&page={page}&sort=pushed"

            resp = requests.get(url, headers=headers, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break
            for r in data:
                repos.append({
                    "repo_name": r.get("full_name", ""),
                    "repo_url": r.get("html_url", ""),
                    "description": r.get("description") or "",
                    "language": r.get("language") or "",
                    "stars": r.get("stargazers_count", 0),
                    "last_pushed": (r.get("pushed_at") or "")[:10],
                    "fork": r.get("fork", False),
                })
            page += 1
            if len(data) < 100:
                break
        except Exception:
            break

    # Skip forks by default — they're usually not your own projects
    return [r for r in repos if not r["fork"]]


def fetch_repo_languages(repo_full_name: str) -> list[str]:
    """Fetches the languages used in a repo."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    try:
        resp = requests.get(f"{GITHUB_API}/repos/{repo_full_name}/languages",
                            headers=headers, timeout=10)
        resp.raise_for_status()
        return list(resp.json().keys())
    except Exception:
        return []


def fetch_readme_excerpt(repo_full_name: str, max_chars: int = 1500) -> str:
    """Fetches the first portion of a repo's README."""
    headers = {"Accept": "application/vnd.github.v3.raw"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    try:
        resp = requests.get(f"{GITHUB_API}/repos/{repo_full_name}/readme",
                            headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.text[:max_chars]
    except Exception:
        pass
    return ""


def generate_accept_token() -> str:
    return uuid.uuid4().hex


def generate_project_bullets(repo_name: str, description: str,
                              languages: list, readme_excerpt: str) -> list[str]:
    """Uses the Groq LLM to generate ATS-friendly experience bullets
    from a GitHub repo's metadata."""
    from .groq_client import GROQ_API_KEY, GROQ_URL, GROQ_MODEL

    if not GROQ_API_KEY:
        # Fallback: simple bullets from description
        bullets = []
        if description:
            bullets.append(f"Built {repo_name.split('/')[-1]}: {description}")
        if languages:
            bullets.append(f"Implemented using {', '.join(languages)}")
        return bullets or [f"Developed {repo_name.split('/')[-1]} project"]

    system_prompt = """You generate ATS-friendly resume bullet points from a GitHub project.
Given the repo name, description, languages, and a README excerpt, produce 3-5 bullet points.
Each bullet must:
- Start with a strong action verb (Built, Developed, Implemented, Designed, Engineered, etc.)
- Be factual — only use information visible in the provided metadata
- Be concise (one line each)
- Mention specific technologies/languages used
- NOT invent metrics, users, or outcomes not evident from the description/README

Respond with ONLY a JSON array of strings, no preamble, no markdown."""

    user_content = (
        f"REPO: {repo_name}\n"
        f"DESCRIPTION: {description or 'none'}\n"
        f"LANGUAGES: {', '.join(languages) if languages else 'unknown'}\n"
        f"README EXCERPT:\n{readme_excerpt or 'none available'}"
    )

    try:
        resp = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "temperature": 0.3,
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"]
        parsed = json.loads(raw)
        # Handle both {"bullets": [...]} and plain [...]
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "bullets" in parsed:
            return parsed["bullets"]
        return [str(parsed)]
    except Exception:
        bullets = []
        if description:
            bullets.append(f"Built {repo_name.split('/')[-1]}: {description}")
        if languages:
            bullets.append(f"Implemented using {', '.join(languages)}")
        return bullets or [f"Developed {repo_name.split('/')[-1]} project"]
