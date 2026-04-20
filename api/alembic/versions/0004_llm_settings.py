"""add llm_settings table

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-20

"""

from alembic import op

revision: str = "0004"
down_revision: str = "0003"
branch_labels = None
depends_on = None

_VALID_PROVIDERS = "('ollama','vllm','openai','anthropic','claude_code')"


def upgrade() -> None:
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS llm_settings (
            id         INT         PRIMARY KEY DEFAULT 1
                           CHECK (id = 1),
            provider   TEXT        NOT NULL
                           CHECK (provider IN {_VALID_PROVIDERS}),
            base_url   TEXT,
            model      TEXT        NOT NULL,
            api_key    TEXT,
            extra      JSONB       NOT NULL DEFAULT '{{}}',
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS llm_settings")
