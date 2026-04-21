"""add plugin tables

Revision ID: 0012
Revises: 0011
Create Date: 2026-04-21

"""

from alembic import op

revision: str = "0012"
down_revision: str = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS plugins (
            id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            name            TEXT        NOT NULL,
            version         TEXT        NOT NULL,
            content_hash    TEXT        NOT NULL,
            manifest_json   JSONB       NOT NULL DEFAULT '{}',
            store_path      TEXT        NOT NULL,
            uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (name, version)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_plugins_name ON plugins (name)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS plugin_repo_registrations (
            id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            repo_id         TEXT        NOT NULL,
            plugin_id       UUID        NOT NULL REFERENCES plugins(id) ON DELETE CASCADE,
            version_pin     TEXT        NOT NULL,
            enabled         BOOLEAN     NOT NULL DEFAULT TRUE,
            registered_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (repo_id, plugin_id)
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_plugin_repo_reg_repo_id"
        " ON plugin_repo_registrations (repo_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS plugin_repo_registrations")
    op.execute("DROP TABLE IF EXISTS plugins")
