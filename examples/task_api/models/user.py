"""
User model for authentication and task ownership.

This module implements a SQLAlchemy User model with secure password handling,
soft deletion capabilities, and proper relationship management with tasks.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import bcrypt
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Index,
    create_engine, text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

# Import Task model - adjust import path as needed
# from .task import Task

Base = declarative_base()


class User(Base):
    """
    User model for authentication and task ownership.
    
    Implements secure password hashing with bcrypt, soft deletion using
    is_active field, and one-to-many relationship with tasks.
    """
    
    __tablename__ = 'users'
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # User credentials and info
    username: Mapped[str] = mapped_column(
        String(80), 
        unique=True, 
        nullable=False,
        index=True,
        comment="Unique username for authentication"
    )
    
    email: Mapped[str] = mapped_column(
        String(120), 
        unique=True, 
        nullable=False,
        index=True,
        comment="Unique email address for user identification"
    )
    
    hashed_password: Mapped[str] = mapped_column(
        String(128), 
        nullable=False,
        comment="Bcrypt hashed password - never store plain text"
    )
    
    # Status and metadata
    is_active: Mapped[bool] = mapped_column(
        Boolean, 
        default=True, 
        nullable=False,
        comment="Soft deletion flag - False indicates deleted user"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
        comment="UTC timestamp of user creation"
    )
    
    # Relationships
    tasks: Mapped[List["Task"]] = relationship(
        "Task",
        back_populates="user",
        cascade="all, save-update",  # Don't cascade delete for soft deletion
        lazy="select",
        order_by="Task.created_at.desc()"
    )
    
    # Database indexes for performance
    __table_args__ = (
        Index('idx_user_username_active', 'username', 'is_active'),
        Index('idx_user_email_active', 'email', 'is_active'),
        Index('idx_user_created_at', 'created_at'),
    )
    
    # Security configuration
    _BCRYPT_ROUNDS = 12  # Cost factor for bcrypt hashing
    
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
            email: Unique email address for the user
            password: Plain text password (will be hashed automatically)
            is_active: Whether the user account is active (default: True)
        """
        self.username = username
        self.email = email
        self.hashed_password = self._hash_password(password)
        self.is_active = is_active
    
    @classmethod
    def _hash_password(cls, password: str) -> str:
        """
        Hash a plain text password using bcrypt.
        
        Uses a cost factor of 12 rounds for security. This provides good
        protection against brute force attacks while maintaining reasonable
        performance for authentication.
        
        Args:
            password: Plain text password to hash
            
        Returns:
            str: Bcrypt hashed password
            
        Raises:
            ValueError: If password is empty or None
            RuntimeError: If bcrypt hashing fails
        """
        if not password:
            raise ValueError("Password cannot be empty or None")
        
        try:
            # Convert password to bytes and generate salt
            password_bytes = password.encode('utf-8')
            salt = bcrypt.gensalt(rounds=cls._BCRYPT_ROUNDS)
            
            # Hash password with salt
            hashed = bcrypt.hashpw(password_bytes, salt)
            
            # Return as string for database storage
            return hashed.decode('utf-8')
            
        except Exception as e:
            raise RuntimeError(f"Failed to hash password: {str(e)}") from e
    
    def verify_password(self, password: str) -> bool:
        """
        Verify a plain text password against the stored hash.
        
        Uses bcrypt's checkpw function which includes timing attack protection
        by always performing the full hash computation regardless of early
        mismatches.
        
        Args:
            password: Plain text password to verify
            
        Returns:
            bool: True if password matches, False otherwise
        """
        if not password or not self.hashed_password:
            return False
        
        try:
            password_bytes = password.encode('utf-8')
            hashed_bytes = self.hashed_password.encode('utf-8')
            
            return bcrypt.checkpw(password_bytes, hashed_bytes)
            
        except Exception:
            # Log the exception in production, but don't expose details
            # logger.warning(f"Password verification failed for user {self.id}")
            return False
    
    def update_password(self, new_password: str) -> None:
        """
        Update the user's password with a new hashed password.
        
        Args:
            new_password: New plain text password
            
        Raises:
            ValueError: If new password is invalid
            RuntimeError: If password hashing fails
        """
        self.hashed_password = self._hash_password(new_password)
    
    def soft_delete(self) -> None:
        """
        Perform soft deletion by setting is_active to False.
        
        This preserves the user record and associated data while marking
        the account as inactive. The user will not be able to authenticate
        and should be filtered out of active user queries.
        """
        self.is_active = False
    
    def reactivate(self) -> None:
        """
        Reactivate a soft-deleted user account.
        
        Sets is_active back to True, allowing the user to authenticate again.
        """
        self.is_active = True
    
    def to_dict(self, include_relationships: bool = False) -> Dict[str, Any]:
        """
        Convert user instance to dictionary for API responses.
        
        Excludes sensitive fields like hashed_password and formats datetime
        objects as ISO strings for JSON serialization.
        
        Args:
            include_relationships: Whether to include related tasks data
            
        Returns:
            Dict[str, Any]: User data dictionary safe for API responses
        """
        user_dict = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        if include_relationships and hasattr(self, 'tasks'):
            # Only include basic task info to avoid circular references
            user_dict['tasks'] = [
                {
                    'id': task.id,
                    'title': getattr(task, 'title', None),
                    'status': getattr(task, 'status', None),
                    'created_at': task.created_at.isoformat() if hasattr(task, 'created_at') and task.created_at else None
                }
                for task in self.tasks
            ]
        
        return user_dict
    
    @property
    def active_tasks_count(self) -> int:
        """
        Get count of active tasks for this user.
        
        Returns:
            int: Number of active tasks
        """
        if not hasattr(self, 'tasks'):
            return 0
        
        return len([
            task for task in self.tasks 
            if getattr(task, 'is_active', True)
        ])
    
    def __repr__(self) -> str:
        """
        String representation for debugging.
        
        Returns:
            str: Safe string representation excluding sensitive data
        """
        return (
            f"<User(id={self.id}, username='{self.username}', "
            f"email='{self.email}', is_active={self.is_active})>"
        )
    
    def __str__(self) -> str:
        """
        Human-readable string representation.
        
        Returns:
            str: User's username
        """
        return self.username


# Query helper methods (can be moved to a separate service class)
class UserQueryMixin:
    """
    Mixin class with common query methods for User model.
    
    These methods can be used with SQLAlchemy sessions to perform
    common user operations with proper soft deletion handling.
    """
    
    @staticmethod
    def get_active_users(session):
        """Get all active users (is_active=True)."""
        return session.query(User).filter(User.is_active == True)
    
    @staticmethod
    def find_by_username(session, username: str, active_only: bool = True):
        """Find user by username, optionally filtering to active users only."""
        query = session.query(User).filter(User.username == username)
        if active_only:
            query = query.filter(User.is_active == True)
        return query.first()
    
    @staticmethod
    def find_by_email(session, email: str, active_only: bool = True):
        """Find user by email, optionally filtering to active users only."""
        query = session.query(User).filter(User.email == email)
        if active_only:
            query = query.filter(User.is_active == True)
        return query.first()