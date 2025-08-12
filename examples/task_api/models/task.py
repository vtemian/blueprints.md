from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base

Base: DeclarativeMeta = declarative_base()

class Task(Base):
    """Task model for managing user tasks with status tracking."""
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1000))
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="tasks")

    # Indexes
    __table_args__ = (
        Index("ix_tasks_user_id", "user_id"),
        Index("ix_tasks_completed", "completed")
    )

    def __repr__(self) -> str:
        return f"<Task {self.id}: {self.title}>"