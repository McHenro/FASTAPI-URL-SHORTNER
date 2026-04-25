"""add webhooks table

Revision ID: b7e3f9a12c45
Revises: 5dd12808df2d
Create Date: 2026-04-24 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'b7e3f9a12c45'
down_revision = '5dd12808df2d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'webhooks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        # JSON column stores the list of subscribed event names
        sa.Column('events', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('now()'),
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_webhooks_id'), 'webhooks', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_webhooks_id'), table_name='webhooks')
    op.drop_table('webhooks')
