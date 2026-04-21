"""
PgOverrideStore — asyncpg-backed implementation of the vellic_flags OverrideStore protocol.

The resolver protocol is synchronous, so we materialise overrides into an in-memory
dict on construction. Call PgOverrideStore.load(pool) to create a fully populated
instance, then inject it into FlagResolver(store=store).

Callers should refresh the store (call load again) after any write to
feature_flag_overrides so that the resolver picks up the latest values.
"""

from __future__ import annotations

import asyncpg


class PgOverrideStore:
    """
    Synchronous OverrideStore backed by a Postgres snapshot.

    Use the async class-method ``load`` to build an instance from a live pool.
    """

    def __init__(self, overrides: dict[tuple[str, str, str], bool]) -> None:
        self._overrides = overrides

    @classmethod
    async def load(cls, pool: asyncpg.Pool) -> "PgOverrideStore":
        """
        Fetch all rows from feature_flag_overrides and return a populated store.

        This is a point-in-time snapshot; call again to refresh.
        """
        rows = await pool.fetch(
            "SELECT flag_key, scope, scope_id, value FROM feature_flag_overrides"
        )
        overrides = {(r["flag_key"], r["scope"], r["scope_id"]): r["value"] for r in rows}
        return cls(overrides)

    def get_override(self, key: str, scope: str, scope_id: str) -> bool | None:
        return self._overrides.get((key, scope, scope_id))

    # ------------------------------------------------------------------
    # Write helpers (async; callers must reload the store after writing)
    # ------------------------------------------------------------------

    @staticmethod
    async def set_override(
        pool: asyncpg.Pool,
        flag_key: str,
        scope: str,
        scope_id: str,
        value: bool,
        set_by: str | None = None,
    ) -> None:
        """Upsert an override. Audit row is written by the DB trigger."""
        await pool.execute(
            """
            INSERT INTO feature_flag_overrides (flag_key, scope, scope_id, value, set_by, updated_at)
            VALUES ($1, $2, $3, $4, $5, NOW())
            ON CONFLICT (flag_key, scope, scope_id)
            DO UPDATE SET value = EXCLUDED.value,
                          set_by = EXCLUDED.set_by,
                          updated_at = NOW()
            """,
            flag_key, scope, scope_id, value, set_by,
        )

    @staticmethod
    async def delete_override(
        pool: asyncpg.Pool,
        flag_key: str,
        scope: str,
        scope_id: str,
        deleted_by: str | None = None,
    ) -> None:
        """Delete an override (revert to lower-priority source). Audit row written by trigger.

        deleted_by is propagated to the audit row via a transaction-local session variable
        so the trigger can record who performed the deletion, not who last set the flag.
        """
        async with pool.acquire() as conn:
            async with conn.transaction():
                if deleted_by:
                    await conn.execute(
                        "SELECT set_config('app.deleted_by', $1, true)", deleted_by
                    )
                await conn.execute(
                    "DELETE FROM feature_flag_overrides WHERE flag_key=$1 AND scope=$2 AND scope_id=$3",
                    flag_key, scope, scope_id,
                )
