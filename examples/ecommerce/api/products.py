from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    ForeignKey, create_engine, text
)
from sqlalchemy.orm import (
    Session, declarative_base, relationship, sessionmaker
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from redis import Redis
from celery import Celery
from slugify import slugify

from core.config import Settings
from core.database import get_db
from core.security import get_current_user
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["products"])

redis_client = Redis(host=Settings.REDIS_HOST, port=Settings.REDIS_PORT)

celery_app = Celery('products', broker=Settings.CELERY_BROKER_URL)

Base = declarative_base()

class Product(Base):
    __tablename__ = "products"
    
    id = Column(PGUUID, primary_key=True, default=uuid4)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    description = Column(String)
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    category_id = Column(PGUUID, ForeignKey("categories.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = relationship("Category", back_populates="products")

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(PGUUID, primary_key=True, default=uuid4)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)

    products = relationship("Product", back_populates="category")

class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal
    stock: int = 0
    category_id: Optional[UUID] = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)

class ProductCreate(ProductBase):
    pass

class ProductUpdate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: UUID
    slug: str
    created_at: datetime
    updated_at: datetime

class BulkProductCreate(BaseModel):
    products: List[ProductCreate]

@router.get("", response_model=List[ProductResponse])
def list_products(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List products with optional filtering and search."""
    query = db.query(Product)

    if category:
        query = query.join(Category).filter(Category.slug == category)
    
    if search:
        search_filter = text(f"%{search}%")
        query = query.filter(Product.name.ilike(search_filter))

    return query.offset(skip).limit(limit).all()

@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new product."""
    db_product = Product(
        **product.model_dump(),
        slug=slugify(product.name)
    )
    
    try:
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        return db_product
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create product"
        )

@router.post("/bulk", status_code=status.HTTP_201_CREATED)
def create_products_bulk(
    products: BulkProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bulk create products."""
    try:
        db_products = [
            Product(**product.model_dump(), slug=slugify(product.name))
            for product in products.products
        ]
        db.add_all(db_products)
        db.commit()
        return {"message": f"Successfully created {len(db_products)} products"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error in bulk product creation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create products"
        )

@router.get("/{slug}", response_model=ProductResponse)
def get_product(slug: str, db: Session = Depends(get_db)):
    """Get product by slug."""
    product = db.query(Product).filter(Product.slug == slug).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    track_product_view(product.id)
    return product

@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: UUID,
    product_update: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update product."""
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    for key, value in product_update.model_dump(exclude_unset=True).items():
        setattr(db_product, key, value)
    
    try:
        db.commit()
        db.refresh(db_product)
        return db_product
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not update product"
        )

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete product."""
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    try:
        db.delete(db_product)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not delete product"
        )

@router.get("/{product_id}/recommendations", response_model=List[ProductResponse])
def get_product_recommendations(
    product_id: UUID,
    limit: int = 5,
    db: Session = Depends(get_db)
):
    """Get product recommendations based on category and views."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    recommendations = db.query(Product).filter(
        Product.category_id == product.category_id,
        Product.id != product_id,
        Product.is_active == True
    ).limit(limit).all()

    return recommendations

def track_product_view(product_id: UUID):
    """Track product view in Redis for analytics."""
    try:
        key = f"product_views:{product_id}"
        redis_client.incr(key)
        redis_client.expire(key, 86400)  # Expire after 24 hours
    except Exception as e:
        logger.error(f"Error tracking product view: {str(e)}")