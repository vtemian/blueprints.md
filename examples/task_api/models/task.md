# models.task

Task model for managing user tasks with status tracking.

Dependencies: sqlalchemy, @./user

Requirements:
- Task table with id, title, description, completed, user_id, created_at, updated_at
- Foreign key relationship to User model
- Title is required and not nullable
- Boolean completed field with default False
- Automatic timestamp handling for created_at and updated_at
- Database indexes on user_id and completed for query performance