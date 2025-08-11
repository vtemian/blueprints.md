# jobs.tasks
Specific background job task implementations with Celery decorators

deps: @..models.job[Job, JobType, JobStatus]; @..models.order[Order]; @..models.user[User]; @..models.inventory[Inventory]; @..services.payment[PaymentService]; @.worker[celery_app, JobWorker, EmailService]; @..core.database[SessionLocal]

# Email notification tasks
@celery_app.task(bind=True, max_retries=3)
send_email_async(self, job_id: str):
    """Send email notification"""
    # Get job details
    # Extract email parameters
    # Send email using EmailService
    # Update job status
    # Handle failures with retry

@celery_app.task(bind=True, max_retries=3)
send_order_confirmation_email(self, order_id: int):
    """Send order confirmation email"""
    # Fetch order details
    # Generate email template
    # Send confirmation email
    # Log email delivery

@celery_app.task(bind=True, max_retries=3)
send_shipping_notification_email(self, order_id: int):
    """Send shipping notification email"""
    # Fetch order with tracking info
    # Generate shipping email
    # Include tracking link
    # Send notification

@celery_app.task(bind=True, max_retries=3)
send_welcome_email(self, user_id: int):
    """Send welcome email to new users"""
    # Fetch user details
    # Generate welcome email template
    # Include verification link
    # Send welcome email

# Order processing tasks
@celery_app.task(bind=True, max_retries=2)
process_order_async(self, order_id: int):
    """Process order after payment confirmation"""
    # Validate order payment
    # Update inventory committed quantities
    # Generate fulfillment instructions
    # Send to warehouse system
    # Update order status

@celery_app.task(bind=True, max_retries=3)
update_order_tracking(self, order_id: int, tracking_number: str):
    """Update order with tracking information"""
    # Update order tracking number
    # Fetch tracking status from carrier
    # Send tracking notification
    # Schedule delivery check

@celery_app.task(bind=True, max_retries=2)
cancel_order_async(self, order_id: int, reason: str):
    """Process order cancellation"""
    # Update order status
    # Process refund if payment made
    # Release reserved inventory
    # Send cancellation notification

# Inventory management tasks
@celery_app.task(bind=True, max_retries=3)
sync_inventory_levels(self):
    """Synchronize inventory levels with external systems"""
    # Connect to warehouse management system
    # Update inventory quantities
    # Check for discrepancies
    # Generate inventory report

@celery_app.task(bind=True, max_retries=3)
check_low_stock_alerts(self):
    """Check for low stock products and send alerts"""
    # Query products below threshold
    # Generate low stock report
    # Send alerts to administrators
    # Update notification flags

@celery_app.task(bind=True, max_retries=2)
update_product_availability(self, product_id: int):
    """Update product availability status"""
    # Check inventory levels
    # Update product active status
    # Notify customers on waitlist
    # Update search indexes

# Payment processing tasks
@celery_app.task(bind=True, max_retries=3)
process_refund_async(self, payment_id: int, amount: float, reason: str):
    """Process payment refund"""
    # Validate refund eligibility
    # Process refund with payment provider
    # Update payment and order status
    # Send refund confirmation

@celery_app.task(bind=True, max_retries=2)
handle_payment_webhook(self, provider: str, webhook_data: dict):
    """Handle payment provider webhook"""
    # Verify webhook signature
    # Process payment status update
    # Update order and payment records
    # Trigger dependent actions

# Analytics and reporting tasks
@celery_app.task(bind=True, max_retries=2)
generate_daily_sales_report(self):
    """Generate daily sales analytics report"""
    # Calculate daily metrics
    # Generate report data
    # Send to administrators
    # Store for historical analysis

@celery_app.task(bind=True, max_retries=2)
update_product_rankings(self):
    """Update product popularity rankings"""
    # Calculate view and purchase metrics
    # Update product rankings
    # Refresh recommendation engine
    # Update featured products

@celery_app.task(bind=True, max_retries=3)
export_data_async(self, job_id: str):
    """Export data based on job parameters"""
    # Parse export parameters
    # Generate data export
    # Upload to cloud storage
    # Send download link

# Image processing tasks
@celery_app.task(bind=True, max_retries=2)
process_product_images(self, product_id: int, image_urls: List[str]):
    """Process and optimize product images"""
    # Download original images
    # Generate thumbnails and variants
    # Optimize for web delivery
    # Update product image URLs

@celery_app.task(bind=True, max_retries=3)
generate_image_variants(self, image_url: str, variants: List[dict]):
    """Generate image size variants"""
    # Download original image
    # Create specified variants
    # Upload to CDN
    # Return variant URLs

# System maintenance tasks
@celery_app.task(bind=True)
cleanup_expired_sessions(self):
    """Clean up expired user sessions"""
    # Remove expired JWT tokens from blacklist
    # Clean expired cart items
    # Update user last seen

@celery_app.task(bind=True)
backup_critical_data(self):
    """Backup critical system data"""
    # Export user data
    # Export order history
    # Upload to backup storage
    # Verify backup integrity

# Scheduled periodic tasks
@celery_app.task
health_check():
    """System health check"""
    # Check database connectivity
    # Verify Redis connection
    # Test external service APIs
    # Report system status

notes: Comprehensive task coverage, proper error handling with retries, integration with all system components, automated scheduling, monitoring capabilities