# api.products

Build comprehensive product management API endpoints for an e-commerce platform with search, categories, and inventory integration.

Dependencies: fastapi, @../models/product, @../models/category, @../models/inventory, @../models/review, @../services/auth, @../core/database

Requirements:
- Create FastAPI router with "/products" prefix and "Products" tag
- GET /products endpoint with advanced search, filtering, sorting, and pagination
- GET /products/{id} and GET /products/slug/{slug} for individual product details
- Admin-only POST, PUT, DELETE endpoints for product management
- GET /products/featured and GET /products/{id}/related for homepage and product pages
- POST /products/{id}/images for admin image uploads
- Include comprehensive Pydantic schemas for all request/response models

Search and Filtering:
- Full-text search across product name and description
- Filter by category, price range, availability, featured status
- Sort by name, price, rating, creation date (ascending/descending)
- Support pagination with page and per_page parameters
- Include faceted search results (category counts, price ranges)

Product Management:
- Only authenticated admins can create, update, or delete products
- Validate product data including SKU uniqueness
- Handle product images with cloud storage integration
- Manage product categories and inventory integration
- Support product variants and attributes

Business Rules:
- Only active products visible to regular users
- Admins can manage all products regardless of status
- Products must belong to valid categories
- Price changes should log audit trail for tracking
- Out-of-stock products remain visible but marked appropriately
- Featured products get priority in search results

Performance and Scalability:
- Cache popular product searches and category listings
- Optimize database queries with proper joins and indexes
- Implement efficient pagination for large product catalogs
- Use database query optimization for search operations
- Include response compression for large product lists

Additional Notes:
- Include comprehensive error handling with appropriate HTTP status codes
- Support bulk operations for admin product management
- Add product view tracking for analytics
- Include SEO-friendly URLs with product slugs
- Support product recommendations based on categories and user behavior