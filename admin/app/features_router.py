import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from vellic_flags import CATALOG, FlagDef, by_key

logger = logging.getLogger("admin.features")

router = APIRouter()

# In-memory runtime overrides (reset on restart; DB persistence added in VEL-97)
_overrides: dict[str, bool] = {}


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
    _overrides[flag.key] = body.enabled
    logger.info("feature flag override: %s = %s", flag.key, body.enabled)
    return {"key": flag.key, "enabled": body.enabled}
