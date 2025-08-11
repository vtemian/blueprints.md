import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from redis import Redis
from sqlalchemy.orm import Session

from core.database import get_db, get_redis
from models.user import User

# Constants
SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
REFRESH_TOKEN_EXPIRE_DAYS: int = 7

# OAuth2 schemes
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")
optional_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="api/v1/auth/login", auto_error=False
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, db: Session, redis_client: Redis):
        self.db = db
        self.redis = redis_client

    def create_access_token(self, data: dict) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    def create_refresh_token(self, data: dict) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Generate password hash"""
        return pwd_context.hash(password)

    def blacklist_token(self, token: str, expire_delta: int) -> None:
        """Add token to blacklist in Redis"""
        self.redis.setex(f"blacklist:{token}", expire_delta, "true")

    def is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted"""
        return bool(self.redis.get(f"blacklist:{token}"))

    def store_refresh_token(self, user_id: int, token: str) -> None:
        """Store refresh token in Redis"""
        key = f"refresh_token:{user_id}"
        self.redis.setex(key, REFRESH_TOKEN_EXPIRE_DAYS * 86400, token)

    def rotate_refresh_token(self, user_id: int, old_token: str) -> str:
        """Rotate refresh token"""
        if not self.redis.get(f"refresh_token:{user_id}") == old_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid refresh token"
            )
        new_token = self.create_refresh_token({"sub": str(user_id)})
        self.store_refresh_token(user_id, new_token)
        return new_token


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Get current admin user"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    return current_user


def get_optional_user(
    token: Optional[str] = Depends(optional_oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Get optional authenticated user"""
    if not token:
        return None

    try:
        return get_current_user(token, db)
    except HTTPException:
        return None
