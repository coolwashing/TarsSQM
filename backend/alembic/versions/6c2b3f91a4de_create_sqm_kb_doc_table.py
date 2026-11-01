"""Create the knowledge base document table.

Revision ID: 6c2b3f91a4de
Revises: 43a18dbd8b12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6c2b3f91a4de"
down_revision: Union[str, None] = "43a18dbd8b12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sqm_kb_doc",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("icon", sa.String(length=32), nullable=False),
        sa.Column("is_folder", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("content_html", sa.Text(), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("biz_type", sa.String(length=32), nullable=True),
        sa.Column("biz_id", sa.Integer(), nullable=True),
        sa.Column("author", sa.String(length=64), nullable=False),
        sa.Column("is_favorite", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["sqm_kb_doc.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("id", "parent_id", "title", "biz_type", "biz_id"):
        op.create_index(op.f(f"ix_sqm_kb_doc_{column}"), "sqm_kb_doc", [column])


def downgrade() -> None:
    for column in ("biz_id", "biz_type", "title", "parent_id", "id"):
        op.drop_index(op.f(f"ix_sqm_kb_doc_{column}"), table_name="sqm_kb_doc")
    op.drop_table("sqm_kb_doc")
