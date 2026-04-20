"""add feedback column to pr_reviews; make posted_at nullable

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-20

"""
from alembic import op

revision: str = "0002"
down_revision: str = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE pr_reviews
            ADD COLUMN IF NOT EXISTS feedback JSONB NOT NULL DEFAULT '{}'
    """)
    op.execute("""
        ALTER TABLE pr_reviews
            ALTER COLUMN posted_at DROP NOT NULL
    """)
    op.execute("""
        ALTER TABLE pr_reviews
            ALTER COLUMN posted_at DROP DEFAULT
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE pr_reviews
            DROP COLUMN IF EXISTS feedback
    """)
    op.execute("""
        ALTER TABLE pr_reviews
            ALTER COLUMN posted_at SET DEFAULT NOW()
    """)
    op.execute("""
        UPDATE pr_reviews SET posted_at = NOW() WHERE posted_at IS NULL
    """)
    op.execute("""
        ALTER TABLE pr_reviews
            ALTER COLUMN posted_at SET NOT NULL
    """)
