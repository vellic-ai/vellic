"""Data models for the prompt DSL."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PromptFrontmatter:
    # Path globs (e.g. "api/**"), PR label names, or event types ("pr.opened").
    # Empty list = matches everything.
    scope: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    # Higher priority wins when multiple prompts match the same PR.
    priority: int = 0
    # Name (without .md) of a prompt this one extends.
    inherits: str | None = None
    # Extra key→value pairs injected into the template context.
    variables: dict[str, str] = field(default_factory=dict)


@dataclass
class PromptFile:
    name: str       # identifier — filename without extension
    path: str       # filesystem path (empty for preset/DB sources)
    frontmatter: PromptFrontmatter
    body: str       # raw template body with {{ variable }} placeholders
    source: str     # "repo" | "db" | "preset"


@dataclass
class PromptContext:
    """Variables available inside prompt templates."""

    diff: str = ""
    symbols: str = ""
    coverage: str = ""
    prev_reviews: list[str] = field(default_factory=list)
    pr_title: str = ""
    pr_body: str = ""
    repo: str = ""
    base_branch: str = ""
    changed_files: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    # Caller-supplied extras override all above when names conflict.
    extra: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, str]:
        """Flatten to a string-valued mapping for template substitution."""
        base: dict[str, str] = {
            "diff": self.diff,
            "symbols": self.symbols,
            "coverage": self.coverage,
            "prev_reviews": "\n".join(self.prev_reviews),
            "pr_title": self.pr_title,
            "pr_body": self.pr_body,
            "repo": self.repo,
            "base_branch": self.base_branch,
            "changed_files": "\n".join(self.changed_files),
            "labels": ", ".join(self.labels),
        }
        base.update(self.extra)
        return base


@dataclass
class ResolvedPrompt:
    """Final rendered prompt for a PR, possibly merged from multiple sources."""

    body: str
    sources: list[str]  # prompt names that contributed, in merge order
