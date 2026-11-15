"""Create FMEA visual risk board and item tables.

Revision ID: 8f4e2a19c7b1
Revises: 6c2b3f91a4de
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f4e2a19c7b1"
down_revision: Union[str, None] = "6c2b3f91a4de"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "sqm_fmea_board" not in existing_tables:
        op.create_table(
            "sqm_fmea_board",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("board_code", sa.String(length=64), nullable=False),
            sa.Column("group_name", sa.String(length=100), nullable=False, server_default="未分组系统"),
            sa.Column("name", sa.String(length=150), nullable=False),
            sa.Column("board_type", sa.String(length=20), nullable=False, server_default="MIXED"),
            sa.Column("description", sa.String(length=500), nullable=True),
            sa.Column("canvas_data", sa.JSON(), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("board_code"),
        )
        for col in ("id", "board_code", "group_name", "is_archived"):
            op.create_index(op.f(f"ix_sqm_fmea_board_{col}"), "sqm_fmea_board", [col])

    if "sqm_fmea_item" not in existing_tables:
        op.create_table(
            "sqm_fmea_item",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("fmea_code", sa.String(length=64), nullable=False),
            sa.Column("board_id", sa.Integer(), nullable=True),
            sa.Column("target_kind", sa.String(length=20), nullable=False, server_default="unassigned"),
            sa.Column("target_id", sa.String(length=64), nullable=True),
            sa.Column("target_title_snapshot", sa.String(length=150), nullable=True),
            sa.Column("fmea_type", sa.String(length=20), nullable=False, server_default="DFMEA"),
            sa.Column("failure_mode", sa.String(length=255), nullable=False),
            sa.Column("failure_mech", sa.Text(), nullable=True),
            sa.Column("failure_effect", sa.Text(), nullable=True),
            sa.Column("control_measure", sa.Text(), nullable=True),
            sa.Column("risk_level", sa.String(length=16), nullable=False, server_default="MED"),
            sa.Column("severity", sa.Integer(), nullable=True),
            sa.Column("occurrence", sa.Integer(), nullable=True),
            sa.Column("detection", sa.Integer(), nullable=True),
            sa.Column("rpn", sa.Integer(), nullable=True),
            sa.Column("photos", sa.JSON(), nullable=True),
            sa.Column("linked_refs", sa.JSON(), nullable=True),
            sa.Column("ref_codes_text", sa.String(length=500), nullable=True),
            sa.Column("source_issue_no", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["board_id"], ["sqm_fmea_board.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("fmea_code"),
        )
        for col in (
            "id",
            "fmea_code",
            "board_id",
            "target_kind",
            "target_id",
            "fmea_type",
            "risk_level",
            "rpn",
            "ref_codes_text",
            "source_issue_no",
        ):
            op.create_index(op.f(f"ix_sqm_fmea_item_{col}"), "sqm_fmea_item", [col])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "sqm_fmea_item" in existing_tables:
        op.drop_table("sqm_fmea_item")
    if "sqm_fmea_board" in existing_tables:
        op.drop_table("sqm_fmea_board")

