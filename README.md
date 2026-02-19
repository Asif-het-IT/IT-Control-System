# HET IT Control System

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
| `HET_SMTP_SERVER` | SMTP server | smtp.gmail.com |
| `HET_SMTP_USERNAME` | SMTP username | - |
| `HET_EMAIL_RECIPIENTS` | Email recipients (comma-separated) | - |
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

- `GET /health` - Health check
- `GET /branches` - List branches
- `GET /jobs` - List scheduled jobs
- `POST /jobs/{job_id}/run` - Run job immediately
- `GET /status` - System status
- `GET /metrics` - System metrics

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

**HET IT Control System v1.0.0**
*Enterprise IT Automation & Monitoring*