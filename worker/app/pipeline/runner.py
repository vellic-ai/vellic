import logging
import uuid

import asyncpg
from vellic_flags import by_key

from ..context.ast.enricher import ASTEnricher
from ..events import PREvent
from ..llm.protocol import LLMProvider
from ..rules import evaluate_rules, load_repo_config
from .context_gatherer import gather_context
from .diff_fetcher import fetch_diff_chunks
from .llm_analyzer import analyze
from .models import AnalysisResult, ReviewComment
from .result_persister import persist

logger = logging.getLogger("worker.pipeline.runner")

_ast_enricher = ASTEnricher()


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

    # Stage 3: LLM analysis
    if not _flag_enabled("pipeline.llm_analysis"):
        logger.info("pipeline.llm_analysis disabled — skipping LLM pass")
        return ""
    result = await analyze(context, chunks, llm)
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
