from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Rule:
    id: str
    pattern: str
    description: str = ""
    languages: list[str] = field(default_factory=list)  # empty = all languages
    severity: str = "warning"  # "info" | "warning" | "error"


@dataclass
class RepoConfig:
    repo_id: str
    rules: list[Rule] = field(default_factory=list)
    ignore: list[str] = field(default_factory=list)  # glob patterns
    severity_threshold: str = "warning"  # minimum severity to report


@dataclass
class RuleViolation:
    rule_id: str
    file: str
    line: int
    matched_text: str
    severity: str
    description: str
