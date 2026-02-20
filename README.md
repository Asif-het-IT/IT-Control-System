# HET IT Control System - Professional Windows Software

Enterprise Automation Dashboard with professional Windows deployment, monitoring, and alerting capabilities.

## 🚀 Quick Start

### For End Users

1. **Download** the installer from the releases page
2. **Run** `HET_IT_Control_System_Installer.exe` as administrator
3. **Follow** the setup wizard to configure email and system settings
4. **Launch** from Start Menu or Desktop shortcut

### For Developers

```bash
# Clone repository
git clone <repository-url>
cd het-it-control-system

# Install dependencies
pip install -r requirements.txt

# Run setup wizard
python het_launcher.py setup

# Launch application
python het_launcher.py gui
```

## 📦 Distribution Options

### 1. Windows Installer (Recommended)
- Professional MSI/EXE installer
- Automatic service installation
- Start menu integration
- Uninstaller support

### 2. Portable Version
- Single executable with embedded files
- No installation required
- Run from any location
- Includes all batch files for easy launching

### 3. Development Setup
- Full source code
- Development dependencies
- Build tools included

## 🏗️ Architecture

```
HET IT Control System/
├── het_launcher.py          # Main launcher with update support
├── run.py                   # Core application launcher
├── app/                     # Main application code
│   ├── config/             # Configuration management
│   ├── infrastructure/     # Core services (DB, logging, scheduler)
│   ├── services/           # Business logic services
│   ├── gui/                # PySide6 GUI components
│   ├── api/                # FastAPI REST API
│   └── version.py          # Version information
├── service/                # Windows service implementation
├── setup/                  # First-time setup wizard
├── updater/                # Auto-update system
├── packaging/              # Build and packaging scripts
└── jobs/                   # Job definitions
```

## 🎯 Features

### Professional Deployment
- **Windows Service**: Auto-start scheduler service
- **Single Executable**: PyInstaller packaged application
- **Auto-Updates**: Built-in update mechanism
- **Setup Wizard**: Guided first-time configuration

### Enterprise Monitoring
- **Real-time System Monitoring**: CPU, RAM, disk usage
- **Job Failure Alerts**: Email and desktop notifications
- **Health Dashboard**: System status indicators
- **Multi-channel Alerts**: Email, Telegram, desktop

### Production Ready
- **Portable Database**: SQLite with WAL mode
- **Structured Logging**: JSON logging with rotation
- **Error Recovery**: Comprehensive exception handling
- **Graceful Shutdown**: Proper cleanup on exit

## 🛠️ Usage

### GUI Application
```bash
# Launch GUI
het_launcher.exe gui
# or
python het_launcher.py gui
```

### Windows Service
```bash
# Install service
het_launcher.exe service install

# Start service
het_launcher.exe service start

# Check status
het_launcher.exe service status

# Stop service
het_launcher.exe service stop

# Uninstall service
het_launcher.exe service uninstall
```

### Setup Wizard
```bash
# Run setup
het_launcher.exe setup
```

### Updates
```bash
# Check for updates
het_launcher.exe update

# Apply updates
het_launcher.exe update --apply
```

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the application directory:

```env
# Database
DATABASE_URL=sqlite:///data/app.db

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password

# Logging
LOG_LEVEL=INFO
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=5

# API
API_HOST=localhost
API_PORT=8000
API_DEBUG=false
```

### Service Configuration
The Windows service runs automatically and can be managed through:
- Windows Services Manager
- Command line tools
- Application shortcuts

## 📁 Directory Structure

After installation, the application creates:

```
%PROGRAMFILES%\HET IT Control System\    # Application files
%APPDATA%\HET IT Control System\        # User data
├── logs\                              # Application logs
├── database\                          # SQLite databases
└── config\                            # Configuration files
```

## 🏗️ Building from Source

### Prerequisites
- Python 3.11+
- PyInstaller
- NSIS (for installer creation)

### Build Steps
```bash
# Install build dependencies
pip install pyinstaller

# Build executable
cd packaging
.\build.bat

# Create installer (requires NSIS)
makensis installer.nsi
```

## 🔄 Auto-Update System

The application includes a built-in update system:

- **Version Checking**: Automatic version comparison
- **Secure Downloads**: SHA256 hash verification
- **Backup Creation**: Automatic backup before updates
- **Rollback Support**: Restore from backup on failure

## 📊 Monitoring & Alerting

### System Monitoring
- CPU usage percentage
- Memory usage
- Disk space monitoring
- Scheduler heartbeat

### Alert Channels
- **Email**: SMTP-based notifications
- **Desktop**: Windows toast notifications
- **Telegram**: Bot-based messaging (future)

### Health Indicators
- Green: System healthy
- Yellow: Warning conditions
- Red: Critical issues

## 🐛 Troubleshooting

