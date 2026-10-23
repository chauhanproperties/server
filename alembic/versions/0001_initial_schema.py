"""Create the six tables from database_tables.txt.

Revision ID: 0001_initial
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("phone", sa.Text(), nullable=False),
        sa.Column("whatsapp_number", sa.Text(), nullable=False),
        sa.Column("email", sa.Text()),
        sa.Column("age", sa.Integer()),
        sa.Column("gender", sa.Text()),
        sa.Column("registered_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("phone", name="uq_customers_phone"),
        sa.CheckConstraint("age IS NULL OR age BETWEEN 0 AND 120", name="ck_customers_age"),
        sa.CheckConstraint("gender IS NULL OR gender IN ('male','female','other')", name="ck_customers_gender"),
    )
    op.create_table(
        "properties",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("property_type", sa.Text(), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("length", sa.Numeric(10, 2), nullable=False),
        sa.Column("width", sa.Numeric(10, 2), nullable=False),
        sa.Column("area", sa.Numeric(14, 2), sa.Computed("length * width", persisted=True), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("price", sa.Numeric(14, 2), nullable=False),
        sa.Column("status", sa.Text(), server_default="available", nullable=False),
        sa.Column("latitude", sa.Numeric(9, 6)),
        sa.Column("longitude", sa.Numeric(9, 6)),
        sa.Column("maps_url", sa.Text()),
        sa.Column("buyer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="SET NULL")),
        sa.Column("sold_at", sa.DateTime(timezone=True)),
        sa.Column("sale_price", sa.Numeric(14, 2)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("property_type IN ('plot','house','flat')", name="ck_properties_type"),
        sa.CheckConstraint("length > 0", name="ck_properties_length_positive"),
        sa.CheckConstraint("width > 0", name="ck_properties_width_positive"),
        sa.CheckConstraint("price >= 0", name="ck_properties_price_nonnegative"),
        sa.CheckConstraint("status IN ('available','sold')", name="ck_properties_status"),
        sa.CheckConstraint("latitude IS NULL OR latitude BETWEEN -90 AND 90", name="ck_properties_latitude"),
        sa.CheckConstraint("longitude IS NULL OR longitude BETWEEN -180 AND 180", name="ck_properties_longitude"),
        sa.CheckConstraint("sale_price IS NULL OR sale_price >= 0", name="ck_properties_sale_price"),
    )
    op.create_index("ix_properties_status", "properties", ["status"])
    op.create_index("ix_properties_property_type", "properties", ["property_type"])
    op.create_index("ix_properties_price", "properties", ["price"])
    op.create_table(
        "building_details",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bedrooms", sa.Integer(), nullable=False),
        sa.Column("kitchens", sa.Integer(), nullable=False),
        sa.Column("bathrooms", sa.Integer(), nullable=False),
        sa.Column("garden_area", sa.Numeric(10, 2), server_default="0"),
        sa.Column("parking_area", sa.Numeric(10, 2), server_default="0"),
        sa.Column("building_area", sa.Numeric(10, 2), nullable=False),
        sa.Column("total_area", sa.Numeric(12, 2), sa.Computed("building_area + COALESCE(garden_area, 0) + COALESCE(parking_area, 0)", persisted=True), nullable=False),
        sa.CheckConstraint("bedrooms >= 0", name="ck_building_bedrooms"),
        sa.CheckConstraint("kitchens >= 0", name="ck_building_kitchens"),
        sa.CheckConstraint("bathrooms >= 0", name="ck_building_bathrooms"),
        sa.CheckConstraint("building_area >= 0", name="ck_building_area"),
        sa.CheckConstraint("garden_area IS NULL OR garden_area >= 0", name="ck_building_garden_area"),
        sa.CheckConstraint("parking_area IS NULL OR parking_area >= 0", name="ck_building_parking_area"),
        sa.UniqueConstraint("property_id", name="uq_building_property"),
    )
    op.create_table(
        "property_images",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=False),
        sa.Column("public_id", sa.Text()),
        sa.Column("display_order", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_index("ix_property_images_property_id", "property_images", ["property_id"])
    op.create_table(
        "queries",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id", ondelete="SET NULL")),
        sa.Column("message", sa.Text()),
        sa.Column("status", sa.Text(), server_default="new", nullable=False),
        sa.Column("raised_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('new','resolved')", name="ck_queries_status"),
    )
    op.create_index("ix_queries_customer_id", "queries", ["customer_id"])
    op.create_index("ix_queries_property_id", "queries", ["property_id"])
    op.create_index("ix_queries_status", "queries", ["status"])
    op.create_index("ix_queries_raised_at", "queries", ["raised_at"])
    op.create_table(
        "login_codes",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("code_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

def downgrade():
    op.drop_table("login_codes")
    op.drop_index("ix_queries_raised_at", table_name="queries")
    op.drop_index("ix_queries_status", table_name="queries")
    op.drop_index("ix_queries_property_id", table_name="queries")
    op.drop_index("ix_queries_customer_id", table_name="queries")
    op.drop_table("queries")
    op.drop_index("ix_property_images_property_id", table_name="property_images")
    op.drop_table("property_images")
    op.drop_table("building_details")
    op.drop_index("ix_properties_price", table_name="properties")
    op.drop_index("ix_properties_property_type", table_name="properties")
    op.drop_index("ix_properties_status", table_name="properties")
    op.drop_table("properties")
    op.drop_table("customers")
