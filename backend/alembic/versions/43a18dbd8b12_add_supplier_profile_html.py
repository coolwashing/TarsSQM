"""add_supplier_profile_html

Revision ID: 43a18dbd8b12
Revises: 223b5a5301ff
Create Date: 2026-10-18 20:47:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '43a18dbd8b12'
down_revision: Union[str, None] = '223b5a5301ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('sqm_supplier', sa.Column('profile_html', sa.Text(), nullable=True, comment='供应商图文详细档案/富文本'))


def downgrade() -> None:
    op.drop_column('sqm_supplier', 'profile_html')
