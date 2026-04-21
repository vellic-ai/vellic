"""
llm_config_router — per-repo LLM provider config endpoints (VEL-133).

GET  /api/repos/{repo_id}/llm-config         Return current config (masked api_key).
PUT  /api/repos/{repo_id}/llm-config         Upsert config (encrypts api_key).
POST /api/repos/{repo_id}/llm-config/test    Probe the configured provider.

All endpoints are gated behind the platform.llm_config_ui feature flag.
Resolution order for the worker: DB config > env vars (handled in worker/app/llm/db_config.py).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from vellic_flags import FlagResolver, ScopeContext, by_key

from . import db
from .crypto import decrypt, encrypt, mask
from .flag_store import PgOverrideStore

logger = logging.getLogger("api.llm_config")

router = APIRouter(prefix="/api/repos", tags=["llm-config"])

VALID_PROVIDERS = frozenset({"ollama", "vllm", "openai", "anthropic", "claude_code"})


# ---------------------------------------------------------------------------
# Feature-flag guard
# ---------------------------------------------------------------------------

async def _require_flag(repo_id: str) -> None:
    """Raise 403 if platform.llm_config_ui is not enabled for this repo."""
    flag = by_key("platform.llm_config_ui")
    if flag is None:
        raise HTTPException(status_code=500, detail="platform.llm_config_ui flag not registered")
    pool = db.get_pool()
    store = await PgOverrideStore.load(pool)
    resolver = FlagResolver(store=store)
    ctx = ScopeContext(repo_id=repo_id)
    if not resolver.resolve(flag, ctx):
        raise HTTPException(status_code=403, detail="platform.llm_config_ui is not enabled")


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

async def _fetch_installation_id(pool: Any, repo_id: str) -> str:
    """Return the installations.id for the given repo_id (org/repo slug)."""
    parts = repo_id.split("/", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=422, detail="repo_id must be in org/repo format")
    org, repo = parts[0].strip(), parts[1].strip()
    row = await pool.fetchrow(
        "SELECT id FROM installations WHERE org = $1 AND COALESCE(repo, '*') = $2",
        org, repo,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    return str(row["id"])


async def _fetch_config_row(pool: Any, installation_id: str) -> dict | None:
    row = await pool.fetchrow(
        "SELECT id, installation_id, provider, model, base_url, api_key_enc, created_at, updated_at"
        " FROM llm_configs WHERE installation_id = $1::uuid",
        installation_id,
    )
    return dict(row) if row else None


def _row_to_response(repo_id: str, row: dict) -> dict:
    masked_key = None
    if row.get("api_key_enc"):
        try:
            plain = decrypt(row["api_key_enc"])
            masked_key = mask(plain)
        except Exception:
            masked_key = "****"
    return {
        "repo_id": repo_id,
        "provider": row["provider"],
        "model": row["model"],
        "base_url": row.get("base_url"),
        "api_key": masked_key,
        "updated_at": (
            row["updated_at"].isoformat()
            if isinstance(row["updated_at"], datetime)
            else row["updated_at"]
        ),
    }


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class LLMConfigIn(BaseModel):
    provider: str
    model: str
    base_url: str | None = None
    api_key: str | None = None


class LLMConfigOut(BaseModel):
    repo_id: str
    provider: str
    model: str
    base_url: str | None
    api_key: str | None
    updated_at: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/{repo_id:path}/llm-config", response_model=LLMConfigOut)
async def get_llm_config(repo_id: str) -> dict:
    await _require_flag(repo_id)
    pool = db.get_pool()
    installation_id = await _fetch_installation_id(pool, repo_id)
    row = await _fetch_config_row(pool, installation_id)
    if row is None:
        raise HTTPException(status_code=404, detail="LLM config not set for this repo")
    return _row_to_response(repo_id, row)


@router.put("/{repo_id:path}/llm-config", response_model=LLMConfigOut)
async def put_llm_config(repo_id: str, body: LLMConfigIn) -> dict:
    await _require_flag(repo_id)
    if body.provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=422, detail=f"Unknown provider: {body.provider!r}")

    pool = db.get_pool()
    installation_id = await _fetch_installation_id(pool, repo_id)
    api_key_enc = encrypt(body.api_key) if body.api_key else None

    row = await pool.fetchrow(
        """
        INSERT INTO llm_configs
            (installation_id, provider, model, base_url, api_key_enc, updated_at)
        VALUES ($1::uuid, $2, $3, $4, $5, NOW())
        ON CONFLICT (installation_id) DO UPDATE SET
            provider    = EXCLUDED.provider,
            model       = EXCLUDED.model,
            base_url    = EXCLUDED.base_url,
            api_key_enc = EXCLUDED.api_key_enc,
            updated_at  = NOW()
        RETURNING
            id, installation_id, provider, model, base_url, api_key_enc, created_at, updated_at
        """,
        installation_id,
        body.provider,
        body.model,
        body.base_url,
        api_key_enc,
    )
    result = _row_to_response(repo_id, dict(row))
    # Show the plaintext key (masked) the caller just provided — avoid a decrypt round-trip
    if body.api_key:
        result["api_key"] = mask(body.api_key)
    logger.info("llm_config upserted repo=%s provider=%s", repo_id, body.provider)
    return result


@router.post("/{repo_id:path}/llm-config/test", status_code=200)
async def test_llm_config(repo_id: str) -> dict:
    await _require_flag(repo_id)
    pool = db.get_pool()
    installation_id = await _fetch_installation_id(pool, repo_id)
    row = await _fetch_config_row(pool, installation_id)
    if row is None:
        raise HTTPException(status_code=404, detail="LLM config not set for this repo")

    provider = row["provider"]
    model = row["model"]
    base_url = row.get("base_url") or ""
    api_key = ""
    if row.get("api_key_enc"):
        try:
            api_key = decrypt(row["api_key_enc"])
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Failed to decrypt api_key") from exc

    # Resolve effective values: DB config > env vars
    effective_base_url = base_url or os.getenv("LLM_BASE_URL", "")
    effective_api_key = api_key or os.getenv("LLM_API_KEY", "")

    try:
        if provider in ("openai", "anthropic", "claude_code"):
            await _probe_openai_compat(effective_base_url, effective_api_key, model, provider)
        elif provider in ("ollama", "vllm"):
            await _probe_ollama_compat(effective_base_url, model)
        else:
            raise HTTPException(status_code=422, detail=f"Unsupported provider: {provider!r}")
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("llm config test failed repo=%s: %s", repo_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"ok": True, "provider": provider, "model": model}


async def _probe_openai_compat(base_url: str, api_key: str, model: str, provider: str) -> None:
    url = base_url or "https://api.openai.com"
    if provider == "anthropic":
        url = base_url or "https://api.anthropic.com"
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{url.rstrip('/')}/v1/models", headers=headers)
    if r.status_code not in (200, 404):
        raise HTTPException(status_code=502, detail=f"Provider returned HTTP {r.status_code}")


async def _probe_ollama_compat(base_url: str, model: str) -> None:
    url = base_url or "http://localhost:11434"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{url.rstrip('/')}/api/tags")
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Ollama returned HTTP {r.status_code}")
