# app/api/main.py
"""
FastAPI REST API for the HET IT Control System.
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uvicorn
from datetime import datetime

from app.config.settings import get_config
from app.infrastructure.scheduler import get_scheduler
from app.infrastructure.database import get_db_manager, JobExecution
from app.services.system_service import get_system_service
from app.infrastructure.logger import get_logger
from app.api.auth import get_current_user, get_current_admin_user, authenticate_user, create_access_token, LoginRequest, TokenResponse

logger = get_logger("api")

app = FastAPI(
    title="HET IT Control System API",
    description="REST API for managing automated IT operations",
    version="1.0.0"
)

# CORS middleware
config = get_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.api.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class JobStatusResponse(BaseModel):
    job_id: str
    name: str
    next_run_time: Optional[datetime]
    trigger: str

class JobResultResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]]
    error: Optional[str]
    execution_time: float
    timestamp: datetime

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    services: Dict[str, bool]

class BranchInfo(BaseModel):
    id: str
    name: str
    active: bool
    last_check: Optional[datetime]

# API routes
@app.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Authenticate user and return access token."""
    user = authenticate_user(request.username, request.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token = create_access_token({
        "sub": user["username"],
        "role": user["role"]
    })

    config = get_config()
    return TokenResponse(
        access_token=access_token,
        expires_in=config.api.jwt_expiration_minutes * 60
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    config = get_config()
    system_service = get_system_service()

    # Check services
    services_status = {
        "database": True,  # Assume DB is working if we get here
        "scheduler": True,  # Assume scheduler is working
        "file_system": True,  # Basic check
    }

    # Try to get system health
    try:
        health = system_service.get_system_health()
        overall_status = "healthy" if health['overall_health'] > 70 else "degraded"
    except Exception:
        overall_status = "unhealthy"

    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now(),
        version=config.version,
        services=services_status
    )

@app.get("/branches", response_model=List[BranchInfo])
async def get_branches(current_user = Depends(get_current_user)):
    """Get list of configured branches."""
    config = get_config()
    branches = []

    for branch_id, branch_config in config.branches.items():
        branches.append(BranchInfo(
            id=branch_id,
            name=branch_config.name,
            active=branch_config.active,
            last_check=None  # Could be enhanced to track last activity
        ))

    return branches

@app.get("/jobs", response_model=List[JobStatusResponse])
async def get_jobs(current_user = Depends(get_current_user)):
    """Get list of scheduled jobs."""
    scheduler = get_scheduler()
    jobs = []

    for job_id, job_info in scheduler.list_jobs().items():
        jobs.append(JobStatusResponse(
            job_id=job_id,
            name=job_info['name'],
            next_run_time=job_info['next_run_time'],
            trigger=job_info['trigger']
        ))

    return jobs

@app.post("/jobs/{job_id}/run", response_model=JobResultResponse)
async def run_job_now(job_id: str, background_tasks: BackgroundTasks, current_user = Depends(get_current_admin_user)):
    """Run a job immediately."""
    scheduler = get_scheduler()

    # Check if job exists
    if job_id not in scheduler.job_registry:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Run job in background
    background_tasks.add_task(scheduler.run_job_now, job_id)

    return JobResultResponse(
        success=True,
        data={"message": f"Job {job_id} started"},
        error=None,
        execution_time=0.0,
        timestamp=datetime.now()
    )

@app.get("/status")
async def get_system_status(current_user = Depends(get_current_user)):
    """Get overall system status."""
    config = get_config()
    system_service = get_system_service()
    scheduler = get_scheduler()

    try:
        health = system_service.get_system_health()
        jobs = scheduler.list_jobs()

        return {
            "system_health": health,
            "active_jobs": len(jobs),
            "branches": len(config.branches),
            "timestamp": datetime.now()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def get_metrics(current_user = Depends(get_current_user)):
    """Get system metrics."""
    try:
        db_manager = get_db_manager()
        system_service = get_system_service()

        # Get recent job executions
        with db_manager.get_session() as session:
            recent_executions = session.query(JobExecution).order_by(
                JobExecution.created_at.desc()
            ).limit(10).all()

            executions_data = []
            for exec in recent_executions:
                executions_data.append({
                    "job_name": exec.job_name,
                    "branch_id": exec.branch_id,
                    "success": exec.success,
                    "execution_time": exec.execution_time,
                    "created_at": exec.created_at
                })

        # Get system metrics
        system_info = system_service.get_system_info()
        cpu_info = system_service.get_cpu_info()
        memory_info = system_service.get_memory_info()

        return {
            "recent_executions": executions_data,
            "system_info": system_info,
            "cpu_info": cpu_info,
            "memory_info": memory_info,
            "timestamp": datetime.now()
        }

    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with API documentation link."""
    return """
    <html>
        <head>
            <title>HET IT Control System API</title>
        </head>
        <body>
            <h1>HET IT Control System API</h1>
            <p>Enterprise IT automation and monitoring system.</p>
            <p><a href="/docs">API Documentation</a></p>
            <p><a href="/health">Health Check</a></p>
        </body>
    </html>
    """

if __name__ == "__main__":
    config = get_config()
    uvicorn.run(
        "app.api.main:app",
        host=config.api.host,
        port=config.api.port,
        reload=config.api.debug
    )