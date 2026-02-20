# app/config/settings.py
"""
Production-grade configuration management for the HET IT Control System.
Features:
- Environment variable support with validation
- Configuration file support (JSON)
- Default fallbacks
- Type validation
- Hot reload capability
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional, List, Union
from dataclasses import dataclass, field
from functools import lru_cache
from dotenv import load_dotenv

from app.infrastructure.exceptions import ConfigurationError
from app.infrastructure.logger import get_logger

logger = get_logger("config")

# Load environment variables from .env file
if getattr(sys, 'frozen', False):
    # Running as PyInstaller bundle
    BASE_DIR = Path(sys.executable).parent
else:
    # Running as script
    try:
        BASE_DIR = Path(__file__).resolve().parent.parent.parent
    except NameError:
        # __file__ not defined (e.g., in PyInstaller spec analysis)
        import os
        BASE_DIR = Path(os.getcwd())

load_dotenv(BASE_DIR / ".env")


def _require_env_var(var_name: str) -> str:
    """Require an environment variable to be set."""
    value = os.getenv(var_name)
    if not value:
        raise ConfigurationError(f"Required environment variable '{var_name}' is not set. Please set it in your .env file.")
    return value


def _validate_email(email: str) -> bool:
    """Basic email validation."""
    return "@" in email and "." in email


def _validate_path(path: Union[str, Path]) -> Path:
    """Validate and convert to Path."""
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    return path_obj


@dataclass
class DatabaseConfig:
    """Database configuration with validation."""
    url: str = "sqlite:///database/het_control.db"
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    history_retention_days: int = 90

    def __post_init__(self):
        if not self.url:
            raise ConfigurationError("Database URL cannot be empty")
        if self.pool_size < 1:
            raise ConfigurationError("Pool size must be >= 1")
        if self.history_retention_days < 1:
            raise ConfigurationError("History retention days must be >= 1")


@dataclass
class EmailConfig:
    """Email configuration with validation."""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_tls: bool = True
    recipients: List[str] = field(default_factory=list)
    timeout: int = 30
    retry_attempts: int = 3

    def __post_init__(self):
        if self.smtp_username and not self.smtp_password:
            raise ConfigurationError("SMTP password required when username is set")
        if self.smtp_port not in [25, 465, 587, 2525]:
            raise ConfigurationError("Invalid SMTP port")
        for recipient in self.recipients:
            if not _validate_email(recipient):
                raise ConfigurationError(f"Invalid email recipient: {recipient}")


@dataclass
class PathConfig:
    """File system paths configuration with validation."""
    base_dir: Path
    nas_base: Path
    laundry_base: Path
    qsync_exe: Path
    export_base: Path
    logs_dir: Path
    reports_dir: Path
    database_dir: Path

    def __post_init__(self):
        # Validate critical paths exist or can be created
        for path_name, path_obj in [
            ("logs_dir", self.logs_dir),
            ("reports_dir", self.reports_dir),
            ("database_dir", self.database_dir),
            ("export_base", self.export_base)
        ]:
            try:
                path_obj.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise ConfigurationError(f"Cannot create {path_name}: {e}")


@dataclass
class LoggingConfig:
    """Logging configuration with validation."""
    level: str = "INFO"
    max_bytes: int = 10 * 1024 * 1024
    backup_count: int = 5
    json_format: bool = False
    enable_console: bool = True
    enable_file: bool = True
    log_scheduler: bool = True
    log_jobs: bool = True

    def __post_init__(self):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.level.upper() not in valid_levels:
            raise ConfigurationError(f"Invalid log level: {self.level}. Must be one of {valid_levels}")
        if self.max_bytes < 1024:
            raise ConfigurationError("Max bytes must be >= 1024")
        if self.backup_count < 1:
            raise ConfigurationError("Backup count must be >= 1")


@dataclass
class APIConfig:
    """API configuration with validation."""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    jwt_secret_key: str = "change-this-in-production-secure-key"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 30
    allowed_origins: List[str] = field(default_factory=lambda: ["http://localhost:3000", "http://localhost:8000"])
    rate_limit: int = 100
    timeout: int = 30

    def __post_init__(self):
        if not (1 <= self.port <= 65535):
            raise ConfigurationError("Port must be between 1 and 65535")
        if self.jwt_expiration_minutes < 1:
            raise ConfigurationError("JWT expiration must be >= 1 minute")


@dataclass
class SchedulerConfig:
    """Scheduler configuration with validation."""
    timezone: str = "UTC"
    job_defaults: Dict[str, Any] = field(default_factory=lambda: {
        'coalesce': True,
        'max_instances': 1,
        'misfire_grace_time': 30
    })
    max_workers: int = 10
    health_check_interval: int = 60
    dead_job_timeout: int = 3600

    def __post_init__(self):
        if self.max_workers < 1:
            raise ConfigurationError("Max workers must be >= 1")
        if self.health_check_interval < 10:
            raise ConfigurationError("Health check interval must be >= 10 seconds")


@dataclass
class MonitoringConfig:
    """Resource monitoring configuration."""
    enabled: bool = True
    memory_threshold: float = 80.0  # percentage
    cpu_threshold: float = 90.0  # percentage
    disk_threshold: float = 90.0  # percentage
    check_interval: int = 30  # seconds
    alert_email: bool = True
    memory_max_mb: float = 0  # 0 = disabled
    disk_min_free_gb: float = 1.0  # minimum free space


@dataclass
class AlertingConfig:
    """Alerting configuration."""
    enabled: bool = True
    job_failure_threshold: int = 3  # alert if job fails more than X times
    job_timeout_threshold: int = 3600  # alert if job runs longer than X seconds
    scheduler_heartbeat_timeout: int = 300  # alert if scheduler doesn't respond for X seconds
    max_alerts_per_hour: int = 10  # rate limiting
    cooldown_period: int = 300  # seconds between similar alerts

    # Alert channels
    email_enabled: bool = True
    telegram_enabled: bool = False
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    desktop_enabled: bool = True

    def __post_init__(self):
        if self.job_failure_threshold < 1:
            raise ConfigurationError("Job failure threshold must be >= 1")
        if self.job_timeout_threshold < 60:
            raise ConfigurationError("Job timeout threshold must be >= 60 seconds")
        if self.telegram_enabled and (not self.telegram_bot_token or not self.telegram_chat_id):
            raise ConfigurationError("Telegram bot token and chat ID required when Telegram is enabled")


@dataclass
class ResilienceConfig:
    """Error resilience configuration."""
    job_timeout: int = 3600  # seconds
    max_retries: int = 3
    retry_delay: int = 60  # seconds
    max_retry_delay: int = 3600  # seconds
    backoff_factor: float = 2.0
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: int = 300  # seconds
    default_timeout: float = 30.0
    network_timeout: float = 10.0
    database_timeout: float = 5.0

    def __post_init__(self):
        if self.job_timeout < 60:
            raise ConfigurationError("Job timeout must be >= 60 seconds")
        if self.max_retries < 0:
            raise ConfigurationError("Max retries cannot be negative")


@dataclass
class BranchConfig:
    """Branch-specific configuration with validation."""
    id: str
    name: str
    nas_base: Path
    tally_base: Path
    laundry_base: Path
    qsync_exe: Optional[Path] = None
    email_recipients: List[str] = field(default_factory=list)
    speed_test_enabled: bool = True
    active: bool = True

    def __post_init__(self):
        if not self.id:
            raise ConfigurationError("Branch ID cannot be empty")
        if not self.name:
            raise ConfigurationError("Branch name cannot be empty")
        for recipient in self.email_recipients:
            if not _validate_email(recipient):
                raise ConfigurationError(f"Invalid email recipient in branch {self.id}: {recipient}")


@dataclass
class AppConfig:
    """Main application configuration with validation."""
    name: str = "het IT Control System"
    version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False

    paths: PathConfig = None
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    api: APIConfig = field(default_factory=APIConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    alerting: AlertingConfig = field(default_factory=AlertingConfig)
    resilience: ResilienceConfig = field(default_factory=ResilienceConfig)
    branches: Dict[str, BranchConfig] = field(default_factory=dict)

    def __post_init__(self):
        if not self.name:
            raise ConfigurationError("Application name cannot be empty")
        if self.environment not in ["development", "staging", "production"]:
            raise ConfigurationError("Environment must be development, staging, or production")

    @property
    def config_hash(self) -> str:
        """Generate hash of current configuration for change detection."""
        config_str = json.dumps(self.__dict__, sort_keys=True, default=str)
        return hashlib.md5(config_str.encode()).hexdigest()


class ConfigLoader:
    """Production-grade centralized configuration management."""

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path("app/config")
        self._config: Optional[AppConfig] = None
        self._config_hash: Optional[str] = None
        self._config_file_mtime: Optional[float] = None

    def load(self, force_reload: bool = False) -> AppConfig:
        """
        Load and validate configuration with caching and change detection.

        Args:
            force_reload: Force reload even if cached

        Returns:
            AppConfig instance
        """
        if not force_reload and self._config is not None:
            # Check if config files have changed
            if not self._has_config_changed():
                return self._config

        logger.info("Loading configuration...")

        try:
            # Load environment variables
            env_config = self._load_env_config()

            # Load JSON config
            json_config = self._load_json_config()

            # Merge configurations (env takes precedence)
            merged = {**json_config, **env_config}

            # Validate required fields
            self._validate_config(merged)

            # Create config object
            self._config = self._create_config_object(merged)
            self._config_hash = self._config.config_hash
            self._update_file_mtime()

            logger.info(f"Configuration loaded successfully for environment: {self._config.environment}")
            return self._config

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def _has_config_changed(self) -> bool:
        """Check if configuration files have changed."""
        if self._config_file_mtime is None:
            return True

        config_file = self.config_dir / "settings.json"
        if config_file.exists():
            current_mtime = config_file.stat().st_mtime
            if current_mtime > self._config_file_mtime:
                return True

        env_file = BASE_DIR / ".env"
        if env_file.exists():
            current_mtime = env_file.stat().st_mtime
            if current_mtime > self._config_file_mtime:
                return True

        return False

    def _update_file_mtime(self):
        """Update the modification time tracking."""
        self._config_file_mtime = 0
        config_file = self.config_dir / "settings.json"
        if config_file.exists():
            self._config_file_mtime = max(self._config_file_mtime, config_file.stat().st_mtime)

        env_file = BASE_DIR / ".env"
        if env_file.exists():
            self._config_file_mtime = max(self._config_file_mtime, env_file.stat().st_mtime)

    def _load_env_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables with validation."""
        config = {}

        # App settings
        config['app'] = {
            'name': os.getenv('HET_APP_NAME', 'het IT Control System'),
            'version': os.getenv('HET_APP_VERSION', '1.0.0'),
            'environment': os.getenv('HET_ENVIRONMENT', 'development'),
            'debug': os.getenv('HET_DEBUG', 'false').lower() == 'true'
        }

        # Database
        config['database'] = {
            'url': os.getenv('HET_DATABASE_URL', 'sqlite:///database/het_control.db'),
            'echo': os.getenv('HET_DATABASE_ECHO', 'false').lower() == 'true',
            'pool_size': int(os.getenv('HET_DATABASE_POOL_SIZE', '5')),
            'max_overflow': int(os.getenv('HET_DATABASE_MAX_OVERFLOW', '10')),
            'pool_timeout': int(os.getenv('HET_DATABASE_POOL_TIMEOUT', '30')),
            'pool_recycle': int(os.getenv('HET_DATABASE_POOL_RECYCLE', '3600')),
            'history_retention_days': int(os.getenv('HET_HISTORY_RETENTION_DAYS', '90'))
        }

        # Email
        config['email'] = {
            'smtp_host': os.getenv('HET_SMTP_HOST', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('HET_SMTP_PORT', '587')),
            'smtp_username': os.getenv('HET_SMTP_USERNAME'),
            'smtp_password': os.getenv('HET_SMTP_PASSWORD'),
            'smtp_tls': os.getenv('HET_SMTP_TLS', 'true').lower() == 'true',
            'recipients': [r.strip() for r in os.getenv('HET_EMAIL_RECIPIENTS', '').split(',') if r.strip()],
            'timeout': int(os.getenv('HET_SMTP_TIMEOUT', '30')),
            'retry_attempts': int(os.getenv('HET_SMTP_RETRY_ATTEMPTS', '3'))
        }

        # API
        config['api'] = {
            'host': os.getenv('HET_API_HOST', '0.0.0.0'),
            'port': int(os.getenv('HET_API_PORT', '8000')),
            'debug': os.getenv('HET_API_DEBUG', 'false').lower() == 'true',
            'jwt_secret_key': os.getenv('HET_JWT_SECRET_KEY') or _require_env_var('HET_JWT_SECRET_KEY'),
            'jwt_algorithm': os.getenv('HET_JWT_ALGORITHM', 'HS256'),
            'jwt_expiration_minutes': int(os.getenv('HET_JWT_EXPIRATION_MINUTES', '30')),
            'allowed_origins': [o.strip() for o in os.getenv('HET_ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:8000').split(',')],
            'rate_limit': int(os.getenv('HET_API_RATE_LIMIT', '100')),
            'timeout': int(os.getenv('HET_API_TIMEOUT', '30'))
        }

        # Logging
        config['logging'] = {
            'level': os.getenv('HET_LOG_LEVEL', 'INFO'),
            'max_bytes': int(os.getenv('HET_LOG_MAX_BYTES', str(10 * 1024 * 1024))),
            'backup_count': int(os.getenv('HET_LOG_BACKUP_COUNT', '5')),
            'json_format': os.getenv('HET_LOG_JSON_FORMAT', 'false').lower() == 'true',
            'enable_console': os.getenv('HET_LOG_CONSOLE', 'true').lower() == 'true',
            'enable_file': os.getenv('HET_LOG_FILE', 'true').lower() == 'true',
            'log_scheduler': os.getenv('HET_LOG_SCHEDULER', 'true').lower() == 'true',
            'log_jobs': os.getenv('HET_LOG_JOBS', 'true').lower() == 'true'
        }

        # Monitoring
        config['monitoring'] = {
            'enabled': os.getenv('HET_MONITORING_ENABLED', 'true').lower() == 'true',
            'memory_threshold': float(os.getenv('HET_MEMORY_THRESHOLD', '80.0')),
            'cpu_threshold': float(os.getenv('HET_CPU_THRESHOLD', '90.0')),
            'disk_threshold': float(os.getenv('HET_DISK_THRESHOLD', '90.0')),
            'check_interval': int(os.getenv('HET_MONITORING_INTERVAL', '30')),
            'alert_email': os.getenv('HET_MONITORING_ALERT_EMAIL', 'true').lower() == 'true'
        }

        # Resilience
        config['resilience'] = {
            'job_timeout': int(os.getenv('HET_JOB_TIMEOUT', '3600')),
            'max_retries': int(os.getenv('HET_MAX_RETRIES', '3')),
            'retry_delay': int(os.getenv('HET_RETRY_DELAY', '60')),
            'circuit_breaker_threshold': int(os.getenv('HET_CIRCUIT_BREAKER_THRESHOLD', '5')),
            'circuit_breaker_timeout': int(os.getenv('HET_CIRCUIT_BREAKER_TIMEOUT', '300'))
        }

        # Paths
        base_dir = Path(os.getenv('HET_BASE_DIR', str(BASE_DIR)))
        config['paths'] = {
            'base_dir': base_dir,
            'nas_base': _validate_path(os.getenv('HET_NAS_BASE', r"\\het-nas\Tally-Africa")),
            'laundry_base': _validate_path(os.getenv('HET_LAUNDRY_BASE', r"\\het-NAS\G-SSS300")),
            'qsync_exe': Path(os.getenv('HET_QSYNC_EXE', r"C:\Program Files (x86)\QNAP\Qsync\Qsync.exe")),
            'export_base': _validate_path(os.getenv('HET_EXPORT_BASE', str(base_dir / "exports"))),
            'logs_dir': _validate_path(os.getenv('HET_LOGS_DIR', str(base_dir / "logs"))),
            'reports_dir': _validate_path(os.getenv('HET_REPORTS_DIR', str(base_dir / "reports"))),
            'database_dir': _validate_path(os.getenv('HET_DATABASE_DIR', str(base_dir / "database")))
        }

        # Scheduler
        config['scheduler'] = {
            'timezone': os.getenv('HET_SCHEDULER_TIMEZONE', 'UTC'),
            'max_workers': int(os.getenv('HET_SCHEDULER_MAX_WORKERS', '10')),
            'health_check_interval': int(os.getenv('HET_SCHEDULER_HEALTH_CHECK_INTERVAL', '60')),
            'dead_job_timeout': int(os.getenv('HET_SCHEDULER_DEAD_JOB_TIMEOUT', '3600'))
        }

        # Branches (loaded from separate file or env)
        config['branches'] = self._load_branches_config()

        return config

    def _load_json_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file with error handling."""
        config_file = self.config_dir / "settings.json"
        if not config_file.exists():
            return {}

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.debug(f"Loaded JSON config from {config_file}")
                return data
        except Exception as e:
            logger.warning(f"Failed to load config file {config_file}: {e}")
            return {}

    def _load_branches_config(self) -> Dict[str, BranchConfig]:
        """Load branch configurations with validation."""
        branches = {}

        # Default branch
        branches['default'] = BranchConfig(
            id='default',
            name='Default Branch',
            nas_base=Path(r"\\het-nas\Tally-Africa"),
            tally_base=Path(r"\\het-nas\Tally-Africa\T-Current"),
            laundry_base=Path(r"\\het-NAS\G-SSS300"),
            qsync_exe=Path(r"C:\Program Files (x86)\QNAP\Qsync\Qsync.exe"),
            email_recipients=['hetgraphic17@gmail.com'],
            speed_test_enabled=True,
            active=True
        )

        # Load additional branches from environment or config file
        branches_file = self.config_dir / "branches.json"
        if branches_file.exists():
            try:
                with open(branches_file, 'r', encoding='utf-8') as f:
                    branches_data = json.load(f)
                    for branch_id, branch_data in branches_data.items():
                        branches[branch_id] = BranchConfig(**branch_data)
                        logger.debug(f"Loaded branch config: {branch_id}")
            except Exception as e:
                logger.warning(f"Failed to load branches config: {e}")

        return branches

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Comprehensive configuration validation."""
        required_paths = ['base_dir', 'logs_dir', 'reports_dir', 'database_dir']
        for path_key in required_paths:
            path = config.get('paths', {}).get(path_key)
            if not path:
                raise ConfigurationError(f"Required path not configured: {path_key}")

        # Validate email if configured
        email = config.get('email', {})
        if email.get('username') and not email.get('password'):
            raise ConfigurationError("Email password required when username is set")

        # Validate API JWT secret for production
        app_config = config.get('app', {})
        if app_config.get('environment') == 'production':
            api_config = config.get('api', {})
            if api_config.get('jwt_secret_key') == 'change-this-in-production-secure-key':
                raise ConfigurationError("JWT secret key must be changed for production")

        logger.debug("Configuration validation passed")

    def _create_config_object(self, config: Dict[str, Any]) -> AppConfig:
        """Create AppConfig object from validated dict."""
        paths = PathConfig(**config['paths'])
        database = DatabaseConfig(**config['database'])
        email = EmailConfig(**config['email'])
        logging_config = LoggingConfig(**config['logging'])
        api = APIConfig(**config['api'])
        scheduler = SchedulerConfig(**config.get('scheduler', {}))
        monitoring = MonitoringConfig(**config.get('monitoring', {}))
        resilience = ResilienceConfig(**config.get('resilience', {}))

        app_config = AppConfig(
            name=config['app']['name'],
            version=config['app']['version'],
            environment=config['app']['environment'],
            debug=config['app']['debug'],
            paths=paths,
            database=database,
            email=email,
            logging=logging_config,
            api=api,
            scheduler=scheduler,
            monitoring=monitoring,
            resilience=resilience,
            branches=config['branches']
        )

        return app_config


