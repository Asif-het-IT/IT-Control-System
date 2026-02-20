# app/ui/dashboard_widget.py
"""
Dashboard widget component for system metrics display.
"""
from typing import Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QGridLayout, QProgressBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class MetricCard(QFrame):
    """Individual metric display card."""

    def __init__(self, title: str, value: str = "--", unit: str = "", parent=None):
        super().__init__(parent)
        self.title = title
        self.unit = unit

        self.setup_ui()
        self.set_value(value)
        self.apply_styling()

    def setup_ui(self):
        """Setup the metric card UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        # Title
        self.title_label = QLabel(self.title)
        self.title_label.setFont(QFont("Segoe UI", 9))
        self.title_label.setStyleSheet("color: #888;")
        layout.addWidget(self.title_label)

        # Value
        self.value_label = QLabel("--")
        self.value_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(self.value_label)

        self.setFixedHeight(70)

    def set_value(self, value: str):
        """Set the metric value."""
        if self.unit:
            self.value_label.setText(f"{value} {self.unit}")
        else:
            self.value_label.setText(value)

    def apply_styling(self):
        """Apply styling to the metric card."""
        self.setStyleSheet("""
            MetricCard {
                background-color: #252526;
                border: 1px solid #3e3e42;
                border-radius: 6px;
                color: #ffffff;
            }
        """)


class DashboardWidget(QWidget):
    """System metrics dashboard widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.system_service = None
        self.setup_ui()

    def setup_ui(self):
        """Setup the dashboard user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # Title
        title = QLabel("System Dashboard")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet("color: #ffffff; margin-bottom: 10px;")
        layout.addWidget(title)

        # System Info Section
        system_group = QFrame()
        system_group.setStyleSheet("""
            QFrame {
                background-color: #2d2d30;
                border: 1px solid #3e3e42;
                border-radius: 8px;
            }
        """)
        system_layout = QVBoxLayout(system_group)
        system_layout.setContentsMargins(15, 15, 15, 15)

        system_title = QLabel("System Information")
        system_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        system_title.setStyleSheet("color: #ffffff;")
        system_layout.addWidget(system_title)

        self.system_info_text = QLabel("Loading system information...")
        self.system_info_text.setFont(QFont("Segoe UI", 9))
        self.system_info_text.setStyleSheet("color: #cccccc;")
        self.system_info_text.setWordWrap(True)
        system_layout.addWidget(self.system_info_text)

        layout.addWidget(system_group)

        # Metrics Grid
        metrics_group = QFrame()
        metrics_group.setStyleSheet("""
            QFrame {
                background-color: #2d2d30;
                border: 1px solid #3e3e42;
                border-radius: 8px;
            }
        """)
        metrics_layout = QVBoxLayout(metrics_group)
        metrics_layout.setContentsMargins(15, 15, 15, 15)

        metrics_title = QLabel("Performance Metrics")
        metrics_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        metrics_title.setStyleSheet("color: #ffffff;")
        metrics_layout.addWidget(metrics_title)

        # Create metrics grid
        self.metrics_grid = QGridLayout()
        self.metrics_grid.setSpacing(10)

        # CPU Usage
        self.cpu_card = MetricCard("CPU Usage", "--", "%")
        self.metrics_grid.addWidget(self.cpu_card, 0, 0)

        # Memory Usage
        self.memory_card = MetricCard("Memory", "--", "%")
        self.metrics_grid.addWidget(self.memory_card, 0, 1)

        # Disk Usage
        self.disk_card = MetricCard("Disk", "--", "%")
        self.metrics_grid.addWidget(self.disk_card, 1, 0)

        # Network
        self.network_card = MetricCard("Network", "--", "KB/s")
        self.metrics_grid.addWidget(self.network_card, 1, 1)

        metrics_layout.addLayout(self.metrics_grid)
        layout.addWidget(metrics_group)

        # Health Status
        health_group = QFrame()
        health_group.setStyleSheet("""
            QFrame {
                background-color: #2d2d30;
                border: 1px solid #3e3e42;
                border-radius: 8px;
            }
        """)
        health_layout = QVBoxLayout(health_group)
        health_layout.setContentsMargins(15, 15, 15, 15)

        health_title = QLabel("System Health")
        health_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        health_title.setStyleSheet("color: #ffffff;")
        health_layout.addWidget(health_title)

        self.health_bar = QProgressBar()
        self.health_bar.setRange(0, 100)
        self.health_bar.setValue(0)
        self.health_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3e3e42;
                border-radius: 4px;
                text-align: center;
                background-color: #1e1e1e;
            }
            QProgressBar::chunk {
                background-color: #00cc44;
            }
        """)
        health_layout.addWidget(self.health_bar)

        self.health_label = QLabel("Health: --%")
        self.health_label.setFont(QFont("Segoe UI", 9))
        self.health_label.setStyleSheet("color: #cccccc;")
        health_layout.addWidget(self.health_label)

        layout.addWidget(health_group)

        # Set stretch to push everything to top
        layout.addStretch()

    def set_system_service(self, system_service):
        """Set the system service for data retrieval."""
        self.system_service = system_service

    def update_system_info(self, system_info: Dict[str, Any]):
        """Update system information display."""
        if not system_info:
            return

        info_text = f"""Platform: {system_info.get('platform', 'Unknown')}
CPU Cores: {system_info.get('cpu_cores', 'Unknown')}
Memory: {system_info.get('memory_total', 'Unknown')} GB
System: {system_info.get('system', 'Unknown')}"""

        self.system_info_text.setText(info_text)

    def update_metrics(self, cpu_percent: float = 0, memory_percent: float = 0,
                      disk_percent: float = 0, network_speed: float = 0):
        """Update performance metrics."""
        self.cpu_card.set_value(f"{cpu_percent:.1f}")
        self.memory_card.set_value(f"{memory_percent:.1f}")
        self.disk_card.set_value(f"{disk_percent:.1f}")
        self.network_card.set_value(f"{network_speed:.1f}")

    def update_health(self, health_percent: float):
        """Update system health display."""
        self.health_bar.setValue(int(health_percent))
        self.health_label.setText(f"Health: {health_percent:.1f}%")

        # Update progress bar color based on health
        if health_percent >= 80:
            color = "#00cc44"  # Green
        elif health_percent >= 60:
            color = "#ffaa00"  # Yellow
        else:
            color = "#cc0000"  # Red

        self.health_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #3e3e42;
                border-radius: 4px;
                text-align: center;
                background-color: #1e1e1e;
            }}
            QProgressBar::chunk {{
                background-color: {color};
            }}
        """)