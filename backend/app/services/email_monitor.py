"""Inbox status scanner — reads your own inbox (via IMAP, using the same Gmail
app password already used for sending) to detect replies about applications
you're tracking, and notifies you whenever it thinks your status changed.

This only ever reads YOUR inbox for YOUR own tracked applications — it does
not send anything to anyone, and it never emails or contacts a third party.

Because classifying free-form email text is inherently fuzzy, this scanner is
deliberately conservative: it only updates status on a fairly confident keyword
match, and it ALWAYS sends you a notification either way so you can correct it
from the Tracker if it guessed wrong.
"""

import os
import re
import imaplib
import email as email_lib
import logging
from datetime import date
from email.header import decode_header

logger = logging.getLogger("launchpad.email_monitor")

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "")
IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
INBOX_SCAN_MAX_EMAILS = int(os.getenv("INBOX_SCAN_MAX_EMAILS", "50"))  # per pass, keeps this cheap

# Ordered so a stronger/more specific signal wins if an email matches more than one.
STATUS_KEYWORDS = [
    ("offer", [
        "pleased to offer", "offer letter", "excited to offer", "extend an offer",
        "welcome to the team", "welcome aboard",
    ]),
    ("interview", [
        "schedule an interview", "interview invitation", "interview with", "next round",
        "technical interview", "would like to interview", "schedule a call",
    ]),
    ("assessment_scheduled", [
        "online assessment", "coding assessment", "coding test", "assessment link",
        "hackerrank test", "take-home assignment", "complete the assessment",
    ]),
    ("screen", [
        "moved to the next stage", "shortlisted", "screening call", "recruiter screen",
    ]),
    ("rejected", [
        "regret to inform", "not moving forward", "unfortunately", "other candidates",
        "will not be proceeding", "decided not to move forward", "not selected",
    ]),
]


def is_enabled() -> bool:
    return bool(EMAIL_ADDRESS and EMAIL_APP_PASSWORD)


def _decode(value) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    out = []
    for text, enc in parts:
        if isinstance(text, bytes):
            out.append(text.decode(enc or "utf-8", errors="ignore"))
        else:
            out.append(text)
    return "".join(out)


def _get_body_text(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                try:
                    return part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="ignore"
                    )
                except Exception:
                    continue
        return ""
    try:
        return msg.get_payload(decode=True).decode(
            msg.get_content_charset() or "utf-8", errors="ignore"
        )
    except Exception:
        return ""


def _classify(text: str) -> str:
    lowered = text.lower()
    for status, phrases in STATUS_KEYWORDS:
        for phrase in phrases:
            if phrase in lowered:
                return status
    return ""


def _find_matching_application(db, subject: str, body: str, from_address: str):
    """Matches an email to a tracked Application by looking for the company
    name (case-insensitive) in the subject, body, or sender address/domain."""
    from ..models import Application

    haystack = f"{subject}\n{body}\n{from_address}".lower()
    apps = (
        db.query(Application)
        .filter(Application.status.notin_(["offer", "rejected"]))
        .all()
    )
    for app_row in apps:
        company = (app_row.company or "").strip().lower()
        if len(company) >= 3 and company in haystack:
            return app_row
    return None


def scan_inbox(db) -> dict:
    """Runs one pass over unseen inbox mail, matches against tracked
    applications, updates status on a confident match, and always emails a
    notification summarizing what it found."""
    from ..models import ScannedEmail
    from .emailer import send_status_notification_email

    if not is_enabled():
        return {"enabled": False, "scanned": 0, "matched": 0}

    try:
        conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        conn.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        conn.select("INBOX")
    except Exception as e:
        logger.error(f"IMAP login/connect failed: {e}")
        return {"enabled": True, "scanned": 0, "matched": 0, "error": str(e)}

    scanned = 0
    matched = 0
    updates = []

    try:
        status, data = conn.search(None, "UNSEEN")
        if status != "OK":
            return {"enabled": True, "scanned": 0, "matched": 0}

        ids = data[0].split()
        ids = ids[-INBOX_SCAN_MAX_EMAILS:]  # cap per pass — keeps this bounded and cheap

        for eid in ids:
            status, msg_data = conn.fetch(eid, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            msg = email_lib.message_from_bytes(raw)
            scanned += 1

            message_id = msg.get("Message-ID", "") or f"noid-{eid.decode()}"
            if db.query(ScannedEmail).filter(ScannedEmail.message_id == message_id).first():
                continue  # already processed in a previous pass

            subject = _decode(msg.get("Subject", ""))
            from_address = _decode(msg.get("From", ""))
            body = _get_body_text(msg)

            app_row = _find_matching_application(db, subject, body, from_address)
            detected_status = _classify(f"{subject}\n{body}") if app_row else ""

            record = ScannedEmail(
                message_id=message_id,
                application_id=app_row.id if app_row else None,
                detected_status=detected_status,
                subject=subject[:250],
                from_address=from_address[:250],
                scanned_date=date.today().isoformat(),
            )
            db.add(record)

            if app_row and detected_status:
                matched += 1
                old_status = app_row.status
                app_row.status = detected_status
                snippet = re.sub(r"\s+", " ", body).strip()[:300]
                app_row.status_note = f"Detected from email \"{subject}\": {snippet}"
                updates.append({
                    "company": app_row.company, "title": app_row.title,
                    "old_status": old_status, "new_status": detected_status,
                    "subject": subject,
                })

        db.commit()
    finally:
        try:
            conn.close()
            conn.logout()
        except Exception:
            pass

    if updates and EMAIL_ADDRESS:
        try:
            send_status_notification_email(EMAIL_ADDRESS, updates)
        except Exception as e:
            logger.warning(f"Status notification email failed: {e}")

    return {"enabled": True, "scanned": scanned, "matched": matched, "updates": updates}
