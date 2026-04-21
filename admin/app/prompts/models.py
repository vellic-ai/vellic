"""Data models for the prompt DSL."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PromptFrontmatter:
    scope: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    priority: int = 0
    inherits: str | None = None
    variables: dict[str, str] = field(default_factory=dict)


@dataclass
class PromptFile:
    name: str
    path: str
    frontmatter: PromptFrontmatter
    body: str
    source: str  # "repo" | "db" | "preset"


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
    extra: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, str]:
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
    body: str
    sources: list[str]
