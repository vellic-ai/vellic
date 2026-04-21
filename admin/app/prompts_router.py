"""REST endpoints for the prompt library (VEL-114, VEL-134).

VEL-134: UI is source of truth. DB is primary; preset files are fallback/export.

GET    /admin/prompts              — list all prompts (DB + presets)
GET    /admin/prompts/export       — download DB prompts as .md zip
POST   /admin/prompts/import       — upload .md files → write to DB
POST   /admin/prompts              — create a new DB-only prompt
GET    /admin/prompts/{name}       — get single prompt
PUT    /admin/prompts/{name}       — save/update prompt body in DB
PATCH  /admin/prompts/{name}/enabled — toggle enabled/disabled
DELETE /admin/prompts/{name}       — delete DB entry (revert preset or remove DB-only)
POST   /admin/prompts/resolve      — resolve effective prompt for a PR
POST   /admin/prompts/dry-run      — render + run LLM without posting
"""

from __future__ import annotations

import io
import json
import logging
import os
import re
import zipfile

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from vellic_flags import by_key

from . import db
from .crypto import decrypt
from .prompts.inheritance import cascade_merge, resolve_all
from .prompts.loader import load_all_presets, load_preset
from .prompts.models import PromptContext
from .prompts.parser import parse_prompt_content
from .prompts.renderer import build_resolved_prompt
from .prompts.schema import PromptValidationError

logger = logging.getLogger("admin.prompts")

router = APIRouter()

_GLOBAL_REPO_ID = "__global__"
_GITHUB_API_BASE = "https://api.github.com"


def _require_prompt_dsl() -> None:
    flag = by_key("platform.prompt_dsl")
    enabled = (flag.read_env() if flag else None)
    if enabled is None:
        enabled = flag.default if flag else False
    if not enabled:
        raise HTTPException(status_code=404, detail="Prompt DSL feature is not enabled")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class FrontmatterOut(BaseModel):
    scope: list[str]
    triggers: list[str]
    priority: int
    inherits: str | None
    variables: dict[str, str]


class PromptOut(BaseModel):
    name: str
    source: str          # "preset" | "db" | "preset+db"
    frontmatter: FrontmatterOut
    body: str            # effective body (db_override if present, else preset)
    db_override: str | None = None
    enabled: bool = True


class PromptBody(BaseModel):
    body: str


class PromptCreate(BaseModel):
    name: str
    body: str


class PromptEnableBody(BaseModel):
    enabled: bool


class PromptDeleteOut(BaseModel):
    deleted: bool


class PromptList(BaseModel):
    items: list[PromptOut]


class ResolvedOut(BaseModel):
    body: str
    sources: list[str]


class DryRunBody(BaseModel):
    pr_review_id: str


class DryRunOut(BaseModel):
    rendered_prompt: str
    sources: list[str]
    analysis: dict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _preset_to_out(p, db_row: dict | None = None) -> PromptOut:
    fm = FrontmatterOut(
        scope=p.frontmatter.scope,
        triggers=p.frontmatter.triggers,
        priority=p.frontmatter.priority,
        inherits=p.frontmatter.inherits,
        variables=p.frontmatter.variables,
    )
    if db_row is not None:
        db_body: str = db_row["body"]
        enabled: bool = db_row.get("enabled", True)
        try:
            parsed = parse_prompt_content(db_body, name=p.name, path="", source="db")
            effective_fm = FrontmatterOut(
                scope=parsed.frontmatter.scope,
                triggers=parsed.frontmatter.triggers,
                priority=parsed.frontmatter.priority,
                inherits=parsed.frontmatter.inherits,
                variables=parsed.frontmatter.variables,
            )
        except Exception:
            effective_fm = fm
        return PromptOut(
            name=p.name,
            source="preset+db",
            frontmatter=effective_fm,
            body=db_body,
            db_override=db_body,
            enabled=enabled,
        )
    return PromptOut(name=p.name, source="preset", frontmatter=fm, body=p.body, enabled=True)


def _db_row_to_out(row: dict) -> PromptOut:
    body: str = row["body"]
    name: str = row["path"]
    enabled: bool = row.get("enabled", True)
    try:
        parsed = parse_prompt_content(body, name=name, path="", source="db")
        fm = FrontmatterOut(
            scope=parsed.frontmatter.scope,
            triggers=parsed.frontmatter.triggers,
            priority=parsed.frontmatter.priority,
            inherits=parsed.frontmatter.inherits,
            variables=parsed.frontmatter.variables,
        )
    except Exception:
        fm = FrontmatterOut(scope=[], triggers=[], priority=0, inherits=None, variables={})
    return PromptOut(
        name=name,
        source="db",
        frontmatter=fm,
        body=body,
        db_override=body,
        enabled=enabled,
    )


