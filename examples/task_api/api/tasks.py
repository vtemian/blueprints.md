from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import Boolean, Column, DateTime, String, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Database configuration
DATABASE_URL = "sqlite+aiosqlite:///./tasks.db"

# SQLAlchemy models
class Base(DeclarativeBase):
    pass

class TaskModel(Base):
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    title = Column(String, nullable=False)
    description = Column(String)
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Pydantic models
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    completed: bool = False

class TaskCreate(TaskBase):
    pass

class TaskUpdate(TaskBase):
    title: Optional[str] = None
    completed: Optional[bool] = None

class Task(TaskBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }

class TaskList(BaseModel):
    tasks: List[Task]
    total: int
    page: int
    per_page: int

# Database setup
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

# Router
router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("/", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_task(task: TaskCreate, db: AsyncSession = Depends(get_db)) -> Task:
    """Create a new task."""
    db_task = TaskModel(**task.model_dump())
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task

@router.get("/", response_model=TaskList)
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, gt=0),
    per_page: int = Query(10, gt=0, le=100),
    completed: Optional[bool] = None
) -> TaskList:
    """List tasks with pagination and optional completion filter."""
    query = select(TaskModel)
    
    if completed is not None:
        query = query.filter(TaskModel.completed == completed)
    
    # Get total count
    result = await db.execute(select(TaskModel))
    total = len(result.scalars().all())
    
    # Apply pagination
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    return TaskList(
        tasks=tasks,
        total=total,
        page=page,
        per_page=per_page
    )

@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: UUID, db: AsyncSession = Depends(get_db)) -> Task:
    """Get a specific task by ID."""
    result = await db.execute(select(TaskModel).filter(TaskModel.id == str(task_id)))
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    return task

@router.patch("/{task_id}", response_model=Task)
async def update_task(
    task_id: UUID,
    task_update: TaskUpdate,
    db: AsyncSession = Depends(get_db)
) -> Task:
    """Update a task."""
    result = await db.execute(select(TaskModel).filter(TaskModel.id == str(task_id)))
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    update_data = task_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    
    await db.commit()
    await db.refresh(task)
    return task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    """Delete a task."""
    result = await db.execute(select(TaskModel).filter(TaskModel.id == str(task_id)))
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    await db.delete(task)
    await db.commit()