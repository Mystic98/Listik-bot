"""Create the PostgreSQL schema for Listik-bot."""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("username", sa.Text()),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("added_by", sa.BigInteger()),
        sa.Column("is_approved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("active_room_id", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "rooms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("creator_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_foreign_key(
        "fk_users_active_room_id", "users", "rooms", ["active_room_id"], ["id"], ondelete="SET NULL"
    )
    op.create_table(
        "room_members",
        sa.Column("room_id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False, server_default="member"),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("room_id", "telegram_id"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Text()),
        sa.Column("added_by", sa.BigInteger(), nullable=False),
        sa.Column("added_by_name", sa.Text()),
        sa.Column("is_purchased", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("purchased_by", sa.BigInteger()),
        sa.Column("purchased_by_name", sa.Text()),
        sa.Column("category", sa.Text(), nullable=False, server_default="other"),
        sa.Column("room_id", sa.Integer()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("purchased_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("room_id", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "template_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Text()),
        sa.Column("category", sa.Text(), nullable=False, server_default="other"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["template_id"], ["templates.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "product_categories",
        sa.Column("name", sa.Text(), primary_key=True),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_items_room_id", "items", ["room_id"])
    op.create_index("idx_items_is_purchased", "items", ["is_purchased"])
    op.create_index("idx_items_category", "items", ["category"])
    op.create_index("idx_templates_room_id", "templates", ["room_id"])
    op.create_index("idx_template_items_template_id", "template_items", ["template_id"])
    op.create_index("idx_room_members_telegram_id", "room_members", ["telegram_id"])


def downgrade() -> None:
    op.drop_table("product_categories")
    op.drop_table("template_items")
    op.drop_table("templates")
    op.drop_table("items")
    op.drop_table("room_members")
    op.drop_constraint("fk_users_active_room_id", "users", type_="foreignkey")
    op.drop_table("rooms")
    op.drop_table("users")