### Service Won't Start
1. Check Windows Event Viewer for errors
2. Verify Python and dependencies are installed
3. Check service permissions

### GUI Won't Launch
1. Ensure PySide6 is properly installed
2. Check display settings
3. Try running from command line for error messages

### Database Issues
1. Check file permissions on database directory
2. Verify SQLite installation
3. Check disk space

## 📝 Version History

See `app/version.py` for detailed version information and changelog.

## 🤝 Support

For support and issues:
- Check the logs in `%APPDATA%\HET IT Control System\logs\`
- Review Windows Event Viewer
- Contact system administrator

## 📄 License

[Add your license information here]

---

**HET IT Control System** - Enterprise Automation Made Simple

A professional enterprise-grade IT automation and monitoring system built with Python.

## Features

- **Multi-branch Support**: Configure and monitor multiple branch locations
- **Automated Jobs**: NAS monitoring, Tally backup, Laundry system monitoring, Speed tests
- **REST API**: FastAPI-based REST API for remote management
- **Modern GUI**: PySide6-based desktop application with real-time monitoring
- **Database Integration**: SQLAlchemy with SQLite/PostgreSQL support
- **Job Scheduling**: APScheduler for automated job execution
- **Email Notifications**: Automated reporting and alerts
- **Comprehensive Logging**: Rotating logs with structured format
- **Health Monitoring**: System health checks and metrics
- **Docker Support**: Containerized deployment

## Architecture

```
het-it-control-system/
├── app/                          # Application core
│   ├── core/                     # Base classes and shared logic
│   ├── services/                 # Business services
│   ├── jobs/                     # Automation jobs
│   ├── infrastructure/           # Infrastructure components
│   ├── api/                      # FastAPI REST API
│   ├── ui/                       # PySide6 GUI application
│   └── config/                   # Configuration management
├── database/                     # Database files and migrations
├── logs/                         # Application logs
├── reports/                      # Generated reports
├── tests/                        # Unit and integration tests
├── requirements.txt              # Python dependencies
├── run.py                        # Main entry point
├── .env.example                  # Environment configuration template
└── README.md
```

## Quick Start

### Prerequisites

- Python 3.9+
- Windows/Linux/macOS
- Network access to NAS systems

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/het-it-control-system.git
   cd het-it-control-system
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

   **Version Lock Information:**
   - Python 3.11+ required
   - All dependencies pinned to specific versions for stability
   - Use virtual environment to avoid conflicts

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize database**
   ```bash
   python run.py setup
   ```

### Running the Application

#### GUI Mode (Recommended)
```bash
python run.py gui
```

#### API Mode
```bash
python run.py api
# Access at http://localhost:8000
# API docs at http://localhost:8000/docs
```

#### Scheduler Mode
```bash
python run.py scheduler
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HET_APP_NAME` | Application name | HET IT Control System |
| `HET_ENVIRONMENT` | Environment (development/production) | development |
| `HET_DATABASE_URL` | Database connection URL | sqlite:///database/het_control.db |
| `HET_SMTP_HOST` | SMTP server host | smtp.gmail.com |
| `HET_SMTP_PORT` | SMTP server port | 587 |
| `HET_SMTP_USERNAME` | SMTP username | - |
| `HET_SMTP_PASSWORD` | SMTP password | - |
| `HET_SMTP_TLS` | SMTP TLS enabled | true |
| `HET_EMAIL_RECIPIENTS` | Email recipients (comma-separated) | - |
| `HET_JWT_SECRET_KEY` | JWT secret key (**REQUIRED**) | - |
| `HET_JWT_ALGORITHM` | JWT algorithm | HS256 |
| `HET_JWT_EXPIRATION_MINUTES` | JWT token expiration | 30 |
| `HET_ADMIN_USERNAME` | Admin username | admin |
| `HET_ADMIN_PASSWORD` | Admin password (**REQUIRED**) | - |
| `HET_ALLOWED_ORIGINS` | CORS allowed origins | http://localhost:3000,http://localhost:8000 |
| `HET_API_HOST` | API host | 0.0.0.0 |
| `HET_API_PORT` | API port | 8000 |
| `HET_NAS_BASE` | NAS base path | \\het-nas\Tally-Africa |
| `HET_LAUNDRY_BASE` | Laundry NAS path | \\het-NAS\G-SSS300 |

### Branch Configuration

Branches are configured in `app/config/branches.json`:

```json
{
  "default": {
    "id": "default",
    "name": "Default Branch",
    "nas_base": "\\\\het-nas\\Tally-Africa",
    "tally_base": "\\\\het-nas\\Tally-Africa\\T-Current",
    "laundry_base": "\\\\het-NAS\\G-SSS300",
    "qsync_exe": "C:\\Program Files (x86)\\QNAP\\Qsync\\Qsync.exe",
    "email_recipients": ["admin@company.com"],
    "speed_test_enabled": true,
    "active": true
  }
}
```

## API Endpoints

### Authentication

The API uses JWT (JSON Web Token) authentication. In development mode, authentication is bypassed for easier testing.

**Login:**
```
POST /auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Using the token:**
```
Authorization: Bearer <access_token>
```

