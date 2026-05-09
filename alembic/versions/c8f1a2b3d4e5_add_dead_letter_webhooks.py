"""add dead_letter_webhooks table

Revision ID: c8f1a2b3d4e5
Revises: b7e3f9a12c45
Create Date: 2026-05-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'c8f1a2b3d4e5'
down_revision = 'b7e3f9a12c45'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'dead_letter_webhooks',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('webhook_id', sa.Integer(), nullable=False),
        sa.Column('webhook_url', sa.String(2048), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('attempt_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('failed_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('is_resolved', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('replayed_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_dlw_webhook_id', 'dead_letter_webhooks', ['webhook_id'])
    op.create_index('ix_dlw_failed_at',  'dead_letter_webhooks', ['failed_at'])


def downgrade() -> None:
    op.drop_index('ix_dlw_failed_at',  table_name='dead_letter_webhooks')
    op.drop_index('ix_dlw_webhook_id', table_name='dead_letter_webhooks')
    op.drop_table('dead_letter_webhooks')
