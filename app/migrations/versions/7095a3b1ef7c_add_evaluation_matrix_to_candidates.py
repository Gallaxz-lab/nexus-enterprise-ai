"""add_evaluation_matrix_to_candidates

Revision ID: 7095a3b1ef7c
Revises: 1243d60eff4e
Create Date: 2026-09-20 16:57:30.944327

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7095a3b1ef7c'
down_revision: Union[str, None] = '1243d60eff4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass
    pass


def downgrade() -> None:
    pass
    pass
