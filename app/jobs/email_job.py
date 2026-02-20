# app/jobs/email_job.py
"""
Email helper used by legacy scripts:
- supports send_report_email(subject, body, html=True)
Reads config from .env:
HET_SMTP_HOST, HET_SMTP_PORT, HET_SMTP_USERNAME, HET_SMTP_PASSWORD, HET_SMTP_TLS, HET_EMAIL_RECIPIENTS
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def send_report_email(subject: str, body: str, html: bool = True):
    host = _env("HET_SMTP_HOST", "smtp.gmail.com")
    port = int(_env("HET_SMTP_PORT", "587") or "587")
    user = _env("HET_SMTP_USERNAME")
    password = _env("HET_SMTP_PASSWORD")
    tls = _env("HET_SMTP_TLS", "true").lower() in ("1", "true", "yes", "y")
    recipients_raw = _env("HET_EMAIL_RECIPIENTS")

    if not user or not password or not recipients_raw:
        # Don't crash jobs if email not configured
        raise RuntimeError("Email not configured. Set HET_SMTP_USERNAME, HET_SMTP_PASSWORD, HET_EMAIL_RECIPIENTS in .env")

    recipients = [x.strip() for x in recipients_raw.split(",") if x.strip()]
    if not recipients:
        raise RuntimeError("HET_EMAIL_RECIPIENTS is empty")

    msg = MIMEMultipart()
    msg["From"] = user
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject

    mime = MIMEText(body, "html" if html else "plain", "utf-8")
    msg.attach(mime)

    with smtplib.SMTP(host, port, timeout=30) as server:
        if tls:
            server.starttls()
        server.login(user, password)
        server.sendmail(user, recipients, msg.as_string())

    return True