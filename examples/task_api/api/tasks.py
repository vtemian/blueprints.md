from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from core.database import get_db
from models.task import Task
from models.user import User

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/", response_model=List[dict])
async def get_tasks(
    db: Session = Depends(get_db),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, le=100)
) -> List[dict]:
    """Get paginated list of tasks."""
    try:
        tasks = db.query(Task).offset(skip).limit(limit).all()
        return [task.to_dict() for task in tasks]
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_task(
    title: str,
    description: Optional[str] = None,
    user_id: int = 1,
    db: Session = Depends(get_db)
) -> dict:
    """Create a new task."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    task = Task(title=title, description=description, user_id=user_id)
    try:
        db.add(task)
        db.commit()
        db.refresh(task)
        return task.to_dict()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task"
        )

@router.get("/{task_id}", response_model=dict)
async def get_task(task_id: int, db: Session = Depends(get_db)) -> dict:
    """Get a specific task by ID."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return task.to_dict()

@router.put("/{task_id}", response_model=dict)
async def update_task(
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    db: Session = Depends(get_db)
) -> dict:
    """Update a task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    if title:
        task.title = title
    if description is not None:
        task.description = description

    try:
        db.commit()
        db.refresh(task)
        return task.to_dict()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task"
        )

@router.patch("/{task_id}/complete", response_model=dict)
async def complete_task(task_id: int, db: Session = Depends(get_db)) -> dict:
    """Mark a task as completed."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    task.completed = True
    try:
        db.commit()
        db.refresh(task)
        return task.to_dict()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete task"
        )

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, db: Session = Depends(get_db)) -> None:
    """Delete a task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    try:
        db.delete(task)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete task"
        )