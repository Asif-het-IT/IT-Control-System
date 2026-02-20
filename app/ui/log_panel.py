# app/ui/log_panel.py
"""
Log panel component for live activity display.
"""
from typing import List, Dict, Any
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit,
    QFrame, QHBoxLayout, QPushButton, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor


class LogEntry:
    """Represents a single log entry."""

    def __init__(self, timestamp: datetime, level: str, message: str, source: str = ""):
        self.timestamp = timestamp
        self.level = level.upper()
        self.message = message
        self.source = source

    def to_html(self) -> str:
        """Convert log entry to HTML format."""
        time_str = self.timestamp.strftime("%H:%M:%S")

        # Color coding based on log level
        if self.level == "ERROR":
            color = "#cc0000"
        elif self.level == "WARNING":
            color = "#ffaa00"
        elif self.level == "INFO":
            color = "#00cc44"
        elif self.level == "DEBUG":
            color = "#888888"
        else:
            color = "#ffffff"

        source_tag = f"[{self.source}] " if self.source else ""

        return f'<span style="color: #666;">{time_str}</span> ' \
               f'<span style="color: {color}; font-weight: bold;">{self.level}</span> ' \
               f'<span style="color: #ccc;">{source_tag}{self.message}</span><br>'


class LogPanel(QWidget):
    """Live activity log panel widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.log_entries: List[LogEntry] = []
        self.max_entries = 100
        self.setup_ui()

    def setup_ui(self):
        """Setup the log panel user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Title and controls
        header_layout = QHBoxLayout()

        title = QLabel("Activity Logs")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet("color: #ffffff;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Control buttons
        self.clear_button = QPushButton("Clear")
        self.clear_button.setFont(QFont("Segoe UI", 9))
        self.clear_button.clicked.connect(self.clear_logs)
        self.clear_button.setStyleSheet("""
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
        """)
        header_layout.addWidget(self.clear_button)

        layout.addLayout(header_layout)

        # Log display area
        log_frame = QFrame()
        log_frame.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border: 1px solid #3e3e42;
                border-radius: 8px;
            }
        """)

        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(10, 10, 10, 10)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                border: none;
                color: #ffffff;
                selection-background-color: #264f78;
            }
        """)
        self.log_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.log_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        log_layout.addWidget(self.log_text)
        layout.addWidget(log_frame)

        # Status bar
        self.status_label = QLabel("Ready - 0 entries")
        self.status_label.setFont(QFont("Segoe UI", 8))
        self.status_label.setStyleSheet("color: #888;")
        layout.addWidget(self.status_label)

    def add_log_entry(self, level: str, message: str, source: str = ""):
        """Add a new log entry to the panel."""
        entry = LogEntry(datetime.now(), level, message, source)
        self.log_entries.append(entry)

        # Maintain max entries limit
        if len(self.log_entries) > self.max_entries:
            self.log_entries.pop(0)

        self.update_display()
        self.update_status()

    def update_display(self):
        """Update the log display with current entries."""
        html_content = ""
        for entry in self.log_entries[-50:]:  # Show last 50 entries
            html_content += entry.to_html()

        self.log_text.setHtml(f"""
        <html>
        <body style="background-color: #1e1e1e; font-family: Consolas, monospace; font-size: 9pt;">
        {html_content}
        </body>
        </html>
        """)

        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def update_status(self):
        """Update the status bar."""
        entry_count = len(self.log_entries)
        self.status_label.setText(f"Active - {entry_count} entries")

    def clear_logs(self):
        """Clear all log entries."""
        self.log_entries.clear()
        self.log_text.clear()
        self.update_status()

    def add_job_execution_log(self, job_name: str, success: bool, duration: float = None):
        """Add a job execution log entry."""
        if success:
            level = "INFO"
            message = f"Job '{job_name}' completed successfully"
            if duration:
                message += f" in {duration:.2f}s"
        else:
            level = "ERROR"
            message = f"Job '{job_name}' failed"
            if duration:
                message += f" after {duration:.2f}s"

        self.add_log_entry(level, message, "JOB")

    def add_system_log(self, message: str, level: str = "INFO"):
        """Add a system-related log entry."""
        self.add_log_entry(level, message, "SYSTEM")

    def add_scheduler_log(self, message: str, level: str = "INFO"):
        """Add a scheduler-related log entry."""
        self.add_log_entry(level, message, "SCHEDULER")