from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Body, Query, status
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from models.inventory import Inventory, InventoryMovement
from models.product import Product
from models.user import User
from services.auth import get_current_admin
from core.database import get_db

inventory_router = APIRouter(prefix="/inventory", tags=["Inventory"])


@inventory_router.get("/")
def get_inventory(
    page: int = 1,
    per_page: int = 50,
    low_stock_only: bool = False,
    warehouse: Optional[str] = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get paginated inventory list with optional filters"""
    query = db.query(Inventory)

    if low_stock_only:
        query = query.filter(Inventory.quantity <= Inventory.low_stock_threshold)
    if warehouse:
        query = query.filter(Inventory.warehouse_location == warehouse)

    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": (total + per_page - 1) // per_page,
    }


@inventory_router.post("/{product_id}")
def create_inventory(
    product_id: int,
    quantity_available: Optional[int] = None,
    low_stock_threshold: Optional[int] = None,
    reorder_point: Optional[int] = None,
    max_stock_level: Optional[int] = None,
    warehouse_location: Optional[str] = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Create new inventory record"""
    try:
        inventory = Inventory(
            product_id=product_id,
            quantity=quantity_available,
            low_stock_threshold=low_stock_threshold,
            reorder_point=reorder_point,
            max_stock_level=max_stock_level,
            warehouse_location=warehouse_location,
        )
        db.add(inventory)
        db.commit()
        db.refresh(inventory)
        return inventory
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@inventory_router.put("/{inventory_id}")
def update_inventory(
    inventory_id: int,
    quantity_available: Optional[int] = None,
    low_stock_threshold: Optional[int] = None,
    reorder_point: Optional[int] = None,
    max_stock_level: Optional[int] = None,
    warehouse_location: Optional[str] = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Update inventory record"""
    inventory = db.query(Inventory).filter(Inventory.id == inventory_id).first()
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")

    try:
        if quantity_available is not None:
            inventory.quantity = quantity_available
        if low_stock_threshold is not None:
            inventory.low_stock_threshold = low_stock_threshold
        if reorder_point is not None:
            inventory.reorder_point = reorder_point
        if max_stock_level is not None:
            inventory.max_stock_level = max_stock_level
        if warehouse_location is not None:
            inventory.warehouse_location = warehouse_location

        db.commit()
        db.refresh(inventory)
        return inventory
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@inventory_router.get("/movements")
def get_inventory_movements(
    page: int = 1,
    per_page: int = 20,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get paginated inventory movement history"""
    query = db.query(InventoryMovement).order_by(desc(InventoryMovement.timestamp))
    total = query.count()
    movements = query.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": movements,
        "total": total,
        "page": page,
        "pages": (total + per_page - 1) // per_page,
    }


@inventory_router.post("/bulk-update")
def bulk_update_inventory(
    inventory_updates: List[dict] = Body(...),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Bulk update inventory quantities"""
    try:
        for update in inventory_updates:
            inventory = (
                db.query(Inventory)
                .filter(Inventory.id == update["inventory_id"])
                .first()
            )

            if not inventory:
                continue

            old_quantity = inventory.quantity
            new_quantity = update["quantity"]
            inventory.quantity = new_quantity

            movement = InventoryMovement(
                inventory_id=inventory.id,
                previous_quantity=old_quantity,
                new_quantity=new_quantity,
                timestamp=datetime.utcnow(),
                user_id=current_user.id,
            )
            db.add(movement)

            if new_quantity <= inventory.low_stock_threshold:
                # TODO: Implement low stock alert notification
                pass

        db.commit()
        return {"message": "Inventory updated successfully"}
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
