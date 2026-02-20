# app/ui/main_window.py
"""
HET IT Control System - Enterprise Dashboard (PRO)
✅ Jobs panel: auto-discover + run + schedule (calendar/time easy)
✅ System dashboard (basic summary)
✅ Activity logs
✅ Job history (SQLite) table-like viewer
✅ Status badges + Last Run + Next Run + Duration
✅ Branch dropdown per job
"""
from __future__ import annotations
import sys
import time
import inspect
import importlib
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Any, List, Dict, Tuple
from PySide6.QtCore import Qt, Signal, QObject, QRunnable, QThreadPool, QTimer, QDateTime
from PySide6.QtGui import QFont, QPalette, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSplitter, QFrame, QScrollArea, QMessageBox,
    QComboBox, QLineEdit, QDateTimeEdit, QTabWidget
)
# ------------------ ROOT PATH ------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
JOBS_DIR = PROJECT_ROOT / "app" / "jobs"
# ------------------ DB + Scheduler ------------------
from app.infrastructure.job_history_db import log_job, get_last_run, get_history, init_db
from app.infrastructure.scheduler import get_scheduler
from app.gui.monitoring_panel import MonitoringPanel
from app.infrastructure.monitoring import start_system_monitoring, record_scheduler_heartbeat, get_system_health, start_job_monitoring, update_job_status
# optional system info
try:
    import psutil
except Exception:
    psutil = None
# ------------------ UI BUS ------------------
class UiBus(QObject):
    log = Signal(str, str)  # msg, level
    job_done = Signal(str, bool, str, float, str)  # job_id, success, msg, dur, branch
UIBUS = UiBus()
@dataclass
class JobSpec:
    job_id: str
    title: str
    module_name: str
    entry_name: str
    entry_type: str  # "function" | "class"
    error: Optional[str] = None
    exception: Optional[str] = None
# ------------------ DISCOVERY ------------------
SKIP_MODULES = {"__init__", "email_job"}  # helper modules not shown as runnable jobs
FUNC_PRIORITY = ["run_job", "main"]
FUNC_PREFIXES = ("run_", "generate_", "restart_", "check_", "sync_")  # exclude send_ to avoid email helpers
EXCLUDE_PREFIXES = ("send_", "get_", "set_", "is_", "has_", "validate_", "test_")  # functions to exclude
def _is_runnable_function(func) -> bool:
    """Check if a function can be called without required arguments."""
    try:
        sig = inspect.signature(func)
        # Must have no required parameters (or only self for methods)
        required_params = [
            p for p in sig.parameters.values()
            if p.default == inspect.Parameter.empty and p.name != 'self'
        ]
        return len(required_params) == 0
    except Exception:
        return False
def _pick_entry(module) -> Optional[Tuple[str, str]]:
    # priority funcs
    for nm in FUNC_PRIORITY:
        if hasattr(module, nm) and callable(getattr(module, nm)):
            func = getattr(module, nm)
            if _is_runnable_function(func):
                return nm, "function"
    # prefixed functions (safe list, exclude dangerous ones)
    for nm in dir(module):
        if nm.startswith(FUNC_PREFIXES) and not nm.startswith(EXCLUDE_PREFIXES):
            obj = getattr(module, nm)
            if callable(obj) and _is_runnable_function(obj):
                return nm, "function"
    # classes with execute() / run() - but NOT abstract
    for nm in dir(module):
        obj = getattr(module, nm)
        if inspect.isclass(obj) and obj.__module__ == module.__name__:
            # Skip abstract classes
            if inspect.isabstract(obj):
                continue
            # Check if it has execute() or run()
            if hasattr(obj, "execute") and callable(getattr(obj, "execute")):
                return nm, "class"
            if hasattr(obj, "run") and callable(getattr(obj, "run")):
                return nm, "class"
    return None
