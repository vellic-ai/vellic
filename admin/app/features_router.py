import logging
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("admin.features")

router = APIRouter()

# ---------------------------------------------------------------------------
# Flag catalog — defaults + metadata
# Keys follow "category.name" convention so the frontend can group them.
# ENV override: VELLIC_FEATURE_<UPPER_KEY_WITH_DOTS_AS_UNDERSCORES>=true|false
# ---------------------------------------------------------------------------

_CATALOG: list[dict[str, Any]] = [
    # VCS adapters
    {"key": "vcs.github",           "name": "GitHub",            "category": "vcs",      "default": True,  "description": "GitHub PR webhooks and review comments"},
    {"key": "vcs.gitlab",           "name": "GitLab",            "category": "vcs",      "default": True,  "description": "GitLab MR webhooks and review comments"},
    {"key": "vcs.bitbucket",        "name": "Bitbucket",         "category": "vcs",      "default": False, "description": "Bitbucket Cloud PR webhooks (alpha)"},
    {"key": "vcs.gitea",            "name": "Gitea",             "category": "vcs",      "default": False, "description": "Gitea PR webhooks (alpha)"},
    # LLM providers
    {"key": "llm.openai",           "name": "OpenAI",            "category": "llm",      "default": True,  "description": "OpenAI-compatible API (GPT-4, etc.)"},
    {"key": "llm.anthropic",        "name": "Anthropic",         "category": "llm",      "default": True,  "description": "Anthropic Claude via API key"},
    {"key": "llm.ollama",           "name": "Ollama",            "category": "llm",      "default": True,  "description": "Self-hosted Ollama server"},
    {"key": "llm.vllm",             "name": "vLLM",              "category": "llm",      "default": False, "description": "Self-hosted vLLM inference server"},
    # Pipeline stages
    {"key": "pipeline.diff",        "name": "Diff fetcher",      "category": "pipeline", "default": True,  "description": "Fetch PR diff for analysis"},
    {"key": "pipeline.context",     "name": "Context gathering", "category": "pipeline", "default": True,  "description": "AST + vector semantic context"},
    {"key": "pipeline.llm_analysis","name": "LLM analysis",      "category": "pipeline", "default": True,  "description": "Core code-review LLM pass"},
    {"key": "pipeline.security_scan","name": "Security scan",    "category": "pipeline", "default": False, "description": "SAST and secret detection pass"},
    {"key": "pipeline.coverage_hints","name": "Coverage hints",  "category": "pipeline", "default": False, "description": "Test coverage gap suggestions"},
    {"key": "pipeline.issue_triage","name": "Issue triage",      "category": "pipeline", "default": False, "description": "Auto-label and prioritise issues"},
    {"key": "pipeline.commit_summary","name": "Commit summary",  "category": "pipeline", "default": False, "description": "One-line commit message generator"},
    {"key": "pipeline.changelog",   "name": "Changelog",         "category": "pipeline", "default": False, "description": "Auto-generate CHANGELOG entries"},
    {"key": "pipeline.notifier_slack","name": "Slack notifier",  "category": "pipeline", "default": False, "description": "Post review summaries to Slack"},
    {"key": "pipeline.notifier_teams","name": "Teams notifier",  "category": "pipeline", "default": False, "description": "Post review summaries to MS Teams"},
    # AST providers
    {"key": "ast.python",           "name": "Python AST",        "category": "ast",      "default": True,  "description": "Python tree-sitter AST context"},
    {"key": "ast.typescript",       "name": "TypeScript AST",    "category": "ast",      "default": True,  "description": "TypeScript/JavaScript AST context"},
    {"key": "ast.go",               "name": "Go AST",            "category": "ast",      "default": False, "description": "Go AST context"},
    {"key": "ast.rust",             "name": "Rust AST",          "category": "ast",      "default": False, "description": "Rust AST context"},
    # Vector stores
    {"key": "vector.qdrant",        "name": "Qdrant",            "category": "vector",   "default": False, "description": "Qdrant vector store"},
    {"key": "vector.weaviate",      "name": "Weaviate",          "category": "vector",   "default": False, "description": "Weaviate vector store"},
    {"key": "vector.pgvector",      "name": "pgvector",          "category": "vector",   "default": False, "description": "PostgreSQL pgvector extension"},
    {"key": "vector.chroma",        "name": "Chroma",            "category": "vector",   "default": False, "description": "Chroma vector store"},
    # Platform
    {"key": "platform.multi_tenant","name": "Multi-tenant",      "category": "platform", "default": False, "description": "Multi-organisation isolation"},
    {"key": "platform.metrics_export","name": "Metrics export",  "category": "platform", "default": False, "description": "Prometheus / OpenTelemetry metrics"},
    {"key": "platform.tracing_export","name": "Tracing export",  "category": "platform", "default": False, "description": "OpenTelemetry distributed tracing"},
    {"key": "platform.prompt_dsl",  "name": "Prompt DSL",        "category": "platform", "default": False, "description": "Custom prompt rules DSL (VEL-91)"},
]

# In-memory runtime overrides (reset on restart; DB persistence added later)
_overrides: dict[str, bool] = {}


def _env_key(flag_key: str) -> str:
    return "VELLIC_FEATURE_" + flag_key.upper().replace(".", "_")


def _resolve(flag: dict[str, Any]) -> bool:
    """Return effective enabled state: override > ENV > default."""
    if flag["key"] in _overrides:
        return _overrides[flag["key"]]
    env = os.getenv(_env_key(flag["key"]))
    if env is not None:
        return env.lower() in ("1", "true", "yes")
    return flag["default"]


def _snapshot() -> dict[str, Any]:
    flags: dict[str, bool] = {f["key"]: _resolve(f) for f in _CATALOG}
    return {
        "flags": flags,
        "catalog": [
            {
                "key": f["key"],
                "name": f["name"],
                "category": f["category"],
                "description": f["description"],
                "enabled": flags[f["key"]],
                "default": f["default"],
            }
            for f in _CATALOG
        ],
        "snapshot_at": datetime.now(timezone.utc).isoformat(),
    }


class FeatureToggle(BaseModel):
    enabled: bool


@router.get("/admin/features")
async def get_features() -> dict:
    return _snapshot()


@router.put("/admin/features/{flag_key:path}", status_code=200)
async def put_feature(flag_key: str, body: FeatureToggle) -> dict:
    if not any(f["key"] == flag_key for f in _CATALOG):
        raise HTTPException(status_code=404, detail=f"Unknown feature flag: {flag_key!r}")
    _overrides[flag_key] = body.enabled
    logger.info("feature flag override: %s = %s", flag_key, body.enabled)
    return {"key": flag_key, "enabled": body.enabled}
