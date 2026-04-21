import json
import logging
import os
import tempfile
import uuid

import asyncpg
from vellic_flags import by_key

from ..context.ast.enricher import ASTEnricher
from ..crypto import decrypt
from ..events import PREvent
from ..llm.protocol import LLMProvider
from ..mcp_host import get_manager
from ..prompts.inheritance import cascade_merge, resolve_all
from ..prompts.models import PromptContext
from ..prompts.renderer import build_resolved_prompt
from ..prompts.repo_loader import load_repo_prompts
from ..rules import evaluate_rules, load_repo_config
from .context_gatherer import gather_context
from .diff_fetcher import fetch_diff_chunks
from .llm_analyzer import analyze
from .models import AnalysisResult, ReviewComment
from .result_persister import persist

logger = logging.getLogger("worker.pipeline.runner")

_ast_enricher = ASTEnricher()
_MCP_TIMEOUT_S = float(os.environ.get("MCP_PROCESS_TIMEOUT", "300"))


def _flag_enabled(key: str) -> bool:
    flag = by_key(key)
    if flag is None:
        return False
    env = flag.read_env()
    return env if env is not None else flag.default


def _merge_rule_violations(result: AnalysisResult, violations: list) -> AnalysisResult:
    """Append rule violations as ReviewComments with confidence=1.0 (deterministic)."""
    if not violations:
        return result
    extra = [
        ReviewComment(
            file=v.file,
            line=v.line,
            body=f"[{v.severity.upper()}] {v.description}: `{v.matched_text}`",
            confidence=1.0,
            rationale=f"Matched rule '{v.rule_id}'",
        )
        for v in violations
    ]
    return AnalysisResult(
        comments=result.comments + extra,
        summary=result.summary,
        generic_ratio=result.generic_ratio,
    )


async def _spawn_mcp_servers(
    run_id: str,
    pool: asyncpg.Pool,
    installation_id: uuid.UUID,
    workspace_dir: str,
) -> None:
    """Load enabled MCP configs for a repo and spawn processes."""
    rows = await pool.fetch(
        "SELECT id, name, url, credentials_enc FROM mcp_servers"
        " WHERE installation_id = $1 AND enabled = TRUE",
        installation_id,
    )
    if not rows:
        return

    manager = get_manager()
    for row in rows:
        creds: dict | None = None
        if row["credentials_enc"]:
            try:
                creds = json.loads(decrypt(row["credentials_enc"]))
            except Exception:
                logger.warning(
                    "failed to decrypt mcp credentials server_id=%s — spawning without creds",
                    row["id"],
                )
        await manager.spawn(
            run_id=run_id,
            server_id=str(row["id"]),
            name=row["name"],
            url=row["url"],
            workspace_dir=workspace_dir,
            credentials=creds,
            timeout_s=_MCP_TIMEOUT_S,
        )
    logger.info("spawned %d mcp server(s) for run_id=%s", len(rows), run_id)


async def run_pipeline(
    event: PREvent,
    pool: asyncpg.Pool,
    llm: LLMProvider,
    job_id: uuid.UUID,
    arq_redis,
    installation_id: uuid.UUID | None = None,
) -> str:
    run_id = str(job_id)

    with tempfile.TemporaryDirectory(prefix="vellic-mcp-") as workspace_dir:
        if installation_id is not None:
            try:
                await _spawn_mcp_servers(run_id, pool, installation_id, workspace_dir)
            except Exception as exc:
                logger.warning("mcp spawn error (non-fatal): %s", exc)

        try:
            # Stage 1: gather context
            context = gather_context(event)
            logger.info(
                "stage1 complete repo=%s pr=%d sha=%s",
                context.repo,
                context.pr_number,
                context.commit_sha,
            )

            # Stage 2: fetch and chunk diff
            if not _flag_enabled("pipeline.diff"):
                logger.info("pipeline.diff disabled — skipping diff fetch; aborting pipeline")
                return ""
            chunks = await fetch_diff_chunks(event.diff_url)
            logger.info("stage2 complete chunks=%d", len(chunks))

            # Stage 2b: AST enrichment (best-effort; failures are non-fatal)
            ast_contexts: dict | None = None
            try:
                ast_contexts = _ast_enricher.enrich_all(chunks)
                enriched = sum(1 for c in ast_contexts.values() if c.symbols)
                logger.info("stage2b complete ast_enriched=%d/%d", enriched, len(chunks))
            except Exception as exc:  # pragma: no cover
                logger.warning("AST enrichment failed (non-fatal): %s", exc)

            # Stage 2c: load repo-specific rules
            repo_config = await load_repo_config(pool, context.repo)
            logger.info("stage2c complete rules=%d repo=%s", len(repo_config.rules), context.repo)

            # Stage 2d: load DSL prompts (gated by platform.prompt_dsl flag)
            custom_instructions: str | None = None
            if _flag_enabled("platform.prompt_dsl"):
                async with pool.acquire() as conn:
                    dsl_prompts = await load_repo_prompts("", context.repo, conn)
                if dsl_prompts:
                    prompt_ctx = PromptContext(
                        repo=context.repo,
                        pr_title=context.title,
                        pr_body=context.body,
                        base_branch=context.base_branch,
                    )
                    resolved = resolve_all(dsl_prompts)
                    merged = cascade_merge(resolved)
                    rendered = build_resolved_prompt(merged, prompt_ctx)
                    custom_instructions = rendered.body
                    logger.info(
                        "stage2d complete dsl_prompts=%d sources=%s",
                        len(dsl_prompts),
                        rendered.sources,
                    )
                else:
                    logger.debug(
                        "stage2d: platform.prompt_dsl enabled but no prompts found for repo=%s",
                        context.repo,
                    )

            # Stage 3: LLM analysis
            if not _flag_enabled("pipeline.llm_analysis"):
                logger.info("pipeline.llm_analysis disabled — skipping LLM pass")
                return ""
            result = await analyze(context, chunks, llm, custom_instructions=custom_instructions)
            logger.info(
                "stage3 complete comments=%d generic_ratio=%.2f",
                len(result.comments),
                result.generic_ratio,
            )

            # Stage 3b: apply deterministic YAML rules
            violations = evaluate_rules(repo_config, chunks)
            if violations:
                logger.info("stage3b complete violations=%d repo=%s", len(violations), context.repo)
                result = _merge_rule_violations(result, violations)

            # Stage 4: persist + enqueue
            pr_review_id = await persist(pool, context, result, job_id, arq_redis)
            logger.info("stage4 complete pr_review_id=%s", pr_review_id)
            return pr_review_id
        finally:
            if installation_id is not None:
                try:
                    await get_manager().kill_run(run_id)
                except Exception as exc:
                    logger.warning("mcp kill_run error: %s", exc)
