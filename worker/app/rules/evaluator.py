"""Evaluate YAML-defined rules against diff chunks."""

from __future__ import annotations

import fnmatch
import logging
import re

from ..pipeline.models import DiffChunk
from .models import RepoConfig, RuleViolation

logger = logging.getLogger("worker.rules.evaluator")

_SEVERITY_ORDER = {"info": 0, "warning": 1, "error": 2}

_LANG_EXTENSION_MAP: dict[str, list[str]] = {
    "python": [".py"],
    "javascript": [".js", ".jsx", ".mjs", ".cjs"],
    "typescript": [".ts", ".tsx"],
    "go": [".go"],
    "ruby": [".rb"],
    "java": [".java"],
    "rust": [".rs"],
    "c": [".c", ".h"],
    "cpp": [".cpp", ".cc", ".cxx", ".hpp"],
    "kotlin": [".kt"],
    "swift": [".swift"],
    "php": [".php"],
}


def _file_matches_languages(filename: str, languages: list[str]) -> bool:
    if not languages:
        return True
    ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
    for lang in languages:
        exts = _LANG_EXTENSION_MAP.get(lang.lower(), [f".{lang.lower()}"])
        if ext in exts:
            return True
    return False


def _file_is_ignored(filename: str, ignore_patterns: list[str]) -> bool:
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(filename, pattern):
            return True
    return False


def _meets_threshold(severity: str, threshold: str) -> bool:
    return _SEVERITY_ORDER.get(severity, 0) >= _SEVERITY_ORDER.get(threshold, 0)


def evaluate_rules(config: RepoConfig, chunks: list[DiffChunk]) -> list[RuleViolation]:
    """
    Scan added lines in each diff chunk against the repo's configured rules.
    Only lines beginning with '+' (excluding '+++') are checked — we only flag
    newly introduced patterns, not pre-existing ones.
    """
    if not config.rules:
        return []

    violations: list[RuleViolation] = []

    for chunk in chunks:
        filename = chunk.filename

        if _file_is_ignored(filename, config.ignore):
            continue

        line_offset = 0
        for raw_line in chunk.patch_lines:
            if raw_line.startswith("@@"):
                # Parse hunk header to track real line numbers when possible
                m = re.search(r"\+(\d+)", raw_line)
                if m:
                    line_offset = int(m.group(1)) - 1
                continue

            if raw_line.startswith("+++"):
                continue

            if raw_line.startswith("+"):
                line_offset += 1
                content = raw_line[1:]  # strip leading '+'

                for rule in config.rules:
                    if not _file_matches_languages(filename, rule.languages):
                        continue
                    if not _meets_threshold(rule.severity, config.severity_threshold):
                        continue
                    if re.search(rule.pattern, content):
                        violations.append(
                            RuleViolation(
                                rule_id=rule.id,
                                file=filename,
                                line=line_offset,
                                matched_text=content.strip(),
                                severity=rule.severity,
                                description=rule.description or rule.id,
                            )
                        )
            elif not raw_line.startswith("-"):
                line_offset += 1

    return violations
