"""add feature_flag_overrides and feature_flag_audit tables

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-21

"""

from alembic import op

revision: str = "0007"
down_revision: str = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS feature_flag_overrides (
            id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            flag_key    TEXT        NOT NULL,
            scope       TEXT        NOT NULL,
            scope_id    TEXT        NOT NULL,
            value       BOOLEAN     NOT NULL,
            set_by      TEXT,
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_flag_overrides_key_scope UNIQUE (flag_key, scope, scope_id),
            CONSTRAINT chk_flag_overrides_scope CHECK (
                scope IN ('global', 'tenant', 'repo', 'user')
            )
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_flag_overrides_flag_key
            ON feature_flag_overrides (flag_key)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_flag_overrides_scope_scope_id
            ON feature_flag_overrides (scope, scope_id)
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS feature_flag_audit (
            id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            flag_key        TEXT        NOT NULL,
            scope           TEXT        NOT NULL,
            scope_id        TEXT        NOT NULL,
            action          TEXT        NOT NULL,
            previous_value  BOOLEAN,
            new_value       BOOLEAN,
            set_by          TEXT,
            deleted_by      TEXT,
            changed_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_flag_audit_scope CHECK (
                scope IN ('global', 'tenant', 'repo', 'user')
            ),
            CONSTRAINT chk_flag_audit_action CHECK (
                action IN ('set', 'delete')
            )
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_flag_audit_flag_key
            ON feature_flag_audit (flag_key)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_flag_audit_changed_at
            ON feature_flag_audit (changed_at DESC)
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION feature_flag_overrides_audit()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
                INSERT INTO feature_flag_audit
                    (flag_key, scope, scope_id, action, previous_value, new_value, set_by)
                VALUES (
                    NEW.flag_key,
                    NEW.scope,
                    NEW.scope_id,
                    'set',
                    CASE WHEN TG_OP = 'UPDATE' THEN OLD.value ELSE NULL END,
                    NEW.value,
                    NEW.set_by
                );
                RETURN NEW;
            ELSIF TG_OP = 'DELETE' THEN
                INSERT INTO feature_flag_audit
                    (flag_key, scope, scope_id, action, previous_value, new_value, set_by, deleted_by)
                VALUES (
                    OLD.flag_key,
                    OLD.scope,
                    OLD.scope_id,
                    'delete',
                    OLD.value,
                    NULL,
                    OLD.set_by,
                    NULLIF(current_setting('app.deleted_by', true), '')
                );
                RETURN OLD;
            END IF;
        END;
        $$
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS trg_feature_flag_overrides_audit ON feature_flag_overrides
    """)
    op.execute("""
        CREATE TRIGGER trg_feature_flag_overrides_audit
        AFTER INSERT OR UPDATE OR DELETE ON feature_flag_overrides
        FOR EACH ROW EXECUTE FUNCTION feature_flag_overrides_audit()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_feature_flag_overrides_audit ON feature_flag_overrides")
    op.execute("DROP FUNCTION IF EXISTS feature_flag_overrides_audit()")
    op.execute("DROP TABLE IF EXISTS feature_flag_audit")
    op.execute("DROP TABLE IF EXISTS feature_flag_overrides")
