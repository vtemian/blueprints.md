from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from models.product import Product
from models.category import Category
from models.inventory import Inventory
from models.review import Review
from services.auth import get_current_user, get_current_admin
from core.database import get_db

products_router = APIRouter(prefix="/products", tags=["Products"])


class ProductBase(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    price: Optional[Decimal] = None
    sale_price: Optional[Decimal] = None
    main_image_url: Optional[str] = None
    gallery_images: Optional[List[str]] = []
    tags: Optional[List[str]] = []
    is_featured: bool = False
    is_digital: bool = False
    category_id: Optional[int] = None
    is_active: Optional[bool] = True


class ProductSearchParams(BaseModel):
    query: Optional[str] = None
    category_id: Optional[int] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    is_featured: Optional[bool] = None
    in_stock_only: bool = True
    sort_by: str = "created_at"
    sort_order: str = "desc"
    page: int = 1
    per_page: int = 24


@products_router.get("/{product_id}")
async def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@products_router.get("/slug/{slug}")
async def get_product_by_slug(slug: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.slug == slug).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@products_router.post("/")
async def create_product(
    product: ProductBase,
    current_user=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    db_product = Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


@products_router.put("/{product_id}")
async def update_product(
    product_id: int,
    product: ProductBase,
    current_user=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    for key, value in product.dict(exclude_unset=True).items():
        setattr(db_product, key, value)

    db.commit()
    db.refresh(db_product)
    return db_product


@products_router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    current_user=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(product)
    db.commit()
    return {"message": "Product deleted"}


@products_router.get("/featured/")
async def get_featured_products(limit: int = 10, db: Session = Depends(get_db)):
    products = (
        db.query(Product)
        .filter(Product.is_featured == True, Product.is_active == True)
        .limit(limit)
        .all()
    )
    return products


@products_router.get("/categories/{category_id}")
async def get_products_by_category(
    category_id: int,
    page: int = 1,
    per_page: int = 24,
    sort_by: str = "name",
    db: Session = Depends(get_db),
):
    sort_column = getattr(Product, sort_by)
    offset = (page - 1) * per_page

    products = (
        db.query(Product)
        .filter(Product.category_id == category_id, Product.is_active == True)
        .order_by(sort_column)
        .offset(offset)
        .limit(per_page)
        .all()
    )

    return products


@products_router.get("/related/{product_id}")
async def get_related_products(
    product_id: int, limit: int = 4, db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    related = (
        db.query(Product)
        .filter(
            Product.category_id == product.category_id,
            Product.id != product_id,
            Product.is_active == True,
        )
        .limit(limit)
        .all()
    )

    return related


@products_router.post("/{product_id}/images")
async def upload_product_images(
    product_id: int,
    images: List[UploadFile] = File(...),
    current_user=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    uploaded_urls = []
    for image in images:
        uploaded_urls.append(f"/media/products/{image.filename}")

    product.gallery_images.extend(uploaded_urls)
    db.commit()

    return {"uploaded_images": uploaded_urls}


@products_router.get("/search/")
async def search_products(
    search_params: ProductSearchParams = Depends(), db: Session = Depends(get_db)
):
    query = db.query(Product).filter(Product.is_active == True)

    if search_params.query:
        query = query.filter(Product.name.ilike(f"%{search_params.query}%"))

    if search_params.category_id:
        query = query.filter(Product.category_id == search_params.category_id)

    if search_params.min_price:
        query = query.filter(Product.price >= search_params.min_price)

    if search_params.max_price:
        query = query.filter(Product.price <= search_params.max_price)

    if search_params.is_featured is not None:
        query = query.filter(Product.is_featured == search_params.is_featured)

    if search_params.in_stock_only:
        query = query.join(Inventory).filter(Inventory.quantity > 0)

    sort_column = getattr(Product, search_params.sort_by)
    if search_params.sort_order == "desc":
        sort_column = desc(sort_column)
    else:
        sort_column = asc(sort_column)

    query = query.order_by(sort_column)

    offset = (search_params.page - 1) * search_params.per_page
    products = query.offset(offset).limit(search_params.per_page).all()

    return products
