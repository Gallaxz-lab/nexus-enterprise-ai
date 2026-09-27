"""add_job_profiles_table

Revision ID: 0bc558a90826
Revises: 58eac4374d87
Create Date: 2026-09-17 10:57:27.357701

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0bc558a90826'
down_revision: Union[str, None] = '58eac4374d87'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass
    pass


def downgrade() -> None:
    pass
    pass
