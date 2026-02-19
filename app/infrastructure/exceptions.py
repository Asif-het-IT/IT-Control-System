# app/infrastructure/exceptions.py
"""
Custom exceptions for the HET IT Control System.
"""


class HETError(Exception):
    """Base exception for HET IT Control System."""
    pass


class ConfigurationError(HETError):
    """Configuration related errors."""
    pass


class JobError(HETError):
    """Job execution related errors."""
    pass


class ValidationError(JobError):
    """Job validation errors."""
    pass


class NetworkError(HETError):
    """Network related errors."""
    pass


class DatabaseError(HETError):
    """Database related errors."""
    pass


class FileSystemError(HETError):
    """File system related errors."""
    pass


class AuthenticationError(HETError):
    """Authentication related errors."""
    pass


class BranchError(HETError):
    """Branch related errors."""
    pass