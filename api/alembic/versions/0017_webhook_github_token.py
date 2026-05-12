"""add webhook_config.github_token

Revision ID: 0017
Revises: 0016
Create Date: 2026-04-24

"""

from alembic import op

revision: str = "0017"
down_revision: str = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Holds an encrypted GitHub personal access token. The admin UI writes it via
    # PUT /admin/settings/github/token; the worker reads it for diff fetching and
    # posting review comments. Ciphertext is produced by vellic_crypto.
    op.execute("ALTER TABLE webhook_config ADD COLUMN IF NOT EXISTS github_token TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE webhook_config DROP COLUMN IF EXISTS github_token")
