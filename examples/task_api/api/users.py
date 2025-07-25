from typing import List
from datetime import datetime, timedelta
import re

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, EmailStr, Field
import bcrypt
from jose import JWTError, jwt

from core.database import get_db
from models.user import User

# Constants
SECRET_KEY = "your-secret-key"  # Move to config
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

router = APIRouter(prefix="/users", tags=["users"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "johndoe",
                "email": "john@example.com",
                "password": "secretpass"
            }
        }
    }

@router.get("/")
async def get_users(db: Session = Depends(get_db)) -> List[dict]:
    """Get list of all users"""
    users = db.query(User).all()
    return [{"id": user.id, "username": user.username, "email": user.email} 
            for user in users]

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: Session = Depends(get_db)) -> dict:
    """Create new user"""
    try:
        hashed_password = bcrypt.hashpw(
            user.password.encode('utf-8'),
            bcrypt.gensalt()
        )
        
        db_user = User(
            username=user.username,
            email=user.email,
            hashed_password=hashed_password.decode('utf-8')
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return {"id": db_user.id, "username": db_user.username, "email": db_user.email}
    
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )

@router.get("/{user_id}")
async def get_user(user_id: int, db: Session = Depends(get_db)) -> dict:
    """Get user by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    return {"id": user.id, "username": user.username, "email": user.email}

@router.get("/{user_id}/tasks")
async def get_user_tasks(user_id: int, db: Session = Depends(get_db)) -> List[dict]:
    """Get tasks for specific user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    return [{"id": task.id, "title": task.title, "completed": task.completed}
            for task in user.tasks]