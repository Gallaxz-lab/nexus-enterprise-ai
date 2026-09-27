"""integrate_langgraph_audit_workflow

Revision ID: afd83268e78e
Revises: e46b0ce85c40
Create Date: 2026-09-24 05:50:11.049416

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'afd83268e78e'
down_revision: Union[str, None] = 'e46b0ce85c40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass
    pass


def downgrade() -> None:
    pass
    pass
