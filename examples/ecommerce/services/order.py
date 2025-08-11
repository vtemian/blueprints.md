from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict
from uuid import UUID

from models.order import Order, OrderStatus
from models.order_item import OrderItem
from models.cart import Cart
from models.inventory import Inventory
from models.user import User
from jobs.tasks import send_email_async, process_order_async


class OrderService:
    def __init__(self, db: Session):
        """Initialize order service with database session."""
        self.db = db

    def create_order(self, user_id: UUID, cart_id: UUID) -> Order:
        """Create new order from cart."""
        try:
            cart = self.db.query(Cart).filter(Cart.id == cart_id).first()
            if not cart:
                raise ValueError("Cart not found")

            # Create order
            order = Order(
                user_id=user_id, status=OrderStatus.PENDING, total_amount=Decimal("0")
            )
            self.db.add(order)

            # Add items and update inventory
            total = Decimal("0")
            for cart_item in cart.items:
                inventory = (
                    self.db.query(Inventory)
                    .filter(Inventory.product_id == cart_item.product_id)
                    .first()
                )

                if not inventory or inventory.quantity < cart_item.quantity:
                    raise ValueError(
                        f"Insufficient inventory for product {cart_item.product_id}"
                    )

                order_item = OrderItem(
                    order_id=order.id,
                    product_id=cart_item.product_id,
                    quantity=cart_item.quantity,
                    unit_price=cart_item.product.price,
                )
                self.db.add(order_item)

                inventory.quantity -= cart_item.quantity
                total += cart_item.quantity * cart_item.product.price

            order.total_amount = total
            self.db.commit()

            # Trigger async processing
            process_order_async(order.id)

            return order

        except SQLAlchemyError as e:
            self.db.rollback()
            raise ValueError(f"Database error: {str(e)}")

    def get_order(self, order_id: UUID) -> Optional[Order]:
        """Retrieve order by ID."""
        return self.db.query(Order).filter(Order.id == order_id).first()

    def update_order_status(self, order_id: UUID, status: OrderStatus) -> Order:
        """Update order status and trigger notifications."""
        order = self.get_order(order_id)
        if not order:
            raise ValueError("Order not found")

        order.status = status
        order.updated_at = datetime.utcnow()

        user = self.db.query(User).filter(User.id == order.user_id).first()
        if user and user.email:
            send_email_async(
                to_email=user.email,
                subject=f"Order {order_id} Status Update",
                body=f"Your order status has been updated to {status.value}",
            )

        self.db.commit()
        return order

    def get_user_orders(self, user_id: UUID) -> List[Order]:
        """Get all orders for a user."""
        return self.db.query(Order).filter(Order.user_id == user_id).all()

    def get_order_analytics(self) -> Dict:
        """Get order analytics and metrics."""
        total_orders = self.db.query(Order).count()
        pending_orders = (
            self.db.query(Order).filter(Order.status == OrderStatus.PENDING).count()
        )
        completed_orders = (
            self.db.query(Order).filter(Order.status == OrderStatus.COMPLETED).count()
        )

        return {
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "completed_orders": completed_orders,
            "completion_rate": (
                (completed_orders / total_orders * 100) if total_orders else 0
            ),
        }