async def _fetch_pr_row(pr_review_id: str) -> dict | None:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT r.repo,
                   r.pr_number,
                   r.commit_sha,
                   d.payload
            FROM   pr_reviews r
            LEFT JOIN webhook_deliveries d
                   ON  (d.payload -> 'pull_request' -> 'head' ->> 'sha') = r.commit_sha
                   AND (d.payload -> 'repository' ->> 'full_name') = r.repo
                   AND (d.payload -> 'pull_request' ->> 'number')::int = r.pr_number
            WHERE  r.id = $1::uuid
            LIMIT  1
            """,
            pr_review_id,
        )
    return dict(row) if row else None


def _context_from_row(row: dict) -> PromptContext:
    payload = row.get("payload") or {}
    pr = payload.get("pull_request") or {}
    return PromptContext(
        repo=row["repo"],
        pr_title=pr.get("title", ""),
        pr_body=pr.get("body", "") or "",
        base_branch=(pr.get("base") or {}).get("ref", ""),
        labels=[lbl["name"] for lbl in pr.get("labels", []) if isinstance(lbl, dict)],
    )


async def _fetch_diff_chunks(repo: str, pr_number: int) -> list[dict]:
    token = os.getenv("GITHUB_TOKEN", "")
    url = f"{_GITHUB_API_BASE}/repos/{repo}/pulls/{pr_number}/files"
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        logger.warning("diff fetch failed for %s#%d: %s", repo, pr_number, exc)
        return []


def _build_diff_text(files: list[dict]) -> tuple[str, list[str]]:
    _SKIP_SUFFIXES = (".lock", "-lock.json", "-lock.yaml")
    _SKIP_SEGMENTS = ("dist/", "node_modules/", ".min.js", ".min.css", "vendor/", "generated/")

    parts: list[str] = []
    changed: list[str] = []
    total = 0
    max_chars = 40_000

    for f in files:
        filename = f.get("filename", "")
        patch = f.get("patch", "")
        if not patch:
            continue
        if any(filename.endswith(s) for s in _SKIP_SUFFIXES):
            continue
        if any(seg in filename for seg in _SKIP_SEGMENTS):
            continue

        changed.append(filename)
        segment = f"### {filename}\n```diff\n{patch}\n```\n"
        if total + len(segment) > max_chars:
            remaining = max_chars - total
            if remaining > 20:
                parts.append(segment[:remaining] + "\n[truncated]\n")
            break
        parts.append(segment)
        total += len(segment)

    return "".join(parts), changed


async def _load_llm_config() -> dict:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM llm_settings WHERE id = 1")
    if row is None:
        raise HTTPException(status_code=422, detail="LLM not configured")
    row = dict(row)
    api_key = decrypt(row["api_key"]) if row.get("api_key") else ""
    return {
        "provider": row["provider"],
        "base_url": row.get("base_url") or "",
        "model": row["model"],
        "api_key": api_key,
    }


def _extract_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    return {"summary": text[:500], "comments": [], "generic_ratio": 1.0}


async def _call_llm(cfg: dict, prompt: str) -> dict:
    provider = cfg["provider"]
    base_url = cfg["base_url"]
    model = cfg["model"]
    api_key = cfg["api_key"]

    try:
        if provider in ("ollama", "vllm"):
            url = (base_url.rstrip("/") or "http://ollama:11434") + "/api/generate"
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    url,
                    json={"model": model, "prompt": prompt, "stream": False,
                          "options": {"num_predict": 2048}},
                )
                resp.raise_for_status()
                raw = resp.json()["response"]

        elif provider == "openai":
            url = (base_url.rstrip("/") or "https://api.openai.com") + "/v1/chat/completions"
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={"model": model, "messages": [{"role": "user", "content": prompt}],
                          "max_tokens": 2048},
                )
                resp.raise_for_status()
                raw = resp.json()["choices"][0]["message"]["content"]

        elif provider == "anthropic":
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                    },
                    json={"model": model, "max_tokens": 2048,
                          "messages": [{"role": "user", "content": prompt}]},
                )
                resp.raise_for_status()
                raw = resp.json()["content"][0]["text"]

        else:
            raise HTTPException(
                status_code=422,
                detail=f"Provider {provider!r} not supported for dry-run",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("LLM call failed during dry-run: %s", exc)
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}") from exc

    return _extract_json(raw)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/admin/prompts", dependencies=[Depends(_require_prompt_dsl)])
async def list_prompts() -> PromptList:
    """List all prompts. DB entries are primary; presets fill in the rest."""
    try:
        presets = load_all_presets()
    except PromptValidationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    preset_names = {p.name for p in presets}

    pool = db.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT path, body, enabled, updated_at"
            " FROM prompt_overrides WHERE repo_id = $1 ORDER BY path",
            _GLOBAL_REPO_ID,
        )
    db_map: dict[str, dict] = {r["path"]: dict(r) for r in rows}

    items: list[PromptOut] = []
    for p in presets:
        items.append(_preset_to_out(p, db_map.get(p.name)))
    for name, row in db_map.items():
        if name not in preset_names:
            items.append(_db_row_to_out(row))

    return PromptList(items=items)


@router.get("/admin/prompts/export", dependencies=[Depends(_require_prompt_dsl)])
async def export_prompts() -> Response:
    """Download all DB prompts as a .md zip archive."""
    pool = db.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT path, body FROM prompt_overrides WHERE repo_id = $1 ORDER BY path",
            _GLOBAL_REPO_ID,
        )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for row in rows:
            zf.writestr(f"{row['path']}.md", row["body"])

    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="prompts.zip"'},
    )


@router.post("/admin/prompts/import", dependencies=[Depends(_require_prompt_dsl)])
async def import_prompts(
    files: list[UploadFile] = File(),  # noqa: B008
) -> dict:
    """Import .md prompt files into DB. Each file becomes a DB entry (upsert)."""
    pool = db.get_pool()
    imported: list[str] = []
    errors: list[str] = []

    for upload in files:
        filename = upload.filename or ""
        if not filename.endswith(".md"):
            errors.append(f"{filename}: not a .md file")
            continue
        name = filename.removesuffix(".md")
        if not name:
            errors.append(f"{filename}: empty name")
            continue

        content = (await upload.read()).decode("utf-8", errors="replace")
        try:
            parse_prompt_content(content, name=name, path="", source="db")
        except Exception as exc:
            errors.append(f"{name}: parse error — {exc}")
            continue

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO prompt_overrides (repo_id, path, body, enabled)
                VALUES ($1, $2, $3, TRUE)
                ON CONFLICT (repo_id, path) DO UPDATE
                    SET body = EXCLUDED.body, updated_at = NOW()
                """,
                _GLOBAL_REPO_ID,
                name,
                content,
            )
        imported.append(name)

    return {"imported": imported, "errors": errors}


