"""
Authentication and authorization utilities for FastAPI applications.

This module provides comprehensive authentication and authorization functionality
including JWT token management, password hashing, OAuth2 integration, and
role-based access control.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from passlib.exc import UnknownHashError
from sqlalchemy.orm import Session

# Import database and user model dependencies
from core.database import get_db
from models.user import User

# Configure logging
logger = logging.getLogger(__name__)

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required")

ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = os.getenv("REFRESH_TOKEN_EXPIRE_DAYS")
if REFRESH_TOKEN_EXPIRE_DAYS:
    REFRESH_TOKEN_EXPIRE_DAYS = int(REFRESH_TOKEN_EXPIRE_DAYS)

# Password hashing context with bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


class AuthenticationError(HTTPException):
    """Custom exception for authentication errors."""
    
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class InactiveUserError(HTTPException):
    """Custom exception for inactive user access attempts."""
    
    def __init__(self, detail: str = "Inactive user"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class TokenExpiredError(AuthenticationError):
    """Custom exception for expired tokens."""
    
    def __init__(self, detail: str = "Token has expired"):
        super().__init__(detail=detail)


class InvalidTokenError(AuthenticationError):
    """Custom exception for invalid tokens."""
    
    def __init__(self, detail: str = "Invalid token"):
        super().__init__(detail=detail)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against its hash using constant-time comparison.
    
    Args:
        plain_password: The plain text password to verify
        hashed_password: The hashed password to compare against
        
    Returns:
        bool: True if password matches, False otherwise
        
    Raises:
        ValueError: If hashed_password is invalid format
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except UnknownHashError as e:
        logger.warning(f"Invalid hash format encountered: {e}")
        return False
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    """
    Generate a secure hash for the given password using bcrypt.
    
    Args:
        password: The plain text password to hash
        
    Returns:
        str: The hashed password
        
    Raises:
        ValueError: If password is empty or None
    """
    if not password:
        raise ValueError("Password cannot be empty")
    
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Password hashing error: {e}")
        raise ValueError("Failed to hash password") from e


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token with the provided data and expiration.
    
    Args:
        data: Dictionary containing token payload data
        expires_delta: Optional custom expiration time
        
    Returns:
        str: Encoded JWT token
        
    Raises:
        ValueError: If data is invalid or token creation fails
    """
    if not data:
        raise ValueError("Token data cannot be empty")
    
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Add standard JWT claims
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    
    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        logger.info(f"Access token created for user: {data.get('sub', 'unknown')}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Token creation error: {e}")
        raise ValueError("Failed to create access token") from e


