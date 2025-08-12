from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from passlib.context import CryptContext
import jwt

# Local imports
from config import settings

# Setup logging
logger = logging.getLogger(__name__)

# Database setup
Base = declarative_base()
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Auth setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: secrets.token_urlsafe(16))
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=False)
    activation_token = Column(String, nullable=True)
    reset_token = Column(String, nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    
    model_config = ConfigDict(from_attributes=True)

class UserResponse(BaseModel):
    email: EmailStr
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise credentials_exception
    return user

def create_access_token(data: Dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

async def send_activation_email(email: str, token: str):
    message = MIMEMultipart()
    message["From"] = settings.SMTP_SENDER
    message["To"] = email
    message["Subject"] = "Activate Your Account"
    
    body = f"Click here to activate your account: {settings.BASE_URL}/activate/{token}"
    message.attach(MIMEText(body, "plain"))
    
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(message)

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    hashed_password = pwd_context.hash(user_data.password)
    activation_token = secrets.token_urlsafe(32)
    
    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        activation_token=activation_token
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    await send_activation_email(user.email, activation_token)
    
    return user

@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please activate your account first"
        )
        
    access_token = create_access_token(data={"sub": user.email})
    return Token(access_token=access_token, token_type="bearer")

@router.get("/activate/{token}")
async def activate_account(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.activation_token == token).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid activation token"
        )
        
    user.is_active = True
    user.activation_token = None
    db.commit()
    
    return {"message": "Account activated successfully"}

@router.post("/password-reset/request")
async def request_password_reset(email: EmailStr, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    reset_token = secrets.token_urlsafe(32)
    user.reset_token = reset_token
    user.reset_token_expires = datetime.utcnow() + timedelta(hours=24)
    db.commit()
    
    # Send reset email implementation here
    return {"message": "Password reset instructions sent"}

@router.post("/password-reset/confirm")
async def reset_password(
    token: str,
    new_password: str,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.reset_token == token,
        User.reset_token_expires > datetime.utcnow()
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    user.hashed_password = pwd_context.hash(new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    
    return {"message": "Password reset successful"}