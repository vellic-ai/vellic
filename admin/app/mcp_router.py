import json
import logging
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import db
from .crypto import decrypt, encrypt

logger = logging.getLogger("admin.mcp")

router = APIRouter()


class MCPAttachBody(BaseModel):
    name: str
    url: str
    credentials: dict | None = None
    enabled: bool = True


class MCPPatchBody(BaseModel):
    enabled: bool | None = None
    url: str | None = None
    credentials: dict | None = None


def _row_to_item(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "installation_id": str(row["installation_id"]),
        "name": row["name"],
        "url": row["url"],
        "credentials_set": bool(row["credentials_enc"]),
        "enabled": row["enabled"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


@router.get("/admin/repos/{repo_id}/mcp")
async def list_mcp_servers(repo_id: str) -> dict:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        inst = await conn.fetchrow(
            "SELECT id FROM installations WHERE id = $1::uuid", repo_id
        )
        if inst is None:
            raise HTTPException(404, "Repository not found")
        rows = await conn.fetch(
            "SELECT id, installation_id, name, url, credentials_enc, enabled, created_at"
            " FROM mcp_servers WHERE installation_id = $1::uuid ORDER BY created_at ASC",
            uuid.UUID(repo_id),
        )
    return {"items": [_row_to_item(dict(r)) for r in rows]}


@router.post("/admin/repos/{repo_id}/mcp", status_code=201)
async def attach_mcp_server(repo_id: str, body: MCPAttachBody) -> dict:
    if not body.name.strip():
        raise HTTPException(422, "name is required")
    if not body.url.strip():
        raise HTTPException(422, "url is required")

    credentials_enc = None
    if body.credentials:
        credentials_enc = encrypt(json.dumps(body.credentials))

    pool = db.get_pool()
    async with pool.acquire() as conn:
        inst = await conn.fetchrow(
            "SELECT id FROM installations WHERE id = $1::uuid", repo_id
        )
        if inst is None:
            raise HTTPException(404, "Repository not found")

        existing = await conn.fetchrow(
            "SELECT id FROM mcp_servers WHERE installation_id = $1::uuid AND name = $2",
            uuid.UUID(repo_id),
            body.name,
        )
        if existing:
            raise HTTPException(409, f"MCP server {body.name!r} already attached to this repo")

        row = await conn.fetchrow(
            """
            INSERT INTO mcp_servers
                (installation_id, name, url, credentials_enc, enabled)
            VALUES ($1::uuid, $2, $3, $4, $5)
            RETURNING id, installation_id, name, url, credentials_enc, enabled, created_at
            """,
            uuid.UUID(repo_id),
            body.name,
            body.url,
            credentials_enc,
            body.enabled,
        )

    logger.info("mcp server attached repo=%s name=%s url=%s", repo_id, body.name, body.url)
    return _row_to_item(dict(row))


@router.patch("/admin/repos/{repo_id}/mcp/{server_id}")
async def update_mcp_server(repo_id: str, server_id: str, body: MCPPatchBody) -> dict:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, installation_id, name, url, credentials_enc, enabled, created_at"
            " FROM mcp_servers WHERE id = $1::uuid AND installation_id = $2::uuid",
            uuid.UUID(server_id),
            uuid.UUID(repo_id),
        )
        if row is None:
            raise HTTPException(404, "MCP server not found")

        new_url = body.url if body.url is not None else row["url"]
        new_enabled = body.enabled if body.enabled is not None else row["enabled"]
        new_creds_enc = row["credentials_enc"]
        if body.credentials is not None:
            new_creds_enc = encrypt(json.dumps(body.credentials))

        updated = await conn.fetchrow(
            """
            UPDATE mcp_servers
            SET url = $3, credentials_enc = $4, enabled = $5
            WHERE id = $1::uuid AND installation_id = $2::uuid
            RETURNING id, installation_id, name, url, credentials_enc, enabled, created_at
            """,
            uuid.UUID(server_id),
            uuid.UUID(repo_id),
            new_url,
            new_creds_enc,
            new_enabled,
        )

    logger.info("mcp server updated id=%s repo=%s", server_id, repo_id)
    return _row_to_item(dict(updated))


@router.delete("/admin/repos/{repo_id}/mcp/{server_id}", status_code=204)
async def detach_mcp_server(repo_id: str, server_id: str) -> None:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM mcp_servers WHERE id = $1::uuid AND installation_id = $2::uuid",
            uuid.UUID(server_id),
            uuid.UUID(repo_id),
        )
    if result == "DELETE 0":
        raise HTTPException(404, "MCP server not found")
    logger.info("mcp server detached id=%s repo=%s", server_id, repo_id)


async def load_mcp_configs_for_repo(pool, installation_id: uuid.UUID) -> list[dict]:
    """Return enabled MCP server configs (with decrypted credentials) for a repo."""
    rows = await pool.fetch(
        "SELECT id, name, url, credentials_enc FROM mcp_servers"
        " WHERE installation_id = $1 AND enabled = TRUE",
        installation_id,
    )
    result = []
    for r in rows:
        creds = None
        if r["credentials_enc"]:
            try:
                creds = json.loads(decrypt(r["credentials_enc"]))
            except Exception:
                logger.warning("failed to decrypt credentials for mcp server id=%s", r["id"])
        result.append({
            "id": str(r["id"]),
            "name": r["name"],
            "url": r["url"],
            "credentials": creds,
        })
    return result
