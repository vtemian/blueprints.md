# api.auth

Build comprehensive authentication and authorization API endpoints for user registration, login, and account management in the e-commerce platform.

Dependencies: fastapi, jwt, bcrypt, @../models/user, @../services/auth, @../core/database

Requirements:
- Create FastAPI router with "/auth" prefix and "Authentication" tag
- POST /register endpoint for new user registration with email verification
- POST /login endpoint for user authentication with JWT token generation
- POST /logout endpoint to invalidate user sessions and tokens
- GET /me endpoint to get current authenticated user profile
- PUT /me endpoint to update user profile information
- POST /forgot-password and POST /reset-password for password recovery
- POST /verify-email endpoint for email address verification

User Registration:
- Validate email format and username requirements
- Check for existing users with same email or username
- Hash passwords securely with bcrypt before storage
- Generate email verification tokens and send verification emails
- Support account activation workflow before allowing login
- Implement proper validation for user data fields

Authentication and Sessions:
- Generate secure JWT access and refresh tokens
- Implement token-based authentication with proper expiration
- Support token refresh mechanism for long-lived sessions
- Store refresh tokens securely and allow revocation
- Implement logout functionality that invalidates all user tokens
- Add rate limiting for authentication endpoints to prevent brute force

Authorization and Permissions:
- Implement role-based access control (customer, admin, staff)
- Create middleware for protecting authenticated routes
- Support different permission levels for various operations
- Include admin-only endpoints for user management
- Implement account suspension and activation controls

Security Features:
- Rate limit login attempts per IP and per user
- Implement account lockout after multiple failed attempts
- Log all authentication events for security monitoring
- Support two-factor authentication preparation
- Include password strength validation
- Implement secure password reset with time-limited tokens

Additional Features:
- Support OAuth2 integration (Google, Facebook) preparation
- User profile management with avatar upload
- Account deletion and data export for GDPR compliance
- Email change verification workflow
- Login history tracking for security monitoring