from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID, uuid4

class Order:
    def __init__(self, id: UUID, customer_id: UUID, status: str, total_amount: Decimal,
                 notes: Optional[str] = None):
        self.id = id or uuid4()
        self.customer_id = customer_id
        self.status = status
        self.total_amount = total_amount
        self.notes = notes
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

class OrderCreate:
    def __init__(self, customer_id: UUID, total_amount: Decimal, notes: Optional[str] = None):
        self.customer_id = customer_id
        self.total_amount = total_amount
        self.notes = notes

class OrderResponse:
    def __init__(self, id: UUID, customer_id: UUID, status: str, total_amount: Decimal,
                 notes: Optional[str], created_at: datetime, updated_at: datetime):
        self.id = id
        self.customer_id = customer_id
        self.status = status
        self.total_amount = total_amount
        self.notes = notes
        self.created_at = created_at
        self.updated_at = updated_at

class OrderService:
    def __init__(self):
        self.orders: List[Order] = []

    async def create_order(self, order: OrderCreate) -> Order:
        """Create a new order"""
        db_order = Order(
            id=uuid4(),
            customer_id=order.customer_id,
            status="pending", 
            total_amount=order.total_amount,
            notes=order.notes
        )
        self.orders.append(db_order)
        return db_order

    def get_order(self, order_id: UUID) -> Optional[Order]:
        """Get order by ID"""
        for order in self.orders:
            if order.id == order_id:
                return order
        return None

    def list_orders(self, skip: int = 0, limit: int = 100) -> List[Order]:
        """List orders with pagination"""
        return self.orders[skip:skip + limit]