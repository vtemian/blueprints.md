from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from models.cart import Cart
from models.product import Product
from models.user import User
from services.auth import get_current_user
from core.database import get_db

cart_router = APIRouter(prefix="/cart", tags=["Shopping Cart"])


class CartItemBase(BaseModel):
    product_id: int
    quantity: int = Field(default=1, gt=0)

    model_config = {"json_schema_extra": {"example": {"product_id": 1, "quantity": 1}}}


class CartItemResponse(CartItemBase):
    id: int
    total_price: float

    model_config = {"from_attributes": True}


@cart_router.get("/", response_model=List[CartItemResponse])
def get_cart(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> List[CartItemResponse]:
    """Get current user's cart items"""
    return db.query(Cart).filter(Cart.user_id == current_user.id).all()


@cart_router.post(
    "/items", response_model=CartItemResponse, status_code=status.HTTP_201_CREATED
)
def add_to_cart(
    item: CartItemBase,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CartItemResponse:
    """Add item to cart with inventory validation"""
    product = db.query(Product).get(item.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.stock < item.quantity:
        raise HTTPException(status_code=400, detail="Insufficient inventory")

    cart_item = Cart(
        user_id=current_user.id,
        product_id=item.product_id,
        quantity=item.quantity,
        total_price=product.price * item.quantity,
    )

    try:
        db.add(cart_item)
        db.commit()
        db.refresh(cart_item)
        return cart_item
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error adding item to cart")


@cart_router.put("/items/{item_id}", response_model=CartItemResponse)
def update_cart_item(
    item_id: int,
    item: CartItemBase,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CartItemResponse:
    """Update cart item quantity with validation"""
    cart_item = (
        db.query(Cart)
        .filter(Cart.id == item_id, Cart.user_id == current_user.id)
        .first()
    )

    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    product = db.query(Product).get(cart_item.product_id)
    if product.stock < item.quantity:
        raise HTTPException(status_code=400, detail="Insufficient inventory")

    try:
        cart_item.quantity = item.quantity
        cart_item.total_price = product.price * item.quantity
        db.commit()
        db.refresh(cart_item)
        return cart_item
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error updating cart item")


@cart_router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_cart(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Remove item from cart"""
    cart_item = (
        db.query(Cart)
        .filter(Cart.id == item_id, Cart.user_id == current_user.id)
        .first()
    )

    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    try:
        db.delete(cart_item)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error removing cart item")


@cart_router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def clear_cart(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> None:
    """Clear all items from cart"""
    try:
        db.query(Cart).filter(Cart.user_id == current_user.id).delete()
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error clearing cart")
