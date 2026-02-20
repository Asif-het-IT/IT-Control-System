# app/ui/job_card.py
"""
Job card component for the HET IT Control System GUI.
"""
from typing import Dict, Any
from datetime import datetime
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QPushButton,
    QHBoxLayout, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class JobCard(QFrame):
    """Professional job card widget with status and controls."""

    def __init__(self, job_id: str, job_info: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.job_id = job_id
        self.job_info = job_info
        self.parent_window = parent

        self.setup_ui()
        self.apply_styling()

    def setup_ui(self):
        """Setup the card user interface."""
        self.setFrameStyle(QFrame.Box)
        self.setLineWidth(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)

        # Header section
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        # Job name
        self.name_label = QLabel(self.job_info.get('name', self.job_id))
        self.name_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        header_layout.addWidget(self.name_label)

        # Status badge
        self.status_badge = QLabel("●")
        self.status_badge.setFont(QFont("Segoe UI", 12))
        self.update_status_badge()
        header_layout.addWidget(self.status_badge)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Description
        description = self.job_info.get('description', 'Automated job execution')
        self.desc_label = QLabel(description)
        self.desc_label.setFont(QFont("Segoe UI", 9))
        self.desc_label.setStyleSheet("color: #888;")
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)

        # Last run time
        self.last_run_label = QLabel("Last run: Never")
        self.last_run_label.setFont(QFont("Segoe UI", 8))
        self.last_run_label.setStyleSheet("color: #666;")
        layout.addWidget(self.last_run_label)

        # Next run time
        next_run = self.job_info.get('next_run_time')
        if next_run:
            next_run_text = f"Next: {next_run.strftime('%H:%M:%S')}"
        else:
            next_run_text = "Not scheduled"
        self.next_run_label = QLabel(next_run_text)
        self.next_run_label.setFont(QFont("Segoe UI", 8))
        self.next_run_label.setStyleSheet("color: #666;")
        layout.addWidget(self.next_run_label)

        # Run button
        self.run_button = QPushButton("▶ Run")
        self.run_button.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.run_button.clicked.connect(self.run_job)
        self.run_button.setMinimumHeight(30)
        layout.addWidget(self.run_button)

        # Set fixed width for consistent card sizing
        self.setFixedWidth(280)

    def apply_styling(self):
        """Apply professional styling to the card."""
        self.setStyleSheet("""
            JobCard {
                background-color: #2d2d30;
                border: 1px solid #3e3e42;
                border-radius: 8px;
                color: #ffffff;
            }
            JobCard:hover {
                background-color: #37373d;
                border-color: #007acc;
            }
            QPushButton {
                background-color: #0e639c;
                border: 1px solid #007acc;
                border-radius: 4px;
                color: white;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
            QPushButton:pressed {
                background-color: #0a4f7a;
            }
            QPushButton:disabled {
                background-color: #555;
                border-color: #666;
                color: #999;
            }
        """)

    def update_status_badge(self):
        """Update the status badge based on job state."""
        status = self.job_info.get('status', 'unknown')

        if status == 'running':
            self.status_badge.setStyleSheet("color: #007acc;")
            self.status_badge.setToolTip("Job is currently running")
        elif status == 'success':
            self.status_badge.setStyleSheet("color: #00cc44;")
            self.status_badge.setToolTip("Last run was successful")
        elif status == 'failed':
            self.status_badge.setStyleSheet("color: #cc0000;")
            self.status_badge.setToolTip("Last run failed")
        else:
            self.status_badge.setStyleSheet("color: #888;")
            self.status_badge.setToolTip("Job status unknown")

    def update_job_info(self, job_info: Dict[str, Any]):
        """Update job information and refresh display."""
        self.job_info = job_info

        # Update status badge
        self.update_status_badge()

        # Update next run time
        next_run = job_info.get('next_run_time')
        if next_run:
            next_run_text = f"Next: {next_run.strftime('%H:%M:%S')}"
        else:
            next_run_text = "Not scheduled"
        self.next_run_label.setText(next_run_text)

    def run_job(self):
        """Handle job run request."""
        if self.parent_window:
            # Disable button during execution
            self.run_button.setEnabled(False)
            self.run_button.setText("Running...")

            # Emit signal through parent window
            self.parent_window.run_job_signal.emit(self.job_id)

    def reset_ui(self):
        """Reset UI after job completion."""
        self.run_button.setEnabled(True)
        self.run_button.setText("▶ Run")