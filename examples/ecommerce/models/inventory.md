# models.inventory

A comprehensive real-time inventory tracking system with stock reservations, low stock alerts, movement logging, and multi-warehouse support for accurate inventory management.

Dependencies: @../core/database[Base], @./product[Product]

Requirements:
- Track real-time inventory levels with multiple quantity states
- Implement reservation system for cart items and pending orders
- Provide low stock alerts and reorder point notifications
- Log all inventory movements with comprehensive audit trail
- Support multi-warehouse inventory management
- Enable backorder functionality where applicable
- Calculate available vs total inventory accurately

Model Structure - Inventory:
- Primary key: id (Integer)
- Product relationship: product_id (unique foreign key to products.id)
- Stock levels: quantity_available, quantity_reserved, quantity_committed
- Thresholds: low_stock_threshold (default 10), reorder_point (default 5), max_stock_level
- Tracking timestamps: last_restocked_at, last_sold_at
- Location fields: warehouse_location (default "MAIN"), bin_location
- Control flags: track_inventory (default true), allow_backorder (default false), is_low_stock_notified
- Audit: created_at, updated_at timestamps
- Relationship: movements (to InventoryMovement records)

Model Structure - InventoryMovement:
- Primary key: id (Integer)
- Foreign key: inventory_id (references inventory.id)
- Movement details: movement_type enum, quantity, previous_quantity, new_quantity
- Reference tracking: reference_type (order/adjustment/etc.), reference_id, notes
- Audit: created_by (user_id), created_at timestamp

Inventory Movement Types:
- RESTOCK: Adding new inventory from suppliers
- SALE: Reducing inventory due to completed sales
- RETURN: Increasing inventory from customer returns
- ADJUSTMENT: Manual corrections to inventory levels
- RESERVATION: Temporarily allocating inventory (cart/pending)
- RELEASE: Releasing previously reserved inventory

Inventory Business Logic:
- get_total_quantity(): Sum all quantity fields for total inventory
- get_available_quantity(): Calculate sellable inventory (available minus reserved)
- is_in_stock(): Check if requested quantity is available
- is_low_stock(): Compare available quantity against low stock threshold
- reserve_quantity(): Allocate inventory for cart/pending orders
- release_reservation(): Free up reserved inventory
- commit_quantity(): Convert reserved to committed (confirmed orders)
- adjust_stock(): Manual adjustment with movement logging
- restock(): Add inventory with automatic movement logging
- process_sale(): Reduce inventory for completed sales
- get_low_stock_products(): Find products below reorder point
- get_out_of_stock_products(): Find products with zero available inventory

Movement Business Logic:
- log_movement(): Create audit record for all inventory changes with before/after quantities

Additional Notes:
- Three-tier quantity tracking: available, reserved, committed
- Reservation system prevents overselling during checkout process
- Comprehensive movement logging provides full audit trail
- Low stock notifications prevent stockouts
- Multi-warehouse support enables distributed inventory
- Backorder functionality allows selling when out of stock