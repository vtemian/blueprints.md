# api.jobs
Background job monitoring and management endpoints

deps: @..models.job[Job, JobStatus, JobType]; @..models.user[User]; @..services.auth[get_current_user, get_current_admin]; @..jobs.tasks[create_job]; @..core.database[get_db]

jobs_router = APIRouter(prefix="/jobs", tags=["Background Jobs"])

# Pydantic schemas
class JobCreate(BaseModel):
    job_type: JobType
    title: str
    description: Optional[str] = None
    parameters: Optional[dict] = {}
    priority: int = 0
    scheduled_for: Optional[datetime] = None

class JobResponse(BaseModel):
    id: str
    job_type: str
    title: str
    status: str
    progress_percentage: int
    progress_message: Optional[str]
    result: Optional[dict]
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

@jobs_router.get("/") -> dict:
async get_user_jobs(
    page: int = 1,
    per_page: int = 20,
    status: Optional[JobStatus] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's background jobs"""
    # Query user jobs with filters
    # Apply pagination
    # Return job list with status

@jobs_router.get("/{job_id}") -> JobResponse:
async get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific job details"""
    # Validate job ownership or admin access
    # Return detailed job information
    # Include progress and results

@jobs_router.post("/") -> JobResponse:
async create_job(
    job_data: JobCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new background job"""
    # Validate job parameters
    # Create job record
    # Queue job for processing
    # Return created job info

@jobs_router.post("/{job_id}/cancel") -> dict:
async cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel pending or running job"""
    # Validate job ownership
    # Check if job can be cancelled
    # Update job status
    # Return cancellation status

@jobs_router.post("/{job_id}/retry") -> dict:
async retry_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retry failed job"""
    # Validate job ownership
    # Check retry eligibility
    # Reset job status and requeue
    # Return retry status

# Admin endpoints
@jobs_router.get("/admin/all") -> dict:
async get_all_jobs(
    page: int = 1,
    per_page: int = 50,
    status: Optional[JobStatus] = None,
    job_type: Optional[JobType] = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all system jobs (admin only)"""
    # Query all jobs with filters
    # Include user information
    # Apply pagination
    # Return comprehensive job list

@jobs_router.get("/admin/statistics") -> dict:
async get_job_statistics(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get job system statistics (admin only)"""
    # Calculate job metrics
    # Success/failure rates
    # Average processing time
    # Queue status
    # Return dashboard data

@jobs_router.post("/admin/{job_id}/force-complete") -> dict:
async force_complete_job(
    job_id: str,
    result: Optional[dict] = Body(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Force mark job as completed (admin only)"""
    # Validate job exists
    # Update job status
    # Set completion result
    # Return status update

@jobs_router.delete("/admin/cleanup") -> dict:
async cleanup_old_jobs(
    days_old: int = 30,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Clean up old completed jobs (admin only)"""
    # Remove completed jobs older than threshold
    # Preserve failed jobs for analysis
    # Return cleanup summary

@jobs_router.get("/admin/queue-status") -> dict:
async get_queue_status(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get job queue status (admin only)"""
    # Check queue health
    # Count pending jobs by type
    # Worker status
    # Return queue monitoring data

notes: Comprehensive job monitoring, user job management, admin oversight, queue health monitoring, job retry logic, system cleanup utilities