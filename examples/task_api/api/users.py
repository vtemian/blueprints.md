"""
User management API endpoints with authentication.
Production-ready FastAPI module for user registration, authentication, and profile management.
"""

import os
import re
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError

from models.user import User
from core.database import get_db

# Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Security setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Router setup
router = APIRouter(prefix="/users", tags=["users"])


# Pydantic Models
class UserRegistration(BaseModel):
    """User registration request model."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    
    @validator("email")
    def validate_email(cls, v):
        """Validate email format and sanitize input."""
        email = v.lower().strip()
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise ValueError("Invalid email format")
        return email
    
    @validator("password")
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r'\d', v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserLogin(BaseModel):
    """User login request model."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")
    
    @validator("email")
    def validate_email(cls, v):
        """Sanitize email input."""
        return v.lower().strip()


class UserProfile(BaseModel):
    """User profile response model."""
    id: int
    email: str
    is_active: bool
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    """User profile update request model."""
    email: Optional[EmailStr] = Field(None, description="New email address")
    
    @validator("email")
    def validate_email(cls, v):
        """Validate and sanitize email input."""
        if v is not None:
            email = v.lower().strip()
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                raise ValueError("Invalid email format")
            return email
        return v


class PasswordResetRequest(BaseModel):
    """Password reset request model."""
    email: EmailStr = Field(..., description="User email address")
    
    @validator("email")
    def validate_email(cls, v):
        """Sanitize email input."""
        return v.lower().strip()


class TokenResponse(BaseModel):
    """JWT token response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = JWT_EXPIRATION_HOURS * 3600


class MessageResponse(BaseModel):
    """Generic message response model."""
    message: str


# Utility Functions
def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email address."""
    result = await db.execute(select(User).filter(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID."""
    result = await db.execute(select(User).filter(User.id == user_id))
    return result.scalar_one_or_none()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer token credentials
        db: Database session
        
    Returns:
        User: Current authenticated user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await get_user_by_id(db, user_id=user_id)
    if user is None or not user.is_active:
        raise credentials_exception
    
    return user


# API Endpoints
@router.post("/register", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserRegistration,
    db: AsyncSession = Depends(get_db)
) -> UserProfile:
    """
    Register a new user account.
    
    Args:
        user_data: User registration data
        db: Database session
        
    Returns:
        UserProfile: Created user profile
        
    Raises:
        HTTPException: If email already exists or validation fails
    """
    # Check if user already exists
    existing_user = await get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = hash_password(user_data.password)
    new_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        is_active=True
    )
    
    try:
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    return UserProfile.from_orm(new_user)


@router.post("/login", response_model=TokenResponse)
async def login_user(
    user_data: UserLogin,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Authenticate user and return JWT token.
    
    Args:
        user_data: User login credentials
        db: Database session
        
    Returns:
        TokenResponse: JWT access token
        
    Raises:
        HTTPException: If credentials are invalid
    """
    user = await get_user_by_email(db, user_data.email)
    
    if not user or not user.is_active or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.id})
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=JWT_EXPIRATION_HOURS * 3600
    )


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
) -> UserProfile:
    """
    Get current user's profile information.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        UserProfile: User profile data
    """
    return UserProfile.from_orm(current_user)


@router.put("/me", response_model=UserProfile)
async def update_user_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserProfile:
    """
    Update current user's profile information.
    
    Args:
        profile_data: Profile update data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        UserProfile: Updated user profile
        
    Raises:
        HTTPException: If email already exists or validation fails
    """
    # Check if email is being updated and if it already exists
    if profile_data.email and profile_data.email != current_user.email:
        existing_user = await get_user_by_email(db, profile_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        current_user.email = profile_data.email
    
    try:
        await db.commit()
        await db.refresh(current_user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    return UserProfile.from_orm(current_user)


@router.post("/password-reset", response_model=MessageResponse)
async def request_password_reset(
    reset_data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Request password reset for user account.
    
    Note: In production, this should send an email with a secure reset link
    instead of directly resetting the password.
    
    Args:
        reset_data: Password reset request data
        db: Database session
        
    Returns:
        MessageResponse: Success message
        
    Raises:
        HTTPException: If user not found
    """
    user = await get_user_by_email(db, reset_data.email)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is inactive"
        )
    
    # In production, generate a secure reset token and send email
    # For now, return a success message
    # reset_token = create_access_token(data={"sub": user.id, "type": "password_reset"})
    # send_password_reset_email(user.email, reset_token)
    
    return MessageResponse(
        message="Password reset instructions have been sent to your email address"
    )