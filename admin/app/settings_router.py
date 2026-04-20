import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import db
from .crypto import decrypt, encrypt, mask

logger = logging.getLogger("admin.settings")

VALID_PROVIDERS = frozenset({"ollama", "vllm", "openai", "anthropic", "claude_code"})

router = APIRouter()


class LLMSettingsIn(BaseModel):
    provider: str
    base_url: str | None = None
    model: str
    api_key: str | None = None
    extra: dict = {}


class LLMSettingsOut(BaseModel):
    provider: str
    base_url: str | None
    model: str
    api_key: str | None
    extra: dict
    updated_at: str | None


def _mask_row(row: dict, plaintext_key: str | None = None) -> LLMSettingsOut:
    """Build response, masking the api_key. plaintext_key avoids a decrypt round-trip."""
    masked = None
    if row["api_key"]:
        plain = plaintext_key if plaintext_key is not None else decrypt(row["api_key"])
        masked = mask(plain)
    updated = row["updated_at"]
    return LLMSettingsOut(
        provider=row["provider"],
        base_url=row["base_url"],
        model=row["model"],
        api_key=masked,
        extra=row["extra"] or {},
        updated_at=updated.isoformat() if isinstance(updated, datetime) else updated,
    )


@router.get("/admin/settings/llm", response_model=LLMSettingsOut)
async def get_llm_settings() -> LLMSettingsOut:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM llm_settings WHERE id = 1")
    if row is None:
        raise HTTPException(status_code=404, detail="LLM settings not configured")
    return _mask_row(dict(row))


@router.put("/admin/settings/llm", response_model=LLMSettingsOut)
async def put_llm_settings(body: LLMSettingsIn) -> LLMSettingsOut:
    if body.provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=422, detail=f"Unknown provider: {body.provider!r}")

    encrypted_key = encrypt(body.api_key) if body.api_key else None

    pool = db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO llm_settings (id, provider, base_url, model, api_key, extra, updated_at)
            VALUES (1, $1, $2, $3, $4, $5::jsonb, NOW())
            ON CONFLICT (id) DO UPDATE SET
                provider   = EXCLUDED.provider,
                base_url   = EXCLUDED.base_url,
                model      = EXCLUDED.model,
                api_key    = EXCLUDED.api_key,
                extra      = EXCLUDED.extra,
                updated_at = EXCLUDED.updated_at
            RETURNING *
            """,
            body.provider,
            body.base_url,
            body.model,
            encrypted_key,
            body.extra,
        )

    logger.info("llm_settings upserted provider=%s", body.provider)
    return _mask_row(dict(row), plaintext_key=body.api_key)
