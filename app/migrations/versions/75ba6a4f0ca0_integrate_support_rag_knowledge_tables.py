"""integrate_support_rag_knowledge_tables

Revision ID: 75ba6a4f0ca0
Revises: afd83268e78e
Create Date: 2026-09-24 07:05:24.005955

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '75ba6a4f0ca0'
down_revision: Union[str, None] = 'afd83268e78e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass
    pass


def downgrade() -> None:
    pass
    pass