@router.post("/admin/prompts", dependencies=[Depends(_require_prompt_dsl)])
async def create_prompt(body: PromptCreate) -> PromptOut:
    """Create a new DB-only prompt. Fails if a DB entry already exists for that name."""
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="name is required")

    pool = db.get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT path FROM prompt_overrides WHERE repo_id = $1 AND path = $2",
            _GLOBAL_REPO_ID,
            name,
        )
        if existing:
            raise HTTPException(
                status_code=409, detail=f"Prompt {name!r} already exists in DB"
            )
        try:
            parse_prompt_content(body.body, name=name, path="", source="db")
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Invalid prompt content: {exc}") from exc

        row = await conn.fetchrow(
            """
            INSERT INTO prompt_overrides (repo_id, path, body, enabled)
            VALUES ($1, $2, $3, TRUE)
            RETURNING path, body, enabled, updated_at
            """,
            _GLOBAL_REPO_ID,
            name,
            body.body,
        )
    return _db_row_to_out(dict(row))


@router.get("/admin/prompts/{name}", dependencies=[Depends(_require_prompt_dsl)])
async def get_prompt(name: str) -> PromptOut:
    """Get a single prompt by name (DB state + preset fallback)."""
    pool = db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT path, body, enabled, updated_at"
            " FROM prompt_overrides WHERE repo_id = $1 AND path = $2",
            _GLOBAL_REPO_ID,
            name,
        )
    db_row = dict(row) if row else None

    try:
        preset = load_preset(name)
        return _preset_to_out(preset, db_row)
    except ValueError:
        pass

    if db_row:
        return _db_row_to_out(db_row)

    raise HTTPException(status_code=404, detail=f"Prompt {name!r} not found")


