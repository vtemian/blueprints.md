# models.review

A comprehensive product reviews and ratings system with moderation capabilities, helpfulness voting, and verified purchase tracking to ensure authentic customer feedback.

Dependencies: @../core/database[Base], @./user[User], @./product[Product]

Requirements:
- Store product reviews with ratings, titles, and comments
- Implement moderation workflow with status tracking
- Support helpfulness voting system
- Track verified purchases for review authenticity
- Enforce one review per user per product
- Provide rating analytics and distribution calculations

Model Structure:
- Primary key: id (Integer)
- Foreign keys: user_id (users.id), product_id (products.id), moderated_by (users.id)
- Review content: rating (1-5 integer), title (200 chars), comment (text)
- Moderation fields: status (enum), moderated_at timestamp, moderation_notes
- Voting fields: helpful_votes, unhelpful_votes (integers, default 0)
- Verification: is_verified_purchase boolean flag
- Timestamps: created_at, updated_at
- Constraint: unique combination of user_id and product_id

Review Status Enum:
- PENDING: Newly submitted, awaiting moderation
- APPROVED: Approved and visible to customers
- REJECTED: Rejected due to policy violations
- HIDDEN: Temporarily hidden from display

Business Logic:
- is_valid_rating(): Validate rating is between 1-5 stars
- approve_review(): Mark review as approved with moderator info
- reject_review(): Mark as rejected with reason in moderation notes
- calculate_helpfulness_score(): Calculate ratio of helpful to total votes
- can_be_edited(): Check if review can still be modified by user
- get_product_reviews(): Retrieve reviews for a product (filtered by status)
- get_average_rating(): Calculate average rating for a product
- get_rating_distribution(): Get count distribution across 1-5 stars
- verify_purchase_eligibility(): Check if user purchased the product

Additional Notes:
- Only one review allowed per user per product combination
- Moderation workflow ensures quality control
- Verified purchase flag adds authenticity
- Helpfulness voting helps surface quality reviews
- Rating analytics support product insights