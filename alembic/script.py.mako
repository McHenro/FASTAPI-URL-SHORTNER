## This is a Mako template. Alembic reads it when you run:
##   alembic revision --autogenerate -m "your message"
## and uses it as a stamp to generate a new file inside versions/.
## You never run or edit this file directly.

"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
## op — DDL operations (add_column, drop_table, create_index ...)
from alembic import op
## sa — column type definitions (sa.String(), sa.Integer(), sa.Boolean() ...)
import sqlalchemy as sa
## Extra imports added automatically only when needed (e.g. postgresql-specific types)
${imports if imports else ""}

# revision identifiers — Alembic uses these (not the filename) to order migrations
revision = ${repr(up_revision)}      # this migration's unique ID
down_revision = ${repr(down_revision)}  # parent migration's ID; None means this is the first
branch_labels = ${repr(branch_labels)}  # for branched migration trees (rarely used)
depends_on = ${repr(depends_on)}        # cross-branch dependencies (rarely used)


def upgrade() -> None:
    ## Apply the change — runs on: alembic upgrade head
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ## Reverse the change — runs on: alembic downgrade -1
    ${downgrades if downgrades else "pass"}
