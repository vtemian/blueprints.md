import logging
from datetime import datetime
from typing import List, Dict
from pathlib import Path
import json

from models.job import Job, JobType, JobStatus
from models.order import Order
from models.user import User
from models.inventory import Inventory
from services.payment import PaymentService
from jobs.worker import celery_app, JobWorker, EmailService
from core.database import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def send_email_async(self, job_id: str) -> None:
    """Send email notification"""
    try:
        with SessionLocal() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise ValueError(f"Job {job_id} not found")

            email_service = EmailService()
            email_service.send(job.data)

            job.status = JobStatus.COMPLETED
            db.commit()

    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        job.status = JobStatus.FAILED
        db.commit()
        self.retry(exc=e)


@celery_app.task(bind=True, max_retries=3)
def send_order_confirmation_email(self, order_id: int) -> None:
    """Send order confirmation email"""
    try:
        with SessionLocal() as db:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                raise ValueError(f"Order {order_id} not found")

            email_service = EmailService()
            email_service.send_order_confirmation(order)

    except Exception as e:
        logger.error(f"Error sending order confirmation: {str(e)}")
        self.retry(exc=e)


@celery_app.task(bind=True, max_retries=3)
def send_shipping_notification_email(self, order_id: int) -> None:
    """Send shipping notification email"""
    try:
        with SessionLocal() as db:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                raise ValueError(f"Order {order_id} not found")

            email_service = EmailService()
            email_service.send_shipping_notification(order)

    except Exception as e:
        logger.error(f"Error sending shipping notification: {str(e)}")
        self.retry(exc=e)


@celery_app.task(bind=True, max_retries=3)
def send_welcome_email(self, user_id: int) -> None:
    """Send welcome email to new users"""
    try:
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User {user_id} not found")

            email_service = EmailService()
            email_service.send_welcome(user)

    except Exception as e:
        logger.error(f"Error sending welcome email: {str(e)}")
        self.retry(exc=e)


@celery_app.task(bind=True, max_retries=2)
def process_order_async(self, order_id: int) -> None:
    """Process order after payment confirmation"""
    try:
        with SessionLocal() as db:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                raise ValueError(f"Order {order_id} not found")

            worker = JobWorker()
            worker.process_order(order)

    except Exception as e:
        logger.error(f"Error processing order: {str(e)}")
        self.retry(exc=e)


@celery_app.task(bind=True, max_retries=3)
def update_order_tracking(self, order_id: int, tracking_number: str) -> None:
    """Update order with tracking information"""
    try:
        with SessionLocal() as db:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                raise ValueError(f"Order {order_id} not found")

            order.tracking_number = tracking_number
            order.status = "SHIPPED"
            db.commit()

    except Exception as e:
        logger.error(f"Error updating tracking: {str(e)}")
        self.retry(exc=e)


@celery_app.task(bind=True, max_retries=2)
def cancel_order_async(self, order_id: int, reason: str) -> None:
    """Process order cancellation"""
    try:
        with SessionLocal() as db:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                raise ValueError(f"Order {order_id} not found")

            worker = JobWorker()
            worker.cancel_order(order, reason)

    except Exception as e:
        logger.error(f"Error cancelling order: {str(e)}")
        self.retry(exc=e)


@celery_app.task(bind=True, max_retries=3)
def sync_inventory_levels(self) -> None:
    """Synchronize inventory levels with external systems"""
    try:
        with SessionLocal() as db:
            inventory_items = db.query(Inventory).all()
            worker = JobWorker()
            worker.sync_inventory(inventory_items)

    except Exception as e:
        logger.error(f"Error syncing inventory: {str(e)}")
        self.retry(exc=e)


@celery_app.task(bind=True, max_retries=3)
def check_low_stock_alerts(self) -> None:
    """Check for low stock products and send alerts"""
    try:
        with SessionLocal() as db:
            inventory_items = (
                db.query(Inventory)
                .filter(Inventory.quantity <= Inventory.low_stock_threshold)
                .all()
            )

            email_service = EmailService()
            email_service.send_low_stock_alerts(inventory_items)

    except Exception as e:
        logger.error(f"Error checking stock alerts: {str(e)}")
        self.retry(exc=e)