# Global config instance with thread-safe access
_config_loader: Optional[ConfigLoader] = None
_config_lock = None

def get_config() -> AppConfig:
    """Get the global configuration instance with thread-safe caching."""
    global _config_loader, _config_lock

    if _config_lock is None:
        import threading
        _config_lock = threading.Lock()

    with _config_lock:
        if _config_loader is None:
            _config_loader = ConfigLoader()
        return _config_loader.load()


def reload_config() -> AppConfig:
    """Force reload configuration (useful for hot reloading in development)."""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader.load(force_reload=True)
    email_recipients: List[str] = field(default_factory=list)
    speed_test_enabled: bool = True
    active: bool = True


@dataclass
class AppConfig:
    """Main application configuration."""
    name: str = "HET IT Control System"
    version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False

    paths: PathConfig = None
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    api: APIConfig = field(default_factory=APIConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    alerting: AlertingConfig = field(default_factory=AlertingConfig)
    resilience: ResilienceConfig = field(default_factory=ResilienceConfig)
    branches: Dict[str, BranchConfig] = field(default_factory=dict)


class ConfigLoader:
    """Centralized configuration management."""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration loader.

        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = config_dir or Path("app/config")
        self._config: Optional[AppConfig] = None

    def load(self) -> AppConfig:
        """
        Load and validate configuration.

        Returns:
            AppConfig instance
        """
        if self._config is not None:
            return self._config

        # Load environment variables
        env_config = self._load_env_config()

        # Load JSON config
        json_config = self._load_json_config()

        # Merge configurations (env takes precedence)
        merged = {**json_config, **env_config}

        # Validate required fields
        self._validate_config(merged)

        # Create config object
        self._config = self._create_config_object(merged)

        return self._config

    def _load_env_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        config = {}

        # App settings
        config['app'] = {
            'name': os.getenv('HET_APP_NAME', 'het IT Control System'),
            'version': os.getenv('HET_APP_VERSION', '1.0.0'),
            'environment': os.getenv('HET_ENVIRONMENT', 'development'),
            'debug': os.getenv('HET_DEBUG', 'false').lower() == 'true'
        }

        # Database
        config['database'] = {
            'url': os.getenv('HET_DATABASE_URL', 'sqlite:///database/het_control.db'),
            'echo': os.getenv('HET_DATABASE_ECHO', 'false').lower() == 'true',
            'pool_size': int(os.getenv('HET_DATABASE_POOL_SIZE', '5')),
            'max_overflow': int(os.getenv('HET_DATABASE_MAX_OVERFLOW', '10'))
        }

        # Email
        config['email'] = {
            'smtp_host': os.getenv('HET_SMTP_HOST', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('HET_SMTP_PORT', '587')),
            'smtp_username': os.getenv('HET_SMTP_USERNAME'),
            'smtp_password': os.getenv('HET_SMTP_PASSWORD'),
            'smtp_tls': os.getenv('HET_SMTP_TLS', 'true').lower() == 'true',
            'recipients': os.getenv('HET_EMAIL_RECIPIENTS', '').split(',') if os.getenv('HET_EMAIL_RECIPIENTS') else [],
        }

        # API
        config['api'] = {
            'host': os.getenv('HET_API_HOST', '0.0.0.0'),
            'port': int(os.getenv('HET_API_PORT', '8000')),
            'debug': os.getenv('HET_API_DEBUG', 'false').lower() == 'true',
            'jwt_secret_key': os.getenv('HET_JWT_SECRET_KEY') or _require_env_var('HET_JWT_SECRET_KEY'),
            'jwt_algorithm': os.getenv('HET_JWT_ALGORITHM', 'HS256'),
            'jwt_expiration_minutes': int(os.getenv('HET_JWT_EXPIRATION_MINUTES', '30')),
            'allowed_origins': os.getenv('HET_ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:8000').split(',')
        }

        # Logging
        config['logging'] = {
            'level': os.getenv('HET_LOG_LEVEL', 'INFO'),
            'max_bytes': int(os.getenv('HET_LOG_MAX_BYTES', str(10 * 1024 * 1024))),
            'backup_count': int(os.getenv('HET_LOG_BACKUP_COUNT', '5'))
        }

        # Paths
        base_dir = Path(os.getenv('HET_BASE_DIR', Path.cwd()))
        config['paths'] = {
            'base_dir': base_dir,
            'nas_base': Path(os.getenv('HET_NAS_BASE', r"\\het-nas\Tally-Africa")),
            'laundry_base': Path(os.getenv('HET_LAUNDRY_BASE', r"\\het-NAS\G-SSS300")),
            'qsync_exe': Path(os.getenv('HET_QSYNC_EXE', r"C:\Program Files (x86)\QNAP\Qsync\Qsync.exe")),
            'export_base': Path(os.getenv('HET_EXPORT_BASE', str(base_dir / "exports"))),
            'logs_dir': Path(os.getenv('HET_LOGS_DIR', str(base_dir / "logs"))),
            'reports_dir': Path(os.getenv('HET_REPORTS_DIR', str(base_dir / "reports"))),
            'database_dir': Path(os.getenv('HET_DATABASE_DIR', str(base_dir / "database")))
        }

        # Branches (loaded from separate file or env)
        config['branches'] = self._load_branches_config()

        return config

    def _load_json_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        config_file = self.config_dir / "settings.json"
        if not config_file.exists():
            return {}

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise ConfigurationError(f"Failed to load config file: {e}")

    def _load_branches_config(self) -> Dict[str, BranchConfig]:
        """Load branch configurations."""
        branches = {}

        # Default branch
        branches['default'] = BranchConfig(
            id='default',
            name='Default Branch',
            nas_base=Path(r"\\het-nas\Tally-Africa"),
            tally_base=Path(r"\\het-nas\Tally-Africa\T-Current"),
            laundry_base=Path(r"\\het-NAS\G-SSS300"),
            qsync_exe=Path(r"C:\Program Files (x86)\QNAP\Qsync\Qsync.exe"),
            email_recipients=['hetgraphic17@gmail.com'],
            speed_test_enabled=True,
            active=True
        )

        # Load additional branches from environment or config file
        branches_file = self.config_dir / "branches.json"
        if branches_file.exists():
            try:
                with open(branches_file, 'r', encoding='utf-8') as f:
                    branches_data = json.load(f)
                    for branch_id, branch_data in branches_data.items():
                        branches[branch_id] = BranchConfig(**branch_data)
            except Exception as e:
                print(f"Warning: Failed to load branches config: {e}")

        return branches

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate configuration requirements."""
        required_paths = ['base_dir', 'logs_dir', 'reports_dir', 'database_dir']
        for path_key in required_paths:
            path = config.get('paths', {}).get(path_key)
            if not path:
                raise ConfigurationError(f"Required path not configured: {path_key}")

        # Validate email if configured
        email = config.get('email', {})
        if email.get('username') and not email.get('password'):
            raise ConfigurationError("Email password required when username is set")

    def _create_config_object(self, config: Dict[str, Any]) -> AppConfig:
        """Create AppConfig object from dict."""
        paths = PathConfig(**config['paths'])
        database = DatabaseConfig(**config['database'])
        email = EmailConfig(**config['email'])
        logging_config = LoggingConfig(**config['logging'])
        api = APIConfig(**config['api'])
        scheduler = SchedulerConfig(**config.get('scheduler', {}))
        monitoring = MonitoringConfig(**config.get('monitoring', {}))
        alerting = AlertingConfig(**config.get('alerting', {}))
        resilience = ResilienceConfig(**config.get('resilience', {}))

        app_config = AppConfig(
            name=config['app']['name'],
            version=config['app']['version'],
            environment=config['app']['environment'],
            debug=config['app']['debug'],
            paths=paths,
            database=database,
            email=email,
            logging=logging_config,
            api=api,
            scheduler=scheduler,
            monitoring=monitoring,
            alerting=alerting,
            resilience=resilience,
            branches=config['branches']
        )

        return app_config


# Global config instance
_config_loader = None

@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Get the global configuration instance."""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader.load()