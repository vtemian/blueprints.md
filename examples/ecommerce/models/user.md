# models.user

Create a comprehensive User model for the e-commerce platform with authentication, profile management, and order history.

Dependencies: sqlalchemy, bcrypt, @./order, @./cart, @./review

Requirements:
- User table with id, email, username, password_hash, first_name, last_name fields
- Include profile fields like phone, date_of_birth, is_active, email_verified
- Add timestamps for created_at, updated_at, last_login
- Support soft deletion with is_active flag
- Include relationships to orders, shopping cart, and product reviews
- Add methods for password hashing, verification, and profile management

Authentication Features:
- Secure password hashing with bcrypt
- Email verification status tracking
- Account activation/deactivation capabilities
- Password reset token generation and validation
- Login attempt tracking for security

Profile Management:
- Full name construction from first_name and last_name
- Phone number validation and formatting
- Profile completeness checking
- User preferences storage (notifications, marketing emails)

Additional Notes:
- Email must be unique and validated format
- Username must be unique and follow naming conventions
- Add database indexes on email, username for fast lookups
- Include audit trail for important account changes
- Support user data export for GDPR compliance
- Hash passwords before storing, never expose in API responses