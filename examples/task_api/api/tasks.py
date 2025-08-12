from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from database import get_db
from models import Task

router = APIRouter(prefix="/tasks", tags=["tasks"])

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    due_date: Optional[datetime] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    due_date: Optional[datetime] = None
    completed: Optional[bool] = None

class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    completed: bool
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }

class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]
    total: int
    page: int
    per_page: int

@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task: TaskCreate,
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """Create a new task."""
    db_task = Task(**task.model_dump())
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task

@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    completed: Optional[bool] = None,
    page: int = Query(1, gt=0),
    per_page: int = Query(10, gt=0, le=100),
    db: AsyncSession = Depends(get_db)
) -> TaskListResponse:
    """List tasks with pagination and filtering."""
    query = select(Task)
    if completed is not None:
        query = query.filter(Task.completed == completed)

    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    
    tasks = await db.scalars(
        query.offset((page - 1) * per_page)
        .limit(per_page)
        .order_by(Task.created_at.desc())
    )
    
    return TaskListResponse(
        tasks=list(tasks),
        total=total,
        page=page,
        per_page=per_page
    )

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """Get a specific task by ID."""
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return task

@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """Update a task."""
    db_task = await db.get(Task, task_id)
    if not db_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    update_data = task_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_task, field, value)
    
    db_task.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(db_task)
    return db_task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a task."""
    db_task = await db.get(Task, task_id)
    if not db_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    await db.delete(db_task)
    await db.commit()