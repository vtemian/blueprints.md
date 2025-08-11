from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from models.review import Review, ReviewStatus
from models.product import Product
from models.user import User
from services.auth import get_current_user, get_current_admin
from core.database import get_db

reviews_router = APIRouter(prefix="/reviews", tags=["Reviews"])


class ReviewCreate(BaseModel):
    title: Optional[str] = None
    comment: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)


class ReviewUpdate(BaseModel):
    title: Optional[str] = None
    comment: Optional[str] = None
    moderation_notes: Optional[str] = None


@reviews_router.post("/products/{product_id}/reviews")
def create_review(
    product_id: int,
    review: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = db.query(Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    existing_review = (
        db.query(Review)
        .filter(Review.product_id == product_id, Review.user_id == current_user.id)
        .first()
    )

    if existing_review:
        raise HTTPException(status_code=400, detail="Review already exists")

    verified_purchase = (
        db.query(func.count())
        .filter(
            # Add purchase verification logic
        )
        .scalar()
        > 0
    )

    new_review = Review(
        user_id=current_user.id,
        product_id=product_id,
        title=review.title,
        comment=review.comment,
        rating=review.rating,
        verified_purchase=verified_purchase,
        status=ReviewStatus.pending,
    )

    db.add(new_review)
    db.commit()
    db.refresh(new_review)
    return new_review


@reviews_router.get("/products/{product_id}/reviews")
def get_product_reviews(
    product_id: int,
    page: int = 1,
    per_page: int = 10,
    sort_by: str = "created_at",
    db: Session = Depends(get_db),
):
    query = db.query(Review).filter(
        Review.product_id == product_id, Review.status == ReviewStatus.approved
    )

    if sort_by == "rating":
        query = query.order_by(Review.rating.desc())
    elif sort_by == "helpful_votes":
        query = query.order_by(Review.helpful_votes.desc())
    else:
        query = query.order_by(Review.created_at.desc())

    total = query.count()
    reviews = query.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "reviews": reviews,
        "total": total,
        "page": page,
        "pages": (total + per_page - 1) // per_page,
    }


@reviews_router.put("/reviews/{review_id}/vote")
def vote_review(
    review_id: int,
    helpful: bool = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    review = db.query(Review).get(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if helpful:
        review.helpful_votes += 1
    else:
        review.unhelpful_votes += 1

    db.commit()
    return review


@reviews_router.get("/admin/reviews/pending")
def get_pending_reviews(
    page: int = 1,
    per_page: int = 20,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Review).filter(Review.status == ReviewStatus.pending)
    total = query.count()
    reviews = query.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "reviews": reviews,
        "total": total,
        "page": page,
        "pages": (total + per_page - 1) // per_page,
    }


@reviews_router.put("/admin/reviews/{review_id}")
def moderate_review(
    review_id: int,
    review_update: ReviewUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    review = db.query(Review).get(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review_update.title:
        review.title = review_update.title
    if review_update.comment:
        review.comment = review_update.comment
    if review_update.moderation_notes:
        review.moderation_notes = review_update.moderation_notes

    review.status = ReviewStatus.approved
    review.moderated_at = datetime.utcnow()
    review.moderator_id = current_user.id

    db.commit()
    return review
