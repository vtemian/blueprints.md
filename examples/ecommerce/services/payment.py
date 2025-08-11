import os
from decimal import Decimal
from datetime import datetime
import hmac
import hashlib
import json
from typing import Dict, Optional
import logging
from sqlalchemy.orm import Session

from models.payment import Payment, PaymentStatus, PaymentMethod
from models.order import Order
from models.user import User

# Type aliases
STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY")
PAYPAL_CLIENT_ID: str = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET: str = os.getenv("PAYPAL_CLIENT_SECRET")

logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.stripe = StripeProvider()
        self.paypal = PayPalProvider()

    def process_payment(
        self,
        amount: Decimal,
        currency: str,
        payment_method: PaymentMethod,
        user_id: int,
        order_id: int,
        **kwargs,
    ) -> Payment:
        """Process payment using specified provider"""

        if not self._validate_payment(amount, user_id):
            raise ValueError("Payment validation failed")

        try:
            if payment_method == PaymentMethod.STRIPE:
                result = self.stripe.charge_card(
                    amount=amount,
                    currency=currency,
                    card_token=kwargs.get("card_token"),
                    description=f"Order {order_id}",
                )
                transaction_id = result["id"]

            elif payment_method == PaymentMethod.PAYPAL:
                payment = self.paypal.create_payment(
                    amount=amount, currency=currency, description=f"Order {order_id}"
                )
                result = self.paypal.execute_payment(
                    payment["id"], kwargs.get("payer_id")
                )
                transaction_id = result["id"]

            else:
                raise ValueError(f"Unsupported payment method: {payment_method}")

            payment = Payment(
                user_id=user_id,
                order_id=order_id,
                amount=amount,
                currency=currency,
                payment_method=payment_method,
                transaction_id=transaction_id,
                status=PaymentStatus.COMPLETED,
                created_at=datetime.utcnow(),
            )

            self.db.add(payment)
            self.db.commit()

            return payment

        except Exception as e:
            logger.error(f"Payment failed: {str(e)}")
            self.db.rollback()
            raise

    def process_refund(
        self,
        payment_id: int,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None,
    ) -> Payment:
        """Process refund for a payment"""

        payment = self.db.query(Payment).get(payment_id)
        if not payment:
            raise ValueError("Payment not found")

        refund_amount = amount or payment.amount

        try:
            if payment.payment_method == PaymentMethod.STRIPE:
                result = self.stripe.create_refund(
                    charge_id=payment.transaction_id,
                    amount=refund_amount,
                    reason=reason,
                )

            elif payment.payment_method == PaymentMethod.PAYPAL:
                result = self.paypal.create_refund(
                    transaction_id=payment.transaction_id, amount=refund_amount
                )

            payment.status = PaymentStatus.REFUNDED
            payment.refunded_at = datetime.utcnow()
            payment.refund_amount = refund_amount

            self.db.commit()
            return payment

        except Exception as e:
            logger.error(f"Refund failed: {str(e)}")
            self.db.rollback()
            raise

    def _validate_payment(self, amount: Decimal, user_id: int) -> bool:
        """Validate payment for fraud detection"""
        user = self.db.query(User).get(user_id)
        if not user:
            return False

        recent_payments = (
            self.db.query(Payment)
            .filter(Payment.user_id == user_id)
            .order_by(Payment.created_at.desc())
            .limit(10)
            .all()
        )

        # Fraud detection rules
        if (
            len(recent_payments) >= 5
            and (datetime.utcnow() - recent_payments[4].created_at).total_seconds()
            < 300
        ):
            return False

        if any(p.amount > amount * 10 for p in recent_payments):
            return False

        return True


class StripeProvider:
    def charge_card(
        self, amount: Decimal, currency: str, card_token: str, description: str
    ) -> Dict:
        """Process card payment via Stripe"""
        try:
            # Simulated Stripe API call
            charge = {
                "id": "ch_123",
                "amount": int(amount * 100),
                "currency": currency,
                "description": description,
            }
            return charge

        except Exception as e:
            logger.error(f"Stripe charge failed: {str(e)}")
            raise

    def create_refund(self, charge_id: str, amount: Decimal, reason: str) -> Dict:
        """Create refund via Stripe"""
        try:
            # Simulated Stripe refund
            refund = {"id": "re_123", "charge": charge_id, "amount": int(amount * 100)}
            return refund

        except Exception as e:
            logger.error(f"Stripe refund failed: {str(e)}")
            raise

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify Stripe webhook signature"""
        try:
            # Simulated signature verification
            expected = hmac.new(
                STRIPE_SECRET_KEY.encode(), payload, hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(signature, expected)
        except:
            return False


class PayPalProvider:
    def create_payment(self, amount: Decimal, currency: str, description: str) -> Dict:
        """Create PayPal payment"""
        try:
            # Simulated PayPal payment creation
            payment = {
                "id": "PAY-123",
                "state": "created",
                "transactions": [
                    {"amount": {"total": str(amount), "currency": currency}}
                ],
            }
            return payment

        except Exception as e:
            logger.error(f"PayPal payment creation failed: {str(e)}")
            raise

    def execute_payment(self, payment_id: str, payer_id: str) -> Dict:
        """Execute PayPal payment"""
        try:
            # Simulated payment execution
            payment = {
                "id": payment_id,
                "state": "approved",
                "payer": {"payer_id": payer_id},
            }
            return payment

        except Exception as e:
            logger.error(f"PayPal payment execution failed: {str(e)}")
            raise

    def create_refund(self, transaction_id: str, amount: Decimal) -> Dict:
        """Create PayPal refund"""
        try:
            # Simulated refund creation
            refund = {
                "id": "REF-123",
                "state": "completed",
                "amount": {"total": str(amount), "currency": "USD"},
            }
            return refund

        except Exception as e:
            logger.error(f"PayPal refund failed: {str(e)}")
            raise
