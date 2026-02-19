# app/services/email_service.py
"""
Email service for sending notifications and reports.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List, Optional, Union
import logging

from app.config.settings import get_config
from app.infrastructure.logger import get_logger

logger = get_logger("email")


class EmailService:
    """Service for sending emails."""

    def __init__(self):
        self.config = get_config().email
        self._server = None
        self._validate_config()

    def _validate_config(self):
        """Validate email configuration on startup."""
        required_fields = ['smtp_host', 'smtp_port', 'smtp_username', 'smtp_password']
        missing_fields = []

        for field in required_fields:
            value = getattr(self.config, field)
            if not value:
                missing_fields.append(field)

        if missing_fields:
            logger.warning(f"Email configuration incomplete. Missing: {', '.join(missing_fields)}")
            logger.warning("Email functionality will be disabled")
        else:
            logger.info("Email configuration validated successfully")

    def test_connection(self) -> bool:
        """
        Test SMTP connection.

        Returns:
            True if connection successful, False otherwise
        """
        # Check if credentials are configured
        if not self.config.smtp_username or not self.config.smtp_password:
            logger.warning("Email credentials not configured")
            return False
            
        try:
            server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port, timeout=10)

            if self.config.smtp_tls:
                server.starttls()

            server.login(self.config.smtp_username, self.config.smtp_password)
            server.quit()

            logger.info("SMTP connection test successful")
            return True

        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False

    def send_email(
        self,
        subject: str,
        body: str,
        recipients: Optional[List[str]] = None,
        html: bool = False,
        attachments: Optional[List[Union[str, Path]]] = None
    ) -> bool:
        """
        Send an email.

        Args:
            subject: Email subject
            body: Email body
            recipients: List of recipients (uses config default if None)
            html: Whether body is HTML
            attachments: List of file paths to attach

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.config.smtp_username or not self.config.smtp_password:
            logger.warning("Email not configured - skipping send")
            return False

        if recipients is None:
            recipients = self.config.recipients

        if not recipients:
            logger.warning("No recipients specified - skipping send")
            return False

        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.config.smtp_username
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject

            # Add body
            if html:
                from email.mime.text import MIMEText
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))

            # Add attachments
            if attachments:
                for attachment in attachments:
                    self._add_attachment(msg, Path(attachment))

            # Send email
            self._send_email(msg, recipients)
            logger.info(f"Email sent successfully to {len(recipients)} recipients")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def send_report(
        self,
        report_path: Union[str, Path],
        subject: Optional[str] = None,
        additional_body: str = ""
    ) -> bool:
        """
        Send a report file via email.

        Args:
            report_path: Path to report file
            subject: Email subject (auto-generated if None)
            additional_body: Additional text to include in body

        Returns:
            True if sent successfully, False otherwise
        """
        report_path = Path(report_path)

        if not report_path.exists():
            logger.error(f"Report file not found: {report_path}")
            return False

        if subject is None:
            subject = f"HET IT Control System Report - {report_path.name}"

        body = f"Automated report: {report_path.name}\n\n{additional_body}"

        return self.send_email(
            subject=subject,
            body=body,
            attachments=[report_path]
        )

    def _add_attachment(self, msg: MIMEMultipart, file_path: Path):
        """Add a file attachment to the email."""
        try:
            with open(file_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{file_path.name}"'
                )
                msg.attach(part)
        except Exception as e:
            logger.error(f"Failed to add attachment {file_path}: {e}")

    def _send_email(self, msg: MIMEMultipart, recipients: List[str]):
        """Send the email via SMTP."""
        try:
            self._server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port)
            if self.config.smtp_tls:
                self._server.starttls()
            self._server.login(self.config.smtp_username, self.config.smtp_password)
            text = msg.as_string()
            self._server.sendmail(self.config.smtp_username, recipients, text)
            self._server.quit()
        except Exception as e:
            raise e
        finally:
            if self._server:
                try:
                    self._server.quit()
                except:
                    pass


# Global email service instance
_email_service = None

def get_email_service() -> EmailService:
    """Get the global email service instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service

def send_report_email(
    subject: Optional[str] = None,
    body: str = "",
    report_path: Optional[Union[str, Path]] = None,
    html: bool = False
) -> bool:
    """
    Convenience function to send report emails.

    Args:
        subject: Email subject
        body: Email body
        report_path: Path to report file
        html: Whether body is HTML

    Returns:
        True if sent successfully, False otherwise
    """
    service = get_email_service()

    if report_path:
        return service.send_report(report_path, subject, body)
    else:
        return service.send_email(subject, body, html=html)