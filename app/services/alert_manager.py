# app/services/alert_manager.py
"""
Enterprise-grade Alert Management System for the HET IT Control System.
Features:
- Multi-channel alerting (Email, Telegram, Desktop)
- Alert deduplication and rate limiting
- Alert escalation and prioritization
- Alert history and analytics
- Configurable alert rules
"""

import threading
import time
import json
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import logging

from app.config.settings import get_config
from app.infrastructure.logger import get_logger
from app.infrastructure.exceptions import AlertingError

logger = get_logger("alert_manager")


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status."""
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


@dataclass
class Alert:
    """Alert data structure."""
    id: str
    title: str
    message: str
    severity: AlertSeverity
    source: str
    status: AlertStatus = AlertStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "severity": self.severity.value,
            "source": self.source,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "tags": self.tags,
            "metadata": self.metadata
        }


@dataclass
class AlertRule:
    """Alert rule configuration."""
    name: str
    condition: Callable[[Dict[str, Any]], bool]
    severity: AlertSeverity
    title_template: str
    message_template: str
    cooldown_seconds: int = 300
    enabled: bool = True
    channels: List[str] = field(default_factory=lambda: ["email"])


class AlertChannel:
    """Base class for alert channels."""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.logger = get_logger(f"alert_channel_{name}")

    def send_alert(self, alert: Alert) -> bool:
        """Send alert through this channel. Must be implemented by subclasses."""
        raise NotImplementedError

    def test_connection(self) -> bool:
        """Test channel connectivity. Default implementation returns True."""
        return True


class EmailChannel(AlertChannel):
    """Email alert channel."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__("email", config)
        self.smtp_config = config.get("email", {})

    def send_alert(self, alert: Alert) -> bool:
        """Send alert via email."""
        try:
            if not self.smtp_config.get("recipients"):
                self.logger.warning("No email recipients configured")
                return False

            msg = MIMEMultipart()
            msg['From'] = self.smtp_config.get("smtp_username", "alerts@het-system.com")
            msg['To'] = ", ".join(self.smtp_config["recipients"])
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.title}"

            body = f"""
HET IT Control System Alert

Title: {alert.title}
Severity: {alert.severity.value.upper()}
Source: {alert.source}
Time: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}

Message:
{alert.message}

Status: {alert.status.value.upper()}

Metadata:
{json.dumps(alert.metadata, indent=2)}

Tags:
{json.dumps(alert.tags, indent=2)}
"""
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(
                self.smtp_config["smtp_host"],
                self.smtp_config["smtp_port"]
            )

            if self.smtp_config.get("smtp_tls", True):
                server.starttls()

            if self.smtp_config.get("smtp_username") and self.smtp_config.get("smtp_password"):
                server.login(
                    self.smtp_config["smtp_username"],
                    self.smtp_config["smtp_password"]
                )

            server.send_message(msg)
            server.quit()

            self.logger.info(f"Alert email sent to {len(self.smtp_config['recipients'])} recipients")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send alert email: {e}")
            return False

    def test_connection(self) -> bool:
        """Test SMTP connection."""
        try:
            server = smtplib.SMTP(
                self.smtp_config["smtp_host"],
                self.smtp_config["smtp_port"],
                timeout=10
            )

            if self.smtp_config.get("smtp_tls", True):
                server.starttls()

            if self.smtp_config.get("smtp_username") and self.smtp_config.get("smtp_password"):
                server.login(
                    self.smtp_config["smtp_username"],
                    self.smtp_config["smtp_password"]
                )

            server.quit()
            return True

        except Exception as e:
            self.logger.error(f"SMTP connection test failed: {e}")
            return False


class TelegramChannel(AlertChannel):
    """Telegram alert channel."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__("telegram", config)
        self.bot_token = config.get("telegram_bot_token")
        self.chat_id = config.get("telegram_chat_id")
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

    def send_alert(self, alert: Alert) -> bool:
        """Send alert via Telegram."""
        try:
            if not self.bot_token or not self.chat_id:
                self.logger.warning("Telegram bot token or chat ID not configured")
                return False

            emoji_map = {
                AlertSeverity.LOW: "ℹ️",
                AlertSeverity.MEDIUM: "⚠️",
                AlertSeverity.HIGH: "🚨",
                AlertSeverity.CRITICAL: "🔴"
            }

            emoji = emoji_map.get(alert.severity, "❓")

            message = f"""{emoji} **{alert.title}**

*Severity:* {alert.severity.value.upper()}
*Source:* {alert.source}
*Time:* {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}

{alert.message}

