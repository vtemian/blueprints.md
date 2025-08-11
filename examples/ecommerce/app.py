from contextlib import asynccontextmanager
from typing import Annotated, List, Optional
from datetime import datetime

from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from pydantic import BaseModel, Field

from models.user import User, UserCreate, UserUpdate
from models.product import Product, ProductCreate, ProductUpdate  
from models.cart import Cart, CartItem
from models.order import Order, OrderCreate
from models.payment import Payment, PaymentCreate
from database import get_db, init_db
from auth import get_current_user, create_access_token
from config import Settings

settings = Settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="E-Commerce API",
    description="API for e-commerce platform with user, product, cart and order management",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True, 
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter()

@api_router.post("/users/", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User.get_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    return User.create(db, user)

@api_router.get("/users/me", response_model=User)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_user)]
):
    return current_user

@api_router.get("/products/", response_model=List[Product])
async def list_products(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    return Product.get_multi(db, skip=skip, limit=limit)

@api_router.post("/products/", response_model=Product)
async def create_product(
    product: ProductCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return Product.create(db, product)

@api_router.get("/cart/", response_model=Cart)
async def get_cart(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    return Cart.get_by_user_id(db, user_id=current_user.id)

@api_router.post("/cart/items/", response_model=CartItem)
async def add_cart_item(
    product_id: int,
    quantity: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    cart = Cart.get_by_user_id(db, user_id=current_user.id)
    return cart.add_item(db, product_id=product_id, quantity=quantity)

@api_router.post("/orders/", response_model=Order)
async def create_order(
    order: OrderCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    return Order.create(db, order, current_user.id)

@api_router.get("/orders/{order_id}", response_model=Order)
async def get_order(
    order_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    order = Order.get(db, id=order_id)
    if not order or order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    return order

@api_router.post("/payments/", response_model=Payment)
async def create_payment(
    payment: PaymentCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    order = Order.get(db, id=payment.order_id)
    if not order or order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    return Payment.create(db, payment)

app.include_router(api_router, prefix="/api/v1")