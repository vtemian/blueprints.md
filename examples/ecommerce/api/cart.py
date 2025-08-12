from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

class CartItem:
    def __init__(self, id: UUID, user_id: UUID, product_id: UUID, quantity: float):
        self.id = id or uuid4()
        self.user_id = user_id
        self.product_id = product_id
        self.quantity = quantity
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

class CartItemCreate:
    def __init__(self, product_id: UUID, quantity: float):
        self.product_id = product_id
        self.quantity = quantity

class CartItemResponse:
    def __init__(self, id: UUID, product_id: UUID, quantity: float,
                 created_at: datetime, updated_at: datetime):
        self.id = id
        self.product_id = product_id
        self.quantity = quantity
        self.created_at = created_at
        self.updated_at = updated_at

class CartRouter:
    def __init__(self):
        self.cart_items: List[CartItem] = []

    async def add_to_cart(self, cart_item: CartItemCreate, user_id: UUID) -> CartItemResponse:
        """Add item to user's cart"""
        new_item = CartItem(
            id=uuid4(),
            user_id=user_id,
            product_id=cart_item.product_id,
            quantity=cart_item.quantity
        )
        self.cart_items.append(new_item)
        return CartItemResponse(
            id=new_item.id,
            product_id=new_item.product_id,
            quantity=new_item.quantity,
            created_at=new_item.created_at,
            updated_at=new_item.updated_at
        )

    async def get_cart(self, user_id: UUID) -> List[CartItemResponse]:
        """Get user's cart items"""
        return [
            CartItemResponse(
                id=item.id,
                product_id=item.product_id,
                quantity=item.quantity,
                created_at=item.created_at,
                updated_at=item.updated_at
            )
            for item in self.cart_items
            if item.user_id == user_id
        ]

    async def remove_from_cart(self, item_id: UUID, user_id: UUID) -> None:
        """Remove item from cart"""
        self.cart_items = [
            item for item in self.cart_items
            if not (item.id == item_id and item.user_id == user_id)
        ]

    async def update_cart_item(self, item_id: UUID, cart_item: CartItemCreate,
                             user_id: UUID) -> Optional[CartItemResponse]:
        """Update cart item quantity"""
        for item in self.cart_items:
            if item.id == item_id and item.user_id == user_id:
                item.quantity = cart_item.quantity
                item.updated_at = datetime.utcnow()
                return CartItemResponse(
                    id=item.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    created_at=item.created_at,
                    updated_at=item.updated_at
                )
        return None