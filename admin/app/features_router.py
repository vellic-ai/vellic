import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from vellic_flags import CATALOG, FlagDef, by_key

from . import db

logger = logging.getLogger("admin.features")

router = APIRouter()

# Warm cache synced from DB on startup and updated on each write.
_overrides: dict[str, bool] = {}

_SCOPE = "global"
_SCOPE_ID = "_global"


async def init_overrides() -> None:
    """Load all global-scope overrides from DB into the in-memory cache."""
    pool = db.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT flag_key, value FROM feature_flag_overrides"
            " WHERE scope = $1 AND scope_id = $2",
            _SCOPE,
            _SCOPE_ID,
        )
    _overrides.clear()
    for row in rows:
        _overrides[row["flag_key"]] = row["value"]
    logger.info("loaded %d feature flag override(s) from DB", len(rows))


def _resolve(flag: FlagDef) -> bool:
    """Return effective enabled state: in-memory override > ENV > default."""
    if flag.key in _overrides:
        return _overrides[flag.key]
    env = flag.read_env()
    if env is not None:
        return env
    return flag.default


def _snapshot() -> dict:
    flags: dict[str, bool] = {f.key: _resolve(f) for f in CATALOG}
    return {
        "flags": flags,
        "catalog": [
            {
                "key": f.key,
                "name": f.name,
                "category": f.category.value,
                "description": f.description,
                "enabled": flags[f.key],
                "default": f.default,
                "scope": f.scope.value,
                "cost_impact": f.cost_impact.value,
                "requires": list(f.requires),
                "tags": list(f.tags),
                "has_consumers": f.has_consumers,
            }
            for f in CATALOG
        ],
        "snapshot_at": datetime.now(UTC).isoformat(),
    }


class FeatureToggle(BaseModel):
    enabled: bool


@router.get("/admin/features")
async def get_features() -> dict:
    return _snapshot()


@router.put("/admin/features/{flag_key:path}", status_code=200)
async def put_feature(flag_key: str, body: FeatureToggle) -> dict:
    flag = by_key(flag_key)
    if flag is None:
        raise HTTPException(status_code=404, detail=f"Unknown feature flag: {flag_key!r}")
    pool = db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO feature_flag_overrides (flag_key, scope, scope_id, value)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (flag_key, scope, scope_id)
            DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
            """,
            flag.key,
            _SCOPE,
            _SCOPE_ID,
            body.enabled,
        )
    _overrides[flag.key] = body.enabled
    logger.info("feature flag override: %s = %s", flag.key, body.enabled)
    return {"key": flag.key, "enabled": body.enabled}


@router.delete("/admin/features/{flag_key:path}", status_code=200)
async def delete_feature(flag_key: str) -> dict:
    flag = by_key(flag_key)
    if flag is None:
        raise HTTPException(status_code=404, detail=f"Unknown feature flag: {flag_key!r}")
    pool = db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM feature_flag_overrides"
            " WHERE flag_key = $1 AND scope = $2 AND scope_id = $3",
            flag.key,
            _SCOPE,
            _SCOPE_ID,
        )
    _overrides.pop(flag.key, None)
    logger.info("feature flag override removed: %s", flag.key)
    return {"key": flag.key, "removed": True}
