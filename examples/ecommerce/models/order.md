# models.order

Create a comprehensive Order model for e-commerce with order lifecycle management, payment tracking, and shipping integration.

Dependencies: sqlalchemy, @./user, @./order_item, @./payment

Requirements:
- Order table with id, order_number, user_id, status, total_amount fields
- Include order status management (pending, processing, shipped, delivered, cancelled)
- Add comprehensive address information for billing and shipping
- Support order items relationship (one order has many order items)
- Include payment tracking and transaction references
- Add timestamps for order lifecycle events
- Include order total calculations with tax and shipping

Order Management:
- Unique order number generation for customer reference
- Order status workflow with proper state transitions
- Support for order modifications (add/remove items) before processing
- Order cancellation with inventory restoration
- Partial shipping support for multi-item orders
- Return and refund management integration

Address and Shipping:
- Separate billing and shipping address storage
- Shipping method selection and cost calculation
- Tracking number integration for shipment monitoring
- Estimated delivery date calculation
- Support for multiple shipping providers
- Address validation and standardization

Financial Tracking:
- Detailed cost breakdown (subtotal, tax, shipping, discounts)
- Multiple currency support with conversion rates
- Tax calculation based on shipping address
- Discount and coupon code application
- Payment method tracking and authorization status
- Invoice generation and management

Business Logic:
- Automatic inventory reservation on order creation
- Order expiration for unpaid orders
- Customer notification system integration
- Order analytics and reporting support
- Fraud detection and risk scoring
- Customer order history and repeat purchase tracking