from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

class Base:
    """Base class for SQLAlchemy models."""
    pass

class User(Base):
    """User model for authentication and task ownership."""
    __tablename__ = "users"

    id: UUID = uuid4()
    username: str
    email: str  
    password_hash: str
    full_name: Optional[str] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

    def __init__(self, username: str, email: str, password: str, full_name: Optional[str] = None):
        """Initialize a new user."""
        self.id = uuid4()
        self.username = username
        self.email = email
        self.password_hash = self._hash_password(password)
        self.full_name = full_name
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def _hash_password(self, password: str) -> str:
        """Hash a password string."""
        # Simple hash implementation since bcrypt not available
        return str(hash(password))

    def verify_password(self, password: str) -> bool:
        """Verify provided password against stored hash."""
        hashed = self._hash_password(password)
        return self.password_hash == hashed