*Status:* {alert.status.value.upper()}"""

            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_notification": alert.severity == AlertSeverity.LOW
            }

            response = requests.post(
                f"{self.api_url}/sendMessage",
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                self.logger.info("Alert sent via Telegram")
                return True
            else:
                self.logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to send Telegram alert: {e}")
            return False

    def test_connection(self) -> bool:
        """Test Telegram bot connectivity."""
        try:
            response = requests.get(f"{self.api_url}/getMe", timeout=10)
            return response.status_code == 200 and response.json().get("ok")
        except Exception as e:
            self.logger.error(f"Telegram connection test failed: {e}")
            return False


class DesktopChannel(AlertChannel):
    """Desktop notification channel."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__("desktop", config)
        self._toast_available = self._check_toast_support()

    def _check_toast_support(self) -> bool:
        """Check if toast notifications are available."""
        try:
            from win11toast import toast
            return True
        except ImportError:
            try:
                import plyer
                return True
            except ImportError:
                return False

    def send_alert(self, alert: Alert) -> bool:
        """Send desktop notification."""
        try:
            if not self._toast_available:
                self.logger.warning("Desktop notifications not available (missing win11toast or plyer)")
                return False

            title = f"HET Alert - {alert.severity.value.upper()}"
            message = f"{alert.title}\n{alert.message[:200]}..."

            # Try win11toast first (Windows 11)
            try:
                from win11toast import toast
                toast(title, message, duration="long")
                return True
            except ImportError:
                pass

            # Fallback to plyer
            try:
                import plyer
                plyer.notification.notify(
                    title=title,
                    message=message,
                    app_name="HET IT Control System",
                    timeout=10
                )
                return True
            except ImportError:
                pass

            self.logger.warning("No desktop notification library available")
            return False

        except Exception as e:
            self.logger.error(f"Failed to send desktop notification: {e}")
            return False


