#!/usr/bin/env python3
"""
HET IT Control System - First-Time Setup Wizard
GUI wizard for initial configuration
"""

import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from PySide6.QtWidgets import (
        QApplication, QWizard, QWizardPage, QLabel, QLineEdit, QTextEdit,
        QVBoxLayout, QHBoxLayout, QFormLayout, QCheckBox, QComboBox,
        QSpinBox, QGroupBox, QMessageBox, QProgressBar, QPushButton
    )
    from PySide6.QtCore import Qt, QThread, Signal, QTimer
    from PySide6.QtGui import QFont, QPixmap, QIcon

    from app.config.settings import get_config, save_config
    from app.infrastructure.logger import setup_logging, get_scheduler_logger
    from app.infrastructure.database import get_db_manager
    from app.infrastructure.job_history_db import init_db as init_job_history_db
    from app.services.email_service import get_email_service
    from app.version import get_version_string
    from app.core.jobs import discover_jobs

except ImportError as e:
    print(f"CRITICAL: Failed to import required modules: {e}")
    print("Please ensure all dependencies are installed.")
    sys.exit(1)


class SetupWorker(QThread):
    """Worker thread for setup operations."""

    progress = Signal(str)  # Progress message
    finished = Signal(bool, str)  # Success, message

    def __init__(self, config_data: Dict[str, Any]):
        super().__init__()
        self.config_data = config_data

    def run(self):
        """Run setup operations."""
        try:
            self.progress.emit("Initializing configuration...")

            # Save configuration
            save_config(self.config_data)
            self.progress.emit("Configuration saved")

            # Setup logging
            config = get_config()
            setup_logging(
                log_level=config.logging.level,
                log_dir=config.paths.logs_dir,
                max_bytes=config.logging.max_bytes,
                backup_count=config.logging.backup_count
            )
            self.progress.emit("Logging system initialized")

            # Initialize database
            init_job_history_db()
            db_manager = get_db_manager()
            self.progress.emit("Database initialized")

            # Discover jobs
            jobs = discover_jobs()
            self.progress.emit(f"Discovered {len(jobs)} jobs")

            # Test email if configured
            if (self.config_data.get('email', {}).get('smtp_server') and
                self.config_data.get('email', {}).get('sender_email')):
                self.progress.emit("Testing email configuration...")
                try:
                    email_service = get_email_service()
                    if email_service.test_connection():
                        self.progress.emit("Email configuration tested successfully")
                    else:
                        self.progress.emit("Email configuration test failed")
                except Exception as e:
                    self.progress.emit(f"Email test error: {e}")

            self.progress.emit("Setup completed successfully")
            self.finished.emit(True, "Setup completed successfully!")

        except Exception as e:
            self.progress.emit(f"Setup failed: {e}")
            self.finished.emit(False, f"Setup failed: {e}")


class WelcomePage(QWizardPage):
    """Welcome page."""

    def __init__(self):
        super().__init__()
        self.setTitle("Welcome to HET IT Control System")
        self.setSubTitle("First-Time Setup Wizard")

        layout = QVBoxLayout()

        welcome_text = QLabel(
            f"Welcome to the HET IT Control System Setup Wizard!\n\n"
            f"Version: {get_version_string()}\n\n"
            "This wizard will help you configure the system for first use.\n"
            "You'll need to provide:\n"
            "• Email configuration for notifications\n"
            "• Job branches and defaults\n"
            "• System preferences\n\n"
            "Click Next to continue."
        )
        welcome_text.setWordWrap(True)
        layout.addWidget(welcome_text)

        self.setLayout(layout)


