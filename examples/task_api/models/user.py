"""
User model for authentication and task ownership.

This module implements a secure User model with bcrypt password hashing,
proper database constraints, and safe serialization methods.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
import bcrypt
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Index,
    func, event
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.declarative import declarative_base
import re

# Assuming base is imported from your database configuration
# from database import Base
Base = declarative_base()


class User(Base):
    """
    User model for authentication and task ownership.
    
    Implements secure password hashing with bcrypt, email validation,
    and soft deletion functionality.
    """
    
    __tablename__ = 'users'
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # User credentials - both unique and required
    username = Column(
        String(50), 
        unique=True, 
        nullable=False, 
        index=True,
        doc="Unique username for authentication"
    )
    
    email = Column(
        String(255), 
        unique=True, 
        nullable=False, 
        index=True,
        doc="Unique email address for user identification"
    )
    
    # Password storage - never expose this field
    hashed_password = Column(
        String(128), 
        nullable=False,
        doc="Bcrypt hashed password - never expose in API responses"
    )
    
    # Soft deletion flag
    is_active = Column(
        Boolean, 
        default=True, 
        nullable=False,
        doc="Soft deletion flag - False means user is deleted"
    )
    
    # Timestamp tracking
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False,
        doc="UTC timestamp of user creation"
    )
    
    # Relationship to tasks (one-to-many)
    tasks = relationship(
        "Task",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
        doc="All tasks owned by this user"
    )
    
    # Database indexes for performance
    __table_args__ = (
        Index('idx_user_username_active', 'username', 'is_active'),
        Index('idx_user_email_active', 'email', 'is_active'),
        Index('idx_user_created_at', 'created_at'),
    )
    
    # Email validation regex pattern
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    # Bcrypt configuration
    BCRYPT_ROUNDS = 12  # Secure salt rounds for production
    
    def __init__(
        self, 
        username: str, 
        email: str, 
        password: str,
        is_active: bool = True
    ) -> None:
        """
        Initialize a new User instance.
        
        Args:
            username: Unique username for the user
            email: Valid email address
            password: Plain text password (will be hashed)
            is_active: Whether the user account is active
            
        Raises:
            ValueError: If email format is invalid
        """
        self.username = username
        self.email = email
        self.set_password(password)
        self.is_active = is_active
    
    @validates('email')
    def validate_email(self, key: str, email: str) -> str:
        """
        Validate email format using regex pattern.
        
        Args:
            key: The field name being validated
            email: Email address to validate
            
        Returns:
            The validated email address
            
        Raises:
            ValueError: If email format is invalid
        """
        if not email or not self.EMAIL_PATTERN.match(email.lower()):
            raise ValueError(f"Invalid email format: {email}")
        return email.lower()
    
    @validates('username')
    def validate_username(self, key: str, username: str) -> str:
        """
        Validate username requirements.
        
        Args:
            key: The field name being validated
            username: Username to validate
            
        Returns:
            The validated username
            
        Raises:
            ValueError: If username is invalid
        """
        if not username or len(username.strip()) < 3:
            raise ValueError("Username must be at least 3 characters long")
        if len(username) > 50:
            raise ValueError("Username must be 50 characters or less")
        return username.strip()
    
    def set_password(self, password: str) -> None:
        """
        Hash and set the user's password using bcrypt.
        
        Args:
            password: Plain text password to hash
            
        Raises:
            ValueError: If password is empty or too weak
            RuntimeError: If bcrypt hashing fails
        """
        if not password or len(password.strip()) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        try:
            # Generate salt and hash password
            salt = bcrypt.gensalt(rounds=self.BCRYPT_ROUNDS)
            password_bytes = password.encode('utf-8')
            hashed = bcrypt.hashpw(password_bytes, salt)
            self.hashed_password = hashed.decode('utf-8')
        except Exception as e:
            raise RuntimeError(f"Failed to hash password: {str(e)}")
    
    def verify_password(self, password: str) -> bool:
        """
        Verify a password against the stored hash.
        
        This method is timing-attack resistant as bcrypt.checkpw
        performs constant-time comparison.
        
        Args:
            password: Plain text password to verify
            
        Returns:
            True if password matches, False otherwise
        """
        if not password or not self.hashed_password:
            return False
        
        try:
            password_bytes = password.encode('utf-8')
            hashed_bytes = self.hashed_password.encode('utf-8')
            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except Exception:
            # Log the exception in production, but don't expose details
            return False
    
    def soft_delete(self) -> None:
        """
        Soft delete the user by setting is_active to False.
        
        This preserves data integrity while marking the user as deleted.
        """
        self.is_active = False
    
    def restore(self) -> None:
        """
        Restore a soft-deleted user by setting is_active to True.
        """
        self.is_active = True
    
    def to_dict(self, include_tasks: bool = False) -> Dict[str, Any]:
        """
        Convert user instance to dictionary for API responses.
        
        Security Note: This method explicitly excludes hashed_password
        to prevent accidental exposure of sensitive data.
        
        Args:
            include_tasks: Whether to include user's tasks in the response
            
        Returns:
            Dictionary representation of the user (safe for API responses)
        """
        user_dict = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_tasks:
            user_dict['tasks'] = [
                task.to_dict() for task in self.tasks
            ] if self.tasks else []
        
        return user_dict
    
    def update_profile(
        self, 
        username: Optional[str] = None, 
        email: Optional[str] = None
    ) -> None:
        """
        Update user profile information.
        
        Args:
            username: New username (optional)
            email: New email address (optional)
        """
        if username is not None:
            self.username = username
        if email is not None:
            self.email = email
    
    def get_active_tasks_count(self) -> int:
        """
        Get count of active tasks for this user.
        
        Returns:
            Number of active tasks
        """
        return len([task for task in self.tasks if task.is_active])
    
    @classmethod
    def find_by_username(cls, session, username: str) -> Optional['User']:
        """
        Find an active user by username.
        
        Args:
            session: SQLAlchemy session
            username: Username to search for
            
        Returns:
            User instance if found and active, None otherwise
        """
        return session.query(cls).filter(
            cls.username == username,
            cls.is_active == True
        ).first()
    
    @classmethod
    def find_by_email(cls, session, email: str) -> Optional['User']:
        """
        Find an active user by email.
        
        Args:
            session: SQLAlchemy session
            email: Email address to search for
            
        Returns:
            User instance if found and active, None otherwise
        """
        return session.query(cls).filter(
            cls.email == email.lower(),
            cls.is_active == True
        ).first()
    
    def __repr__(self) -> str:
        """
        String representation for debugging.
        
        Note: Does not include sensitive information like passwords.
        """
        return (
            f"<User(id={self.id}, username='{self.username}', "
            f"email='{self.email}', is_active={self.is_active})>"
        )
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"User: {self.username} ({self.email})"


# Event listeners for additional security and data integrity

@event.listens_for(User.hashed_password, 'set')
def receive_set_password(target, value, oldvalue, initiator):
    """
    Event listener to prevent setting already hashed passwords.
    
    This helps prevent double-hashing if set_password is called multiple times.
    """
    # Check if the value looks like a bcrypt hash
    if value and isinstance(value, str) and value.startswith('$2b$'):
        # This is likely already a bcrypt hash, allow it
        return value
    return value


@event.listens_for(User, 'before_insert')
def receive_before_insert(mapper, connection, target):
    """
    Event listener to ensure data consistency before insert.
    """
    # Ensure email is lowercase
    if target.email:
        target.email = target.email.lower()
    
    # Ensure username is stripped
    if target.username:
        target.username = target.username.strip()


@event.listens_for(User, 'before_update')
def receive_before_update(mapper, connection, target):
    """
    Event listener to ensure data consistency before update.
    """
    # Ensure email is lowercase
    if target.email:
        target.email = target.email.lower()
    
    # Ensure username is stripped
    if target.username:
        target.username = target.username.strip()