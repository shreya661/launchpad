import os
import smtplib
from email.mime.text import MIMEText

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "")


def send_application_email(to_address: str, application: dict) -> None:
    if not EMAIL_ADDRESS or not EMAIL_APP_PASSWORD:
        raise RuntimeError(
            "EMAIL_ADDRESS / EMAIL_APP_PASSWORD not set in backend/.env — "
            "see README for how to generate a free Gmail app password."
        )

    subject = f"Applied: {application['title']} at {application['company']} [{application['code']}]"
    lines = [
        f"Tracking code: {application['code']}",
        f"Company: {application['company']}",
        f"Role: {application['title']}",
        f"Source: {application['source']}",
        f"Applied on: {application['applied_date']}",
        f"Match score: {application['match_score']}/100",
    ]
    if application.get("deadline"):
        lines.append(f"Deadline: {application['deadline']}")
    if application.get("url"):
        lines.append(f"Posting: {application['url']}")
    lines.append("")
    lines.append("Tailored summary used:")
    lines.append(application.get("tailored_summary", ""))

    body = "\n".join(lines)
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_address or EMAIL_ADDRESS

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, [msg["To"]], msg.as_string())


BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def send_project_notification_email(
    to_address: str,
    repo_name: str,
    repo_url: str,
    description: str,
    languages: list,
    stars: int,
    bullets: list,
    accept_token: str,
) -> None:
    """Sends an HTML email asking the user to accept or ignore a newly
    detected GitHub project.  The accept link hits the backend API which
    adds the project to the master resume automatically."""
    if not EMAIL_ADDRESS or not EMAIL_APP_PASSWORD:
        raise RuntimeError(
            "EMAIL_ADDRESS / EMAIL_APP_PASSWORD not set in backend/.env"
        )

    accept_url = f"{BACKEND_URL}/api/github/accept/{accept_token}"
    decline_url = f"{BACKEND_URL}/api/github/decline/{accept_token}"
    subject = f"🚀 New project detected: {repo_name.split('/')[-1]}"

    lang_str = ", ".join(languages) if languages else "Not specified"
    bullets_html = "".join(f"<li>{b}</li>" for b in bullets)

    html = f"""
    <html>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #f5f5f5;">
      <div style="background: #fff; border-radius: 12px; padding: 28px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
        <h2 style="margin: 0 0 6px; color: #1a1a1a;">New project detected 🎯</h2>
        <p style="color: #666; margin: 0 0 20px; font-size: 14px;">Launchpad found a new repo on your GitHub. Want to add it to your resume?</p>

        <div style="background: #f8f9fa; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
          <h3 style="margin: 0 0 8px; color: #2d2d2d;">
            <a href="{repo_url}" style="color: #0066cc; text-decoration: none;">{repo_name}</a>
          </h3>
          <p style="margin: 0 0 10px; color: #555; font-size: 14px;">{description or 'No description'}</p>
          <div style="font-size: 13px; color: #777;">
            <strong>Languages:</strong> {lang_str} &nbsp;|&nbsp; <strong>Stars:</strong> ⭐ {stars}
          </div>
        </div>

        <div style="margin-bottom: 20px;">
          <p style="font-size: 14px; color: #333; margin: 0 0 8px;"><strong>Auto-generated resume bullets:</strong></p>
          <ul style="margin: 0; padding-left: 20px; color: #444; font-size: 13px; line-height: 1.7;">
            {bullets_html}
          </ul>
          <p style="font-size: 12px; color: #999; margin: 8px 0 0;">You can edit these after accepting.</p>
        </div>

        <div style="text-align: center; margin-top: 24px;">
          <a href="{accept_url}" style="display: inline-block; background: #22c55e; color: #fff; padding: 12px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 15px; margin-right: 10px;">
            ✅ Accept &amp; add to resume
          </a>
          <a href="{decline_url}" style="display: inline-block; background: #f3f4f6; color: #374151; padding: 12px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 15px; border: 1px solid #d1d5db;">
            ✖ Decline
          </a>
        </div>

        <p style="text-align: center; margin-top: 16px; font-size: 12px; color: #aaa;">
          Accept opens a preview before anything changes. Decline marks it as skipped —
          your resume stays untouched either way unless you confirm Accept.
          You can also manage all detected repos from the Launchpad dashboard.
        </p>
      </div>
    </body>
    </html>
    """

    msg = MIMEText(html, "html")
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_address or EMAIL_ADDRESS

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, [msg["To"]], msg.as_string())


def send_status_notification_email(to_address: str, updates: list) -> None:
    """Sends a summary email whenever the inbox scanner detects a likely
    status change (interview/offer/rejected/etc) for one or more tracked
    applications. Always sent — good news or bad — so the user finds out
    either way and can correct it in the Tracker if the guess was wrong."""
    if not EMAIL_ADDRESS or not EMAIL_APP_PASSWORD:
        raise RuntimeError("EMAIL_ADDRESS / EMAIL_APP_PASSWORD not set in backend/.env")

    STATUS_LABEL = {
        "offer": "🎉 Offer",
        "interview": "📞 Interview",
        "assessment_scheduled": "📝 Assessment scheduled",
        "screen": "👀 Screening",
        "rejected": "❌ Not selected",
    }

    subject = f"Launchpad: {len(updates)} application status update(s) detected"
    rows_html = "".join(f"""
        <div style="padding:12px 0; border-bottom:1px solid #eee;">
          <strong>{u['company']}</strong> — {u['title']}<br>
          <span style="font-size:13px; color:#555;">
            {STATUS_LABEL.get(u['new_status'], u['new_status'])}
            (was: {u['old_status']})
          </span><br>
          <span style="font-size:12px; color:#999;">From email: "{u['subject']}"</span>
        </div>""" for u in updates)

    html = f"""
    <html>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
      <h2 style="margin:0 0 4px;">Status update{'s' if len(updates) != 1 else ''} detected</h2>
      <p style="color:#666; font-size:13px; margin:0 0 16px;">
        Launchpad scanned your inbox and thinks these applications changed status.
        This is a best-effort guess from email text — double check and correct it
        in the Tracker if it's wrong.
      </p>
      {rows_html}
    </body>
    </html>
    """

    msg = MIMEText(html, "html")
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_address or EMAIL_ADDRESS

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, [msg["To"]], msg.as_string())