def create_refresh_token(data: Dict[str, Any]) -> Optional[str]:
    """
    Create a JWT refresh token with extended expiration.
    
    Args:
        data: Dictionary containing token payload data
        
    Returns:
        Optional[str]: Encoded JWT refresh token or None if refresh tokens disabled
        
    Raises:
        ValueError: If data is invalid or token creation fails
    """
    if not REFRESH_TOKEN_EXPIRE_DAYS:
        return None
    
    if not data:
        raise ValueError("Token data cannot be empty")
    
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })
    
    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        logger.info(f"Refresh token created for user: {data.get('sub', 'unknown')}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Refresh token creation error: {e}")
        raise ValueError("Failed to create refresh token") from e


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: The JWT token to decode
        
    Returns:
        Dict[str, Any]: Decoded token payload
        
    Raises:
        TokenExpiredError: If token has expired
        InvalidTokenError: If token is invalid or malformed
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        raise TokenExpiredError()
    except jwt.JWTClaimsError as e:
        logger.warning(f"Invalid token claims: {e}")
        raise InvalidTokenError("Invalid token claims")
    except jwt.JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise InvalidTokenError("Invalid token format")
    except Exception as e:
        logger.error(f"Unexpected token decode error: {e}")
        raise InvalidTokenError("Token validation failed")


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Authenticate a user with email/username and password.
    
    Args:
        db: Database session
        email: User's email or username
        password: Plain text password
        
    Returns:
        Optional[User]: User object if authentication successful, None otherwise
    """
    if not email or not password:
        logger.warning("Authentication attempted with empty credentials")
        return None
    
    try:
        # Try to get user by email first
        user = db.query(User).filter(User.email == email).first()
        
        # If not found and username field exists, try username
        if not user and hasattr(User, 'username'):
            user = db.query(User).filter(User.username == email).first()
        
        if not user:
            logger.warning(f"Authentication failed: user not found for {email}")
            return None
        
        if not verify_password(password, user.hashed_password):
            logger.warning(f"Authentication failed: invalid password for {email}")
            return None
        
        logger.info(f"User authenticated successfully: {email}")
        return user
        
    except Exception as e:
        logger.error(f"Authentication error for {email}: {e}")
        return None


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from JWT token.
    
    Args:
        token: JWT token from OAuth2 scheme
        db: Database session
        
    Returns:
        User: Current authenticated user
        
    Raises:
        AuthenticationError: If token is invalid or user not found
    """
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        
        if user_id is None:
            logger.warning("Token missing user ID")
            raise AuthenticationError("Invalid token: missing user ID")
        
        # Validate token type
        token_type = payload.get("type")
        if token_type != "access":
            logger.warning(f"Invalid token type: {token_type}")
            raise AuthenticationError("Invalid token type")
        
    except (TokenExpiredError, InvalidTokenError):
        # Re-raise custom token errors
        raise
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        raise AuthenticationError("Token validation failed")
    
    try:
        # Get user from database
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            logger.warning(f"User not found for ID: {user_id}")
            raise AuthenticationError("User not found")
        
        return user
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Database error while getting user {user_id}: {e}")
        raise AuthenticationError("Failed to retrieve user")


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get the current authenticated and active user.
    
    Args:
        current_user: Current authenticated user from get_current_user
        
    Returns:
        User: Current active user
        
    Raises:
        InactiveUserError: If user is not active
    """
    if not current_user.is_active:
        logger.warning(f"Inactive user access attempt: {current_user.email}")
        raise InactiveUserError()
    
    return current_user


def check_user_role(user: User, required_role: str) -> bool:
    """
    Check if user has the required role.
    
    Args:
        user: User object to check
        required_role: Required role name
        
    Returns:
        bool: True if user has the role, False otherwise
    """
    if not hasattr(user, 'roles') or not user.roles:
        return False
    
    # Handle different role storage formats
    if isinstance(user.roles, str):
        user_roles = [role.strip() for role in user.roles.split(',')]
    elif isinstance(user.roles, list):
        user_roles = user.roles
    else:
        # Assume it's a relationship with role objects
        user_roles = [role.name for role in user.roles]
    
    return required_role in user_roles


def require_role(required_role: str):
    """
    Dependency factory for role-based access control.
    
    Args:
        required_role: Required role name
        
    Returns:
        Dependency function that checks user role
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if not check_user_role(current_user, required_role):
            logger.warning(
                f"Access denied: user {current_user.email} lacks role {required_role}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: {required_role} role required"
            )
        return current_user
    
    return role_checker


def require_any_role(*required_roles: str):
    """
    Dependency factory for checking if user has any of the specified roles.
    
    Args:
        required_roles: List of acceptable role names
        
    Returns:
        Dependency function that checks user has at least one role
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if not any(check_user_role(current_user, role) for role in required_roles):
            logger.warning(
                f"Access denied: user {current_user.email} lacks any of roles {required_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: one of {required_roles} roles required"
            )
        return current_user
    
    return role_checker


def create_token_pair(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create both access and refresh tokens for a user.
    
    Args:
        user_data: User data to include in token payload
        
    Returns:
        Dict containing access_token, token_type, expires_in, and optionally refresh_token
    """
    access_token = create_access_token(user_data)
    result = {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
    }
    
    refresh_token = create_refresh_token(user_data)
    if refresh_token:
        result["refresh_token"] = refresh_token
        result["refresh_expires_in"] = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60  # Convert to seconds
    
    return result


async def refresh_access_token(
    refresh_token: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Create a new access token using a valid refresh token.
    
    Args:
        refresh_token: Valid refresh token
        db: Database session
        
    Returns:
        Dict containing new access token information
        
    Raises:
        AuthenticationError: If refresh token is invalid
    """
    try:
        payload = decode_token(refresh_token)
        user_id: str = payload.get("sub")
        token_type = payload.get("type")
        
        if user_id is None or token_type != "refresh":
            raise AuthenticationError("Invalid refresh token")
        
        # Verify user still exists and is active
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")
        
        # Create new access token
        user_data = {"sub": str(user.id)}
        if hasattr(user, 'roles') and user.roles:
            user_data["roles"] = user.roles
        
        return {
            "access_token": create_access_token(user_data),
            "token_type": "bearer"
        }
    except (TokenExpiredError, InvalidTokenError) as e:
        logger.warning(f"Refresh token validation error: {e}")
        raise AuthenticationError("Invalid refresh token")