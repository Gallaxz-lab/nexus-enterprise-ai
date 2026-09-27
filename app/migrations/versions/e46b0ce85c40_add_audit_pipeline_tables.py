"""add_audit_pipeline_tables

Revision ID: e46b0ce85c40
Revises: 264deefcf9e9
Create Date: 2026-09-24 04:36:33.903924

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e46b0ce85c40'
down_revision: Union[str, None] = '264deefcf9e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass
    pass


def downgrade() -> None:
    pass
    pass
