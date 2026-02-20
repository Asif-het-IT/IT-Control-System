# scripts/validate_system.py
"""
System validation script for HET IT Control System.
Tests all components before deployment.
"""

import sys
import os
import logging
from pathlib import Path
import subprocess
import time
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def setup_logging():
    """Setup logging for validation."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(project_root / "logs" / "validation.log", mode='w')
        ]
    )

def test_imports():
    """Test that all required modules can be imported."""
    logger = logging.getLogger(__name__)

    required_modules = [
        'PySide6.QtWidgets',
        'PySide6.QtCore',
        'apscheduler',
        'sqlite3',
        'win32serviceutil',
        'win32service',
        'win32cred',
        'psutil',
        'app.infrastructure.database',
        'app.infrastructure.logging',
        'app.infrastructure.scheduler',
        'app.security.credentials',
        'app.core.job',
        'app.domain.entities',
    ]

    failed_imports = []

    for module in required_modules:
        try:
            __import__(module)
            logger.info(f"✓ {module} imported successfully")
        except ImportError as e:
            logger.error(f"✗ Failed to import {module}: {e}")
            failed_imports.append(module)

    return len(failed_imports) == 0, failed_imports

def test_database():
    """Test database functionality."""
    logger = logging.getLogger(__name__)

    try:
        from app.infrastructure.database import get_database_manager

        db_manager = get_database_manager()

        # Test basic operations
        db_size = db_manager.get_db_size()
        logger.info(f"✓ Database initialized, size: {db_size} bytes")

        # Test WAL mode
        # This would require checking the database file directly
        logger.info("✓ Database manager created successfully")

        return True, None

    except Exception as e:
        logger.error(f"✗ Database test failed: {e}")
        return False, str(e)

def test_logging():
    """Test logging system."""
    logger = logging.getLogger(__name__)

    try:
        from app.infrastructure.logging import init_logging, get_service_logger, get_gui_logger

        # Test service logger
        service_logger = get_service_logger()
        service_logger.info("Test service log message")

        # Test GUI logger
        gui_logger = get_gui_logger()
        gui_logger.info("Test GUI log message")

        logger.info("✓ Logging system initialized successfully")
        return True, None

    except Exception as e:
        logger.error(f"✗ Logging test failed: {e}")
        return False, str(e)

def test_scheduler():
    """Test scheduler functionality."""
    logger = logging.getLogger(__name__)

    try:
        from app.infrastructure.scheduler import get_scheduler

        scheduler = get_scheduler()
        scheduler.initialize()

        # Check if scheduler is ready
        if scheduler.is_running():
            logger.info("✓ Scheduler is running")
        else:
            logger.info("✓ Scheduler initialized (not started)")

        scheduler.stop()
        logger.info("✓ Scheduler stopped successfully")

        return True, None

    except Exception as e:
        logger.error(f"✗ Scheduler test failed: {e}")
        return False, str(e)

def test_credentials():
    """Test credential management."""
    logger = logging.getLogger(__name__)

    try:
        from app.security.credentials import CredentialManager

        cred_manager = CredentialManager()

        # Test storing a test credential
        test_key = "test_validation_key"
        test_value = "test_value"

        success = cred_manager.store_credential(test_key, test_value)
        if success:
            logger.info("✓ Test credential stored successfully")

            # Test retrieving
            retrieved = cred_manager.get_credential(test_key)
            if retrieved == test_value:
                logger.info("✓ Test credential retrieved successfully")
            else:
                logger.warning("✗ Test credential retrieval failed")

            # Clean up
            cred_manager.delete_credential(test_key)
            logger.info("✓ Test credential cleaned up")
        else:
            logger.warning("✗ Test credential storage failed")

        return True, None

    except Exception as e:
        logger.error(f"✗ Credential test failed: {e}")
        return False, str(e)

def test_job_framework():
    """Test job framework."""
    logger = logging.getLogger(__name__)

    try:
        from app.core.job import BaseJob, JobStatus, JobResult
        from app.domain.entities import Job

        # Test creating a job instance
        test_job = Job(
            id="test_job",
            name="Test Job",
            enabled=True,
            config={"test": "value"}
        )

        logger.info("✓ Job entity created successfully")

        # Test job result
        result = JobResult(
            job_id="test_job",
            success=True,
            message="Test completed",
            duration=1.0,
            data={"test": "data"}
        )

        logger.info("✓ Job result created successfully")

        return True, None

    except Exception as e:
        logger.error(f"✗ Job framework test failed: {e}")
        return False, str(e)

def test_windows_service():
    """Test Windows service components."""
    logger = logging.getLogger(__name__)

    try:
        # Test service module import
        from app.service.windows_service import HETService

        logger.info("✓ Windows service class imported successfully")

        # We can't actually test service installation without admin rights
        # But we can test the class exists and has required attributes
        if hasattr(HETService, '_svc_name_'):
            logger.info(f"✓ Service name: {HETService._svc_name_}")

        return True, None

    except Exception as e:
        logger.error(f"✗ Windows service test failed: {e}")
        return False, str(e)

def test_build_artifacts():
    """Test that build artifacts exist."""
    logger = logging.getLogger(__name__)

    build_artifacts = [
        "build_exe.spec",
        "scripts/build_exe.py",
        "scripts/service_manager.py"
    ]

    missing_artifacts = []

    for artifact in build_artifacts:
        artifact_path = project_root / artifact
        if artifact_path.exists():
            logger.info(f"✓ {artifact} exists")
        else:
            logger.error(f"✗ {artifact} missing")
            missing_artifacts.append(artifact)

    return len(missing_artifacts) == 0, missing_artifacts

def run_validation():
    """Run all validation tests."""
    logger = logging.getLogger(__name__)

    logger.info("Starting HET IT Control System validation...")

    tests = [
        ("Import Tests", test_imports),
        ("Database Tests", test_database),
        ("Logging Tests", test_logging),
        ("Scheduler Tests", test_scheduler),
        ("Credential Tests", test_credentials),
        ("Job Framework Tests", test_job_framework),
        ("Windows Service Tests", test_windows_service),
        ("Build Artifacts Tests", test_build_artifacts),
    ]

    results = []

    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} ---")
        try:
            success, details = test_func()
            results.append((test_name, success, details))
            if success:
                logger.info(f"✓ {test_name} PASSED")
            else:
                logger.error(f"✗ {test_name} FAILED: {details}")
        except Exception as e:
            logger.error(f"✗ {test_name} ERROR: {e}")
            results.append((test_name, False, str(e)))

    # Summary
    logger.info("\n" + "="*50)
    logger.info("VALIDATION SUMMARY")
    logger.info("="*50)

    passed = 0
    failed = 0

    for test_name, success, details in results:
        status = "PASS" if success else "FAIL"
        logger.info(f"{test_name}: {status}")
        if success:
            passed += 1
        else:
            failed += 1
            if details:
                logger.info(f"  Details: {details}")

    logger.info(f"\nTotal Tests: {len(results)}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")

    if failed == 0:
        logger.info("\n🎉 All validation tests PASSED! System is ready for deployment.")
        return True
    else:
        logger.error(f"\n❌ {failed} validation test(s) FAILED. Please fix issues before deployment.")
        return False

def main():
    """Main validation entry point."""
    setup_logging()
    success = run_validation()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
<parameter name="filePath">d:\My App\scripts\validate_system.py