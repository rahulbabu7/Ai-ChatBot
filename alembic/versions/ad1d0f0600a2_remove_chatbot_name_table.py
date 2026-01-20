"""remove chatbot_name table
Revision ID: ad1d0f0600a2
Revises: b3d35b7e9d41
Create Date: 2026-01-20 14:45:58.158208
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'ad1d0f0600a2'
down_revision: Union[str, Sequence[str], None] = 'b3d35b7e9d41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop table directly - this will automatically drop foreign keys and indexes
    op.drop_table('chatbot_name')


def downgrade() -> None:
    """Downgrade schema."""
    # Recreate table with all constraints
    op.create_table('chatbot_name',
        sa.Column('id', mysql.INTEGER(display_width=11), autoincrement=True, nullable=False),
        sa.Column('client_id', mysql.VARCHAR(length=100), nullable=False),
        sa.Column('chatbot_name', mysql.VARCHAR(length=100), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['users.client_id'], name='chatbot_name_ibfk_1', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        mysql_collate='utf8mb4_general_ci',
        mysql_default_charset='utf8mb4',
        mysql_engine='InnoDB'
    )
    op.create_index('ix_chatbot_name_client_id', 'chatbot_name', ['client_id'], unique=False)