class EmailConfigPage(QWizardPage):
    """Email configuration page."""

    def __init__(self):
        super().__init__()
        self.setTitle("Email Configuration")
        self.setSubTitle("Configure email settings for notifications and alerts")

        layout = QVBoxLayout()

        # Email group
        email_group = QGroupBox("SMTP Configuration")
        email_layout = QFormLayout()

        self.smtp_server = QLineEdit()
        self.smtp_server.setPlaceholderText("smtp.gmail.com")
        email_layout.addRow("SMTP Server:", self.smtp_server)

        self.smtp_port = QSpinBox()
        self.smtp_port.setRange(1, 65535)
        self.smtp_port.setValue(587)
        email_layout.addRow("SMTP Port:", self.smtp_port)

        self.sender_email = QLineEdit()
        self.sender_email.setPlaceholderText("your-email@gmail.com")
        email_layout.addRow("Sender Email:", self.sender_email)

        self.sender_password = QLineEdit()
        self.sender_password.setEchoMode(QLineEdit.Password)
        email_layout.addRow("Password/App Password:", self.sender_password)

        self.use_tls = QCheckBox("Use TLS")
        self.use_tls.setChecked(True)
        email_layout.addRow(self.use_tls)

        email_group.setLayout(email_layout)
        layout.addWidget(email_group)

        # Recipients
        recipients_group = QGroupBox("Notification Recipients")
        recipients_layout = QVBoxLayout()

        recipients_layout.addWidget(QLabel("Enter email addresses (one per line):"))
        self.recipients = QTextEdit()
        self.recipients.setPlaceholderText("admin@company.com\nit@company.com")
        self.recipients.setMaximumHeight(100)
        recipients_layout.addWidget(self.recipients)

        recipients_group.setLayout(recipients_layout)
        layout.addWidget(recipients_group)

        # Test button
        self.test_button = QPushButton("Test Email Configuration")
        self.test_button.clicked.connect(self.test_email)
        layout.addWidget(self.test_button)

        self.setLayout(layout)

    def test_email(self):
        """Test email configuration."""
        try:
            # This would need to be implemented with a temporary email service
            QMessageBox.information(self, "Test", "Email testing will be performed during setup.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Test failed: {e}")

    def validatePage(self):
        """Validate email configuration."""
        if not self.sender_email.text().strip():
            QMessageBox.warning(self, "Validation Error", "Sender email is required.")
            return False
        if not self.smtp_server.text().strip():
            QMessageBox.warning(self, "Validation Error", "SMTP server is required.")
            return False
        return True


class BranchesConfigPage(QWizardPage):
    """Job branches configuration page."""

    def __init__(self):
        super().__init__()
        self.setTitle("Job Branches")
        self.setSubTitle("Configure job execution branches")

        layout = QVBoxLayout()

        branches_text = QLabel(
            "Job branches allow you to run jobs in different environments or configurations.\n"
            "Common branches include 'production', 'staging', 'development'.\n\n"
            "Enter branch names (one per line):"
        )
        branches_text.setWordWrap(True)
        layout.addWidget(branches_text)

        self.branches = QTextEdit()
        self.branches.setPlainText("production\nstaging\ndevelopment")
        self.branches.setMaximumHeight(150)
        layout.addWidget(self.branches)

        # Default branch
        default_layout = QHBoxLayout()
        default_layout.addWidget(QLabel("Default Branch:"))
        self.default_branch = QComboBox()
        self.default_branch.addItems(["production", "staging", "development"])
        default_layout.addWidget(self.default_branch)
        layout.addLayout(default_layout)

        self.setLayout(layout)

    def validatePage(self):
        """Validate branches configuration."""
        branches = [b.strip() for b in self.branches.toPlainText().split('\n') if b.strip()]
        if not branches:
            QMessageBox.warning(self, "Validation Error", "At least one branch is required.")
            return False
        return True


class SystemConfigPage(QWizardPage):
    """System configuration page."""

    def __init__(self):
        super().__init__()
        self.setTitle("System Configuration")
        self.setSubTitle("Configure system preferences and defaults")

        layout = QVBoxLayout()

        # Logging
        logging_group = QGroupBox("Logging")
        logging_layout = QFormLayout()

        self.log_level = QComboBox()
        self.log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.log_level.setCurrentText("INFO")
        logging_layout.addRow("Log Level:", self.log_level)

        logging_group.setLayout(logging_layout)
        layout.addWidget(logging_group)

        # Scheduler
        scheduler_group = QGroupBox("Scheduler Defaults")
        scheduler_layout = QFormLayout()

        self.max_instances = QSpinBox()
        self.max_instances.setRange(1, 100)
        self.max_instances.setValue(5)
        scheduler_layout.addRow("Max Job Instances:", self.max_instances)

        self.timezone = QComboBox()
        self.timezone.addItems(["UTC", "Local"])
        self.timezone.setCurrentText("Local")
        scheduler_layout.addRow("Timezone:", self.timezone)

        scheduler_group.setLayout(scheduler_layout)
        layout.addWidget(scheduler_group)

        # Monitoring
        monitoring_group = QGroupBox("Monitoring")
        monitoring_layout = QVBoxLayout()

        self.enable_monitoring = QCheckBox("Enable system monitoring")
        self.enable_monitoring.setChecked(True)
        monitoring_layout.addWidget(self.enable_monitoring)

        self.enable_alerts = QCheckBox("Enable email alerts")
        self.enable_alerts.setChecked(True)
        monitoring_layout.addWidget(self.enable_alerts)

        monitoring_group.setLayout(monitoring_layout)
        layout.addWidget(monitoring_group)

        self.setLayout(layout)


