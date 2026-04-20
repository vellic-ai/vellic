"""add github_review_id to pr_reviews

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-20

"""
from alembic import op

revision: str = "0003"
down_revision: str = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE pr_reviews
            ADD COLUMN IF NOT EXISTS github_review_id TEXT
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_pr_reviews_github_review_id
            ON pr_reviews (github_review_id)
            WHERE github_review_id IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_pr_reviews_github_review_id")
    op.execute("ALTER TABLE pr_reviews DROP COLUMN IF EXISTS github_review_id")
