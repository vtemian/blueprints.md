# api.inventory
Inventory management endpoints with real-time stock tracking and alerts

deps: @..models.inventory[Inventory, InventoryMovement]; @..models.product[Product]; @..models.user[User]; @..services.auth[get_current_admin]; @..core.database[get_db]

inventory_router = APIRouter(prefix="/inventory", tags=["Inventory"])

# Pydantic schemas
class InventoryUpdate(BaseModel):
    quantity_available: Optional[int] = None
    low_stock_threshold: Optional[int] = None
    reorder_point: Optional[int] = None
    max_stock_level: Optional[int] = None
    warehouse_location: Optional[str] = None

class StockAdjustment(BaseModel):
    quantity: int  # Positive for increase, negative for decrease
    movement_type: str  # RESTOCK, ADJUSTMENT, RETURN
    notes: Optional[str] = None

class InventoryResponse(BaseModel):
    product_id: int
    product_name: str
    product_sku: str
    quantity_available: int
    quantity_reserved: int
    quantity_committed: int
    low_stock_threshold: int
    is_low_stock: bool
    last_restocked_at: Optional[datetime]
    warehouse_location: str

@inventory_router.get("/") -> dict:
async get_inventory_list(
    page: int = 1,
    per_page: int = 50,
    low_stock_only: bool = False,
    warehouse: Optional[str] = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get inventory list with filters (admin only)"""
    # Query inventory with filters
    # Include product information
    # Apply pagination
    # Return inventory summary

@inventory_router.get("/{product_id}") -> InventoryResponse:
async get_product_inventory(
    product_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get inventory details for specific product (admin only)"""
    # Fetch product inventory
    # Include movement history
    # Return detailed inventory info

@inventory_router.put("/{product_id}") -> InventoryResponse:
async update_inventory(
    product_id: int,
    inventory_data: InventoryUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update inventory settings (admin only)"""
    # Validate product exists
    # Update inventory parameters
    # Log changes
    # Return updated inventory

@inventory_router.post("/{product_id}/adjust") -> dict:
async adjust_stock(
    product_id: int,
    adjustment_data: StockAdjustment,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Adjust product stock levels (admin only)"""
    # Validate adjustment data
    # Update inventory quantities
    # Log inventory movement
    # Check for low stock alerts
    # Return adjustment confirmation

@inventory_router.get("/{product_id}/movements") -> dict:
async get_inventory_movements(
    product_id: int,
    page: int = 1,
    per_page: int = 20,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get inventory movement history (admin only)"""
    # Query inventory movements
    # Include user and reference information
    # Apply pagination
    # Return movement history

@inventory_router.get("/alerts/low-stock") -> List[InventoryResponse]:
async get_low_stock_alerts(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get low stock alerts (admin only)"""
    # Query products below threshold
    # Include product details
    # Return low stock products

@inventory_router.get("/reports/summary") -> dict:
async get_inventory_summary(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get inventory summary report (admin only)"""
    # Calculate inventory metrics
    # Total products, stock levels
    # Low stock count
    # Return summary dashboard

@inventory_router.post("/bulk-update") -> dict:
async bulk_inventory_update(
    inventory_updates: List[dict] = Body(...),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Bulk update inventory levels (admin only)"""
    # Validate bulk update data
    # Process multiple inventory updates
    # Log all movements
    # Return update summary

notes: Real-time inventory tracking, movement logging, low stock alerts, bulk operations, warehouse management, comprehensive reporting