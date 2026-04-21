"""add platform, gitlab_discussion_id, bitbucket_comment_id to pr_reviews

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-21

"""

from alembic import op

revision: str = "0008"
down_revision: str = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE pr_reviews
            ADD COLUMN IF NOT EXISTS platform TEXT NOT NULL DEFAULT 'github'
    """)
    op.execute("""
        ALTER TABLE pr_reviews
            ADD COLUMN IF NOT EXISTS gitlab_discussion_id TEXT
    """)
    op.execute("""
        ALTER TABLE pr_reviews
            ADD COLUMN IF NOT EXISTS bitbucket_comment_id TEXT
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_pr_reviews_gitlab_discussion_id
            ON pr_reviews (gitlab_discussion_id)
            WHERE gitlab_discussion_id IS NOT NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_pr_reviews_bitbucket_comment_id
            ON pr_reviews (bitbucket_comment_id)
            WHERE bitbucket_comment_id IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_pr_reviews_bitbucket_comment_id")
    op.execute("DROP INDEX IF EXISTS ix_pr_reviews_gitlab_discussion_id")
    op.execute("ALTER TABLE pr_reviews DROP COLUMN IF EXISTS bitbucket_comment_id")
    op.execute("ALTER TABLE pr_reviews DROP COLUMN IF EXISTS gitlab_discussion_id")
    op.execute("ALTER TABLE pr_reviews DROP COLUMN IF EXISTS platform")
