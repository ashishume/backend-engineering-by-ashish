"""update_balance_column_in_bank_accounts

Revision ID: cd0812d31424
Revises: dd4a8ac7da4c
Create Date: 2026-01-26 19:23:56.607610

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'cd0812d31424'
down_revision: Union[str, None] = 'dd4a8ac7da4c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if balance column exists
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('bank_accounts')]
    
    if 'balance' not in columns:
        # Add the balance column as nullable first
        op.add_column('bank_accounts', sa.Column('balance', sa.Float(), nullable=True))
    
    # Update any NULL balance values to 0
    op.execute("UPDATE bank_accounts SET balance = 0 WHERE balance IS NULL")
    
    # Alter the balance column to be non-nullable with default 0
    op.alter_column(
        'bank_accounts',
        'balance',
        existing_type=sa.Float(),
        nullable=False,
        server_default='0'
    )


def downgrade() -> None:
    # Revert balance column to nullable and remove default
    op.alter_column(
        'bank_accounts',
        'balance',
        existing_type=sa.Float(),
        nullable=True,
        server_default=None
    )
    # Note: We don't drop the column in downgrade to preserve data
