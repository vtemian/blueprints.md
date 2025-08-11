# models.category

Create a hierarchical product category system with nested categories and SEO optimization for an ecommerce platform.

Dependencies: sqlalchemy, @../core/database

Requirements:
- Create a Category SQLAlchemy model with hierarchical structure (parent/child relationships)
- Include basic category information (name, description, slug)
- Support SEO metadata (meta_title, meta_description)
- Add display and ordering fields (sort_order, is_active, icon_url, banner_image_url)
- Implement self-referential foreign key for parent-child relationships
- Include timestamps for creation and modification tracking

Model Structure:
- Primary key: id (Integer)
- Basic info: name (String, max 100 chars, indexed), description (Text), slug (String, unique, indexed)
- Hierarchy: parent_id (ForeignKey to categories.id), parent/children relationships
- Display: sort_order (Integer, default 0), is_active (Boolean, default True)
- Media: icon_url, banner_image_url (String, max 500 chars)
- SEO: meta_title (String, max 200), meta_description (String, max 500)
- Timestamps: created_at, updated_at (DateTime with auto-update)

Relationships:
- Self-referential parent/children relationship
- One-to-many relationship with Product model

Instance Methods:
- get_all_children(): Return all descendant categories recursively
- get_breadcrumb_path(): Return path from root to current category
- get_product_count(): Count products in this category and subcategories
- is_leaf_category(): Check if category has no children
- generate_slug_from_name(): Create URL-friendly slug from category name

Class Methods:
- get_root_categories(db: Session): Get all top-level categories
- get_by_slug(db: Session, slug: str): Find category by slug

Additional Notes:
- Support hierarchical category tree navigation
- Generate SEO-friendly URLs using slugs
- Enable breadcrumb navigation for better UX
- Provide efficient product counting across category hierarchy
- Include admin-friendly ordering system