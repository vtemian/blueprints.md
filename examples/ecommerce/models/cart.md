# models.cart

A shopping cart model for temporary item storage before checkout, allowing users to add products with specific quantities and managing cart state across sessions.

Dependencies: @../core/database[Base], @./user[User], @./product[Product]

Requirements:
- Store cart items with user and product relationships
- Track quantity, timestamps for added/updated times
- Prevent duplicate products per user (unique constraint on user_id + product_id)
- Support cart management operations like add, update, clear
- Calculate subtotals and total cart value
- Verify product availability before operations

Model Structure:
- Primary key: id (Integer)
- Foreign keys: user_id (references users.id), product_id (references products.id)
- Cart details: quantity (default 1), added_at, updated_at timestamps
- Relationships: user (back to User model), product (back to Product model)
- Constraint: unique combination of user_id and product_id

Business Logic:
- get_subtotal(): Calculate subtotal for this cart item (quantity * product price)
- update_quantity(): Update item quantity with validation
- is_product_available(): Check if the product is still available in inventory
- get_user_cart(): Retrieve all cart items for a specific user
- get_cart_total(): Calculate total value of all items in user's cart
- clear_user_cart(): Remove all items from user's cart
- add_to_cart(): Add product to cart or update quantity if already exists

Additional Notes:
- Automatic quantity updates when same product added multiple times
- Easy conversion to order items during checkout process
- Timestamps track when items were added and last modified