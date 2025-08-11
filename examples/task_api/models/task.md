# models.task

Create a Task model for the task management system with user ownership and status tracking.

Dependencies: sqlalchemy, @./user

Requirements:
- Task table with id, title, description, completed, created_at, updated_at, user_id fields
- Title is required (not nullable), description is optional
- Include foreign key relationship to user (many tasks belong to one user)
- Add methods for marking tasks as completed/incomplete
- Support updating task title and description
- Include method to convert task data to dictionary for API responses

Additional Notes:
- Add database index on user_id for efficient user task queries
- Add index on completed status for filtering completed vs incomplete tasks
- Include created_at and updated_at timestamps with automatic updates
- Validate title length (e.g., max 200 characters)
- Ensure user_id foreign key references users.id with proper constraints