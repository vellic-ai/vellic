"""REST endpoints for the prompt library (VEL-114).

GET  /admin/prompts            — list all prompts (presets)
GET  /admin/prompts/{name}     — get single prompt
POST /admin/prompts/resolve    — resolve effective prompt for a PR (query: ?pr=<pr_review_id>)
POST /admin/prompts/dry-run    — render + run LLM without posting (body: DryRunBody)
"""

from __future__ import annotations

import json
import logging
import os
import re

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from . import db
from .crypto import decrypt
from .prompts.inheritance import cascade_merge, resolve_all
from .prompts.loader import load_all_presets, load_preset
from .prompts.models import PromptContext
from .prompts.renderer import build_resolved_prompt
from .prompts.schema import PromptValidationError

logger = logging.getLogger("admin.prompts")

router = APIRouter()

_GITHUB_API_BASE = "https://api.github.com"

# ---------------------------------------------------------------------------
# Pydantic output models
# ---------------------------------------------------------------------------


class FrontmatterOut(BaseModel):
    scope: list[str]
    triggers: list[str]
    priority: int
    inherits: str | None
    variables: dict[str, str]


class PromptOut(BaseModel):
    name: str
    source: str
    frontmatter: FrontmatterOut
    body: str


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


def _prompt_to_out(p) -> PromptOut:
    return PromptOut(
        name=p.name,
        source=p.source,
        frontmatter=FrontmatterOut(
            scope=p.frontmatter.scope,
            triggers=p.frontmatter.triggers,
            priority=p.frontmatter.priority,
            inherits=p.frontmatter.inherits,
            variables=p.frontmatter.variables,
        ),
        body=p.body,
    )


async def _fetch_pr_row(pr_review_id: str) -> dict | None:
    """Return a row with pr_reviews + webhook delivery payload, or None."""
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
    """Fetch PR file list from GitHub API; returns raw file dicts."""
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
    """Return (diff_text, changed_files) from a GitHub files response."""
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


@router.get("/admin/prompts")
async def list_prompts() -> dict:
    """List all available prompts (built-in presets)."""
    try:
        prompts = load_all_presets()
    except PromptValidationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"items": [_prompt_to_out(p).model_dump() for p in prompts]}


@router.get("/admin/prompts/{name}")
async def get_prompt(name: str) -> PromptOut:
    """Get a single prompt by name."""
    try:
        prompt = load_preset(name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"Prompt {name!r} not found") from exc
    return _prompt_to_out(prompt)


@router.post("/admin/prompts/resolve")
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


@router.post("/admin/prompts/dry-run")
async def dry_run_prompt(body: DryRunBody) -> DryRunOut:
    """Render prompt + run LLM for a stored PR without posting the review."""
    row = await _fetch_pr_row(body.pr_review_id)
    if row is None:
        raise HTTPException(
            status_code=404, detail=f"PR review {body.pr_review_id!r} not found"
        )

    # Build context — fetch diff from GitHub if token is available
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
