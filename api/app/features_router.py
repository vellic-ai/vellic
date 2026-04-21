"""
features_router — /api/features and /api/features/catalog endpoints.

GET /api/features
    Returns a resolved flag snapshot for the given scope context.
    Results are cached in-memory for FEATURES_CACHE_TTL_SECONDS (default 30).

GET /api/features/catalog
    Returns the static flag catalog (code-defined metadata).
    The catalog is immutable between deployments so it is built once at import
    time and served from a module-level constant.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Query

from vellic_flags import CATALOG, FlagResolver, ScopeContext
from vellic_flags._catalog import FlagDef

from . import db
from .flag_store import PgOverrideStore

logger = logging.getLogger("api.features")

router = APIRouter(prefix="/api/features", tags=["features"])

# ---------------------------------------------------------------------------
# Catalog (static — built once)
# ---------------------------------------------------------------------------

def _flag_def_to_dict(f: FlagDef) -> dict[str, Any]:
    return {
        "key": f.key,
        "name": f.name,
        "category": f.category.value,
        "description": f.description,
        "default": f.default,
        "scope": f.scope.value,
        "cost_impact": f.cost_impact.value,
        "requires": list(f.requires),
        "tags": list(f.tags),
    }


_CATALOG_RESPONSE: dict[str, Any] = {
    "flags": [_flag_def_to_dict(f) for f in CATALOG]
}

# ---------------------------------------------------------------------------
# Snapshot cache
# ---------------------------------------------------------------------------

_TTL: float = float(os.getenv("FEATURES_CACHE_TTL_SECONDS", "30"))

# key → (snapshot_dict, expires_at_monotonic, cached_at_iso)
_cache: dict[tuple[str | None, str | None, str | None], tuple[dict[str, bool], float, str]] = {}
_cache_lock = asyncio.Lock()


async def _get_snapshot(
    tenant_id: str | None,
    repo_id: str | None,
    user_id: str | None,
) -> tuple[dict[str, bool], str]:
    cache_key = (tenant_id, repo_id, user_id)
    now = time.monotonic()

    async with _cache_lock:
        entry = _cache.get(cache_key)
        if entry is not None:
            snapshot, expires_at, cached_at = entry
            if now < expires_at:
                return snapshot, cached_at

        pool = db.get_pool()
        store = await PgOverrideStore.load(pool)
        resolver = FlagResolver(store=store)
        ctx = ScopeContext(tenant_id=tenant_id, repo_id=repo_id, user_id=user_id)
        snapshot = resolver.snapshot(ctx)
        cached_at = datetime.now(timezone.utc).isoformat()
        _cache[cache_key] = (snapshot, now + _TTL, cached_at)
        return snapshot, cached_at


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/catalog")
async def get_catalog() -> dict:
    """Return the full flag catalog with metadata."""
    return _CATALOG_RESPONSE


@router.get("")
async def get_features(
    tenant_id: str | None = Query(default=None),
    repo_id: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
) -> dict:
    """Return a resolved flag snapshot for the given scope context."""
    snapshot, cached_at = await _get_snapshot(tenant_id, repo_id, user_id)
    return {"flags": snapshot, "cached_at": cached_at}