class ProgressPage(QWizardPage):
    """Setup progress page."""

    def __init__(self):
        super().__init__()
        self.setTitle("Setting Up System")
        self.setSubTitle("Please wait while the system is configured...")

        layout = QVBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Initializing setup...")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def initializePage(self):
        """Start setup when page is shown."""
        wizard = self.wizard()
        config_data = wizard.get_config_data()

        self.worker = SetupWorker(config_data)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.setup_finished)
        self.worker.start()

    def update_progress(self, message: str):
        """Update progress message."""
        self.status_label.setText(message)

    def setup_finished(self, success: bool, message: str):
        """Handle setup completion."""
        if success:
            self.status_label.setText("Setup completed successfully!")
            self.wizard().next()
        else:
            QMessageBox.critical(self, "Setup Failed", message)
            self.wizard().back()


class CompletionPage(QWizardPage):
    """Setup completion page."""

    def __init__(self):
        super().__init__()
        self.setTitle("Setup Complete")
        self.setSubTitle("HET IT Control System is ready to use!")

        layout = QVBoxLayout()

        completion_text = QLabel(
            "🎉 Setup completed successfully!\n\n"
            "The HET IT Control System is now configured and ready to use.\n\n"
            "You can now:\n"
            "• Start the GUI application\n"
            "• Install and start the Windows service\n"
            "• Begin scheduling jobs\n\n"
            "Click Finish to exit the setup wizard."
        )
        completion_text.setWordWrap(True)
        layout.addWidget(completion_text)

        self.setLayout(layout)


class SetupWizard(QWizard):
    """Main setup wizard."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("HET IT Control System - Setup Wizard")
        self.setWizardStyle(QWizard.ModernStyle)
        self.setOption(QWizard.NoCancelButtonOnLastPage, True)

        # Add pages
        self.addPage(WelcomePage())
        self.addPage(EmailConfigPage())
        self.addPage(BranchesConfigPage())
        self.addPage(SystemConfigPage())
        self.addPage(ProgressPage())
        self.addPage(CompletionPage())

        # Set window properties
        self.setMinimumSize(600, 500)

    def get_config_data(self) -> Dict[str, Any]:
        """Collect configuration data from all pages."""
        config_data = {}

        # Email config
        email_page = self.page(1)  # EmailConfigPage
        config_data['email'] = {
            'smtp_server': email_page.smtp_server.text(),
            'smtp_port': email_page.smtp_port.value(),
            'sender_email': email_page.sender_email.text(),
            'sender_password': email_page.sender_password.text(),
            'use_tls': email_page.use_tls.isChecked(),
            'recipients': [r.strip() for r in email_page.recipients.toPlainText().split('\n') if r.strip()]
        }

        # Branches config
        branches_page = self.page(2)  # BranchesConfigPage
        branches = [b.strip() for b in branches_page.branches.toPlainText().split('\n') if b.strip()]
        config_data['jobs'] = {
            'branches': branches,
            'default_branch': branches_page.default_branch.currentText()
        }

        # System config
        system_page = self.page(3)  # SystemConfigPage
        config_data['logging'] = {
            'level': system_page.log_level.currentText()
        }
        config_data['scheduler'] = {
            'max_instances': system_page.max_instances.value(),
            'timezone': system_page.timezone.currentText()
        }
        config_data['monitoring'] = {
            'enabled': system_page.enable_monitoring.isChecked()
        }
        config_data['alerting'] = {
            'enabled': system_page.enable_alerts.isChecked()
        }

        return config_data


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("HET IT Control System Setup")
    app.setApplicationVersion(get_version_string())

    # Check if already configured
    try:
        config = get_config()
        if config.database.url.exists():
            reply = QMessageBox.question(
                None, "Already Configured",
                "The system appears to be already configured. Run setup anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return 0
    except:
        pass  # Not configured yet, continue

    wizard = SetupWizard()
    result = wizard.exec()

    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())