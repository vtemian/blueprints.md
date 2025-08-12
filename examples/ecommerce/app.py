import logging
import os
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
import stripe

from config import config
from db.base import Base, SessionLocal
from celery_app import celery_app
import routers.auth as auth
import routers.users as users 
import routers.products as products
import routers.cart as cart
import routers.orders as orders
import security

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="E-Commerce API",
    description="E-commerce platform API with user management, products, cart and orders", 
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for app startup and shutdown events"""
    # Startup
    logger.info("Starting up application...")
    
    # Initialize database
    engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
    SessionLocal.configure(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # Initialize Stripe
    stripe.api_key = config.STRIPE_SECRET_KEY
    
    # Start Celery worker
    celery_app.conf.update(broker_url=config.CELERY_BROKER_URL)
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")

# Include routers
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
app.include_router(cart.router, prefix="/api/v1/cart", tags=["cart"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])

# Dependency to get DB session
async def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency to get current user
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)]
):
    """Get current authenticated user"""
    user = security.get_current_user(db, token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "E-Commerce API"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}