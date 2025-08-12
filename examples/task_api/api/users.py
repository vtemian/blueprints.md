"""
User management API endpoints with authentication.

This module provides comprehensive user management functionality including
registration, authentication, profile management, and password reset.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from models.user import User
from core.database import get_db

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Security setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/users/login")

# Router setup
router = APIRouter(prefix="/api/users", tags=["users"])


# Pydantic Models
class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str
    
    @validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user response (excludes sensitive data)."""
    id: int
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Schema for user profile updates."""
    email: Optional[EmailStr] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None
    
    @validator("new_password")
    def validate_new_password(cls, v):
        if v is not None:
            if len(v) < 8:
                raise ValueError("Password must be at least 8 characters long")
            if not any(c.isupper() for c in v):
                raise ValueError("Password must contain at least one uppercase letter")
            if not any(c.islower() for c in v):
                raise ValueError("Password must contain at least one lowercase letter")
            if not any(c.isdigit() for c in v):
                raise ValueError("Password must contain at least one digit")
        return v


class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""
    email: EmailStr


# Utility Functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate user with email and password."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    
    return user


# API Endpoints
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.
    
    - **email**: Valid email address (must be unique)
    - **password**: Strong password (min 8 chars, uppercase, lowercase, digit)
    
    Returns the created user data (excluding password).
    """
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        
        # Create new user
        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            email=user_data.email,
            hashed_password=hashed_password,
            created_at=datetime.utcnow()
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return db_user
        
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during registration"
        )


@router.post("/login", response_model=Token)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT token.
    
    - **username**: User's email address
    - **password**: User's password
    
    Returns JWT access token for authenticated requests.
    """
    try:
        user = authenticate_user(db, form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's profile information.
    
    Requires valid JWT token in Authorization header.
    Returns current user's profile data.
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile.
    
    - **email**: New email address (optional, must be unique)
    - **current_password**: Required if changing password
    - **new_password**: New password (optional, must meet strength requirements)
    
    Requires valid JWT token in Authorization header.
    """
    try:
        # Handle password change
        if user_update.new_password:
            if not user_update.current_password:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Current password required to set new password"
                )
            
            if not verify_password(user_update.current_password, current_user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Current password is incorrect"
                )
            
            current_user.hashed_password = get_password_hash(user_update.new_password)
        
        # Handle email change
        if user_update.email and user_update.email != current_user.email:
            # Check if new email is already taken
            existing_user = db.query(User).filter(
                User.email == user_update.email,
                User.id != current_user.id
            ).first()
            
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already in use"
                )
            
            current_user.email = user_update.email
        
        db.commit()
        db.refresh(current_user)
        
        return current_user
        
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already in use"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during profile update"
        )


@router.post("/password-reset", status_code=status.HTTP_200_OK)
async def request_password_reset(
    reset_request: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """
    Request password reset for user account.
    
    - **email**: Email address of the account
    
    Returns consistent response regardless of whether email exists (security measure).
    In production, this would trigger an email with reset instructions.
    """
    try:
        # Check if user exists (but don't reveal this information in response)
        user = db.query(User).filter(User.email == reset_request.email).first()
        
        if user:
            # In production, you would:
            # 1. Generate a secure reset token
            # 2. Store it in database with expiration
            # 3. Send email with reset link
            # 4. Log the reset request
            pass
        
        # Always return the same response for security
        return {
            "message": "If an account with that email exists, password reset instructions have been sent."
        }
        
    except Exception as e:
        # Log error but still return consistent response
        return {
            "message": "If an account with that email exists, password reset instructions have been sent."
        }


# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint for user service."""
    return {"status": "healthy", "service": "user-management"}