@celery_app.task(bind=True, max_retries=2)
def update_product_availability(self, product_id: int) -> None:
    """Update product availability status"""
    try:
        with SessionLocal() as db:
            inventory = (
                db.query(Inventory).filter(Inventory.product_id == product_id).first()
            )
            if not inventory:
                raise ValueError(f"Product {product_id} not found")

            worker = JobWorker()
            worker.update_availability(inventory)

    except Exception as e:
        logger.error(f"Error updating availability: {str(e)}")
        self.retry(exc=e)


@celery_app.task(bind=True, max_retries=3)
def process_refund_async(self, payment_id: int, amount: float, reason: str) -> None:
    """Process payment refund"""
    try:
        payment_service = PaymentService()
        payment_service.process_refund(payment_id, amount, reason)

    except Exception as e:
        logger.error(f"Error processing refund: {str(e)}")
        self.retry(exc=e)


@celery_app.task(bind=True, max_retries=2)
def handle_payment_webhook(self, provider: str, webhook_data: Dict) -> None:
    """Handle payment provider webhook"""
    try:
        payment_service = PaymentService()
        payment_service.handle_webhook(provider, webhook_data)

    except Exception as e:
        logger.error(f"Error handling webhook: {str(e)}")
        self.retry(exc=e)


@celery_app.task(bind=True, max_retries=2)
def generate_daily_sales_report(self) -> None:
    """Generate daily sales analytics report"""
    try:
        with SessionLocal() as db:
            worker = JobWorker()
            worker.generate_sales_report()

    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        self.retry(exc=e)


@celery_app.task(bind=True, max_retries=2)
def update_product_rankings(self) -> None:
    """Update product popularity rankings"""
    try:
        with SessionLocal() as db:
            worker = JobWorker()
            worker.update_rankings()

    except Exception as e:
        logger.error(f"Error updating rankings: {str(e)}")
        self.retry(exc=e)


@celery_app.task(bind=True, max_retries=3)
def export_data_async(self, job_id: str) -> None:
    """Export data based on job parameters"""
    try:
        with SessionLocal() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise ValueError(f"Job {job_id} not found")

            worker = JobWorker()
            worker.export_data(job)

    except Exception as e:
        logger.error(f"Error exporting data: {str(e)}")
        self.retry(exc=e)


@celery_app.task(bind=True, max_retries=2)
def process_product_images(self, product_id: int, image_urls: List[str]) -> None:
    """Process and optimize product images"""
    try:
        worker = JobWorker()
        worker.process_images(product_id, image_urls)

    except Exception as e:
        logger.error(f"Error processing images: {str(e)}")
        self.retry(exc=e)


@celery_app.task(bind=True, max_retries=3)
def generate_image_variants(self, image_url: str, variants: List[Dict]) -> None:
    """Generate image size variants"""
    try:
        worker = JobWorker()
        worker.generate_variants(image_url, variants)

    except Exception as e:
        logger.error(f"Error generating variants: {str(e)}")
        self.retry(exc=e)


@celery_app.task(bind=True)
def cleanup_expired_sessions(self) -> None:
    """Clean up expired user sessions"""
    try:
        with SessionLocal() as db:
            worker = JobWorker()
            worker.cleanup_sessions()

    except Exception as e:
        logger.error(f"Error cleaning sessions: {str(e)}")


@celery_app.task(bind=True)
def backup_critical_data(self) -> None:
    """Backup critical system data"""
    try:
        backup_dir = Path("backups") / datetime.now().strftime("%Y%m%d")
        backup_dir.mkdir(parents=True, exist_ok=True)

        with SessionLocal() as db:
            for model in [User, Order, Inventory]:
                data = db.query(model).all()
                with open(backup_dir / f"{model.__name__}.json", "w") as f:
                    json.dump([item.dict() for item in data], f)

    except Exception as e:
        logger.error(f"Error backing up data: {str(e)}")


def health_check() -> bool:
    """System health check"""
    try:
        with SessionLocal() as db:
            db.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return False
