"""add_granular_filters_to_candidates

Revision ID: 1243d60eff4e
Revises: 1ab6a97532fc
Create Date: 2026-09-20 16:28:55.518686

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1243d60eff4e'
down_revision: Union[str, None] = '1ab6a97532fc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass
    pass


def downgrade() -> None:
    pass
    pass
