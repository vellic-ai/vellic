"""
repos_router — /api/repos/{repo_id}/config endpoints.

GET /api/repos/{repo_id}/config
    Returns the repo-specific rules config (rules_yaml + metadata).
    Returns a default empty config if none has been set.

PUT /api/repos/{repo_id}/config
    Validates and upserts the YAML rules config for a repo.
    Returns 422 if the YAML is invalid or the rule schema is violated.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import db

logger = logging.getLogger("api.repos")

router = APIRouter(prefix="/api/repos", tags=["repos"])

# ---------------------------------------------------------------------------
# YAML schema validation
# ---------------------------------------------------------------------------

_VALID_SEVERITIES = {"info", "warning", "error"}
_VALID_THRESHOLDS = {"info", "warning", "error"}


def _validate_rules_yaml(rules_yaml: str) -> None:
    """Parse and validate the rules YAML. Raises ValueError with a detailed message on failure."""
    if not rules_yaml.strip():
        return

    try:
        doc = yaml.safe_load(rules_yaml)
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML parse error: {exc}") from exc

    if not isinstance(doc, dict):
        raise ValueError("Top-level document must be a YAML mapping")

    rules = doc.get("rules", [])
    if not isinstance(rules, list):
        raise ValueError("'rules' must be a sequence")

    for i, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise ValueError(f"rules[{i}] must be a mapping")
        if "id" not in rule:
            raise ValueError(f"rules[{i}] missing required field 'id'")
        if "pattern" not in rule:
            raise ValueError(f"rules[{i}] missing required field 'pattern'")
        sev = rule.get("severity", "warning")
        if sev not in _VALID_SEVERITIES:
            raise ValueError(
                f"rules[{i}].severity must be one of {sorted(_VALID_SEVERITIES)}, got {sev!r}"
            )
        langs = rule.get("languages", [])
        if not isinstance(langs, list):
            raise ValueError(f"rules[{i}].languages must be a sequence")

    ignore = doc.get("ignore", [])
    if not isinstance(ignore, list):
        raise ValueError("'ignore' must be a sequence of glob patterns")

    threshold = doc.get("severity_threshold", "warning")
    if threshold not in _VALID_THRESHOLDS:
        raise ValueError(
            f"'severity_threshold' must be one of {sorted(_VALID_THRESHOLDS)}, got {threshold!r}"
        )


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class RepoConfigUpdate(BaseModel):
    rules_yaml: str


class RepoConfigResponse(BaseModel):
    repo_id: str
    rules_yaml: str
    updated_at: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/{repo_id}/config", response_model=RepoConfigResponse)
async def get_repo_config(repo_id: str) -> dict[str, Any]:
    """Return the rules config for a repository. Returns defaults if none is set."""
    pool = db.get_pool()
    row = await pool.fetchrow(
        "SELECT repo_id, rules_yaml, updated_at FROM repo_config WHERE repo_id = $1",
        repo_id,
    )
    if row is None:
        return {
            "repo_id": repo_id,
            "rules_yaml": "",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    return {
        "repo_id": row["repo_id"],
        "rules_yaml": row["rules_yaml"],
        "updated_at": row["updated_at"].isoformat(),
    }


@router.put("/{repo_id}/config", response_model=RepoConfigResponse)
async def put_repo_config(repo_id: str, body: RepoConfigUpdate) -> dict[str, Any]:
    """Upsert the rules config for a repository."""
    try:
        _validate_rules_yaml(body.rules_yaml)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    pool = db.get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO repo_config (repo_id, rules_yaml, updated_at)
        VALUES ($1, $2, NOW())
        ON CONFLICT (repo_id) DO UPDATE
            SET rules_yaml = EXCLUDED.rules_yaml,
                updated_at = NOW()
        RETURNING repo_id, rules_yaml, updated_at
        """,
        repo_id,
        body.rules_yaml,
    )
    return {
        "repo_id": row["repo_id"],
        "rules_yaml": row["rules_yaml"],
        "updated_at": row["updated_at"].isoformat(),
    }
