from datetime import datetime
from typing import Dict, Optional

from sqlalchemy import Column, Integer, String, Boolean, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
import bcrypt

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __init__(self, username: str, email: str, password: str) -> None:
        """Initialize a new user with hashed password."""
        self.username = username
        self.email = email
        self.hashed_password = self._hash_password(password)

    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()

    def verify_password(self, password: str) -> bool:
        """Verify a password against the stored hash."""
        return bcrypt.checkpw(
            password.encode(),
            self.hashed_password.encode()
        )

    def to_dict(self) -> Dict:
        """Convert user to dictionary, excluding sensitive fields."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def get_by_username(cls, db: Session, username: str) -> Optional["User"]:
        """Get user by username."""
        return db.query(cls).filter(cls.username == username).first()

    @classmethod
    def get_by_email(cls, db: Session, email: str) -> Optional["User"]:
        """Get user by email."""
        return db.query(cls).filter(cls.email == email).first()

    def deactivate(self, db: Session) -> None:
        """Soft delete the user."""
        self.is_active = False
        db.commit()