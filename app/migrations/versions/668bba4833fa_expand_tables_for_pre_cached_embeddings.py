"""expand_tables_for_pre_cached_embeddings

Revision ID: 668bba4833fa
Revises: 0bc558a90826
Create Date: 2026-09-17 11:40:14.252316

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '668bba4833fa'
down_revision: Union[str, None] = '0bc558a90826'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass
    pass


def downgrade() -> None:
    pass
    pass
