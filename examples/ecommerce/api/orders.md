# api.orders

A comprehensive order management API providing customer-facing checkout and order tracking functionality, plus administrative order management tools for the complete order lifecycle.

Dependencies: @../models/order[Order, OrderStatus], @../models/order_item[OrderItem], @../models/user[User], @../models/cart[Cart], @../services/auth[get_current_user], @../services/order[OrderService], @../services/payment[PaymentService], @../jobs/tasks[process_order_async], @../core/database[get_db]

Requirements:
- Implement secure checkout process converting cart to order
- Provide order history and detailed order views for customers
- Enable order tracking and cancellation functionality
- Support administrative order management and fulfillment
- Integrate with payment processing and inventory systems
- Trigger background jobs for order processing workflows
- Send transactional notifications at key order states

API Router: FastAPI router with "/orders" prefix and "Orders" tag

Pydantic Schemas:
- CheckoutRequest: shipping_address, billing_address, payment_method, payment_details, order_notes
- OrderResponse: Complete order details including id, order_number, status, amounts, items, addresses, tracking
- OrderUpdate: Optional fields for admin updates (status, tracking_number, internal_notes)

Customer Endpoints:
- POST /checkout: Process cart checkout with payment and address validation
  - Validate non-empty cart and product availability
  - Create order from cart items with pricing verification
  - Process payment through payment service
  - Clear cart after successful order creation
  - Trigger background order processing job
  - Send order confirmation email
  - Return order confirmation with order number

- GET /: Get paginated user order history
  - Query orders belonging to authenticated user
  - Include order items and current status
  - Support pagination with page/per_page parameters
  - Return user-friendly order summaries

- GET /{order_id}: Get detailed order information
  - Validate order ownership by current user
  - Include complete order details and all items
  - Return comprehensive order data for order view

- GET /number/{order_number}: Find order by order number
  - Locate order using unique order number
  - Validate user ownership of the order
  - Return same detailed order information

- PUT /{order_id}/cancel: Cancel order with reason
  - Validate order can be cancelled (not shipped/delivered)
  - Update order status to cancelled
  - Process refund if payment already captured
  - Restore inventory for cancelled items
  - Send order cancellation notification
  - Return confirmation of cancellation

- GET /{order_id}/track: Get order tracking information
  - Validate user owns the order
  - Retrieve tracking details from shipping carrier
  - Return current tracking status and history

Administrative Endpoints:
- GET /admin/all: View all orders with filters (admin only)
  - Query all system orders with optional status filter
  - Support pagination for large order volumes
  - Include user and order summary information
  - Return admin dashboard order view

- PUT /admin/{order_id}: Update order details (admin only)
  - Allow admin to update order status and tracking
  - Add internal notes for order management
  - Trigger appropriate status change notifications
  - Return updated order information

- POST /admin/{order_id}/fulfill: Mark order shipped (admin only)
  - Update order status to shipped/fulfilled
  - Add tracking number for customer reference
  - Send shipping notification to customer
  - Return fulfillment confirmation

Additional Notes:
- Complete order lifecycle from checkout to delivery
- Secure checkout process with payment validation
- Real-time order tracking integration with carriers
- Administrative tools for order fulfillment workflow
- Background job integration for complex order processing
- Comprehensive notification system for order status changes