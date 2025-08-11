from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Body, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field

from models.user import User
from services.auth import AuthService
from core.database import get_db

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


class UserRegistration(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "password": "strongpassword123",
                "full_name": "John Doe",
                "phone": "+1234567890",
            }
        }
    }


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegistration, db: Session = Depends(get_db)):
    """Register a new user"""
    if AuthService.get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    user = AuthService.create_user(db, user_data)
    await AuthService.send_verification_email(user.email)

    return {
        "message": "Registration successful. Please check your email to verify your account."
    }


@auth_router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return tokens"""
    user = AuthService.authenticate_user(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    tokens = AuthService.create_tokens(user.id)
    return tokens


@auth_router.post("/logout")
async def logout(current_user: User = Depends(AuthService.get_current_user)):
    """Logout current user"""
    AuthService.blacklist_token(current_user.id)
    return {"message": "Successfully logged out"}


@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str = Body(...), db: Session = Depends(get_db)):
    """Get new access token using refresh token"""
    new_tokens = AuthService.refresh_access_token(db, refresh_token)
    if not new_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    return new_tokens


@auth_router.get("/profile")
async def get_profile(current_user: User = Depends(AuthService.get_current_user)):
    """Get current user profile"""
    return current_user


@auth_router.put("/profile")
async def update_profile(
    profile_data: dict,
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
):
    """Update user profile"""
    updated_user = AuthService.update_user(db, current_user.id, profile_data)
    return updated_user


@auth_router.post("/change-password")
async def change_password(
    current_password: str = Body(...),
    new_password: str = Body(...),
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
):
    """Change user password"""
    if not AuthService.verify_password(current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    AuthService.update_password(db, current_user.id, new_password)
    return {"message": "Password updated successfully"}


@auth_router.post("/forgot-password")
async def forgot_password(email: str = Body(...), db: Session = Depends(get_db)):
    """Initiate password reset flow"""
    user = AuthService.get_user_by_email(db, email)
    if user:
        reset_token = AuthService.create_password_reset_token(user.id)
        await AuthService.send_password_reset_email(email, reset_token)
    return {
        "message": "If an account exists with this email, you will receive password reset instructions"
    }


@auth_router.post("/reset-password")
async def reset_password(
    token: str = Body(...), new_password: str = Body(...), db: Session = Depends(get_db)
):
    """Reset password using reset token"""
    user_id = AuthService.verify_password_reset_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    AuthService.update_password(db, user_id, new_password)
    return {"message": "Password has been reset successfully"}


@auth_router.post("/verify-email")
async def verify_email(token: str = Body(...), db: Session = Depends(get_db)):
    """Verify user email address"""
    user_id = AuthService.verify_email_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    AuthService.mark_email_verified(db, user_id)
    return {"message": "Email verified successfully"}
