# app/ui/main_window.py
"""
Main GUI window for the HET IT Control System.
"""
import sys
import threading
from queue import Queue
from typing import Dict, Any, List, Optional
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QTextEdit, QTabWidget,
    QTableWidget, QTableWidgetItem, QProgressBar, QSplitter,
    QGroupBox, QScrollArea, QFrame, QMessageBox, QComboBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QFont, QPalette, QColor, QIcon

from app.config.settings import get_config
from app.infrastructure.scheduler import get_scheduler
from app.infrastructure.database import get_db_manager, JobExecution
from app.services.system_service import get_system_service
from app.infrastructure.logger import get_logger

logger = get_logger("ui")


class JobCard(QFrame):
    """Card widget for displaying job information."""

    def __init__(self, job_id: str, job_info: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.job_id = job_id
        self.job_info = job_info

        self.setFrameStyle(QFrame.Box)
        self.setLineWidth(1)

        layout = QVBoxLayout(self)

        # Job name
        name_label = QLabel(job_info.get('name', job_id))
        name_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(name_label)

        # Next run time
        next_run = job_info.get('next_run_time')
        if next_run:
            time_label = QLabel(f"Next: {next_run.strftime('%H:%M:%S')}")
        else:
            time_label = QLabel("Not scheduled")
        time_label.setStyleSheet("color: #666;")
        layout.addWidget(time_label)

        # Run button
        self.run_button = QPushButton("Run Now")
        self.run_button.clicked.connect(self.run_job)
        layout.addWidget(self.run_button)

        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.setStyleSheet("""
            JobCard {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 10px;
                margin: 5px;
            }
            JobCard:hover {
                background-color: #e9ecef;
            }
        """)

    def run_job(self):
        """Run the job."""
        self.run_button.setEnabled(False)
        self.run_button.setText("Running...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress

        # Emit signal to parent
        self.parent().run_job_signal.emit(self.job_id)

    def reset_ui(self):
        """Reset UI after job completion."""
        self.run_button.setEnabled(True)
        self.run_button.setText("Run Now")
        self.progress_bar.setVisible(False)


class MainWindow(QMainWindow):
    """Main application window."""

    run_job_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self.config = get_config()
        self.scheduler = get_scheduler()
        self.system_service = get_system_service()

        self.setWindowTitle("HET IT Control System")
        self.setGeometry(100, 100, 1200, 800)

        # Setup UI
        self.setup_ui()
        self.setup_connections()

        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start(5000)  # Update every 5 seconds

        # Initial update
        self.update_status()

    def setup_ui(self):
        """Setup the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # Header
        header = self.create_header()
        main_layout.addWidget(header)

        # Main content
        content_splitter = QSplitter(Qt.Vertical)

        # Jobs section
        jobs_group = self.create_jobs_section()
        content_splitter.addWidget(jobs_group)

        # Status and logs section
        bottom_splitter = QSplitter(Qt.Horizontal)

        # System status
        status_group = self.create_status_section()
        bottom_splitter.addWidget(status_group)

        # Logs
        logs_group = self.create_logs_section()
        bottom_splitter.addWidget(logs_group)

        content_splitter.addWidget(bottom_splitter)
        content_splitter.setSizes([400, 400])

        main_layout.addWidget(content_splitter)

    def create_header(self) -> QWidget:
        """Create header widget."""
        header = QWidget()
        layout = QHBoxLayout(header)

        title = QLabel("HET IT Control System")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        layout.addWidget(title)

        layout.addStretch()

        # Branch selector (placeholder)
        branch_label = QLabel("Branch:")
        layout.addWidget(branch_label)

        self.branch_combo = QComboBox()
        self.branch_combo.addItems(["default"] + list(self.config.branches.keys()))
        layout.addWidget(self.branch_combo)

        return header

    def create_jobs_section(self) -> QGroupBox:
        """Create jobs section."""
        group = QGroupBox("Automated Jobs")
        layout = QVBoxLayout(group)

        # Jobs grid
        self.jobs_scroll = QScrollArea()
        self.jobs_widget = QWidget()
        self.jobs_layout = QGridLayout(self.jobs_widget)

        self.jobs_scroll.setWidget(self.jobs_widget)
        self.jobs_scroll.setWidgetResizable(True)
        layout.addWidget(self.jobs_scroll)

        return group

    def create_status_section(self) -> QGroupBox:
        """Create system status section."""
        group = QGroupBox("System Status")
        layout = QVBoxLayout(group)

        # System info
        self.system_info_text = QTextEdit()
        self.system_info_text.setMaximumHeight(200)
        self.system_info_text.setReadOnly(True)
        layout.addWidget(self.system_info_text)

        # Recent executions table
        executions_label = QLabel("Recent Job Executions")
        executions_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(executions_label)

        self.executions_table = QTableWidget()
        self.executions_table.setColumnCount(4)
        self.executions_table.setHorizontalHeaderLabels(["Job", "Branch", "Status", "Time"])
        self.executions_table.setMaximumHeight(200)
        layout.addWidget(self.executions_table)

        return group

    def create_logs_section(self) -> QGroupBox:
        """Create logs section."""
        group = QGroupBox("Activity Logs")
        layout = QVBoxLayout(group)

        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        layout.addWidget(self.logs_text)

        # Clear logs button
        clear_button = QPushButton("Clear Logs")
        clear_button.clicked.connect(self.clear_logs)
        layout.addWidget(clear_button)

        return group

    def setup_connections(self):
        """Setup signal connections."""
        self.run_job_signal.connect(self.handle_run_job)

    def update_status(self):
        """Update system status display."""
        try:
            # Update system info
            system_info = self.system_service.get_system_info()
            health = self.system_service.get_system_health()

            status_text = f"""
System Information:
Platform: {system_info.get('platform', 'Unknown')}
CPU Cores: {self.system_service.get_cpu_info().get('total_cores', 'Unknown')}
Memory: {self.system_service.get_memory_info().get('percent', 0):.1f}% used
System Health: {health.get('overall_health', 0):.1f}%

Last Updated: {datetime.now().strftime('%H:%M:%S')}
            """.strip()

            self.system_info_text.setPlainText(status_text)

            # Update jobs
            self.update_jobs_display()

            # Update recent executions
            self.update_executions_table()

        except Exception as e:
            logger.error(f"Failed to update status: {e}")

    def update_jobs_display(self):
        """Update jobs display."""
        # Clear existing job cards
        for i in reversed(range(self.jobs_layout.count())):
            widget = self.jobs_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # Add job cards
        jobs = self.scheduler.list_jobs()
        row, col = 0, 0
        max_cols = 3

        for job_id, job_info in jobs.items():
            card = JobCard(job_id, job_info, self)
            self.jobs_layout.addWidget(card, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def update_executions_table(self):
        """Update recent executions table."""
        try:
            db_manager = get_db_manager()
            with db_manager.get_session() as session:
                executions = session.query(JobExecution).order_by(
                    JobExecution.created_at.desc()
                ).limit(10).all()

                self.executions_table.setRowCount(len(executions))

                for row, exec in enumerate(executions):
                    self.executions_table.setItem(row, 0, QTableWidgetItem(exec.job_name))
                    self.executions_table.setItem(row, 1, QTableWidgetItem(exec.branch_id))
                    status = "Success" if exec.success else "Failed"
                    self.executions_table.setItem(row, 2, QTableWidgetItem(status))
                    time_str = exec.created_at.strftime("%H:%M:%S")
                    self.executions_table.setItem(row, 3, QTableWidgetItem(time_str))

        except Exception as e:
            logger.error(f"Failed to update executions table: {e}")

    def handle_run_job(self, job_id: str):
        """Handle job run request."""
        def run_job_thread():
            try:
                result = self.scheduler.run_job_now(job_id)

                # Update UI in main thread
                self.update_status()

                # Show result message
                if result and result.success:
                    QMessageBox.information(self, "Success", f"Job {job_id} completed successfully")
                else:
                    error_msg = result.error if result else "Unknown error"
                    QMessageBox.warning(self, "Job Failed", f"Job {job_id} failed: {error_msg}")

            except Exception as e:
                logger.error(f"Failed to run job {job_id}: {e}")
                QMessageBox.critical(self, "Error", f"Failed to run job {job_id}: {str(e)}")

        # Run in background thread
        thread = threading.Thread(target=run_job_thread, daemon=True)
        thread.start()

    def clear_logs(self):
        """Clear logs display."""
        self.logs_text.clear()

    def closeEvent(self, event):
        """Handle application close."""
        self.update_timer.stop()
        event.accept()


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)

    # Set dark theme
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()