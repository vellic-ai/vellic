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

from vellic_flags import CATALOG, FlagDef, FlagResolver, ScopeContext

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
_MAX_CACHE_ENTRIES = 512

# key → (snapshot_dict, expires_at_monotonic, cached_at_iso)
_CacheEntry = tuple[dict[str, bool], float, str]
_cache: dict[tuple[str | None, str | None, str | None], _CacheEntry] = {}
_cache_lock = asyncio.Lock()


def _evict_stale() -> None:
    """Remove expired entries; if still over limit, drop those expiring soonest."""
    now = time.monotonic()
    stale = [k for k, (_, exp, _) in _cache.items() if now >= exp]
    for k in stale:
        del _cache[k]
    if len(_cache) > _MAX_CACHE_ENTRIES:
        overflow = len(_cache) - _MAX_CACHE_ENTRIES
        for k, _ in sorted(_cache.items(), key=lambda kv: kv[1][1])[:overflow]:
            del _cache[k]


async def _get_snapshot(
    tenant_id: str | None,
    repo_id: str | None,
    user_id: str | None,
) -> tuple[dict[str, bool], str]:
    cache_key = (tenant_id, repo_id, user_id)

    # Step 1: check under lock, release immediately on miss
    async with _cache_lock:
        entry = _cache.get(cache_key)
        if entry is not None and time.monotonic() < entry[1]:
            return entry[0], entry[2]

    # Step 2: lock is released — perform DB I/O without holding it
    pool = db.get_pool()
    store = await PgOverrideStore.load(pool)
    resolver = FlagResolver(store=store)
    ctx = ScopeContext(tenant_id=tenant_id, repo_id=repo_id, user_id=user_id)
    snapshot = resolver.snapshot(ctx)
    cached_at = datetime.now(timezone.utc).isoformat()

    # Step 3: re-acquire lock, double-check, write with bounded eviction
    async with _cache_lock:
        entry = _cache.get(cache_key)
        if entry is not None and time.monotonic() < entry[1]:
            return entry[0], entry[2]
        _cache[cache_key] = (snapshot, time.monotonic() + _TTL, cached_at)
        if len(_cache) > _MAX_CACHE_ENTRIES:
            _evict_stale()

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
