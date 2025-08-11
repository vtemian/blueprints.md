from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models.order import Order, OrderStatus
from models.order_item import OrderItem
from models.user import User
from models.cart import Cart
from services.auth import get_current_user
from services.order import OrderService
from services.payment import PaymentService
from jobs.tasks import process_order_async
from core.database import get_db

orders_router = APIRouter(prefix="/orders", tags=["Orders"])


class OrderCreate(BaseModel):
    shipping_address: str
    payment_method_id: str
    order_notes: Optional[str] = None


class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    tracking_number: Optional[str] = None
    internal_notes: Optional[str] = None


@orders_router.post("/checkout", status_code=status.HTTP_201_CREATED)
async def checkout(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Process order checkout"""
    cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    payment = PaymentService().process_payment(order_data.payment_method_id)
    if not payment.success:
        raise HTTPException(status_code=400, detail=payment.error)

    order = OrderService.create_order(
        db=db,
        user=current_user,
        cart=cart,
        shipping_address=order_data.shipping_address,
        order_notes=order_data.order_notes,
    )

    process_order_async.delay(order.id)
    return {"order_id": order.id}


@orders_router.get("/history")
def get_order_history(
    page: int = 1,
    per_page: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Order]:
    """Get user's order history"""
    return OrderService.get_user_orders(
        db=db, user_id=current_user.id, page=page, per_page=per_page
    )


@orders_router.get("/{order_id}")
def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Order:
    """Get order details"""
    order = OrderService.get_order(db, order_id)
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return order


@orders_router.post("/{order_id}/cancel")
def cancel_order(
    order_id: int,
    reason: str = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Order:
    """Cancel an order"""
    order = OrderService.get_order(db, order_id)
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return OrderService.cancel_order(db, order, reason)


@orders_router.get("/tracking/{tracking_number}")
def track_order(
    tracking_number: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Track order status"""
    return OrderService.get_tracking_info(tracking_number)


@orders_router.get("/admin/orders")
def list_all_orders(
    page: int = 1,
    per_page: int = 50,
    status: Optional[OrderStatus] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Order]:
    """Admin endpoint to list all orders"""
    return OrderService.list_orders(db, page, per_page, status)


@orders_router.put("/admin/orders/{order_id}")
def update_order(
    order_id: int,
    order_update: OrderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Order:
    """Admin endpoint to update order"""
    return OrderService.update_order(
        db, order_id, order_update.dict(exclude_unset=True)
    )


@orders_router.post("/admin/orders/{order_id}/tracking")
def add_tracking(
    order_id: int,
    tracking_number: str = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Order:
    """Admin endpoint to add tracking number"""
    return OrderService.add_tracking(db, order_id, tracking_number)
