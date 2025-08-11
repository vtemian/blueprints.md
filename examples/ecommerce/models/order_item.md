# models.order_item

Create an OrderItem model to represent individual items within orders with pricing and quantity tracking.

Dependencies: sqlalchemy, @../core/database, @./order, @./product

Requirements:
- Create OrderItem SQLAlchemy model for line items in orders
- Track quantity and pricing information at time of purchase
- Maintain product snapshot to preserve historical data even if product changes
- Establish relationships with Order and Product models
- Include automatic timestamp tracking for creation

Model Structure:
- Primary key: id (Integer)
- Foreign keys: order_id (ForeignKey to orders.id), product_id (ForeignKey to products.id)
- Quantity and pricing: quantity (Integer), unit_price (Numeric 10,2), total_price (Numeric 10,2)
- Product snapshot: product_name (String 200), product_sku (String 100), product_image_url (String 500)
- Timestamp: created_at (DateTime with default)

Relationships:
- Many-to-one with Order (order_id -> Order.items)
- Many-to-one with Product (product_id -> Product.order_items)

Instance Methods:
- calculate_total(): Calculate and return total price (quantity × unit_price)
- get_product_snapshot(): Return dictionary with captured product information

Class Methods:
- create_from_product(product: Product, quantity: int): Create OrderItem from Product instance

Business Logic:
- Preserve product information at time of purchase for historical accuracy
- Handle quantity and pricing calculations automatically
- Maintain product snapshot so order history remains accurate even if product details change
- Support order line item operations (add, update, remove items from orders)