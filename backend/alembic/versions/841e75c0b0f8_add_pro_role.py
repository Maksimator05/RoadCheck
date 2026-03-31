"""add pro role

Revision ID: 841e75c0b0f8
Revises: c3959c6cbb77
Create Date: 2026-03-20 13:19:34.609188

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '841e75c0b0f8'
down_revision: Union[str, Sequence[str], None] = 'c3959c6cbb77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE role ADD VALUE IF NOT EXISTS 'pro' AFTER 'user'")


def downgrade() -> None:
    # PostgreSQL не поддерживает удаление значения из enum напрямую.
    # При необходимости: пересоздать тип вручную без 'pro'.
    pass