def discover_jobs() -> List[JobSpec]:
    specs: List[JobSpec] = []
    if not JOBS_DIR.exists():
        return specs
    for py in sorted(JOBS_DIR.glob("*.py")):
        if py.name.startswith("__"):
            continue
        if py.stem in SKIP_MODULES:
            continue
        module_name = f"app.jobs.{py.stem}"
        job_id = py.stem
        try:
            module = importlib.import_module(module_name)
            picked = _pick_entry(module)
            if not picked:
                specs.append(JobSpec(
                    job_id=job_id,
                    title=job_id.replace("_", " ").title(),
                    module_name=module_name,
                    entry_name="",
                    entry_type="",
                    error="No runnable entry found (run_job/main/run_* or runnable class missing)"
                ))
                continue
            entry_name, entry_type = picked
            doc = getattr(module, "__doc__", None)
            title = doc.splitlines()[0].strip() if doc else job_id.replace("_", " ").title()
            specs.append(JobSpec(
                job_id=job_id,
                title=title,
                module_name=module_name,
                entry_name=entry_name,
                entry_type=entry_type
            ))
        except Exception as e:
            specs.append(JobSpec(
                job_id=job_id,
                title=job_id.replace("_", " ").title(),
                module_name=module_name,
                entry_name="",
                entry_type="",
                error=str(e),
                exception=traceback.format_exc()
            ))
    return specs
# ------------------ WORKER ------------------
class JobRunner(QRunnable):
    def __init__(self, spec: JobSpec, branch: str):
        super().__init__()
        self.spec = spec
        self.branch = branch
    def run(self):
        start = time.time()
        # Start job monitoring
        start_job_monitoring(self.spec.job_id, self.branch)
        UIBUS.log.emit(f"Starting job: {self.spec.job_id} | Branch={self.branch}", "INFO")
        success = False
        message = ""
        duration = 0.0
        try:
            module = importlib.import_module(self.spec.module_name)
            if self.spec.entry_type == "function":
                fn = getattr(module, self.spec.entry_name)
                result = fn()
                success = True
                message = str(result) if result is not None else "Completed"
            elif self.spec.entry_type == "class":
                cls = getattr(module, self.spec.entry_name)
                # Try different instantiation strategies
                instance = None
                try:
                    # Try no-arg constructor first (legacy compatibility)
                    instance = cls()
                except TypeError:
                    try:
                        # Try BaseJob-style constructor
                        instance = cls(self.spec.job_id, {"branch": self.branch}, self.branch)
                    except TypeError:
                        # Try single arg constructor
                        instance = cls(self.spec.job_id)
                if instance is None:
                    raise RuntimeError(f"Cannot instantiate {cls.__name__}")
                # Call the execution method
                if hasattr(instance, "execute") and callable(instance.execute):
                    result = instance.execute()
                elif hasattr(instance, "run") and callable(instance.run):
                    result = instance.run()
                else:
                    raise RuntimeError("Class has no execute() or run() method")
                # Handle different result types
                if hasattr(result, "success"):
                    # JobResult-like object
                    success = result.success
                    message = result.message or ("Success" if success else "Failed")
                    if hasattr(result, "error") and result.error:
                        message += f" | Error: {result.error}"
                else:
                    # Raw result - assume success
                    success = True
                    message = str(result) if result is not None else "Completed"
            duration = time.time() - start
            # Update job monitoring
            update_job_status(self.spec.job_id, "completed", duration=duration)
            # Log to database
            log_job(
                job_id=self.spec.job_id,
                status="SUCCESS" if success else "FAILED",
                message=message,
                duration=duration,
                branch=self.branch
            )
            UIBUS.log.emit(f"Job {self.spec.job_id} completed: {message} ({duration:.2f}s)", "INFO" if success else "ERROR")
        except Exception as e:
            duration = time.time() - start
            success = False
            message = f"Exception: {str(e)}"
            # Update job monitoring
            update_job_status(self.spec.job_id, "failed", error_message=message, duration=duration)
            # Log failure to database
            log_job(
                job_id=self.spec.job_id,
                status="FAILED",
                message=message,
                duration=duration,
                branch=self.branch
            )
            UIBUS.log.emit(f"Job {self.spec.job_id} failed: {message}", "ERROR")
        # Emit completion signal
        UIBUS.job_done.emit(self.spec.job_id, success, message, duration, self.branch)
# ------------------ UI HELPERS ------------------
def _color(level: str) -> str:
    return {
        "INFO": "#9cdcfe",
        "SUCCESS": "#00cc44",
        "ERROR": "#ff6b6b",
        "WARN": "#ffd866",
    }.get(level, "#ddd")
