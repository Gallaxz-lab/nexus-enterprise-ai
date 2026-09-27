"""deploy_evaluation_audit_records

Revision ID: 264deefcf9e9
Revises: 7095a3b1ef7c
Create Date: 2026-09-21 18:21:49.956771

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '264deefcf9e9'
down_revision: Union[str, None] = '7095a3b1ef7c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass
    pass


def downgrade() -> None:
    pass
    pass
