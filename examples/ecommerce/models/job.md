# models.job

A comprehensive background job tracking and monitoring system with retry logic, progress tracking, priority queuing, and scheduling capabilities for asynchronous task processing.

Dependencies: @../core/database[Base]

Requirements:
- Track background jobs with UUID-based identification
- Support multiple job types for different business operations
- Implement comprehensive retry logic with configurable attempts
- Provide real-time progress tracking and monitoring
- Enable job prioritization and queue management
- Support delayed/scheduled job execution
- Link jobs to business entities (users, orders, products)
- Maintain detailed execution history and error tracking

Model Structure:
- Primary key: id (String/UUID for global uniqueness)
- Job classification: job_type enum, status enum
- Job details: title (200 chars), description (text), parameters (JSON), result (JSON)
- Execution tracking: started_at, completed_at, failed_at timestamps
- Progress monitoring: progress_percentage (0-100), progress_message (500 chars)
- Retry management: max_retries (default 3), retry_count, next_retry_at
- Error handling: error_message (text), error_traceback (text)
- Priority system: priority (integer, higher = more important), scheduled_for timestamp
- Business references: user_id (job initiator), reference_type/reference_id (linked entity)
- Worker metadata: worker_name, queue_name (default "default")
- Audit: created_at, updated_at timestamps

Job Status Enum:
- PENDING: Job created and waiting to be processed
- RUNNING: Currently being executed by a worker
- COMPLETED: Successfully finished execution
- FAILED: Failed execution (may be eligible for retry)
- RETRYING: Failed job scheduled for retry attempt
- CANCELLED: Manually cancelled before completion

Job Type Enum:
- EMAIL_NOTIFICATION: Send transactional emails
- ORDER_PROCESSING: Process order fulfillment
- INVENTORY_SYNC: Synchronize inventory data
- PAYMENT_PROCESSING: Handle payment transactions
- ANALYTICS_REPORT: Generate business reports
- IMAGE_PROCESSING: Process product images
- DATA_EXPORT: Export data for analysis

Business Logic:
- is_completed(): Check if job finished successfully
- is_failed(): Check if job failed and can't retry
- can_retry(): Validate retry eligibility based on count and max
- mark_as_started(): Update status and record worker info
- mark_as_completed(): Finalize job with optional result data
- mark_as_failed(): Record failure with error details
- update_progress(): Update progress percentage and message
- schedule_retry(): Set up next retry attempt with delay
- cancel_job(): Mark job as cancelled
- get_execution_time(): Calculate total execution duration
- create_job(): Factory method to create new job instances
- get_pending_jobs(): Retrieve jobs ready for processing
- get_user_jobs(): Get job history for specific user
- get_failed_jobs(): Find failed jobs for troubleshooting
- cleanup_old_jobs(): Remove completed jobs older than specified days

Additional Notes:
- UUID-based identification ensures global uniqueness
- Comprehensive retry logic prevents temporary failure loss
- Progress monitoring enables real-time job status updates
- Priority queuing ensures critical jobs process first
- Business entity linking provides context and traceability
- Worker metadata helps with distributed processing