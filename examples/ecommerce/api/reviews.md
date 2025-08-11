# api.reviews

A comprehensive product review and rating system API with customer review submission, helpfulness voting, moderation workflow, and review analytics for building trust and driving purchasing decisions.

Dependencies: @../models/review[Review, ReviewStatus], @../models/product[Product], @../models/user[User], @../services/auth[get_current_user, get_current_admin], @../core/database[get_db]

Requirements:
- Enable customers to submit and manage product reviews
- Implement helpfulness voting to surface quality reviews
- Provide moderation workflow for review quality control
- Support verified purchase indicators for authenticity
- Generate review statistics for product insights
- Prevent duplicate reviews per user per product
- Enable flexible review sorting and pagination

API Router: FastAPI router with "/reviews" prefix and "Reviews" tag

Pydantic Schemas:
- ReviewCreate: product_id (int), rating (1-5 stars), title (optional), comment (optional)
- ReviewUpdate: Optional fields for rating, title, comment modifications
- ReviewResponse: Complete review with user info, verification status, vote counts, timestamps
- ReviewModerationRequest: status (ReviewStatus enum), moderation_notes (optional)

Customer Review Endpoints:
- GET /product/{product_id}: Get paginated product reviews
  - Query approved reviews for specific product
  - Include reviewer information and verification status
  - Support sorting by created_at, rating, or helpful_votes
  - Apply pagination for large review sets
  - Return reviews with aggregate rating statistics

- POST /: Create new product review
  - Validate user hasn't already reviewed this product
  - Check if user has purchased the product for verification
  - Create review record with pending moderation status
  - Set verified purchase flag based on order history
  - Return created review for immediate user feedback

- PUT /{review_id}: Update existing review (owner only)
  - Validate review belongs to authenticated user
  - Check if review is still editable (not locked by admin)
  - Update review content fields (rating, title, comment)
  - Reset moderation status to pending for re-review
  - Return updated review with new moderation status

- DELETE /{review_id}: Delete user's own review
  - Validate review ownership by authenticated user
  - Mark review as hidden rather than hard delete
  - Preserve review data for audit purposes
  - Return confirmation of successful deletion

- POST /{review_id}/helpful: Vote on review helpfulness
  - Validate review exists and user is authenticated
  - Record user's helpful/unhelpful vote
  - Update review's helpful and unhelpful vote counts
  - Prevent duplicate voting by same user
  - Return updated vote counts for UI display

- GET /user/{user_id}: Get reviews by specific user
  - Query approved reviews written by specified user
  - Include product information for each review
  - Apply pagination for prolific reviewers
  - Return user's review history with product context

Administrative Review Management:
- GET /admin/pending: Get pending reviews for moderation (admin only)
  - Query all reviews with pending moderation status
  - Include product and user information for context
  - Support pagination for moderation queue management
  - Return reviews awaiting admin approval/rejection

- PUT /admin/{review_id}/moderate: Moderate review status (admin only)
  - Update review status (approved, rejected, hidden)
  - Add moderation notes explaining decision
  - Send notification to reviewer about status change
  - Log moderation action for audit trail
  - Return updated review with moderation details

- GET /admin/statistics: Get review system analytics (admin only)
  - Calculate review metrics across entire system
  - Aggregate data: total reviews, average ratings, approval rates
  - Generate insights for business intelligence
  - Return comprehensive statistics for admin dashboard

Review System Features:
- Verified purchase indicators build customer trust
- Helpfulness voting surfaces most useful reviews
- Moderation workflow ensures review quality
- Comprehensive analytics support business decisions
- Spam prevention through user validation
- Flexible sorting helps customers find relevant reviews

Additional Notes:
- One review per user per product prevents gaming
- Verified purchase tracking enhances review authenticity
- Helpfulness voting creates community-driven quality control
- Moderation workflow balances free expression with quality
- Review analytics provide valuable product and customer insights