# models.user

User model for authentication and task ownership.

Dependencies: sqlalchemy, bcrypt, @./task

Requirements:
- User table with id, username, email, hashed_password, is_active, created_at
- Username and email must be unique and not nullable
- Relationship to tasks (one user has many tasks)
- Password hashing and verification with bcrypt
- to_dict method for API responses (exclude password fields)
- Soft deletion using is_active field