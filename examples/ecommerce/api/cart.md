# api.cart

A responsive shopping cart management API providing real-time cart operations with inventory validation, pricing updates, and seamless user experience for e-commerce shopping flows.

Dependencies: @../models/cart[Cart], @../models/product[Product], @../models/user[User], @../services/auth[get_current_user], @../core/database[get_db]

Requirements:
- Provide fast cart operations for responsive user interface
- Validate product availability and pricing in real-time
- Support cart persistence across user sessions
- Calculate accurate totals including tax estimates
- Prevent adding unavailable or inactive products
- Optimize for frequent cart updates during shopping
- Return consistent cart state for UI synchronization

API Router: FastAPI router with "/cart" prefix and "Shopping Cart" tag

Pydantic Schemas:
- AddToCartRequest: product_id (int), quantity (int, default 1)
- UpdateCartItemRequest: quantity (int) for cart item updates
- CartItemResponse: Complete cart item with id, product details, quantity, subtotal, added_at
- CartResponse: Full cart summary with items, counts, totals, and tax estimates

Cart Management Endpoints:
- GET /: Get complete user shopping cart
  - Fetch all cart items for authenticated user
  - Validate each product is still available and active
  - Calculate current pricing for all items
  - Compute subtotal, estimated tax, and total amounts
  - Return comprehensive cart summary for checkout readiness

- POST /add: Add product to shopping cart
  - Validate product exists and is currently active
  - Check sufficient inventory for requested quantity
  - Add new cart item or update quantity if product already in cart
  - Return success confirmation with updated cart count
  - Handle duplicate product additions by merging quantities

- PUT /{item_id}: Update existing cart item quantity
  - Validate cart item belongs to authenticated user
  - Check inventory availability for new quantity
  - Update cart item with new quantity
  - Recalculate cart totals with updated quantity
  - Return updated cart summary for UI refresh

- DELETE /{item_id}: Remove specific item from cart
  - Validate user owns the cart item
  - Remove cart item from database
  - Return updated cart summary without removed item
  - Provide feedback for successful item removal

- DELETE /clear: Clear entire shopping cart
  - Remove all cart items for authenticated user
  - Clean up all associated cart data
  - Return confirmation of cart clearing
  - Reset cart state for fresh shopping session

- GET /count: Get total cart item count
  - Count all items in user's cart (sum of quantities)
  - Return item count for header badge display
  - Optimize for frequent calls from UI components
  - Provide fast response for cart indicator updates

Business Logic:
- Real-time inventory validation prevents overselling
- Automatic pricing updates reflect current product prices
- Cart persistence maintains state across browser sessions
- Tax estimation provides checkout preview calculations
- Quantity merging handles duplicate product additions intelligently
- Responsive design optimized for frequent UI updates

Additional Notes:
- Optimized for high-frequency cart operations
- Consistent cart state synchronization across UI
- Real-time validation prevents checkout errors
- Seamless integration with inventory management system
- Cart persistence enables cross-device shopping continuity