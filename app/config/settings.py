# app/config/settings.py
"""
Configuration management for the HET IT Control System.
"""
import os
import json
from pathlib import Path
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from functools import lru_cache

from app.infrastructure.exceptions import ConfigurationError


@dataclass
class DatabaseConfig:
    """Database configuration."""
    url: str = "sqlite:///database/het_control.db"
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10


@dataclass
class EmailConfig:
    """Email configuration."""
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    username: Optional[str] = None
    password: Optional[str] = None
    recipients: List[str] = field(default_factory=list)
    use_tls: bool = True


@dataclass
class PathConfig:
    """File system paths configuration."""
    base_dir: Path
    nas_base: Path
    laundry_base: Path
    qsync_exe: Path
    export_base: Path
    logs_dir: Path
    reports_dir: Path
    database_dir: Path


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    max_bytes: int = 10 * 1024 * 1024
    backup_count: int = 5


@dataclass
class APIConfig:
    """API configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    jwt_secret: str = "change-this-in-production"
    jwt_expiration_hours: int = 24


@dataclass
class SchedulerConfig:
    """Scheduler configuration."""
    timezone: str = "UTC"
    job_defaults: Dict[str, Any] = field(default_factory=lambda: {
        'coalesce': True,
        'max_instances': 1,
        'misfire_grace_time': 30
    })


@dataclass
class BranchConfig:
    """Branch-specific configuration."""
    id: str
    name: str
    nas_base: Path
    tally_base: Path
    laundry_base: Path
    qsync_exe: Optional[Path] = None
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
            'name': os.getenv('HET_APP_NAME', 'HET IT Control System'),
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
            'smtp_server': os.getenv('HET_SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('HET_SMTP_PORT', '587')),
            'username': os.getenv('HET_SMTP_USERNAME'),
            'password': os.getenv('HET_SMTP_PASSWORD'),
            'recipients': os.getenv('HET_EMAIL_RECIPIENTS', '').split(',') if os.getenv('HET_EMAIL_RECIPIENTS') else [],
            'use_tls': os.getenv('HET_SMTP_TLS', 'true').lower() == 'true'
        }

        # API
        config['api'] = {
            'host': os.getenv('HET_API_HOST', '0.0.0.0'),
            'port': int(os.getenv('HET_API_PORT', '8000')),
            'debug': os.getenv('HET_API_DEBUG', 'false').lower() == 'true',
            'jwt_secret': os.getenv('HET_JWT_SECRET', 'change-this-in-production'),
            'jwt_expiration_hours': int(os.getenv('HET_JWT_EXPIRATION_HOURS', '24'))
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