"""
vellic_flags — typed flag catalog (code-first definitions).

Single source of truth for feature flags across api, worker, and admin.
Each flag is a FlagDef dataclass; the CATALOG list is authoritative.

Scope levels (most-specific wins during resolution):
    global → tenant → repo → user

ENV override convention:
    VELLIC_FEATURE_<KEY_UPPER_UNDERSCORED>=true|false
    e.g. VELLIC_FEATURE_VCS_GITHUB=false
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

__all__ = [
    "CostImpact",
    "FlagCategory",
    "FlagScope",
    "FlagDef",
    "CATALOG",
    "by_key",
    "env_var",
    "ScopeContext",
    "FlagResolver",
]


class FlagCategory(str, Enum):
    VCS = "vcs"
    LLM = "llm"
    PIPELINE = "pipeline"
    AST = "ast"
    VECTOR = "vector"
    PLATFORM = "platform"


class FlagScope(str, Enum):
    """Finest scope at which this flag can be overridden."""
    GLOBAL = "global"
    TENANT = "tenant"
    REPO = "repo"
    USER = "user"


class CostImpact(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class FlagDef:
    """Immutable descriptor for a single feature flag."""

    key: str
    """Dot-notation identifier, e.g. ``vcs.github``."""

    name: str
    """Human-readable display name."""

    category: FlagCategory
    """Grouping category for UI and catalog endpoints."""

    description: str
    """One-line explanation shown in the settings UI and docs."""

    default: bool
    """Baseline enabled state before any overrides are applied."""

    scope: FlagScope = FlagScope.GLOBAL
    """Finest granularity at which this flag may be overridden."""

    cost_impact: CostImpact = CostImpact.NONE
    """Estimated cost/latency impact when enabled (shown in settings UI)."""

    requires: tuple[str, ...] = field(default_factory=tuple)
    """Keys of flags that must be enabled for this flag to function."""

    tags: tuple[str, ...] = field(default_factory=tuple)
    """Optional free-form labels for filtering/search."""

    def env_var(self) -> str:
        """Return the ENV variable name that can override this flag."""
        return "VELLIC_FEATURE_" + self.key.upper().replace(".", "_")

    def read_env(self) -> bool | None:
        """Return parsed ENV override, or None if not set."""
        raw = os.getenv(self.env_var())
        if raw is None:
            return None
        return raw.lower() in ("1", "true", "yes")


# ---------------------------------------------------------------------------
# Authoritative flag catalog
# ---------------------------------------------------------------------------

CATALOG: list[FlagDef] = [
    # ------------------------------------------------------------------
    # VCS adapters
    # ------------------------------------------------------------------
    FlagDef(
        key="vcs.github",
        name="GitHub",
        category=FlagCategory.VCS,
        description="GitHub PR webhooks and review comments",
        default=True,
        scope=FlagScope.REPO,
        tags=("vcs", "webhook"),
    ),
    FlagDef(
        key="vcs.gitlab",
        name="GitLab",
        category=FlagCategory.VCS,
        description="GitLab MR webhooks and review comments",
        default=True,
        scope=FlagScope.REPO,
        tags=("vcs", "webhook"),
    ),
    FlagDef(
        key="vcs.bitbucket",
        name="Bitbucket",
        category=FlagCategory.VCS,
        description="Bitbucket Cloud PR webhooks (alpha)",
        default=False,
        scope=FlagScope.REPO,
        tags=("vcs", "webhook", "alpha"),
    ),
    FlagDef(
        key="vcs.gitea",
        name="Gitea",
        category=FlagCategory.VCS,
        description="Gitea PR webhooks (alpha)",
        default=False,
        scope=FlagScope.REPO,
        tags=("vcs", "webhook", "alpha"),
    ),
    # ------------------------------------------------------------------
    # LLM providers
    # ------------------------------------------------------------------
    FlagDef(
        key="llm.openai",
        name="OpenAI",
        category=FlagCategory.LLM,
        description="OpenAI-compatible API (GPT-4, etc.)",
        default=True,
        scope=FlagScope.TENANT,
        cost_impact=CostImpact.HIGH,
        tags=("llm", "provider"),
    ),
    FlagDef(
        key="llm.anthropic",
        name="Anthropic",
        category=FlagCategory.LLM,
        description="Anthropic Claude via API key",
        default=True,
        scope=FlagScope.TENANT,
        cost_impact=CostImpact.HIGH,
        tags=("llm", "provider"),
    ),
    FlagDef(
        key="llm.ollama",
        name="Ollama",
        category=FlagCategory.LLM,
        description="Self-hosted Ollama inference server",
        default=True,
        scope=FlagScope.TENANT,
        cost_impact=CostImpact.LOW,
        tags=("llm", "provider", "self-hosted"),
    ),
    FlagDef(
        key="llm.vllm",
        name="vLLM",
        category=FlagCategory.LLM,
        description="Self-hosted vLLM inference server",
        default=False,
        scope=FlagScope.TENANT,
        cost_impact=CostImpact.LOW,
        tags=("llm", "provider", "self-hosted"),
    ),
    # ------------------------------------------------------------------
    # Pipeline stages
    # ------------------------------------------------------------------
    FlagDef(
        key="pipeline.diff",
        name="Diff fetcher",
        category=FlagCategory.PIPELINE,
        description="Fetch PR diff for analysis",
        default=True,
        scope=FlagScope.REPO,
        cost_impact=CostImpact.NONE,
        tags=("pipeline", "core"),
    ),
    FlagDef(
        key="pipeline.context",
        name="Context gathering",
        category=FlagCategory.PIPELINE,
        description="AST + vector semantic context enrichment",
        default=True,
        scope=FlagScope.REPO,
        cost_impact=CostImpact.LOW,
        tags=("pipeline", "context"),
    ),
    FlagDef(
        key="pipeline.llm_analysis",
        name="LLM analysis",
        category=FlagCategory.PIPELINE,
        description="Core code-review LLM pass",
        default=True,
        scope=FlagScope.REPO,
        cost_impact=CostImpact.HIGH,
        tags=("pipeline", "core"),
    ),
    FlagDef(
        key="pipeline.security_scan",
        name="Security scan",
        category=FlagCategory.PIPELINE,
        description="SAST and secret detection pass",
        default=False,
        scope=FlagScope.REPO,
        cost_impact=CostImpact.MEDIUM,
        tags=("pipeline", "security"),
    ),
    FlagDef(
        key="pipeline.coverage_hints",
        name="Coverage hints",
        category=FlagCategory.PIPELINE,
        description="Test coverage gap suggestions",
        default=False,
        scope=FlagScope.REPO,
        cost_impact=CostImpact.MEDIUM,
        tags=("pipeline", "quality"),
    ),
    FlagDef(
        key="pipeline.issue_triage",
        name="Issue triage",
        category=FlagCategory.PIPELINE,
        description="Auto-label and prioritise linked issues",
        default=False,
        scope=FlagScope.REPO,
        cost_impact=CostImpact.LOW,
        tags=("pipeline", "triage"),
    ),
    FlagDef(
        key="pipeline.commit_summary",
        name="Commit summary",
        category=FlagCategory.PIPELINE,
        description="One-line commit message generator",
        default=False,
        scope=FlagScope.REPO,
        cost_impact=CostImpact.LOW,
        tags=("pipeline", "summary"),
    ),
    FlagDef(
        key="pipeline.changelog",
        name="Changelog",
        category=FlagCategory.PIPELINE,
        description="Auto-generate CHANGELOG entries",
        default=False,
        scope=FlagScope.REPO,
        cost_impact=CostImpact.LOW,
        tags=("pipeline", "docs"),
    ),
    FlagDef(
        key="pipeline.notifier_slack",
        name="Slack notifier",
        category=FlagCategory.PIPELINE,
        description="Post review summaries to Slack",
        default=False,
        scope=FlagScope.TENANT,
        cost_impact=CostImpact.NONE,
        tags=("pipeline", "notifier", "slack"),
    ),
    FlagDef(
        key="pipeline.notifier_teams",
        name="Teams notifier",
        category=FlagCategory.PIPELINE,
        description="Post review summaries to MS Teams",
        default=False,
        scope=FlagScope.TENANT,
        cost_impact=CostImpact.NONE,
        tags=("pipeline", "notifier", "teams"),
    ),
    # ------------------------------------------------------------------
    # AST providers (per-language)
    # ------------------------------------------------------------------
    FlagDef(
        key="ast.python",
        name="Python AST",
        category=FlagCategory.AST,
        description="Python tree-sitter AST context",
        default=True,
        scope=FlagScope.REPO,
        cost_impact=CostImpact.LOW,
        requires=("pipeline.context",),
        tags=("ast", "python"),
    ),
    FlagDef(
        key="ast.typescript",
        name="TypeScript AST",
        category=FlagCategory.AST,
        description="TypeScript/JavaScript tree-sitter AST context",
        default=True,
        scope=FlagScope.REPO,
        cost_impact=CostImpact.LOW,
        requires=("pipeline.context",),
        tags=("ast", "typescript", "javascript"),
    ),
    FlagDef(
        key="ast.go",
        name="Go AST",
        category=FlagCategory.AST,
        description="Go tree-sitter AST context",
        default=False,
        scope=FlagScope.REPO,
        cost_impact=CostImpact.LOW,
        requires=("pipeline.context",),
        tags=("ast", "go"),
    ),
    FlagDef(
        key="ast.rust",
        name="Rust AST",
        category=FlagCategory.AST,
        description="Rust tree-sitter AST context",
        default=False,
        scope=FlagScope.REPO,
        cost_impact=CostImpact.LOW,
        requires=("pipeline.context",),
        tags=("ast", "rust"),
    ),
    # ------------------------------------------------------------------
    # Vector store providers
    # ------------------------------------------------------------------
    FlagDef(
        key="vector.qdrant",
        name="Qdrant",
        category=FlagCategory.VECTOR,
        description="Qdrant vector store for semantic search",
        default=False,
        scope=FlagScope.TENANT,
        cost_impact=CostImpact.LOW,
        requires=("pipeline.context",),
        tags=("vector", "store"),
    ),
    FlagDef(
        key="vector.weaviate",
        name="Weaviate",
        category=FlagCategory.VECTOR,
        description="Weaviate vector store",
        default=False,
        scope=FlagScope.TENANT,
        cost_impact=CostImpact.LOW,
        requires=("pipeline.context",),
        tags=("vector", "store"),
    ),
    FlagDef(
        key="vector.pgvector",
        name="pgvector",
        category=FlagCategory.VECTOR,
        description="PostgreSQL pgvector extension",
        default=False,
        scope=FlagScope.TENANT,
        cost_impact=CostImpact.LOW,
        requires=("pipeline.context",),
        tags=("vector", "store", "postgres"),
    ),
    FlagDef(
        key="vector.chroma",
        name="Chroma",
        category=FlagCategory.VECTOR,
        description="Chroma vector store",
        default=False,
        scope=FlagScope.TENANT,
        cost_impact=CostImpact.LOW,
        requires=("pipeline.context",),
        tags=("vector", "store"),
    ),
    # ------------------------------------------------------------------
    # Platform-wide flags
    # ------------------------------------------------------------------
    FlagDef(
        key="platform.multi_tenant",
        name="Multi-tenant",
        category=FlagCategory.PLATFORM,
        description="Multi-organisation isolation mode",
        default=False,
        scope=FlagScope.GLOBAL,
        cost_impact=CostImpact.NONE,
        tags=("platform", "infra"),
    ),
    FlagDef(
        key="platform.metrics_export",
        name="Metrics export",
        category=FlagCategory.PLATFORM,
        description="Prometheus / OpenTelemetry metrics export",
        default=False,
        scope=FlagScope.GLOBAL,
        cost_impact=CostImpact.LOW,
        tags=("platform", "observability"),
    ),
    FlagDef(
        key="platform.tracing_export",
        name="Tracing export",
        category=FlagCategory.PLATFORM,
        description="OpenTelemetry distributed tracing export",
        default=False,
        scope=FlagScope.GLOBAL,
        cost_impact=CostImpact.LOW,
        tags=("platform", "observability"),
    ),
    FlagDef(
        key="platform.prompt_dsl",
        name="Prompt DSL",
        category=FlagCategory.PLATFORM,
        description="Custom prompt rules DSL (see VEL-91)",
        default=True,
        scope=FlagScope.REPO,
        cost_impact=CostImpact.NONE,
        tags=("platform", "prompts"),
    ),
    FlagDef(
        key="platform.vcs_settings",
        name="VCS adapter settings UI",
        category=FlagCategory.PLATFORM,
        description="Show GitHub App + GitLab token configuration tab in admin settings",
        default=True,
        scope=FlagScope.GLOBAL,
        cost_impact=CostImpact.NONE,
        tags=("platform", "admin", "vcs"),
    ),
    FlagDef(
        key="plugins.enabled",
        name="Plugin Loader",
        category=FlagCategory.PLATFORM,
        description="Enable plugin loader: upload zips, register tools per repo (VEL-123)",
        default=False,
        scope=FlagScope.REPO,
        cost_impact=CostImpact.NONE,
        tags=("platform", "plugins"),
    ),
    FlagDef(
        key="platform.llm_config_ui",
        name="LLM config UI",
        category=FlagCategory.PLATFORM,
        description="DB-backed LLM provider config per repo with UI form (VEL-133)",
        default=False,
        scope=FlagScope.REPO,
        cost_impact=CostImpact.NONE,
        tags=("platform", "llm", "config"),
    ),
]

# ---------------------------------------------------------------------------
# Scope context and resolver
# ---------------------------------------------------------------------------

@dataclass
class ScopeContext:
    """Carries the runtime scope identifiers used for override resolution."""
    tenant_id: str | None = None
    repo_id: str | None = None
    user_id: str | None = None


class FlagResolver:
    """Resolves flag values from ENV overrides and a store snapshot."""

    def __init__(self, store: object = None) -> None:
        self._store = store

    def resolve(self, flag: FlagDef, ctx: ScopeContext) -> bool:
        env_val = flag.read_env()
        if env_val is not None:
            return env_val
        if self._store is not None:
            for scope, scope_id in [
                ("user", ctx.user_id),
                ("repo", ctx.repo_id),
                ("tenant", ctx.tenant_id),
                ("global", ""),
            ]:
                if scope_id is not None:
                    val = self._store.get_override(flag.key, scope, scope_id)
                    if val is not None:
                        return val
        return flag.default

    def snapshot(self, ctx: ScopeContext) -> dict[str, bool]:
        return {f.key: self.resolve(f, ctx) for f in CATALOG}


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

_INDEX: dict[str, FlagDef] = {f.key: f for f in CATALOG}


def by_key(key: str) -> FlagDef | None:
    """Return the FlagDef for *key*, or None if unknown."""
    return _INDEX.get(key)


def env_var(key: str) -> str:
    """Return the ENV variable name for *key* (does not require flag to exist)."""
    return "VELLIC_FEATURE_" + key.upper().replace(".", "_")