class AlertManager:
    """Central alert management system."""

    def __init__(self):
        self.config = get_config()
        self.logger = get_logger("alert_manager")

        # Alert storage
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_history: List[Alert] = []
        self._max_history_size = 1000

        # Rate limiting
        self._alert_counts: Dict[str, List[datetime]] = {}
        self._cooldowns: Dict[str, datetime] = {}

        # Channels
        self._channels: Dict[str, AlertChannel] = {}
        self._initialize_channels()

        # Rules
        self._rules: List[AlertRule] = []
        self._initialize_rules()

        # Threading
        self._lock = threading.RLock()
        self._worker_thread = None
        self._stop_event = threading.Event()
        self._alert_queue: List[Alert] = []

        # Callbacks
        self._alert_callbacks: List[Callable[[Alert], None]] = []

    def _initialize_channels(self):
        """Initialize alert channels."""
        config = self.config

        # Email channel
        if config.alerting.email_enabled:
            self._channels["email"] = EmailChannel({
                "email": {
                    "smtp_host": config.email.smtp_host,
                    "smtp_port": config.email.smtp_port,
                    "smtp_username": config.email.smtp_username,
                    "smtp_password": config.email.smtp_password,
                    "smtp_tls": config.email.smtp_tls,
                    "recipients": config.email.recipients
                }
            })

        # Telegram channel
        if config.alerting.telegram_enabled:
            self._channels["telegram"] = TelegramChannel({
                "telegram_bot_token": config.alerting.telegram_bot_token,
                "telegram_chat_id": config.alerting.telegram_chat_id
            })

        # Desktop channel
        if config.alerting.desktop_enabled:
            self._channels["desktop"] = DesktopChannel({})

    def _initialize_rules(self):
        """Initialize built-in alert rules."""
        # Job failure rule
        self.add_rule(AlertRule(
            name="job_failure_threshold",
            condition=lambda data: (
                data.get("type") == "job_failed" and
                data.get("failure_count", 0) >= self.config.alerting.job_failure_threshold
            ),
            severity=AlertSeverity.HIGH,
            title_template="Job Failure Threshold Exceeded",
            message_template="Job '{job_id}' has failed {failure_count} times in the last hour",
            cooldown_seconds=self.config.alerting.cooldown_period,
            channels=["email", "telegram", "desktop"]
        ))

        # Job timeout rule
        self.add_rule(AlertRule(
            name="job_timeout",
            condition=lambda data: (
                data.get("type") == "job_timeout" and
                data.get("duration", 0) > self.config.alerting.job_timeout_threshold
            ),
            severity=AlertSeverity.CRITICAL,
            title_template="Job Timeout Alert",
            message_template="Job '{job_id}' exceeded timeout threshold ({duration}s > {threshold}s)",
            cooldown_seconds=self.config.alerting.cooldown_period,
            channels=["email", "telegram", "desktop"]
        ))

        # Scheduler heartbeat rule
        self.add_rule(AlertRule(
            name="scheduler_down",
            condition=lambda data: data.get("type") == "scheduler_down",
            severity=AlertSeverity.CRITICAL,
            title_template="Scheduler Down Alert",
            message_template="Job scheduler has stopped responding. Last heartbeat: {last_heartbeat}",
            cooldown_seconds=self.config.alerting.cooldown_period,
            channels=["email", "telegram", "desktop"]
        ))

        # System resource rules
        self.add_rule(AlertRule(
            name="high_cpu",
            condition=lambda data: (
                data.get("type") == "cpu_high" and
                data.get("value", 0) > self.config.monitoring.cpu_threshold
            ),
            severity=AlertSeverity.MEDIUM,
            title_template="High CPU Usage Alert",
            message_template="CPU usage is {value:.1f}% (threshold: {threshold}%)",
            cooldown_seconds=self.config.alerting.cooldown_period,
            channels=["email", "desktop"]
        ))

        self.add_rule(AlertRule(
            name="high_memory",
            condition=lambda data: (
                data.get("type") == "memory_high" and
                data.get("value", 0) > self.config.monitoring.memory_threshold
            ),
            severity=AlertSeverity.HIGH,
            title_template="High Memory Usage Alert",
            message_template="Memory usage is {value:.1f}% (threshold: {threshold}%)",
            cooldown_seconds=self.config.alerting.cooldown_period,
            channels=["email", "desktop"]
        ))

    def add_rule(self, rule: AlertRule):
        """Add an alert rule."""
        with self._lock:
            self._rules.append(rule)
            self.logger.info(f"Added alert rule: {rule.name}")

    def remove_rule(self, rule_name: str):
        """Remove an alert rule."""
        with self._lock:
            self._rules = [r for r in self._rules if r.name != rule_name]
            self.logger.info(f"Removed alert rule: {rule_name}")

    def add_alert_callback(self, callback: Callable[[Alert], None]):
        """Add alert callback."""
        with self._lock:
            self._alert_callbacks.append(callback)

    def trigger_alert(self, title: str, message: str, severity: AlertSeverity,
                     source: str, tags: Optional[Dict[str, Any]] = None,
                     metadata: Optional[Dict[str, Any]] = None,
                     channels: Optional[List[str]] = None) -> Optional[str]:
        """
        Trigger a manual alert.

        Returns alert ID if created, None if rate limited.
        """
        # Check rate limiting
        if not self._check_rate_limit(source):
            self.logger.debug(f"Alert rate limited for source: {source}")
            return None

        # Create alert
        alert_id = self._generate_alert_id(title, source)
        alert = Alert(
            id=alert_id,
            title=title,
            message=message,
            severity=severity,
            source=source,
            tags=tags or {},
            metadata=metadata or {}
        )

        # Queue for processing
        with self._lock:
            self._alert_queue.append(alert)
            self._active_alerts[alert_id] = alert

        # Start worker if needed
        if not self._worker_thread or not self._worker_thread.is_alive():
            self._start_worker()

        self.logger.info(f"Alert triggered: {title} (severity: {severity.value})")
        return alert_id

    def process_event(self, event_data: Dict[str, Any]):
        """Process an event and check against rules."""
        for rule in self._rules:
            if not rule.enabled:
                continue

            try:
                if rule.condition(event_data):
                    # Check cooldown
                    if not self._check_cooldown(rule.name):
                        continue

                    # Format message
                    title = rule.title_template.format(**event_data)
                    message = rule.message_template.format(**event_data)

                    # Trigger alert
                    self.trigger_alert(
                        title=title,
                        message=message,
                        severity=rule.severity,
                        source=rule.name,
                        tags={"rule": rule.name, "event_type": event_data.get("type")},
                        metadata=event_data,
                        channels=rule.channels
                    )

                    # Set cooldown
                    self._set_cooldown(rule.name, rule.cooldown_seconds)

            except Exception as e:
                self.logger.error(f"Error processing rule {rule.name}: {e}")

    def resolve_alert(self, alert_id: str, resolution_message: Optional[str] = None):
        """Resolve an active alert."""
        with self._lock:
            if alert_id in self._active_alerts:
                alert = self._active_alerts[alert_id]
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now()
                if resolution_message:
                    alert.metadata["resolution"] = resolution_message

                # Move to history
                self._alert_history.append(alert)
                if len(self._alert_history) > self._max_history_size:
                    self._alert_history.pop(0)

                del self._active_alerts[alert_id]

                self.logger.info(f"Alert resolved: {alert.title}")

                # Notify callbacks
                for callback in self._alert_callbacks:
                    try:
                        callback(alert)
                    except Exception as e:
                        self.logger.error(f"Alert callback failed: {e}")

    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        with self._lock:
            return list(self._active_alerts.values())

    def get_alert_history(self, limit: int = 50) -> List[Alert]:
        """Get alert history."""
        with self._lock:
            return self._alert_history[-limit:] if limit > 0 else self._alert_history.copy()

    def get_alert_stats(self) -> Dict[str, Any]:
        """Get alert statistics."""
        with self._lock:
            now = datetime.now()
            last_24h = now - timedelta(hours=24)
            last_7d = now - timedelta(days=7)

            recent_alerts = [a for a in self._alert_history if a.created_at >= last_24h]
            weekly_alerts = [a for a in self._alert_history if a.created_at >= last_7d]

            severity_counts = {}
            for alert in self._alert_history:
                severity_counts[alert.severity.value] = severity_counts.get(alert.severity.value, 0) + 1

            return {
                "active_alerts": len(self._active_alerts),
                "total_history": len(self._alert_history),
                "alerts_24h": len(recent_alerts),
                "alerts_7d": len(weekly_alerts),
                "severity_breakdown": severity_counts,
                "channels": list(self._channels.keys())
            }

    def test_channels(self) -> Dict[str, bool]:
        """Test all configured channels."""
        results = {}
        test_alert = Alert(
            id="test",
            title="Test Alert",
            message="This is a test alert to verify channel connectivity.",
            severity=AlertSeverity.LOW,
            source="test"
        )

        for name, channel in self._channels.items():
            try:
                # Test connection first
                if channel.test_connection():
                    # Try to send test alert
                    results[name] = channel.send_alert(test_alert)
                else:
                    results[name] = False
            except Exception as e:
                self.logger.error(f"Channel test failed for {name}: {e}")
                results[name] = False

        return results

    def _generate_alert_id(self, title: str, source: str) -> str:
        """Generate unique alert ID."""
        content = f"{title}:{source}:{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _check_rate_limit(self, source: str) -> bool:
        """Check if alert is within rate limits."""
        now = datetime.now()
        window_start = now - timedelta(hours=1)

        # Clean old entries
        self._alert_counts[source] = [
            ts for ts in self._alert_counts.get(source, [])
            if ts >= window_start
        ]

        # Check limit
        if len(self._alert_counts[source]) >= self.config.alerting.max_alerts_per_hour:
            return False

        # Add current alert
        self._alert_counts[source].append(now)
        return True

    def _check_cooldown(self, rule_name: str) -> bool:
        """Check if rule is in cooldown period."""
        cooldown_until = self._cooldowns.get(rule_name)
        if cooldown_until and datetime.now() < cooldown_until:
            return False
        return True

    def _set_cooldown(self, rule_name: str, seconds: int):
        """Set cooldown for a rule."""
        self._cooldowns[rule_name] = datetime.now() + timedelta(seconds=seconds)

    def _start_worker(self):
        """Start alert processing worker."""
        if self._worker_thread and self._worker_thread.is_alive():
            return

        self._stop_event.clear()
        self._worker_thread = threading.Thread(
            target=self._alert_worker,
            name="alert-worker",
            daemon=True
        )
        self._worker_thread.start()

    def _alert_worker(self):
        """Alert processing worker thread."""
        self.logger.info("Alert worker started")

        while not self._stop_event.is_set():
            try:
                # Process queued alerts
                with self._lock:
                    if self._alert_queue:
                        alert = self._alert_queue.pop(0)
                    else:
                        alert = None

                if alert:
                    self._process_alert(alert)

                # Sleep briefly
                time.sleep(0.1)

            except Exception as e:
                self.logger.error(f"Error in alert worker: {e}")
                time.sleep(1)

        self.logger.info("Alert worker stopped")

    def _process_alert(self, alert: Alert):
        """Process a single alert."""
        try:
            # Determine channels
            channels = alert.metadata.get("channels", ["email"])

            # Send through channels
            success_count = 0
            for channel_name in channels:
                if channel_name in self._channels:
                    if self._channels[channel_name].send_alert(alert):
                        success_count += 1

            if success_count > 0:
                self.logger.info(f"Alert sent through {success_count} channels")
            else:
                self.logger.warning("Alert failed to send through any channel")

            # Notify callbacks
            for callback in self._alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    self.logger.error(f"Alert callback failed: {e}")

        except Exception as e:
            self.logger.error(f"Failed to process alert {alert.id}: {e}")

    def shutdown(self):
        """Shutdown the alert manager."""
        self.logger.info("Shutting down alert manager")
        self._stop_event.set()

        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5.0)


# Global instance
_alert_manager = None

def get_alert_manager() -> AlertManager:
    """Get the global alert manager instance."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


# Convenience functions
def trigger_alert(title: str, message: str, severity: AlertSeverity = AlertSeverity.MEDIUM,
                 source: str = "system", **kwargs) -> Optional[str]:
    """Trigger an alert."""
    manager = get_alert_manager()
    return manager.trigger_alert(title, message, severity, source, **kwargs)


def process_event(event_data: Dict[str, Any]):
    """Process an event through alert rules."""
    manager = get_alert_manager()
    manager.process_event(event_data)