# app/api/auth.py
"""
JWT Authentication for the HET IT Control System API.
"""
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

from app.config.settings import get_config
from app.infrastructure.logger import get_logger

logger = get_logger("auth")

# Security scheme
security = HTTPBearer(auto_error=False)

class TokenData(BaseModel):
    """Token payload data."""
    sub: str  # Subject (username)
    exp: datetime  # Expiration
    iat: datetime  # Issued at
    role: Optional[str] = "user"

class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str

class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.

    Args:
        data: Token payload data
        expires_delta: Optional expiration time delta

    Returns:
        JWT token string
    """
    config = get_config()

    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=config.api.jwt_expiration_minutes)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow()
    })

    try:
        encoded_jwt = jwt.encode(
            to_encode,
            config.api.jwt_secret_key,
            algorithm=config.api.jwt_algorithm
        )
        return encoded_jwt
    except Exception as e:
        logger.error(f"Failed to create JWT token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token creation failed"
        )

def verify_token(token: str) -> TokenData:
    """
    Verify and decode JWT token.

    Args:
        token: JWT token string

    Returns:
        TokenData object

    Raises:
        HTTPException: If token is invalid
    """
    config = get_config()

    try:
        payload = jwt.decode(
            token,
            config.api.jwt_secret_key,
            algorithms=[config.api.jwt_algorithm]
        )

        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return TokenData(**payload)

    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication verification failed"
        )

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> TokenData:
    """
    FastAPI dependency to get current authenticated user.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        TokenData for authenticated user

    Raises:
        HTTPException: If authentication fails
    """
    config = get_config()

    # Skip authentication in development mode (for testing)
    if config.environment == "development" and not credentials:
        # Return a mock user for development
        return TokenData(
            sub="dev_user",
            exp=datetime.utcnow() + timedelta(hours=24),
            iat=datetime.utcnow(),
            role="admin"
        )

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return verify_token(credentials.credentials)

async def get_current_admin_user(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """
    FastAPI dependency to get current admin user.

    Args:
        current_user: Current authenticated user

    Returns:
        TokenData for admin user

    Raises:
        HTTPException: If user is not admin
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate user credentials.

    Args:
        username: Username
        password: Password

    Returns:
        User data dict if authenticated, None otherwise
    """
    config = get_config()

    # Simple authentication for demo - in production, use proper user store
    # TODO: Replace with proper user authentication system
    admin_username = os.getenv('HET_ADMIN_USERNAME', 'admin')
    admin_password = os.getenv('HET_ADMIN_PASSWORD')
    
    if not admin_password:
        raise HTTPException(
            status_code=500,
            detail="Admin authentication not configured. Set HET_ADMIN_PASSWORD environment variable."
        )
    
    if username == admin_username and password == admin_password:
        return {
            "username": username,
            "role": "admin",
            "full_name": "System Administrator"
        }

    return None