def _badge_color(status: str) -> str:
    s = (status or "").upper()
    if s in ("SUCCESS", "OK"):
        return "#00cc44"
    if s in ("FAILED", "ERROR"):
        return "#ff6b6b"
    if s == "RUNNING":
        return "#ffd866"
    return "#9cdcfe"
# ------------------ WIDGETS ------------------
class LogPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QFrame { background:#1e1e1e; border:1px solid #3e3e42; border-radius:12px; }
            QLabel { color:white; }
            QPushButton {
                background-color:#0078d4; color:white; border-radius:6px; padding:6px 10px;
            }
            QPushButton:hover { background-color:#1391ff; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        header = QHBoxLayout()
        title = QLabel("Activity Logs")
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        header.addWidget(title)
        header.addStretch()
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFixedWidth(80)
        self.clear_btn.clicked.connect(self.clear)
        header.addWidget(self.clear_btn)
        layout.addLayout(header)
        from PySide6.QtWidgets import QTextEdit
        self.box = QTextEdit()
        self.box.setReadOnly(True)
        self.box.setStyleSheet("background:#111; color:#ddd; border:1px solid #333;")
        layout.addWidget(self.box)
    def clear(self):
        self.box.clear()
    def add(self, msg: str, level: str = "INFO"):
        self.box.append(f'<span style="color:{_color(level)}">[{level}] {msg}</span>')
class HistoryPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QFrame { background:#1e1e1e; border:1px solid #3e3e42; border-radius:12px; }
            QLabel { color:white; }
            QComboBox {
                background:#1e1e1e; border:1px solid #3e3e42; border-radius:6px; padding:6px; color:#ddd;
            }
            QPushButton {
                background-color:#0078d4; color:white; border-radius:6px; padding:6px 10px;
            }
            QPushButton:hover { background-color:#1391ff; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        top = QHBoxLayout()
        title = QLabel("Job Execution History")
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        top.addWidget(title)
        top.addStretch()
        self.filter = QComboBox()
        self.filter.addItem("All Jobs")
        top.addWidget(self.filter)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        top.addWidget(self.refresh_btn)
        layout.addLayout(top)
        from PySide6.QtWidgets import QTextEdit
        self.box = QTextEdit()
        self.box.setReadOnly(True)
        self.box.setStyleSheet("background:#111; color:#ddd; border:1px solid #333;")
        layout.addWidget(self.box)
    def set_jobs(self, job_ids: List[str]):
        current = self.filter.currentText()
        self.filter.clear()
        self.filter.addItem("All Jobs")
        for j in job_ids:
            self.filter.addItem(j)
        if current in job_ids:
            self.filter.setCurrentText(current)
    def refresh(self):
        self.box.clear()
        selected = self.filter.currentText()
        job_id = None if selected == "All Jobs" else selected
        rows = get_history(job_id=job_id, limit=80)
        if not rows:
            self.box.append("No history yet.")
            return
        for created_at, jid, branch, dur, status, msg in rows:
            color = _badge_color(status)
            self.box.append(
                f'<span style="color:{color}; font-weight:bold;">{status}</span> '
                f'<span style="color:#9cdcfe;">{created_at}</span> '
                f'<span style="color:#c8c8c8;">[{jid}]</span> '
                f'<span style="color:#ffd866;">({branch})</span> '
                f'<span style="color:#ddd;">dur={dur}s</span><br/>'
                f'<span style="color:#888;">{msg}</span><br/><br/>'
            )
class JobCard(QFrame):
    def __init__(self, spec: JobSpec, on_run, on_schedule, on_unschedule, scheduler, parent=None):
        super().__init__(parent)
        self.spec = spec
        self.on_run = on_run
        self.on_schedule = on_schedule
        self.on_unschedule = on_unschedule
        self.scheduler = scheduler
        self.setStyleSheet("""
            QFrame { background:#2d2d30; border:1px solid #3e3e42; border-radius:12px; }
            QLabel { color:white; }
            QComboBox, QLineEdit, QDateTimeEdit {
                background:#1e1e1e; border:1px solid #3e3e42; border-radius:6px; padding:6px; color:#ddd;
            }
            QPushButton {
                background-color:#0078d4; color:white; border-radius:6px; padding:6px 10px;
            }
            QPushButton:hover { background-color:#1391ff; }
            QPushButton:disabled { background:#444; color:#aaa; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        # title row
        top = QHBoxLayout()
        self.title = QLabel(spec.title)
        self.title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        top.addWidget(self.title)
        top.addStretch()
        self.badge = QLabel("READY")
        self.badge.setStyleSheet(f"color:{_badge_color('READY')}; font-weight:bold;")
        top.addWidget(self.badge)
        layout.addLayout(top)
        self.meta = QLabel(f"Job ID: {spec.job_id}")
        self.meta.setStyleSheet("color:#c8c8c8; font-size:11px;")
        layout.addWidget(self.meta)
        self.last_run = QLabel("Last Run: — | Duration: — | Branch: —")
        self.last_run.setStyleSheet("color:#9cdcfe; font-size:11px;")
        layout.addWidget(self.last_run)
        self.next_run = QLabel("Next Run: —")
        self.next_run.setStyleSheet("color:#c8c8c8; font-size:11px;")
        layout.addWidget(self.next_run)
        # branch + mode
        row1 = QHBoxLayout()
        self.branch_box = QComboBox()
        self.branch_box.addItems(["default", "Kano", "Abuja", "Lagos", "BUK", "DXB"])
        row1.addWidget(self.branch_box, 2)
        self.mode = QComboBox()
        self.mode.addItems(["Run Once", "Daily", "Weekly", "Cron"])
        self.mode.currentTextChanged.connect(self._mode_changed)
        row1.addWidget(self.mode, 2)
        layout.addLayout(row1)
        # schedule controls (dynamic)
        self.run_once_dt = QDateTimeEdit()
        self.run_once_dt.setCalendarPopup(True)
        self.run_once_dt.setDateTime(QDateTime.currentDateTime().addSecs(300))  # +5 min
        self.daily_time = QLineEdit()
        self.daily_time.setPlaceholderText("HH:MM  (e.g. 09:00)")
        self.daily_time.setText("09:00")
        self.week_day = QComboBox()
        self.week_day.addItems(["mon", "tue", "wed", "thu", "fri", "sat", "sun"])
        self.week_time = QLineEdit()
        self.week_time.setPlaceholderText("HH:MM  (e.g. 11:10)")
        self.week_time.setText("11:10")
        self.cron = QLineEdit()
        self.cron.setPlaceholderText("Cron: m h dom mon dow  (0 9 * * *)")
        self.cron.setText("0 9 * * *")
        self.ctrl_row = QHBoxLayout()
        self.ctrl_row.addWidget(self.run_once_dt)
        layout.addLayout(self.ctrl_row)
        # buttons
        btns = QHBoxLayout()
        btns.addStretch()
        self.run_btn = QPushButton("▶ Run")
        self.run_btn.clicked.connect(self._run_clicked)
        btns.addWidget(self.run_btn)
        self.sch_btn = QPushButton("⏱ Schedule")
        self.sch_btn.clicked.connect(self._schedule_clicked)
        btns.addWidget(self.sch_btn)
        self.uns_btn = QPushButton("✖ Remove")
        self.uns_btn.clicked.connect(self._unschedule_clicked)
        btns.addWidget(self.uns_btn)
        layout.addLayout(btns)
        if spec.error:
            self.badge.setText("ERROR")
            self.badge.setStyleSheet(f"color:{_badge_color('ERROR')}; font-weight:bold;")
            self.run_btn.setEnabled(False)
            self.sch_btn.setEnabled(False)
            self.uns_btn.setEnabled(False)
        self.refresh_last_next()
    def selected_branch(self) -> str:
        return self.branch_box.currentText().strip() or "default"
    def refresh_last_next(self):
        # last run
        last = get_last_run(self.spec.job_id)
        if last:
            st, dur, ts, br = last
            self.last_run.setText(f"Last Run: {ts} | Duration: {dur}s | Branch: {br}")
            self.badge.setText(st.upper())
            self.badge.setStyleSheet(f"color:{_badge_color(st)}; font-weight:bold;")
        # next run
        if hasattr(self, 'scheduler') and self.scheduler:
            nxt = self.scheduler.get_next_run_time(self.spec.job_id)
            self.next_run.setText(f"Next Run: {nxt}" if nxt else "Next Run: —")
        else:
            self.next_run.setText("Next Run: —")
    def set_running(self):
        self.run_btn.setEnabled(False)
        self.badge.setText("RUNNING")
        self.badge.setStyleSheet(f"color:{_badge_color('RUNNING')}; font-weight:bold;")
    def set_done(self, success: bool):
        self.run_btn.setEnabled(True)
        self.refresh_last_next()
        if success:
            self.badge.setText("SUCCESS")
            self.badge.setStyleSheet(f"color:{_badge_color('SUCCESS')}; font-weight:bold;")
        else:
            self.badge.setText("FAILED")
            self.badge.setStyleSheet(f"color:{_badge_color('FAILED')}; font-weight:bold;")
    def _mode_changed(self, mode: str):
        # clear ctrl row
        while self.ctrl_row.count():
            item = self.ctrl_row.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        if mode == "Run Once":
            self.ctrl_row.addWidget(self.run_once_dt)
        elif mode == "Daily":
            self.ctrl_row.addWidget(self.daily_time)
        elif mode == "Weekly":
            self.ctrl_row.addWidget(self.week_day)
            self.ctrl_row.addWidget(self.week_time)
        else:  # Cron
            self.ctrl_row.addWidget(self.cron)
    def _run_clicked(self):
        self.set_running()
        self.on_run(self.spec, self.selected_branch())
    def _schedule_clicked(self):
        branch = self.selected_branch()
        mode = self.mode.currentText()
        try:
            if mode == "Run Once":
                dt = self.run_once_dt.dateTime().toPython()
                self.on_schedule(self.spec, branch, ("once", dt))
            elif mode == "Daily":
                hh, mm = self.daily_time.text().strip().split(":")
                self.on_schedule(self.spec, branch, ("daily", int(hh), int(mm)))
            elif mode == "Weekly":
                dow = self.week_day.currentText().strip()
                hh, mm = self.week_time.text().strip().split(":")
                self.on_schedule(self.spec, branch, ("weekly", dow, int(hh), int(mm)))
            else:  # Cron
                expr = self.cron.text().strip()
                self.on_schedule(self.spec, branch, ("cron", expr))
        except Exception as e:
            QMessageBox.warning(self, "Schedule Error", str(e))
    def _unschedule_clicked(self):
        self.on_unschedule(self.spec.job_id)
        self.refresh_last_next()
# ------------------ MAIN WINDOW ------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        init_db()
        # Get scheduler instance
        self.scheduler = get_scheduler()
# Start system monitoring
        start_system_monitoring()
        self.setWindowTitle("HET Dashboard - Enterprise")
        self.setGeometry(120, 80, 1600, 900)
        self._apply_dark_theme()
        self.threadpool = QThreadPool.globalInstance()
        self.cards: Dict[str, JobCard] = {}
        self.jobs: List[JobSpec] = []
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(10)
        header = self._header()
        root_layout.addWidget(header)
        splitter = QSplitter(Qt.Horizontal)
        # LEFT: Jobs
        left = QFrame()
        left.setStyleSheet("background:#1e1e1e; border:1px solid #3e3e42; border-radius:12px;")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_title = QLabel("Scheduled Jobs")
        left_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        left_title.setStyleSheet("color:white;")
        left_layout.addWidget(left_title)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border:none; background:transparent;")
        self.jobs_container = QWidget()
        self.jobs_layout = QVBoxLayout(self.jobs_container)
        self.jobs_layout.setContentsMargins(6, 6, 6, 6)
        self.jobs_layout.setSpacing(10)
        self.scroll.setWidget(self.jobs_container)
        left_layout.addWidget(self.scroll)
        # CENTER: Dashboard + History + Monitoring
        center = QFrame()
        center.setStyleSheet("background:#1e1e1e; border:1px solid #3e3e42; border-radius:12px;")
        c = QVBoxLayout(center)
        c.setContentsMargins(10, 10, 10, 10)
        c.setSpacing(10)
        # Create tab widget for different panels
        self.center_tabs = QTabWidget()
        self.center_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #3e3e42;
                background: #1e1e1e;
                border-radius: 5px;
            }
            QTabBar::tab {
                background: #2d2d30;
                color: white;
                padding: 8px 16px;
                margin-right: 2px;
                border: 1px solid #3e3e42;
                border-bottom: none;
                border-radius: 5px 5px 0 0;
            }
            QTabBar::tab:selected {
                background: #1e1e1e;
                border-bottom: 2px solid #007acc;
            }
            QTabBar::tab:hover {
                background: #3e3e42;
            }
        """)
        # Dashboard tab
        dashboard_tab = QWidget()
        dashboard_layout = QVBoxLayout(dashboard_tab)
        dash_title = QLabel("System Dashboard")
        dash_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        dash_title.setStyleSheet("color:white;")
        dashboard_layout.addWidget(dash_title)
        self.sys_info = QLabel("Loading system info...")
        self.sys_info.setStyleSheet("color:#c8c8c8;")
        dashboard_layout.addWidget(self.sys_info)
        self.history = HistoryPanel()
        dashboard_layout.addWidget(self.history, 1)
        self.center_tabs.addTab(dashboard_tab, "Dashboard")
        # Monitoring tab
        self.monitoring_panel = MonitoringPanel()
        self.center_tabs.addTab(self.monitoring_panel, "Monitoring")
        c.addWidget(self.center_tabs)
        # RIGHT: Logs
        self.logs = LogPanel()
        splitter.addWidget(left)
        splitter.addWidget(center)
        splitter.addWidget(self.logs)
        splitter.setSizes([520, 650, 430])
        root_layout.addWidget(splitter)
        # Signals
        UIBUS.log.connect(self.on_log)
        UIBUS.job_done.connect(self.on_job_done)
        # Load
        self.reload_jobs()
        self._refresh_system_info()
        # timer refresh
        self.timer = QTimer()
        self.timer.timeout.connect(self._periodic_refresh)
        self.timer.start(5000)
    def _apply_dark_theme(self):
        pal = QPalette()
        pal.setColor(QPalette.Window, QColor(30, 30, 30))
        pal.setColor(QPalette.WindowText, QColor(255, 255, 255))
        pal.setColor(QPalette.Base, QColor(45, 45, 48))
        pal.setColor(QPalette.Text, QColor(255, 255, 255))
        pal.setColor(QPalette.Button, QColor(45, 45, 48))
        pal.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        self.setPalette(pal)
    def _header(self) -> QFrame:
        header = QFrame()
        header.setStyleSheet("background:#2d2d30; border:1px solid #3e3e42; border-radius:12px;")
        # Health indicator
        self.health_indicator = QLabel("● HEALTHY")
        self.health_indicator.setStyleSheet("color:#00cc44; font-size:12px; font-weight:bold;")
        h.addWidget(self.health_indicator)
        h = QHBoxLayout(header)
        h.setContentsMargins(14, 10, 14, 10)
        t = QLabel("HET IT Control System")
        t.setFont(QFont("Segoe UI", 16, QFont.Bold))
        t.setStyleSheet("color:white;")
        h.addWidget(t)
        h.addStretch()
        self.online = QLabel("● Online")
        self.online.setStyleSheet("color:#00cc44; font-size:12px; font-weight:bold;")
        h.addWidget(self.online)
        return header

    def _refresh_system_info(self):
        if psutil is None:
            self.sys_info.setText(
                f"Project Root: {PROJECT_ROOT}\nJobs Folder: {JOBS_DIR}\n\n"
                "psutil not installed - system metrics limited."
            )
            return

        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage(str(PROJECT_ROOT)).percent
        self.sys_info.setText(
            f"Project Root: {PROJECT_ROOT}\nJobs Folder: {JOBS_DIR}\n\n"
            f"CPU: {cpu}%   RAM: {mem}%   DISK: {disk}%\n"
            "Tip: Schedule is simple: Run Once / Daily / Weekly (no cron needed)."
        )

def _periodic_refresh(self):
    # Record scheduler heartbeat
    record_scheduler_heartbeat()

    # Update health indicator
    health = get_system_health()
    health_colors = {
        "healthy": "#00cc44",
        "warning": "#ff9800",
        "critical": "#ff4444",
        "unknown": "#9e9e9e"
    }
    color = health_colors.get(health.overall_status, "#9e9e9e")
    self.health_indicator.setStyleSheet(f"color:{color}; font-size:12px; font-weight:bold;")
    self.health_indicator.setText(f"● {health.overall_status.upper()}")

    # Set tooltip with issues
    if health.issues:
        tooltip = f"System Status: {health.overall_status.title()}\n\nIssues:\n" + "\n".join(f"• {issue}" for issue in health.issues[:3])
        self.health_indicator.setToolTip(tooltip)
    else:
        self.health_indicator.setToolTip(f"System Status: {health.overall_status.title()}")

    # refresh system + history + nextrun on cards
    self._refresh_system_info()
    self.history.refresh()
    for card in self.cards.values():
        card.refresh_last_next()

def on_log(self, msg: str, level: str):
    self.logs.add(msg, level)

def on_job_done(self, job_id: str, success: bool, message: str, duration: float, branch: str):
    card = self.cards.get(job_id)
    if card:
        card.set_done(success)

    if success:
        self.logs.add(f"{job_id} SUCCESS | {duration}s | {branch} | {message}", "SUCCESS")
    else:
        self.logs.add(f"{job_id} FAILED | {duration}s | {branch} | {message}", "ERROR")
        QMessageBox.warning(self, "Job Failed", f"{job_id} failed:\n{message}")

    self.history.refresh()

def clear_job_cards(self):
    for i in reversed(range(self.jobs_layout.count())):
        item = self.jobs_layout.itemAt(i)
        w = item.widget()
        if w:
            w.setParent(None)

def reload_jobs(self):
    self.clear_job_cards()
    self.cards.clear()

    self.jobs = discover_jobs()
    ids = [j.job_id for j in self.jobs]
    self.history.set_jobs(ids)

    if not self.jobs:
        lbl = QLabel("No jobs found in app/jobs")
        lbl.setStyleSheet("color:#ff6b6b;")
        self.jobs_layout.addWidget(lbl)
        self.jobs_layout.addStretch()
        return

    for spec in self.jobs:
        card = JobCard(spec, self.run_job, self.schedule_job_ui, self.unschedule_job_ui, self.scheduler, parent=self)
        self.cards[spec.job_id] = card
        self.jobs_layout.addWidget(card)

        if spec.error:
            self.logs.add(f"{spec.job_id} discovery error: {spec.error}", "ERROR")
            if spec.exception:
                self.logs.add(spec.exception, "ERROR")

    self.jobs_layout.addStretch()
    self.logs.add(f"Jobs loaded: {len(self.jobs)}", "INFO")
    self.history.refresh()

def run_job(self, spec: JobSpec, branch: str):
    if spec.error:
        self.logs.add(f"Cannot run {spec.job_id}: {spec.error}", "ERROR")
        return
    worker = JobRunner(spec, branch)
    self.threadpool.start(worker)

def schedule_job_ui(self, spec: JobSpec, branch: str, payload: tuple):
    # scheduler will call a wrapper that runs job in background safely
    def scheduled_call():
        worker = JobRunner(spec, branch)
        self.threadpool.start(worker)

    kind = payload[0]
    if kind == "once":
        dt = payload[1]
        self.scheduler.schedule_job(spec.job_id, scheduled_call, "once", {"datetime": dt}, branch)
        self.logs.add(f"Scheduled (Run Once): {spec.job_id} @ {dt} | {branch}", "INFO")

    elif kind == "daily":
        hour, minute = payload[1], payload[2]
        self.scheduler.schedule_job(spec.job_id, scheduled_call, "daily", {"hour": hour, "minute": minute}, branch)
        self.logs.add(f"Scheduled (Daily): {spec.job_id} @ {hour:02d}:{minute:02d} | {branch}", "INFO")

    elif kind == "weekly":
        dow, hour, minute = payload[1], payload[2], payload[3]
        self.scheduler.schedule_job(spec.job_id, scheduled_call, "weekly",
                                  {"day_of_week": dow, "hour": hour, "minute": minute}, branch)
        self.logs.add(f"Scheduled (Weekly): {spec.job_id} {dow} @ {hour:02d}:{minute:02d} | {branch}", "INFO")

    elif kind == "cron":
        expr = payload[1]
        self.scheduler.schedule_job(spec.job_id, scheduled_call, "cron", {"cron_expression": expr}, branch)
        self.logs.add(f"Scheduled (Cron): {spec.job_id} -> {expr} | {branch}", "INFO")

    # update UI
    card = self.cards.get(spec.job_id)
    if card:
        card.refresh_last_next()
    self.history.refresh()

def unschedule_job_ui(self, job_id: str):
    self.scheduler.unschedule_job(job_id)
    self.logs.add(f"Schedule removed: {job_id}", "WARN")


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()