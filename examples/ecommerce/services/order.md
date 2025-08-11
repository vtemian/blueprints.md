# services.order
Order processing service with inventory management and notification integration

deps: @..models.order[Order, OrderStatus]; @..models.order_item[OrderItem]; @..models.cart[Cart]; @..models.inventory[Inventory]; @..models.user[User]; @..jobs.tasks[send_email_async, process_order_async]

OrderService:
    - __init__(db: Session)
    
    # Order creation
    - create_order_from_cart(user_id: int, checkout_data: dict) -> Order
    - generate_unique_order_number() -> str
    - calculate_order_totals(cart_items: List[Cart]) -> dict
    - validate_cart_availability(cart_items: List[Cart]) -> bool
    
    # Order management
    - update_order_status(order_id: int, status: OrderStatus, notes: str = None) -> Order
    - cancel_order(order_id: int, reason: str) -> bool
    - can_cancel_order(order: Order) -> bool
    - process_order_fulfillment(order_id: int, tracking_number: str) -> bool
    
    # Inventory integration
    - reserve_inventory_for_order(order: Order) -> bool
    - commit_inventory_for_order(order: Order) -> bool
    - release_inventory_for_order(order: Order) -> bool
    
    # Address management
    - validate_shipping_address(address: dict) -> bool
    - format_address_for_display(address_data: dict) -> str
    - calculate_shipping_cost(address: dict, cart_items: List[Cart]) -> Decimal
    
    # Order notifications
    - send_order_confirmation(order: Order) -> None
    - send_shipping_notification(order: Order) -> None
    - send_delivery_notification(order: Order) -> None
    - send_cancellation_notification(order: Order, reason: str) -> None
    
    # Order queries
    - get_user_orders(user_id: int, page: int = 1, per_page: int = 10) -> dict
    - get_order_by_number(order_number: str) -> Optional[Order]
    - get_orders_by_status(status: OrderStatus, limit: int = 100) -> List[Order]
    
    # Analytics
    - get_order_statistics(days: int = 30) -> dict
    - get_popular_products(days: int = 30, limit: int = 10) -> List[dict]

notes: Complete order lifecycle management, inventory synchronization, automated notifications, comprehensive order analytics, shipping integration ready