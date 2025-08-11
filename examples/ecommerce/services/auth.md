# services.auth
Authentication and authorization service with JWT token management

deps: @..models.user[User]; @..core.database[get_db, get_redis]

# JWT Configuration
SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
REFRESH_TOKEN_EXPIRE_DAYS: int = 7

AuthService:
    - __init__(db: Session, redis_client)
    
    # Password operations
    - hash_password(password: str) -> str
    - verify_password(plain_password: str, hashed_password: str) -> bool
    
    # JWT token operations
    - create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str
    - create_refresh_token(data: dict) -> str
    - verify_token(token: str) -> Optional[dict]
    - decode_token(token: str) -> dict
    
    # User authentication
    - authenticate_user(username: str, password: str) -> Optional[User]
    - get_current_user_from_token(token: str) -> Optional[User]
    
    # Token blacklisting
    - blacklist_token(token: str) -> None
    - is_token_blacklisted(token: str) -> bool
    
    # Refresh token management
    - store_refresh_token(user_id: int, token: str) -> None
    - validate_refresh_token(token: str) -> Optional[int]
    - revoke_refresh_token(token: str) -> None
    
    # Password reset
    - generate_reset_token(user_id: int) -> str
    - verify_reset_token(token: str) -> Optional[int]
    - invalidate_reset_token(token: str) -> None
    
    # Email verification
    - generate_verification_token(user_id: int) -> str
    - verify_email_token(token: str) -> Optional[int]

# FastAPI Dependencies
get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Get current authenticated user"""
    # Decode JWT token
    # Check token blacklist
    # Retrieve user from database
    # Validate user is active
    # Return user object

get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Ensure current user is admin"""
    # Check user admin status
    # Raise exception if not admin
    # Return admin user

get_optional_user(token: Optional[str] = Depends(optional_oauth2_scheme), db: Session = Depends(get_db)) -> Optional[User]:
    """Get current user if token provided, otherwise None"""
    # Handle optional authentication
    # Return user or None

# OAuth2 scheme configuration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)

notes: Secure JWT implementation, token blacklisting, refresh token rotation, password reset flow, email verification, Redis-based session management