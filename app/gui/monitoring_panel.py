# app/gui/monitoring_panel.py
"""
Real-time system monitoring panel for the HET IT Control System.
Features:
- Live CPU, RAM, and disk usage charts
- System health indicator
- Job execution status
- Alert notifications
- Performance metrics dashboard
"""

import sys
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QProgressBar, QGridLayout, QGroupBox, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy,
    QSplitter, QTextEdit
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QObject
from PySide6.QtGui import QFont, QColor, QPalette, QPainter, QBrush
from PySide6.QtCharts import (
    QChart, QChartView, QLineSeries, QValueAxis, QDateTimeAxis,
    QAreaSeries, QBarSeries, QBarSet, QBarCategoryAxis
)

from app.infrastructure.monitoring import (
    get_monitoring_service, SystemHealth, ResourceMetrics, JobMetrics
)
from app.services.alert_manager import get_alert_manager, AlertSeverity
from app.infrastructure.logger import get_gui_logger

logger = get_gui_logger()


class HealthIndicator(QWidget):
    """Visual health status indicator."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 60)
        self._status = "unknown"
        self._issues = []

    def set_health(self, health: SystemHealth):
        """Update health status."""
        self._status = health.overall_status
        self._issues = health.issues
        self.update()

    def paintEvent(self, event):
        """Paint the health indicator."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Define colors
        colors = {
            "healthy": QColor("#4CAF50"),    # Green
            "warning": QColor("#FF9800"),    # Orange
            "critical": QColor("#F44336"),   # Red
            "unknown": QColor("#9E9E9E")     # Gray
        }

        color = colors.get(self._status, colors["unknown"])

        # Draw circle
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(5, 5, 50, 50)

        # Draw border
        painter.setPen(QColor("#333333"))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(5, 5, 50, 50)

        # Draw status text
        painter.setPen(QColor("white"))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(8)
        painter.setFont(font)

        status_text = self._status.upper()[:3]  # First 3 letters
        text_rect = painter.boundingRect(5, 5, 50, 50, Qt.AlignCenter, status_text)
        painter.drawText(text_rect, Qt.AlignCenter, status_text)

    def get_tooltip_text(self) -> str:
        """Get tooltip text with issues."""
        if not self._issues:
            return f"System Status: {self._status.title()}"

        issues_text = "\n".join(f"• {issue}" for issue in self._issues[:5])  # Max 5 issues
        return f"System Status: {self._status.title()}\n\nIssues:\n{issues_text}"


class ResourceChart(QChartView):
    """Real-time resource usage chart."""

    def __init__(self, title: str, max_points: int = 60, parent=None):
        super().__init__(parent)

        self.max_points = max_points
        self.series = QLineSeries()
        self.series.setName(title)

        self.chart = QChart()
        self.chart.addSeries(self.series)
        self.chart.setTitle(title)
        self.chart.legend().hide()

        # X-axis (time)
        self.axis_x = QDateTimeAxis()
        self.axis_x.setFormat("HH:mm:ss")
        self.axis_x.setTitleText("Time")
        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.series.attachAxis(self.axis_x)

        # Y-axis (percentage)
        self.axis_y = QValueAxis()
        self.axis_y.setRange(0, 100)
        self.axis_y.setTitleText("Usage (%)")
        self.axis_y.setLabelFormat("%.0f%%")
        self.chart.addAxis(self.axis_y, Qt.AlignLeft)
        self.series.attachAxis(self.axis_y)

        self.setChart(self.chart)
        self.setMinimumHeight(200)

    def add_point(self, timestamp: datetime, value: float):
        """Add a data point to the chart."""
        # Convert to milliseconds since epoch
        x_value = timestamp.timestamp() * 1000

        self.series.append(x_value, value)

        # Remove old points
        while self.series.count() > self.max_points:
            self.series.remove(0)

        # Update X-axis range
        if self.series.count() > 0:
            min_x = min(p.x() for p in self.series.points())
            max_x = max(p.x() for p in self.series.points())
            self.axis_x.setRange(datetime.fromtimestamp(min_x / 1000),
                               datetime.fromtimestamp(max_x / 1000))


