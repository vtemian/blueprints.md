"""
Task model for managing user tasks with status tracking.

This module defines the Task model with proper relationships to the User model,
automatic timestamp handling, and optimized database indexes for performance.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# Assuming you're using Flask-SQLAlchemy or similar setup
# If using pure SQLAlchemy, replace 'db' with your declarative base
try:
    from flask_sqlalchemy import SQLAlchemy
    db = SQLAlchemy()
    Base = db.Model
except ImportError:
    # Fallback for pure SQLAlchemy
    Base = declarative_base()


class Task(Base):
    """
    Task model for managing user tasks with status tracking.
    
    Attributes:
        id: Primary key identifier
        title: Task title (required)
        description: Optional task description
        completed: Boolean status with default False
        user_id: Foreign key reference to User model
        created_at: Automatic creation timestamp
        updated_at: Automatic update timestamp
        user: Relationship to User model
    """
    
    __tablename__ = 'tasks'
    
    # Primary key
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Primary key identifier"
    )
    
    # Task fields
    title = Column(
        String(255),
        nullable=False,
        doc="Task title - required field"
    )
    
    description = Column(
        Text,
        nullable=True,
        doc="Optional detailed task description"
    )
    
    completed = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text('FALSE'),
        doc="Task completion status"
    )
    
    # Foreign key relationship
    user_id = Column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        doc="Foreign key reference to User model"
    )
    
    # Automatic timestamps
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP'),
        default=datetime.utcnow,
        doc="Automatic creation timestamp"
    )
    
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP'),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        doc="Automatic update timestamp"
    )
    
    # Relationships
    user = relationship(
        "User",
        back_populates="tasks",
        lazy="select",
        doc="Relationship to User model"
    )
    
    # Database indexes for performance optimization
    __table_args__ = (
        Index('idx_task_user_id', 'user_id'),
        Index('idx_task_completed', 'completed'),
        Index('idx_task_user_completed', 'user_id', 'completed'),
        Index('idx_task_created_at', 'created_at'),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}
    )
    
    def __init__(
        self,
        title: str,
        user_id: int,
        description: Optional[str] = None,
        completed: bool = False
    ) -> None:
        """
        Initialize a new Task instance.
        
        Args:
            title: The task title (required)
            user_id: The ID of the user who owns this task
            description: Optional task description
            completed: Task completion status (defaults to False)
        """
        self.title = title
        self.user_id = user_id
        self.description = description
        self.completed = completed
    
    def __repr__(self) -> str:
        """
        String representation of the Task instance for debugging.
        
        Returns:
            String representation of the task
        """
        return (
            f"<Task(id={self.id}, title='{self.title}', "
            f"completed={self.completed}, user_id={self.user_id})>"
        )
    
    def __str__(self) -> str:
        """
        Human-readable string representation of the Task.
        
        Returns:
            Human-readable task representation
        """
        status = "✓" if self.completed else "○"
        return f"{status} {self.title}"
    
    def to_dict(self) -> dict:
        """
        Convert the Task instance to a dictionary representation.
        
        Returns:
            Dictionary containing task data
        """
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'completed': self.completed,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def mark_completed(self) -> None:
        """Mark the task as completed."""
        self.completed = True
    
    def mark_incomplete(self) -> None:
        """Mark the task as incomplete."""
        self.completed = False
    
    def toggle_completion(self) -> bool:
        """
        Toggle the completion status of the task.
        
        Returns:
            The new completion status
        """
        self.completed = not self.completed
        return self.completed
    
    @property
    def is_completed(self) -> bool:
        """
        Check if the task is completed.
        
        Returns:
            True if task is completed, False otherwise
        """
        return self.completed
    
    @property
    def age_in_days(self) -> Optional[int]:
        """
        Calculate the age of the task in days.
        
        Returns:
            Number of days since task creation, or None if created_at is not set
        """
        if not self.created_at:
            return None
        
        delta = datetime.utcnow() - self.created_at
        return delta.days
    
    @classmethod
    def get_by_user_and_status(
        cls,
        session,
        user_id: int,
        completed: Optional[bool] = None
    ):
        """
        Get tasks by user ID and optionally filter by completion status.
        
        Args:
            session: SQLAlchemy session
            user_id: The user ID to filter by
            completed: Optional completion status filter
            
        Returns:
            Query object for tasks matching the criteria
        """
        query = session.query(cls).filter(cls.user_id == user_id)
        
        if completed is not None:
            query = query.filter(cls.completed == completed)
            
        return query.order_by(cls.created_at.desc())
    
    @classmethod
    def get_completed_tasks(cls, session, user_id: int):
        """
        Get all completed tasks for a user.
        
        Args:
            session: SQLAlchemy session
            user_id: The user ID to filter by
            
        Returns:
            Query object for completed tasks
        """
        return cls.get_by_user_and_status(session, user_id, completed=True)
    
    @classmethod
    def get_pending_tasks(cls, session, user_id: int):
        """
        Get all pending (incomplete) tasks for a user.
        
        Args:
            session: SQLAlchemy session
            user_id: The user ID to filter by
            
        Returns:
            Query object for pending tasks
        """
        return cls.get_by_user_and_status(session, user_id, completed=False)


# If using Flask-SQLAlchemy, you might want to add this to your User model:
"""
# Add this to your User model:
tasks = relationship(
    "Task",
    back_populates="user",
    lazy="dynamic",
    cascade="all, delete-orphan",
    order_by="Task.created_at.desc()"
)
"""