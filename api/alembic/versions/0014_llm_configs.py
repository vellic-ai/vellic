"""add llm_configs table (per-repo LLM provider config)

Revision ID: 0014
Revises: 0013
Create Date: 2026-04-21

"""

from alembic import op

revision: str = "0014"
down_revision: str = "0013"
branch_labels = None
depends_on = None

_VALID_PROVIDERS = "('ollama','vllm','openai','anthropic','claude_code')"


def upgrade() -> None:
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS llm_configs (
            id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            installation_id  UUID        NOT NULL REFERENCES installations(id) ON DELETE CASCADE,
            provider         TEXT        NOT NULL
                                 CHECK (provider IN {_VALID_PROVIDERS}),
            model            TEXT        NOT NULL,
            base_url         TEXT,
            api_key_enc      TEXT,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_llm_configs_installation UNIQUE (installation_id)
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_llm_configs_installation_id
            ON llm_configs (installation_id)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS llm_configs")
