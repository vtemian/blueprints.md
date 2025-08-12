from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, event
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from .user import User
from ..database import Base


class Task(Base):
    __tablename__ = 'tasks'
    
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    title: str = Column(String(200), nullable=False)
    description: Optional[str] = Column(Text, nullable=True)
    completed: bool = Column(Boolean, nullable=False, default=False)
    user_id: int = Column(
        Integer, 
        ForeignKey('users.id', name='fk_tasks_user_id'), 
        nullable=False
    )
    created_at: datetime = Column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=func.now()
    )
    updated_at: datetime = Column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationship
    user = relationship("User", back_populates="tasks", lazy="select")
    
    # Indexes
    __table_args__ = (
        Index('ix_tasks_user_id', 'user_id'),
        Index('ix_tasks_completed', 'completed'),
        Index('ix_tasks_user_id_completed', 'user_id', 'completed'),
    )
    
    @validates('title')
    def validate_title(self, key: str, title: str) -> str:
        if not title or not title.strip():
            raise ValueError("Title cannot be empty or contain only whitespace")
        return title.strip()
    
    def __repr__(self) -> str:
        return (
            f"<Task(id={self.id}, title='{self.title}', "
            f"completed={self.completed}, user_id={self.user_id})>"
        )


# Event listener to ensure updated_at is always set on modification
@event.listens_for(Task, 'before_update')
def receive_before_update(mapper, connection, target):
    target.updated_at = func.now()