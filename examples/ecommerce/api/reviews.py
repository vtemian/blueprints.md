from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

class Review:
    """Review model representing a product review"""
    def __init__(self, id: UUID, user_id: UUID, product_id: UUID, 
                 rating: int, comment: Optional[str] = None):
        self.id = id or uuid4()
        self.user_id = user_id
        self.product_id = product_id
        self.rating = rating
        self.comment = comment
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

class ReviewCreate:
    """Data model for creating a new review"""
    def __init__(self, product_id: UUID, rating: int, comment: Optional[str] = None):
        self.product_id = product_id
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")
        self.rating = rating
        self.comment = comment

class ReviewResponse:
    """Response model for review data"""
    def __init__(self, review: Review):
        self.id = review.id
        self.user_id = review.user_id
        self.product_id = review.product_id
        self.rating = review.rating
        self.comment = review.comment
        self.created_at = review.created_at
        self.updated_at = review.updated_at

class ReviewRepository:
    """Repository for managing review data"""
    def __init__(self):
        self.reviews: List[Review] = []

    def create(self, user_id: UUID, review_data: ReviewCreate) -> Review:
        """Create a new review"""
        if self.get_by_user_and_product(user_id, review_data.product_id):
            raise ValueError("User has already reviewed this product")
            
        review = Review(
            id=uuid4(),
            user_id=user_id,
            product_id=review_data.product_id,
            rating=review_data.rating,
            comment=review_data.comment
        )
        self.reviews.append(review)
        return review

    def get(self, review_id: UUID) -> Optional[Review]:
        """Get review by ID"""
        return next((r for r in self.reviews if r.id == review_id), None)

    def get_by_product(self, product_id: UUID) -> List[Review]:
        """Get all reviews for a product"""
        return [r for r in self.reviews if r.product_id == product_id]

    def get_by_user_and_product(self, user_id: UUID, product_id: UUID) -> Optional[Review]:
        """Get review by user and product"""
        return next((r for r in self.reviews 
                    if r.user_id == user_id and r.product_id == product_id), None)

    def delete(self, review_id: UUID, user_id: UUID) -> bool:
        """Delete a review if it belongs to the user"""
        review = self.get(review_id)
        if not review:
            return False
        if review.user_id != user_id:
            raise ValueError("Not authorized to delete this review")
        self.reviews.remove(review)
        return True