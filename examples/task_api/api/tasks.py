"""
Task management API endpoints with CRUD operations.

This module provides RESTful endpoints for managing tasks with proper
authentication, authorization, and error handling.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

# Import dependencies (these would be implemented in your project)
from ..core.database import get_db
from ..models.task import Task
from ..models.user import User
from ..core.auth import get_current_user

# Create router instance
router = APIRouter(prefix="/tasks", tags=["tasks"])


# Pydantic Models
class TaskBase(BaseModel):
    """Base task model with common fields."""
    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    description: Optional[str] = Field(None, max_length=1000, description="Task description")
    completed: bool = Field(default=False, description="Task completion status")
    priority: Optional[str] = Field(
        default="medium", 
        regex="^(low|medium|high)$", 
        description="Task priority level"
    )
    due_date: Optional[datetime] = Field(None, description="Task due date")


class TaskCreate(TaskBase):
    """Model for creating new tasks."""
    pass


class TaskUpdate(BaseModel):
    """Model for updating existing tasks."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    completed: Optional[bool] = None
    priority: Optional[str] = Field(None, regex="^(low|medium|high)$")
    due_date: Optional[datetime] = None


class TaskResponse(TaskBase):
    """Model for task responses."""
    id: int = Field(..., description="Task ID")
    user_id: int = Field(..., description="Owner user ID")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: datetime = Field(..., description="Task last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class TaskList(BaseModel):
    """Model for paginated task list responses."""
    tasks: List[TaskResponse] = Field(..., description="List of tasks")
    total: int = Field(..., description="Total number of tasks")
    limit: int = Field(..., description="Number of tasks per page")
    offset: int = Field(..., description="Number of tasks skipped")
    has_next: bool = Field(..., description="Whether there are more tasks")


# Dependency Functions
async def get_task_by_id(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Task:
    """
    Retrieve a task by ID and validate user ownership.
    
    Args:
        task_id: The task ID to retrieve
        current_user: The authenticated user
        db: Database session
        
    Returns:
        Task: The requested task
        
    Raises:
        HTTPException: If task not found or user doesn't own the task
    """
    try:
        task = db.query(Task).filter(
            Task.id == task_id,
            Task.user_id == current_user.id
        ).first()
        
        if not task:
            # Check if task exists but belongs to different user
            task_exists = db.query(Task).filter(Task.id == task_id).first()
            if task_exists:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to access this task"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Task not found"
                )
        
        return task
        
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )


# API Endpoints
@router.get("/", response_model=TaskList, status_code=status.HTTP_200_OK)
async def list_tasks(
    completed: Optional[bool] = Query(None, description="Filter by completion status"),
    limit: int = Query(20, ge=1, le=100, description="Number of tasks to return"),
    offset: int = Query(0, ge=0, description="Number of tasks to skip"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> TaskList:
    """
    Retrieve a paginated list of tasks for the authenticated user.
    
    Args:
        completed: Optional filter by completion status
        limit: Maximum number of tasks to return (1-100)
        offset: Number of tasks to skip for pagination
        current_user: The authenticated user
        db: Database session
        
    Returns:
        TaskList: Paginated list of tasks with metadata
    """
    try:
        # Build query with user filter
        query = db.query(Task).filter(Task.user_id == current_user.id)
        
        # Apply completion status filter if provided
        if completed is not None:
            query = query.filter(Task.completed == completed)
        
        # Get total count for pagination metadata
        total = query.count()
        
        # Apply pagination and ordering
        tasks = query.order_by(Task.created_at.desc()).offset(offset).limit(limit).all()
        
        # Calculate pagination metadata
        has_next = (offset + limit) < total
        
        return TaskList(
            tasks=tasks,
            total=total,
            limit=limit,
            offset=offset,
            has_next=has_next
        )
        
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while retrieving tasks"
        )


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> TaskResponse:
    """
    Create a new task for the authenticated user.
    
    Args:
        task_data: Task creation data
        current_user: The authenticated user
        db: Database session
        
    Returns:
        TaskResponse: The created task
    """
    try:
        # Create new task instance
        db_task = Task(
            **task_data.model_dump(),
            user_id=current_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Add to database
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        
        return db_task
        
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while creating task"
        )


@router.get("/{task_id}", response_model=TaskResponse, status_code=status.HTTP_200_OK)
async def get_task(
    task: Task = Depends(get_task_by_id)
) -> TaskResponse:
    """
    Retrieve a specific task by ID.
    
    Args:
        task: The task retrieved by dependency injection
        
    Returns:
        TaskResponse: The requested task
    """
    return task


@router.put("/{task_id}", response_model=TaskResponse, status_code=status.HTTP_200_OK)
async def update_task(
    task_data: TaskUpdate,
    task: Task = Depends(get_task_by_id),
    db: Session = Depends(get_db)
) -> TaskResponse:
    """
    Update an existing task.
    
    Args:
        task_data: Task update data
        task: The task to update (retrieved by dependency injection)
        db: Database session
        
    Returns:
        TaskResponse: The updated task
    """
    try:
        # Update only provided fields
        update_data = task_data.model_dump(exclude_unset=True)
        
        if not update_data:
            # No fields to update
            return task
        
        # Apply updates
        for field, value in update_data.items():
            setattr(task, field, value)
        
        # Update timestamp
        task.updated_at = datetime.utcnow()
        
        # Commit changes
        db.commit()
        db.refresh(task)
        
        return task
        
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while updating task"
        )


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task: Task = Depends(get_task_by_id),
    db: Session = Depends(get_db)
) -> None:
    """
    Delete a specific task.
    
    Args:
        task: The task to delete (retrieved by dependency injection)
        db: Database session
    """
    try:
        db.delete(task)
        db.commit()
        
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while deleting task"
        )


# Health check endpoint for the tasks module
@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict:
    """
    Health check endpoint for the tasks API.
    
    Returns:
        dict: Health status information
    """
    return {
        "status": "healthy",
        "module": "tasks",
        "timestamp": datetime.utcnow().isoformat()
    }