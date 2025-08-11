import os
import logging
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
from celery import Celery
from celery.result import AsyncResult
from celery.schedules import crontab
from celery.signals import task_failure, worker_ready
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session

from models.job import Job, JobStatus, JobType
from models.user import User
from models.order import Order
from models.inventory import Inventory
from core.database import SessionLocal, get_redis

# Celery configuration
CELERY_BROKER_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
CELERY_RESULT_BACKEND: str = os.getenv("REDIS_URL", "redis://localhost:6379")

celery_app = Celery(
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["jobs.tasks"],
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
)

logger = logging.getLogger(__name__)


class JobWorker:
    def __init__(self, db: Session):
        """Initialize job worker with database session"""
        self.db = db
        self.redis = get_redis()


class EmailService:
    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str):
        """Initialize email service with SMTP credentials"""
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.jinja_env = Environment(loader=FileSystemLoader("templates"))

    def send_email(
        self, to: str, subject: str, body: str, html_body: str = None
    ) -> bool:
        """Send single email"""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.username
            msg["To"] = to

            msg.attach(MIMEText(body, "plain"))
            if html_body:
                msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False

    def send_template_email(self, to: str, template: str, context: dict) -> bool:
        """Send email using template"""
        try:
            template = self.jinja_env.get_template(template)
            html = template.render(**context)
            return self.send_email(to, context.get("subject", ""), "", html)
        except Exception as e:
            logger.error(f"Failed to send template email: {str(e)}")
            return False

    def send_bulk_email(self, recipients: List[str], subject: str, body: str) -> dict:
        """Send bulk emails with status tracking"""
        results = {"success": [], "failed": []}
        for recipient in recipients:
            success = self.send_email(recipient, subject, body)
            if success:
                results["success"].append(recipient)
            else:
                results["failed"].append(recipient)
        return results


def start_worker() -> None:
    """Start the Celery worker process"""
    celery_app.worker_main(["worker", "--loglevel=info"])


def schedule_periodic_tasks() -> None:
    """Schedule recurring background tasks"""
    celery_app.conf.beat_schedule = {
        "cleanup-old-jobs": {
            "task": "jobs.tasks.cleanup_old_jobs",
            "schedule": crontab(hour=0, minute=0),
        },
        "monitor-queues": {
            "task": "jobs.tasks.monitor_queues",
            "schedule": 300.0,  # Every 5 minutes
        },
    }


def monitor_job_queues() -> Dict:
    """Monitor job queue health"""
    stats = {"active_jobs": 0, "failed_jobs": 0, "pending_jobs": 0, "queue_length": 0}

    try:
        i = celery_app.control.inspect()
        active = i.active()
        reserved = i.reserved()
        stats["active_jobs"] = sum(len(tasks) for tasks in active.values())
        stats["pending_jobs"] = sum(len(tasks) for tasks in reserved.values())
        return stats
    except Exception as e:
        logger.error(f"Failed to monitor queues: {str(e)}")
        return stats


def create_job_async(
    job_type: JobType,
    title: str,
    parameters: dict = None,
    user_id: int = None,
    priority: int = 0,
    scheduled_for: datetime = None,
) -> str:
    """Create and queue an async job"""
    job = Job(
        type=job_type,
        title=title,
        parameters=parameters or {},
        user_id=user_id,
        priority=priority,
        scheduled_for=scheduled_for,
        status=JobStatus.PENDING,
    )

    task = celery_app.send_task(
        f"jobs.tasks.{job_type.value}",
        args=[job.id],
        countdown=scheduled_for - datetime.utcnow() if scheduled_for else None,
        priority=priority,
    )
    return task.id


def get_job_result(job_id: str) -> dict:
    """Get job result from Celery"""
    result = AsyncResult(job_id, app=celery_app)
    return {
        "status": result.status,
        "result": result.result if result.ready() else None,
        "traceback": result.traceback if result.failed() else None,
    }


def cancel_job_async(job_id: str) -> bool:
    """Cancel a queued or running job"""
    try:
        celery_app.control.revoke(job_id, terminate=True)
        return True
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {str(e)}")
        return False


@task_failure.connect
def handle_task_failure(task_id, exception, *args, **kwargs):
    """Handle task failures"""
    logger.error(f"Task {task_id} failed: {str(exception)}")


@worker_ready.connect
def worker_ready_handler(**kwargs):
    """Handle worker startup"""
    logger.info("Celery worker is ready")
