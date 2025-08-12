"""
Task management API endpoints with CRUD operations.

This module provides RESTful endpoints for managing user tasks with proper
authentication, authorization, and data validation.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

# Assuming these imports exist based on the blueprint
from models.task import Task
from models.user import User
from core.database import get_db
from core.auth import get_current_user  # Assumed authentication dependency


# Pydantic Models for Request/Response Validation
class TaskBase(BaseModel):
    """Base task model with common fields."""
    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    description: Optional[str] = Field(None, max_length=1000, description="Task description")
    completed: bool = Field(default=False, description="Task completion status")
    priority: Optional[str] = Field(
        default="medium", 
        pattern="^(low|medium|high)$", 
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
    priority: Optional[str] = Field(None, pattern="^(low|medium|high)$")
    due_date: Optional[datetime] = None


class TaskResponse(TaskBase):
    """Model for task API responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Task unique identifier")
    user_id: int = Field(..., description="Owner user ID")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: datetime = Field(..., description="Task last update timestamp")


class TaskListResponse(BaseModel):
    """Model for paginated task list responses."""
    tasks: List[TaskResponse] = Field(..., description="List of tasks")
    total: int = Field(..., description="Total number of tasks")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")


# Router setup
router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    responses={
        404: {"description": "Task not found"},
        403: {"description": "Not authorized to access this task"},
    }
)


# Helper Functions
async def get_task_by_id_and_user(
    task_id: int, 
    user_id: int, 
    db: AsyncSession
) -> Task:
    """
    Retrieve a task by ID ensuring it belongs to the specified user.
    
    Args:
        task_id: The task identifier
        user_id: The user identifier
        db: Database session
        
    Returns:
        Task object if found and owned by user
        
    Raises:
        HTTPException: If task not found or not owned by user
    """
    query = select(Task).where(
        and_(Task.id == task_id, Task.user_id == user_id)
    )
    result = await db.execute(query)
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or you don't have permission to access it"
        )
    
    return task


# API Endpoints
@router.get("/", response_model=TaskListResponse, status_code=status.HTTP_200_OK)
async def list_tasks(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    completed: Optional[bool] = Query(None, description="Filter by completion status"),
    priority: Optional[str] = Query(
        None, 
        pattern="^(low|medium|high)$",
        description="Filter by priority level"
    ),
    search: Optional[str] = Query(None, min_length=1, description="Search in title and description"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TaskListResponse:
    """
    Retrieve a paginated list of tasks for the authenticated user.
    
    Supports filtering by completion status, priority, and text search.
    Results are ordered by creation date (newest first).
    """
    try:
        # Build base query
        query = select(Task).where(Task.user_id == current_user.id)
        
        # Apply filters
        if completed is not None:
            query = query.where(Task.completed == completed)
            
        if priority:
            query = query.where(Task.priority == priority)
            
        if search:
            search_term = f"%{search}%"
            query = query.where(
                Task.title.ilike(search_term) | 
                Task.description.ilike(search_term)
            )
        
        # Get total count for pagination
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination and ordering
        offset = (page - 1) * per_page
        query = query.order_by(Task.created_at.desc()).offset(offset).limit(per_page)
        
        # Execute query
        result = await db.execute(query)
        tasks = result.scalars().all()
        
        # Calculate pagination metadata
        total_pages = (total + per_page - 1) // per_page
        
        return TaskListResponse(
            tasks=[TaskResponse.model_validate(task) for task in tasks],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving tasks"
        )


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """
    Create a new task for the authenticated user.
    
    The task will be automatically associated with the current user.
    """
    try:
        # Create new task instance
        new_task = Task(
            title=task_data.title,
            description=task_data.description,
            completed=task_data.completed,
            priority=task_data.priority,
            due_date=task_data.due_date,
            user_id=current_user.id
        )
        
        # Add to database
        db.add(new_task)
        await db.commit()
        await db.refresh(new_task)
        
        return TaskResponse.model_validate(new_task)
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the task"
        )


@router.get("/{task_id}", response_model=TaskResponse, status_code=status.HTTP_200_OK)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """
    Retrieve a specific task by ID.
    
    Users can only access their own tasks.
    """
    task = await get_task_by_id_and_user(task_id, current_user.id, db)
    return TaskResponse.model_validate(task)


@router.put("/{task_id}", response_model=TaskResponse, status_code=status.HTTP_200_OK)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """
    Update an existing task.
    
    Users can only update their own tasks. Only provided fields will be updated.
    """
    try:
        # Get existing task
        task = await get_task_by_id_and_user(task_id, current_user.id, db)
        
        # Update only provided fields
        update_data = task_data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(task, field, value)
        
        # Update timestamp
        task.updated_at = datetime.utcnow()
        
        # Commit changes
        await db.commit()
        await db.refresh(task)
        
        return TaskResponse.model_validate(task)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the task"
        )


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Delete a specific task.
    
    Users can only delete their own tasks.
    """
    try:
        # Get existing task (this validates ownership)
        task = await get_task_by_id_and_user(task_id, current_user.id, db)
        
        # Delete task
        await db.delete(task)
        await db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the task"
        )


# Bulk operations (bonus endpoints for better UX)
@router.patch("/bulk/complete", status_code=status.HTTP_200_OK)
async def bulk_complete_tasks(
    task_ids: List[int],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Mark multiple tasks as completed.
    
    Only tasks owned by the current user will be updated.
    """
    try:
        if not task_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No task IDs provided"
            )
        
        # Update tasks
        query = (
            select(Task)
            .where(
                and_(
                    Task.id.in_(task_ids),
                    Task.user_id == current_user.id
                )
            )
        )
        
        result = await db.execute(query)
        tasks = result.scalars().all()
        
        updated_count = 0
        for task in tasks:
            if not task.completed:
                task.completed = True
                task.updated_at = datetime.utcnow()
                updated_count += 1
        
        await db.commit()
        
        return {
            "message": f"Successfully updated {updated_count} tasks",
            "updated_count": updated_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating tasks"
        )


# Health check endpoint for the tasks module
@router.get("/health", include_in_schema=False)
async def tasks_health_check():
    """Health check endpoint for tasks module."""
    return {"status": "healthy", "module": "tasks"}