class MonitoringWorker(QObject):
    """Background worker for monitoring data updates."""

    data_updated = Signal(ResourceMetrics, SystemHealth, dict, dict)
    alerts_updated = Signal(list)

    def __init__(self):
        super().__init__()
        self.monitoring_service = get_monitoring_service()
        self.alert_manager = get_alert_manager()
        self._running = False

    def start(self):
        """Start the monitoring worker."""
        self._running = True
        self._update_data()

    def stop(self):
        """Stop the monitoring worker."""
        self._running = False

    def _update_data(self):
        """Update monitoring data."""
        if not self._running:
            return

        try:
            # Get current metrics
            metrics = self.monitoring_service.get_current_metrics()
            health = self.monitoring_service.get_system_health()

            # Get job statistics
            job_stats = self.monitoring_service.get_job_statistics()

            # Get performance metrics
            perf_metrics = self.monitoring_service.get_performance_metrics()

            # Get recent alerts
            recent_alerts = self.alert_manager.get_recent_alerts(limit=10)

            # Emit data
            self.data_updated.emit(metrics, health, job_stats, perf_metrics)
            self.alerts_updated.emit(recent_alerts)

        except Exception as e:
            logger.error(f"Error updating monitoring data: {e}")

        # Schedule next update
        if self._running:
            QTimer.singleShot(2000, self._update_data)  # Update every 2 seconds


