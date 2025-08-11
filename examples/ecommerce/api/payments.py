from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models.payment import Payment, PaymentStatus
from models.order import Order
from models.user import User
from services.auth import get_current_user, get_current_admin
from services.payment import PaymentService
from core.database import get_db


class PaymentMethodRequest(BaseModel):
    method: str
    token: str
    save_for_future: bool = False

    model_config = {
        "json_schema_extra": {
            "example": {
                "method": "credit_card",
                "token": "tok_123",
                "save_for_future": True,
            }
        }
    }


payments_router = APIRouter(prefix="/payments", tags=["Payments"])


@payments_router.get("/methods")
async def get_payment_methods(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> List[dict]:
    """Get available payment methods for the current user"""
    payment_service = PaymentService(db)
    return payment_service.get_available_methods(current_user.id)


@payments_router.post("/process")
async def process_payment(
    order_id: int = Body(...),
    payment_data: PaymentMethodRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Process a payment for an order"""
    payment_service = PaymentService(db)
    return await payment_service.process_payment(
        order_id=order_id, user_id=current_user.id, payment_data=payment_data
    )


@payments_router.post("/{payment_id}/refund")
async def refund_payment(
    payment_id: int,
    amount: Optional[Decimal] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Refund a payment partially or fully"""
    payment_service = PaymentService(db)
    return await payment_service.refund_payment(
        payment_id=payment_id, user_id=current_user.id, amount=amount
    )


@payments_router.get("/transactions")
async def get_transactions(
    page: int = Query(1, gt=0),
    per_page: int = Query(50, gt=0, le=100),
    status: Optional[PaymentStatus] = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get paginated transaction history (admin only)"""
    payment_service = PaymentService(db)
    return payment_service.get_transactions(page=page, per_page=per_page, status=status)


@payments_router.post("/webhook")
async def payment_webhook(data: dict = Body(...), db: Session = Depends(get_db)):
    """Handle payment provider webhooks"""
    payment_service = PaymentService(db)
    return await payment_service.handle_webhook(data)


@payments_router.get("/analytics")
async def payment_analytics(
    current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)
):
    """Get payment analytics data (admin only)"""
    payment_service = PaymentService(db)
    return payment_service.get_analytics()


@payments_router.post("/fraud-check")
async def check_fraud(
    payment_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Run fraud detection check on payment (admin only)"""
    payment_service = PaymentService(db)
    return await payment_service.check_fraud(payment_id)
