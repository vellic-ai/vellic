import logging
import os
import secrets
from datetime import datetime
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

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


# ---------------------------------------------------------------------------
# Webhook config
# ---------------------------------------------------------------------------

class WebhookEndpointIn(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def url_must_be_http_or_https(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme not in ("https", "http"):
            raise ValueError("url must use http or https scheme")
        if not parsed.hostname:
            raise ValueError("url must include a hostname")
        return v


class GitHubAppIn(BaseModel):
    app_id: str
    installation_id: str
    private_key: str | None = None


class GitLabIn(BaseModel):
    token: str | None = None


def _row_to_webhook_out(row: dict) -> dict:
    return {
        "url": row.get("url") or "",
        "hmac": decrypt(row["hmac"]) if row.get("hmac") else "",
        "github_app_id": row.get("github_app_id") or "",
        "github_installation_id": row.get("github_installation_id") or "",
        "github_key_set": bool(row.get("github_private_key")),
        "gitlab_token_set": bool(row.get("gitlab_token")),
    }


@router.get("/admin/settings/webhook")
async def get_webhook_settings() -> dict:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM webhook_config WHERE id = 1")
    if row is None:
        raise HTTPException(status_code=404, detail="Webhook not configured")
    return _row_to_webhook_out(dict(row))


@router.put("/admin/settings/webhook", status_code=200)
async def put_webhook_endpoint(body: WebhookEndpointIn) -> dict:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO webhook_config (id, url, updated_at)
            VALUES (1, $1, NOW())
            ON CONFLICT (id) DO UPDATE SET url = EXCLUDED.url, updated_at = NOW()
            RETURNING *
            """,
            body.url,
        )
    logger.info("webhook url updated")
    return _row_to_webhook_out(dict(row))


@router.post("/admin/settings/webhook/rotate", status_code=200)
async def rotate_webhook_hmac() -> dict:
    new_hmac = "whsec_" + secrets.token_urlsafe(32)
    encrypted = encrypt(new_hmac)
    pool = db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO webhook_config (id, hmac, updated_at) VALUES (1, $1, NOW()) "
            "ON CONFLICT (id) DO UPDATE SET hmac = EXCLUDED.hmac, updated_at = NOW()",
            encrypted,
        )
    logger.info("webhook hmac rotated")
    return {"hmac": new_hmac}


@router.put("/admin/settings/github", status_code=200)
async def put_github_settings(body: GitHubAppIn) -> dict:
    encrypted_key = encrypt(body.private_key) if body.private_key else None
    pool = db.get_pool()
    async with pool.acquire() as conn:
        if encrypted_key:
            row = await conn.fetchrow(
                """
                INSERT INTO webhook_config
                    (id, github_app_id, github_installation_id, github_private_key, updated_at)
                VALUES (1, $1, $2, $3, NOW())
                ON CONFLICT (id) DO UPDATE SET
                    github_app_id = EXCLUDED.github_app_id,
                    github_installation_id = EXCLUDED.github_installation_id,
                    github_private_key = EXCLUDED.github_private_key,
                    updated_at = NOW()
                RETURNING *
                """,
                body.app_id, body.installation_id, encrypted_key,
            )
        else:
            row = await conn.fetchrow(
                """
                INSERT INTO webhook_config (id, github_app_id, github_installation_id, updated_at)
                VALUES (1, $1, $2, NOW())
                ON CONFLICT (id) DO UPDATE SET
                    github_app_id = EXCLUDED.github_app_id,
                    github_installation_id = EXCLUDED.github_installation_id,
                    updated_at = NOW()
                RETURNING *
                """,
                body.app_id, body.installation_id,
            )
    logger.info("github app settings updated app_id=%s", body.app_id)
    return _row_to_webhook_out(dict(row))


@router.post("/admin/settings/github/test", status_code=200)
async def test_github_connection() -> dict:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM webhook_config WHERE id = 1")
    if not row or not row.get("github_private_key"):
        raise HTTPException(status_code=422, detail="GitHub App not configured")

    app_id = row["github_app_id"]
    private_key_pem = decrypt(row["github_private_key"])

    try:
        import time

        import jwt

        now = int(time.time())
        payload = {"iat": now - 60, "exp": now + 600, "iss": app_id}
        token = jwt.encode(payload, private_key_pem, algorithm="RS256")
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://api.github.com/app",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                },
            )
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"GitHub API returned {r.status_code}")
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("github test failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"ok": True}


@router.put("/admin/settings/gitlab", status_code=200)
async def put_gitlab_settings(body: GitLabIn) -> dict:
    if not body.token:
        raise HTTPException(status_code=422, detail="token is required")
    encrypted = encrypt(body.token)
    pool = db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO webhook_config (id, gitlab_token, updated_at)
            VALUES (1, $1, NOW())
            ON CONFLICT (id) DO UPDATE SET gitlab_token = EXCLUDED.gitlab_token, updated_at = NOW()
            RETURNING *
            """,
            encrypted,
        )
    logger.info("gitlab token updated")
    return _row_to_webhook_out(dict(row))


@router.post("/admin/settings/gitlab/test", status_code=200)
async def test_gitlab_connection() -> dict:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM webhook_config WHERE id = 1")
    if not row or not row.get("gitlab_token"):
        raise HTTPException(status_code=422, detail="GitLab token not configured")

    token = decrypt(row["gitlab_token"])
    gitlab_url = os.getenv("GITLAB_BASE_URL", "https://gitlab.com")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{gitlab_url}/api/v4/user",
                headers={"PRIVATE-TOKEN": token},
            )
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"GitLab API returned {r.status_code}")
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("gitlab test failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"ok": True}
