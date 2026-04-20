import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import db

logger = logging.getLogger("admin.repos")

VALID_PLATFORMS = frozenset({"github", "gitlab"})
VALID_PROVIDERS = frozenset({"ollama", "vllm", "openai", "anthropic", "claude_code"})

router = APIRouter()


class RepoBody(BaseModel):
    """Shared body for create/edit. Accepts slug (org/repo) or org+repo."""
    platform: str
    org: str | None = None
    repo: str | None = None
    slug: str | None = None  # "org/repo" or "org/*"
    provider: str = "ollama"
    model: str = "qwen2.5-coder:14b"
    enabled: bool = True


def _parse_slug(body: RepoBody) -> tuple[str, str]:
    """Return (org, repo) from body, normalising slug or explicit fields."""
    if body.slug:
        parts = body.slug.split("/", 1)
        org = parts[0].strip()
        repo = parts[1].strip() if len(parts) > 1 else "*"
    else:
        org = (body.org or "").strip()
        repo = (body.repo or "").strip()
    if not org:
        raise HTTPException(422, "org is required")
    if not repo:
        raise HTTPException(422, "repo is required")
    return org, repo


def _row_to_item(row: dict) -> dict:
    cfg = row["config_json"] or {}
    org = row["org"]
    repo_raw = row["repo"] or "*"
    return {
        "id": str(row["id"]),
        "platform": row["platform"],
        "org": org,
        "repo": repo_raw,
        "slug": f"{org}/{repo_raw}",
        "enabled": cfg.get("enabled", True),
        "provider": cfg.get("provider", "ollama"),
        "model": cfg.get("model", ""),
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


@router.get("/admin/settings/repos")
async def list_repos() -> list:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, platform, org, repo, config_json, created_at"
            " FROM installations ORDER BY created_at DESC"
        )
    return [_row_to_item(dict(r)) for r in rows]


@router.post("/admin/settings/repos", status_code=201)
async def create_repo(body: RepoBody) -> dict:
    if body.platform not in VALID_PLATFORMS:
        raise HTTPException(422, f"Unknown platform: {body.platform!r}")
    if body.provider not in VALID_PROVIDERS:
        raise HTTPException(422, f"Unknown provider: {body.provider!r}")

    org, repo = _parse_slug(body)
    repo_val = None if repo == "*" else repo
    config = {"enabled": True, "provider": body.provider, "model": body.model}

    pool = db.get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id FROM installations"
            " WHERE platform=$1 AND org=$2 AND COALESCE(repo,'*')=$3",
            body.platform, org, repo,
        )
        if existing:
            raise HTTPException(409, "Repository already configured")

        row = await conn.fetchrow(
            """
            INSERT INTO installations (platform, org, repo, config_json)
            VALUES ($1, $2, $3, $4::jsonb)
            RETURNING id, platform, org, repo, config_json, created_at
            """,
            body.platform, org, repo_val, config,
        )

    logger.info("repo created platform=%s org=%s repo=%s", body.platform, org, repo)
    return _row_to_item(dict(row))


@router.put("/admin/settings/repos/{repo_id}")
async def update_repo(repo_id: str, body: RepoBody) -> dict:
    if body.platform not in VALID_PLATFORMS:
        raise HTTPException(422, f"Unknown platform: {body.platform!r}")
    if body.provider not in VALID_PROVIDERS:
        raise HTTPException(422, f"Unknown provider: {body.provider!r}")

    org, repo = _parse_slug(body)
    repo_val = None if repo == "*" else repo

    pool = db.get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id FROM installations WHERE id = $1::uuid", repo_id
        )
        if existing is None:
            raise HTTPException(404, "Not found")

        cfg = {"enabled": body.enabled, "provider": body.provider, "model": body.model}
        updated = await conn.fetchrow(
            """
            UPDATE installations
            SET platform=$2, org=$3, repo=$4, config_json=$5::jsonb
            WHERE id=$1::uuid
            RETURNING id, platform, org, repo, config_json, created_at
            """,
            repo_id, body.platform, org, repo_val, cfg,
        )

    logger.info("repo updated id=%s platform=%s org=%s repo=%s", repo_id, body.platform, org, repo)
    return _row_to_item(dict(updated))


@router.post("/admin/settings/repos/{repo_id}/toggle", status_code=200)
async def toggle_repo(repo_id: str) -> dict:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, platform, org, repo, config_json, created_at"
            " FROM installations WHERE id = $1::uuid",
            repo_id,
        )
        if row is None:
            raise HTTPException(404, "Not found")

        cfg = dict(row["config_json"] or {})
        cfg["enabled"] = not cfg.get("enabled", True)

        updated = await conn.fetchrow(
            """
            UPDATE installations SET config_json=$2::jsonb
            WHERE id=$1::uuid
            RETURNING id, platform, org, repo, config_json, created_at
            """,
            repo_id, cfg,
        )

    return _row_to_item(dict(updated))


@router.delete("/admin/settings/repos/{repo_id}", status_code=204)
async def delete_repo(repo_id: str) -> None:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM installations WHERE id = $1::uuid", repo_id
        )
    if result == "DELETE 0":
        raise HTTPException(404, "Not found")
