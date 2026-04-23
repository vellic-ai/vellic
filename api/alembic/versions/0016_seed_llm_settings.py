"""seed default llm_settings row (VEL-147)

Revision ID: 0016
Revises: 0015
Create Date: 2026-04-23

"""

from alembic import op

revision: str = "0016"
down_revision: str = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "INSERT INTO llm_settings (id, provider, model, extra) "
        "VALUES (1, 'ollama', 'llama3.2', '{}') "
        "ON CONFLICT (id) DO NOTHING"
    )


def downgrade() -> None:
    op.execute("DELETE FROM llm_settings WHERE id = 1")
