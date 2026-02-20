# infrastructure/security/secure_email_service.py
"""
Secure email service that uses Windows Credential Manager for credentials.
This replaces the plaintext email service with secure credential storage.
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
from infrastructure.security.credential_manager import get_credential_manager

logger = get_logger("secure_email")

class SecureEmailService:
    """Email service using secure credential storage."""

    def __init__(self, credential_key: str = "email_smtp"):
        self.config = get_config().email
        self.credential_key = credential_key
        self._server = None
        self._credentials = None
        self._load_credentials()

    def _load_credentials(self):
        """Load credentials from secure storage."""
        try:
            cm = get_credential_manager()
            self._credentials = cm.get_credential(self.credential_key)

            if self._credentials:
                logger.info(f"Email credentials loaded from secure storage (key: {self.credential_key})")
            else:
                logger.warning(f"No email credentials found in secure storage (key: {self.credential_key})")
                logger.warning("Email functionality will be disabled")
                logger.info("Run 'python infrastructure/security/migrate_credentials.py' to migrate existing credentials")

        except Exception as e:
            logger.error(f"Failed to load email credentials: {e}")
            self._credentials = None

    def _get_smtp_credentials(self) -> tuple[str, str]:
        """Get SMTP username and password from secure storage."""
        if not self._credentials:
            raise ValueError("Email credentials not available")

        return self._credentials["username"], self._credentials["password"]

    def _get_smtp_config(self) -> dict:
        """Get SMTP configuration with fallback to config file."""
        # Use secure credentials if available
        if self._credentials and "metadata" in self._credentials:
            metadata = self._credentials["metadata"]
            return {
                "host": metadata.get("host", self.config.smtp_host),
                "port": metadata.get("port", self.config.smtp_port),
                "tls": metadata.get("tls", self.config.smtp_tls)
            }
        else:
            # Fallback to config file
            return {
                "host": self.config.smtp_host,
                "port": self.config.smtp_port,
                "tls": self.config.smtp_tls
            }

    def test_connection(self) -> bool:
        """
        Test SMTP connection using secure credentials.

        Returns:
            True if connection successful, False otherwise
        """
        if not self._credentials:
            logger.error("Cannot test connection: no credentials available")
            return False

        try:
            smtp_config = self._get_smtp_config()
            username, password = self._get_smtp_credentials()

            server = smtplib.SMTP(smtp_config["host"], smtp_config["port"], timeout=self.config.timeout)

            if smtp_config["tls"]:
                server.starttls()

            server.login(username, password)
            server.quit()

            logger.info("SMTP connection test successful")
            return True

        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False

    def send_email(self, subject: str, body: str, recipients: Optional[List[str]] = None,
                  attachments: Optional[List[Path]] = None, html: bool = False) -> bool:
        """
        Send email using secure credentials.

        Args:
            subject: Email subject
            body: Email body
            recipients: List of recipients (uses config default if None)
            attachments: List of file paths to attach
            html: Whether body is HTML

        Returns:
            True if sent successfully, False otherwise
        """
        if not self._credentials:
            logger.error("Cannot send email: no credentials available")
            return False

        if not recipients:
            recipients = self.config.recipients

        if not recipients:
            logger.error("No recipients specified")
            return False

        try:
            smtp_config = self._get_smtp_config()
            username, password = self._get_smtp_credentials()

            # Create message
            msg = MIMEMultipart()
            msg['From'] = username
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
                for attachment_path in attachments:
                    if attachment_path.exists():
                        with open(attachment_path, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            part.add_header('Content-Disposition',
                                          f'attachment; filename="{attachment_path.name}"')
                            msg.attach(part)
                    else:
                        logger.warning(f"Attachment not found: {attachment_path}")

            # Send email
            server = smtplib.SMTP(smtp_config["host"], smtp_config["port"], timeout=self.config.timeout)

            if smtp_config["tls"]:
                server.starttls()

            server.login(username, password)
            server.send_message(msg)
            server.quit()

            logger.info(f"Email sent successfully to {len(recipients)} recipients")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def send_report_email(self, report_path: Path, subject: Optional[str] = None) -> bool:
        """
        Send report email with attachment.

        Args:
            report_path: Path to report file
            subject: Email subject (auto-generated if None)

        Returns:
            True if sent successfully
        """
        if not subject:
            subject = f"HET Report - {report_path.stem}"

        body = f"Please find the attached report: {report_path.name}"

        return self.send_email(
            subject=subject,
            body=body,
            attachments=[report_path]
        )

    def update_credentials(self, username: str, password: str, metadata: Optional[dict] = None) -> bool:
        """
        Update email credentials in secure storage.

        Args:
            username: New SMTP username
            password: New SMTP password
            metadata: Additional metadata

        Returns:
            True if updated successfully
        """
        try:
            cm = get_credential_manager()
            success = cm.store_credential(self.credential_key, username, password, metadata)

            if success:
                logger.info("Email credentials updated successfully")
                # Reload credentials
                self._load_credentials()
                return True
            else:
                logger.error("Failed to update email credentials")
                return False

        except Exception as e:
            logger.error(f"Error updating email credentials: {e}")
            return False

# Global instance for backward compatibility
_secure_email_service = None

def get_secure_email_service(credential_key: str = "email_smtp") -> SecureEmailService:
    """Get the secure email service instance."""
    global _secure_email_service
    if _secure_email_service is None:
        _secure_email_service = SecureEmailService(credential_key)
    return _secure_email_service

# Backward compatibility alias
SecureEmailService = get_secure_email_service
<parameter name="filePath">d:\My App\infrastructure\security\secure_email_service.py