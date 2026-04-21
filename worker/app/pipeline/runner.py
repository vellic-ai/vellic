import logging
import uuid

import asyncpg

from ..context.ast.enricher import ASTEnricher
from ..events import PREvent
from ..llm.protocol import LLMProvider
from .context_gatherer import gather_context
from .diff_fetcher import fetch_diff_chunks
from .llm_analyzer import analyze
from .result_persister import persist

logger = logging.getLogger("worker.pipeline.runner")

_ast_enricher = ASTEnricher()


async def run_pipeline(
    event: PREvent,
    pool: asyncpg.Pool,
    llm: LLMProvider,
    job_id: uuid.UUID,
    arq_redis,
) -> str:
    # Stage 1: gather context
    context = gather_context(event)
    logger.info(
        "stage1 complete repo=%s pr=%d sha=%s", context.repo, context.pr_number, context.commit_sha
    )

    # Stage 2: fetch and chunk diff
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

    # Stage 3: LLM analysis
    result = await analyze(context, chunks, llm, ast_contexts=ast_contexts)
    logger.info(
        "stage3 complete comments=%d generic_ratio=%.2f",
        len(result.comments),
        result.generic_ratio,
    )

    # Stage 4: persist + enqueue
    pr_review_id = await persist(pool, context, result, job_id, arq_redis)
    logger.info("stage4 complete pr_review_id=%s", pr_review_id)
    return pr_review_id
