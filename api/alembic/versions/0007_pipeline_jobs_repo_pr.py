"""add repo and pr_number columns to pipeline_jobs

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-20

"""

from alembic import op
import sqlalchemy as sa

revision: str = "0007"
down_revision: str = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pipeline_jobs", sa.Column("repo", sa.Text(), nullable=True))
    op.add_column("pipeline_jobs", sa.Column("pr_number", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("pipeline_jobs", "pr_number")
    op.drop_column("pipeline_jobs", "repo")
