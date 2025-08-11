# models.user

Create a User model for authentication and task ownership in the task management system.

Dependencies: sqlalchemy, bcrypt, @./task

Requirements:
- User table with id, username, email, hashed_password, is_active, created_at fields
- Username and email must be unique and not nullable
- Include relationship to tasks (one user has many tasks)
- Add methods for password hashing and verification using bcrypt
- Support converting user data to dictionary format for API responses (exclude password)

Additional Notes:
- Hash passwords with bcrypt before storing in database
- Add unique database indexes on username and email for fast lookups
- Use is_active field for soft deletion instead of hard deletes
- Include created_at timestamp for audit trails
- to_dict method should never expose password or hashed_password fields