@router.put("/admin/prompts/{name}", dependencies=[Depends(_require_prompt_dsl)])
async def save_prompt(name: str, body: PromptBody) -> PromptOut:
    """Save (upsert) prompt body in DB. Works for both preset overrides and DB-only prompts."""
    try:
        parse_prompt_content(body.body, name=name, path="", source="db")
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid prompt content: {exc}") from exc

    pool = db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO prompt_overrides (repo_id, path, body, enabled)
            VALUES ($1, $2, $3, TRUE)
            ON CONFLICT (repo_id, path) DO UPDATE
                SET body = EXCLUDED.body, updated_at = NOW()
            RETURNING path, body, enabled, updated_at
            """,
            _GLOBAL_REPO_ID,
            name,
            body.body,
        )

    db_row = dict(row)
    try:
        preset = load_preset(name)
        return _preset_to_out(preset, db_row)
    except ValueError:
        return _db_row_to_out(db_row)


@router.patch("/admin/prompts/{name}/enabled", dependencies=[Depends(_require_prompt_dsl)])
async def set_prompt_enabled(name: str, body: PromptEnableBody) -> PromptOut:
    """Enable or disable a prompt. Creates a DB entry if needed (for presets)."""
    pool = db.get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT path, body FROM prompt_overrides WHERE repo_id = $1 AND path = $2",
            _GLOBAL_REPO_ID,
            name,
        )
        if existing is None:
            try:
                preset = load_preset(name)
                seed_body = preset.body
            except ValueError as exc:
                raise HTTPException(status_code=404, detail=f"Prompt {name!r} not found") from exc
            row = await conn.fetchrow(
                """
                INSERT INTO prompt_overrides (repo_id, path, body, enabled)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (repo_id, path) DO UPDATE
                    SET enabled = EXCLUDED.enabled, updated_at = NOW()
                RETURNING path, body, enabled, updated_at
                """,
                _GLOBAL_REPO_ID,
                name,
                seed_body,
                body.enabled,
            )
        else:
            row = await conn.fetchrow(
                """
                UPDATE prompt_overrides SET enabled = $1, updated_at = NOW()
                WHERE repo_id = $2 AND path = $3
                RETURNING path, body, enabled, updated_at
                """,
                body.enabled,
                _GLOBAL_REPO_ID,
                name,
            )

    db_row = dict(row)
    try:
        preset = load_preset(name)
        return _preset_to_out(preset, db_row)
    except ValueError:
        return _db_row_to_out(db_row)


@router.delete("/admin/prompts/{name}", dependencies=[Depends(_require_prompt_dsl)])
async def delete_prompt(name: str) -> PromptDeleteOut:
    """Delete the DB entry for a prompt. Presets revert to file default; DB-only prompts removed."""
    pool = db.get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM prompt_overrides WHERE repo_id = $1 AND path = $2",
            _GLOBAL_REPO_ID,
            name,
        )
    return PromptDeleteOut(deleted=result != "DELETE 0")


@router.post("/admin/prompts/resolve", dependencies=[Depends(_require_prompt_dsl)])
async def resolve_prompt(
    pr: str = Query(..., description="pr_review_id UUID"),
) -> ResolvedOut:
    """Resolve the effective rendered prompt for a stored PR review."""
    row = await _fetch_pr_row(pr)
    if row is None:
        raise HTTPException(status_code=404, detail=f"PR review {pr!r} not found")

    ctx = _context_from_row(row)

    try:
        prompts = load_all_presets()
    except PromptValidationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    resolved = resolve_all(prompts)
    merged = cascade_merge(resolved)
    result = build_resolved_prompt(merged, ctx)
    return ResolvedOut(body=result.body, sources=result.sources)


@router.post("/admin/prompts/dry-run", dependencies=[Depends(_require_prompt_dsl)])
async def dry_run_prompt(body: DryRunBody) -> DryRunOut:
    """Render prompt + run LLM for a stored PR without posting the review."""
    row = await _fetch_pr_row(body.pr_review_id)
    if row is None:
        raise HTTPException(
            status_code=404, detail=f"PR review {body.pr_review_id!r} not found"
        )

    ctx = _context_from_row(row)
    files = await _fetch_diff_chunks(row["repo"], row["pr_number"])
    if files:
        diff_text, changed_files = _build_diff_text(files)
        ctx.diff = diff_text
        ctx.changed_files = changed_files

    try:
        prompts = load_all_presets()
    except PromptValidationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    resolved = resolve_all(prompts)
    merged = cascade_merge(resolved)
    rendered = build_resolved_prompt(merged, ctx)

    llm_cfg = await _load_llm_config()
    analysis = await _call_llm(llm_cfg, rendered.body)

    return DryRunOut(
        rendered_prompt=rendered.body,
        sources=rendered.sources,
        analysis=analysis,
    )
