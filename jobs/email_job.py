# jobs/email_job.py
# Reliable HTML email sender using smtplib + email.message (no yagmail required)

import os
import smtplib
from email.message import EmailMessage
from datetime import datetime
from settings.secrets import SMTP_USER, SMTP_APP_PASSWORD, EMAIL_TO, SMTP_SERVER, SMTP_PORT

def send_report_email(subject: str = None, body: str = None, attachment_path: str = None, html: bool = True):
    """
    Send report via SMTP. Accepts HTML in body when html=True.
    Parameters:
        subject (str): Email subject. If None, generated with timestamp.
        body (str): Email body. If html=True, treated as HTML alternative.
        attachment_path (str): Optional path to attach a file (not used by default).
        html (bool): If True, send body as HTML alternative.
    """
    try:
        now = datetime.now()
        if not subject:
            subject = f"Combined Test Report - {now.strftime('%d-%b-%Y %H:%M:%S')}"
        if not body:
            body = f"<p>Automated report generated on {now.strftime('%d-%b-%Y %H:%M:%S')}</p>"

        # Build message
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = SMTP_USER
        msg['To'] = EMAIL_TO if isinstance(EMAIL_TO, str) else ", ".join(EMAIL_TO)

        # Plain text fallback
        plain_fallback = reformat_plain = None
        try:
            # crude plain text fallback: strip tags
            import re
            plain_fallback = re.sub('<[^<]+?>', '', body) if html else body
        except Exception:
            plain_fallback = body if not html else "Please view this email in HTML-capable client."

        msg.set_content(plain_fallback)

        if html:
            msg.add_alternative(body, subtype='html')

        # Attachment optional
        if attachment_path and os.path.exists(attachment_path):
            try:
                with open(attachment_path, 'rb') as af:
                    data = af.read()
                maintype = 'application'
                subtype = 'octet-stream'
                filename = os.path.basename(attachment_path)
                msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=filename)
            except Exception as e:
                print(f"[WARN] Attachment failed: {e}")

        # SMTP send
        server = SMTP_SERVER if 'SMTP_SERVER' in globals() else "smtp.gmail.com"
        port = SMTP_PORT if 'SMTP_PORT' in globals() else 587

        with smtplib.SMTP(server, port, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(SMTP_USER, SMTP_APP_PASSWORD)
            smtp.send_message(msg)

        print(f"[INFO] Email sent successfully: Subject='{subject}'")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")
        return False