class MonitoringPanel(QWidget):
    """Main monitoring panel widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.monitoring_service = get_monitoring_service()
        self.alert_manager = get_alert_manager()

        # Initialize charts
        self.cpu_chart = ResourceChart("CPU Usage")
        self.memory_chart = ResourceChart("Memory Usage")

        # Initialize worker
        self.worker = MonitoringWorker()
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)

        # Connect signals
        self.worker.data_updated.connect(self._update_display)
        self.worker.alerts_updated.connect(self._update_alerts)
        self.worker_thread.started.connect(self.worker.start)

        self._setup_ui()
        self._start_monitoring()

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)

        # Header with health indicator
        header_layout = QHBoxLayout()

        title_label = QLabel("System Monitoring")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        self.health_indicator = HealthIndicator()
        self.health_indicator.setToolTip("System Health Status")
        header_layout.addWidget(self.health_indicator)

        layout.addLayout(header_layout)

        # Main content splitter
        splitter = QSplitter(Qt.Vertical)

        # Top section: Charts and metrics
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)

        # Charts section
        charts_widget = QWidget()
        charts_layout = QVBoxLayout(charts_widget)

        charts_layout.addWidget(self.cpu_chart)
        charts_layout.addWidget(self.memory_chart)

        top_layout.addWidget(charts_widget, 2)  # 2/3 width

        # Metrics section
        metrics_widget = QWidget()
        metrics_layout = QVBoxLayout(metrics_widget)

        # Current metrics
        current_group = QGroupBox("Current Usage")
        current_layout = QGridLayout(current_group)

        self.cpu_label = QLabel("CPU: --%")
        self.memory_label = QLabel("Memory: --%")
        self.disk_label = QLabel("Disk: --%")
        self.network_label = QLabel("Network: -- KB/s")

        current_layout.addWidget(QLabel("CPU:"), 0, 0)
        current_layout.addWidget(self.cpu_label, 0, 1)
        current_layout.addWidget(QLabel("Memory:"), 1, 0)
        current_layout.addWidget(self.memory_label, 1, 1)
        current_layout.addWidget(QLabel("Disk:"), 2, 0)
        current_layout.addWidget(self.disk_label, 2, 1)
        current_layout.addWidget(QLabel("Network:"), 3, 0)
        current_layout.addWidget(self.network_label, 3, 1)

        metrics_layout.addWidget(current_group)

        # Performance summary
        perf_group = QGroupBox("Performance Summary (1h)")
        perf_layout = QGridLayout(perf_group)

        self.avg_cpu_label = QLabel("Avg CPU: --%")
        self.peak_cpu_label = QLabel("Peak CPU: --%")
        self.avg_memory_label = QLabel("Avg Memory: --%")
        self.peak_memory_label = QLabel("Peak Memory: --%")
        self.process_count_label = QLabel("Processes: --")
        self.thread_count_label = QLabel("Threads: --")

        perf_layout.addWidget(QLabel("Avg CPU:"), 0, 0)
        perf_layout.addWidget(self.avg_cpu_label, 0, 1)
        perf_layout.addWidget(QLabel("Peak CPU:"), 1, 0)
        perf_layout.addWidget(self.peak_cpu_label, 1, 1)
        perf_layout.addWidget(QLabel("Avg Memory:"), 2, 0)
        perf_layout.addWidget(self.avg_memory_label, 2, 1)
        perf_layout.addWidget(QLabel("Peak Memory:"), 3, 0)
        perf_layout.addWidget(self.peak_memory_label, 3, 1)
        perf_layout.addWidget(QLabel("Processes:"), 4, 0)
        perf_layout.addWidget(self.process_count_label, 4, 1)
        perf_layout.addWidget(QLabel("Threads:"), 5, 0)
        perf_layout.addWidget(self.thread_count_label, 5, 1)

        metrics_layout.addWidget(perf_group)
        metrics_layout.addStretch()

        top_layout.addWidget(metrics_widget, 1)  # 1/3 width

        splitter.addWidget(top_widget)

        # Bottom section: Jobs and alerts
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)

        # Job statistics
        jobs_group = QGroupBox("Job Statistics")
        jobs_layout = QVBoxLayout(jobs_group)

        self.jobs_table = QTableWidget()
        self.jobs_table.setColumnCount(4)
        self.jobs_table.setHorizontalHeaderLabels(["Job ID", "Status", "Duration", "Last Run"])
        self.jobs_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.jobs_table.setMaximumHeight(200)

        jobs_layout.addWidget(self.jobs_table)

        # Job summary
        summary_layout = QHBoxLayout()
        self.total_jobs_label = QLabel("Total: --")
        self.success_rate_label = QLabel("Success Rate: --%")
        self.failed_jobs_label = QLabel("Failed: --")

        summary_layout.addWidget(self.total_jobs_label)
        summary_layout.addWidget(self.success_rate_label)
        summary_layout.addWidget(self.failed_jobs_label)
        summary_layout.addStretch()

        jobs_layout.addLayout(summary_layout)

        bottom_layout.addWidget(jobs_group, 1)

        # Recent alerts
        alerts_group = QGroupBox("Recent Alerts")
        alerts_layout = QVBoxLayout(alerts_group)

        self.alerts_text = QTextEdit()
        self.alerts_text.setReadOnly(True)
        self.alerts_text.setMaximumHeight(200)
        self.alerts_text.setFont(QFont("Consolas", 9))

        alerts_layout.addWidget(self.alerts_text)

        bottom_layout.addWidget(alerts_group, 1)

        splitter.addWidget(bottom_widget)

        # Set splitter proportions
        splitter.setSizes([400, 300])

        layout.addWidget(splitter)

    def _start_monitoring(self):
        """Start the monitoring updates."""
        self.worker_thread.start()

    def _update_display(self, metrics: ResourceMetrics, health: SystemHealth,
                       job_stats: dict, perf_metrics: dict):
        """Update the display with new monitoring data."""
        try:
            # Update health indicator
            self.health_indicator.set_health(health)
            self.health_indicator.setToolTip(self.health_indicator.get_tooltip_text())

            # Update charts
            self.cpu_chart.add_point(metrics.timestamp, metrics.cpu_percent)
            self.memory_chart.add_point(metrics.timestamp, metrics.memory_percent)

            # Update current metrics
            self.cpu_label.setText(f"{metrics.cpu_percent:.1f}%")
            self.memory_label.setText(f"{metrics.memory_percent:.1f}%")

            # Disk usage (show primary disk)
            if metrics.disk_percent:
                primary_disk = max(metrics.disk_percent.items(), key=lambda x: x[1])
                self.disk_label.setText(f"{primary_disk[1]:.1f}% ({primary_disk[0]})")
            else:
                self.disk_label.setText("--%")

            # Network (convert to KB/s)
            network_kb_s = (metrics.network_bytes_sent + metrics.network_bytes_recv) / 1024
            self.network_label.setText(f"{network_kb_s:.1f} KB/s")

            # Update performance metrics
            if perf_metrics:
                self.avg_cpu_label.setText(f"{perf_metrics.get('average_cpu_percent', 0):.1f}%")
                self.peak_cpu_label.setText(f"{perf_metrics.get('peak_cpu_percent', 0):.1f}%")
                self.avg_memory_label.setText(f"{perf_metrics.get('average_memory_percent', 0):.1f}%")
                self.peak_memory_label.setText(f"{perf_metrics.get('peak_memory_percent', 0):.1f}%")
                self.process_count_label.setText(str(perf_metrics.get('process_count', 0)))
                self.thread_count_label.setText(str(perf_metrics.get('thread_count', 0)))

            # Update job statistics
            if job_stats:
                self.total_jobs_label.setText(f"Total: {job_stats.get('total_jobs', 0)}")
                self.success_rate_label.setText(f"Success Rate: {job_stats.get('success_rate', 0):.1f}%")
                self.failed_jobs_label.setText(f"Failed: {job_stats.get('failed_jobs', 0)}")

                # Update jobs table with recent failures
                recent_failures = job_stats.get('recent_failures', [])
                self.jobs_table.setRowCount(len(recent_failures))

                for row, failure in enumerate(recent_failures):
                    self.jobs_table.setItem(row, 0, QTableWidgetItem(failure['job_id']))
                    self.jobs_table.setItem(row, 1, QTableWidgetItem("Failed"))
                    self.jobs_table.setItem(row, 2, QTableWidgetItem(f"{failure.get('duration', 0):.1f}s"))
                    self.jobs_table.setItem(row, 3, QTableWidgetItem(
                        failure.get('end_time', 'Unknown')[:19] if failure.get('end_time') else 'Unknown'
                    ))

        except Exception as e:
            logger.error(f"Error updating monitoring display: {e}")

    def _update_alerts(self, alerts: list):
        """Update the alerts display."""
        try:
            if not alerts:
                self.alerts_text.setPlainText("No recent alerts")
                return

            alert_text = ""
            for alert in alerts[:10]:  # Show last 10 alerts
                timestamp = alert.get('timestamp', 'Unknown')
                severity = alert.get('severity', 'info')
                title = alert.get('title', 'Unknown Alert')
                message = alert.get('message', '')

                # Color coding
                color = {
                    'critical': '#F44336',
                    'warning': '#FF9800',
                    'info': '#2196F3'
                }.get(severity, '#9E9E9E')

                alert_text += f'<span style="color: {color};">[{timestamp}] {severity.upper()}: {title}</span><br>'
                if message:
                    alert_text += f'<span style="color: #666;">{message}</span><br>'
                alert_text += '<br>'

            self.alerts_text.setHtml(alert_text)

        except Exception as e:
            logger.error(f"Error updating alerts display: {e}")

    def closeEvent(self, event):
        """Handle widget close event."""
        self.worker.stop()
        self.worker_thread.quit()
        self.worker_thread.wait()
        super().closeEvent(event)