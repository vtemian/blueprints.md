from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Body, status
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from models.job import Job, JobStatus, JobType
from models.user import User
from services.auth import get_current_user, get_current_admin
from jobs.tasks import create_job
from core.database import get_db

jobs_router = APIRouter(prefix="/jobs", tags=["Background Jobs"])


@jobs_router.post("/", status_code=status.HTTP_201_CREATED)
def create_background_job(
    description: Optional[str] = None,
    parameters: Optional[dict] = {},
    priority: int = 0,
    scheduled_for: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Job:
    """Create a new background job."""
    job = create_job(
        db=db,
        user_id=current_user.id,
        description=description,
        parameters=parameters,
        priority=priority,
        scheduled_for=scheduled_for,
    )
    return job


@jobs_router.get("/my", response_model=List[Job])
def get_my_jobs(
    page: int = 1,
    per_page: int = 20,
    status: Optional[JobStatus] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Job]:
    """Get jobs created by current user."""
    query = db.query(Job).filter(Job.user_id == current_user.id)

    if status:
        query = query.filter(Job.status == status)

    return (
        query.order_by(desc(Job.created_at))
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )


@jobs_router.get("/{job_id}", response_model=Job)
def get_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Job:
    """Get job details by ID."""
    job = (
        db.query(Job)
        .filter(and_(Job.id == job_id, Job.user_id == current_user.id))
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )
    return job


@jobs_router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Cancel a pending job."""
    job = (
        db.query(Job)
        .filter(
            and_(
                Job.id == job_id,
                Job.user_id == current_user.id,
                Job.status == JobStatus.PENDING,
            )
        )
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or cannot be cancelled",
        )

    job.status = JobStatus.CANCELLED
    db.commit()


@jobs_router.get("/admin/all", response_model=List[Job])
def get_all_jobs(
    page: int = 1,
    per_page: int = 50,
    status: Optional[JobStatus] = None,
    job_type: Optional[JobType] = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> List[Job]:
    """Get all jobs (admin only)."""
    query = db.query(Job)

    if status:
        query = query.filter(Job.status == status)
    if job_type:
        query = query.filter(Job.type == job_type)

    return (
        query.order_by(desc(Job.created_at))
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )


@jobs_router.post("/admin/{job_id}/retry", response_model=Job)
def retry_job(
    job_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> Job:
    """Retry a failed job (admin only)."""
    job = (
        db.query(Job)
        .filter(and_(Job.id == job_id, Job.status == JobStatus.FAILED))
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Failed job not found"
        )

    job.status = JobStatus.PENDING
    job.retries += 1
    db.commit()
    return job


@jobs_router.post("/admin/{job_id}/complete", response_model=Job)
def complete_job(
    job_id: int,
    result: Optional[dict] = Body(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> Job:
    """Mark a job as complete with results (admin only)."""
    job = db.query(Job).get(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )

    job.status = JobStatus.COMPLETED
    job.result = result
    job.completed_at = datetime.utcnow()
    db.commit()
    return job


@jobs_router.delete("/admin/cleanup", status_code=status.HTTP_204_NO_CONTENT)
def cleanup_old_jobs(
    days_old: int = 30,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> None:
    """Delete old completed/failed jobs (admin only)."""
    cutoff_date = datetime.utcnow() - timedelta(days=days_old)

    db.query(Job).filter(
        and_(
            Job.created_at < cutoff_date,
            Job.status.in_([JobStatus.COMPLETED, JobStatus.FAILED]),
        )
    ).delete(synchronize_session=False)

    db.commit()


@jobs_router.get("/admin/queue-health")
def get_queue_health(
    current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)
) -> dict:
    """Get queue health metrics (admin only)."""
    total = db.query(Job).count()
    pending = db.query(Job).filter(Job.status == JobStatus.PENDING).count()
    running = db.query(Job).filter(Job.status == JobStatus.RUNNING).count()
    failed = db.query(Job).filter(Job.status == JobStatus.FAILED).count()
    completed = db.query(Job).filter(Job.status == JobStatus.COMPLETED).count()

    return {
        "total_jobs": total,
        "pending_jobs": pending,
        "running_jobs": running,
        "failed_jobs": failed,
        "completed_jobs": completed,
        "success_rate": (completed / total * 100) if total > 0 else 0,
    }