### Endpoints

| Method | Endpoint | Auth Required | Description |
|--------|----------|---------------|-------------|
| `GET` | `/health` | No | Health check |
| `POST` | `/auth/login` | No | User authentication |
| `GET` | `/branches` | Yes | List branches |
| `GET` | `/jobs` | Yes | List scheduled jobs |
| `POST` | `/jobs/{job_id}/run` | Yes (Admin) | Run job immediately |
| `GET` | `/status` | Yes | System status |
| `GET` | `/metrics` | Yes | System metrics |

### API Documentation

When running the API server, visit `http://localhost:8000/docs` for interactive API documentation.

## Jobs

### Available Jobs

1. **NAS Status Job** (`nas_status_job`)
   - Monitors Tally files on NAS
   - Checks for file conflicts
   - Monitors Laundry backup status
   - Generates HTML reports

2. **Speed Test Job** (`speed_test_job`)
   - Tests internet speed
   - Generates trend charts
   - Maintains historical data

### Scheduling Jobs

Jobs can be scheduled via the GUI or API:

```python
from app.infrastructure.scheduler import get_scheduler

scheduler = get_scheduler()
scheduler.add_job(
    "nas_status_daily",
    NasStatusJob,
    trigger="cron",
    hour=9,
    minute=0
)
```

## Development

### Running Tests
```bash
python -m pytest tests/
```

### Code Quality
```bash
# Type checking
mypy app/

# Linting
flake8 app/

# Formatting
black app/
```

### Database Migrations
```bash
# Generate migration
alembic revision --autogenerate -m "Add new table"

# Run migration
alembic upgrade head
```

## Production Security Requirements

### 🔐 Critical Security Configuration

**Before deploying to production:**

1. **Set Strong JWT Secret Key**
   ```bash
   # Generate a secure 256-bit key
   openssl rand -hex 32
   # Set HET_JWT_SECRET_KEY in .env
   ```

2. **Configure Admin Authentication**
   ```bash
   # Set strong admin password
   HET_ADMIN_PASSWORD=your-secure-admin-password-here
   ```

3. **Restrict CORS Origins**
   ```bash
   # Only allow your domains
   HET_ALLOWED_ORIGINS=https://yourdomain.com,https://admin.yourdomain.com
   ```

4. **HTTPS Required**
   - Deploy behind reverse proxy (nginx/apache)
   - Configure SSL/TLS certificates
   - Redirect HTTP to HTTPS

5. **Environment Variables**
   - Never commit `.env` file
   - Use strong, unique passwords
   - Rotate secrets regularly

### 🚨 Security Checklist

- [ ] JWT secret key set (32+ characters)
- [ ] Admin password configured
- [ ] CORS origins restricted
- [ ] HTTPS enabled
- [ ] `.env` not committed
- [ ] File permissions secure
- [ ] Logs not exposing sensitive data

## Deployment

### Docker Deployment

1. **Build image**
   ```bash
   docker build -t het-it-control .
   ```

2. **Run container**
   ```bash
   docker run -p 8000:8000 -v /host/logs:/app/logs het-it-control
   ```

### Windows Service

Use `nssm` or Windows Task Scheduler to run as a service:

```bash
nssm install HETControl "python" "run.py" "scheduler"
nssm start HETControl
```

## Security

- Environment variables for sensitive data
- Path validation and sanitization
- Input validation on all endpoints
- Rotating logs to prevent disk space issues
- Database connection pooling

## Monitoring

### Health Checks

The system provides comprehensive health monitoring:

- System resource usage
- Database connectivity
- Network accessibility
- Job execution status

### Metrics

Prometheus-compatible metrics available at `/metrics`:

- Job execution times
- Success/failure rates
- System resource usage
- Branch status

## Troubleshooting

### Common Issues

1. **NAS Access Denied**
   - Check network credentials
   - Verify firewall settings
   - Ensure SMB access

2. **Email Not Sending**
   - Verify SMTP credentials
   - Check Gmail app passwords
   - Review spam folder

3. **Database Errors**
   - Check file permissions
   - Verify SQLite path
   - Run database migrations

### Logs

Logs are stored in `logs/` directory:
- `app.log` - General application logs
- `error.log` - Error logs only
- `jobs.log` - Job-specific logs
- `database.log` - Database operation logs

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit pull request

## License

MIT License - see LICENSE file for details.

## Support

For support, please contact:
- IT Department
- Email: it@het.com
- Phone: +971 50 140 9840

---

**het IT Control System v1.0.0**
*Enterprise IT Automation & Monitoring*