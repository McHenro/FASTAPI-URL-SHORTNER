"""add title to urls

Revision ID: 5dd12808df2d
Revises:
Create Date: 2026-04-24 10:41:14.323316

"""
# op — the tool for DDL operations (ALTER TABLE, CREATE INDEX, DROP COLUMN ...)
from alembic import op
# sa — column type definitions used inside op calls
import sqlalchemy as sa

# revision identifiers — Alembic reads these to build the migration chain
revision = '5dd12808df2d'  # this migration's unique fingerprint
down_revision = None       # None = this is the first (and only) migration; no parent
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Adds the title column to the existing urls table in PostgreSQL.
    # nullable=True → existing rows get NULL automatically; no data loss, no downtime.
    op.add_column('urls', sa.Column('title', sa.String(), nullable=True))


def downgrade() -> None:
    # Exact reverse of upgrade — removes the column.
    # Runs when you do: alembic downgrade -1
    op.drop_column('urls', 'title')
