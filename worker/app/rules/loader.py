"""Load per-repo rules config from the database, falling back to defaults."""

from __future__ import annotations

import logging

import asyncpg
import yaml

from .models import RepoConfig, Rule

logger = logging.getLogger("worker.rules.loader")

DEFAULT_RULES_YAML = """\
rules: []
ignore: []
severity_threshold: warning
"""

_SEVERITY_ORDER = {"info": 0, "warning": 1, "error": 2}


def parse_rules_yaml(repo_id: str, rules_yaml: str) -> RepoConfig:
    """Parse a YAML string into a RepoConfig. Uses defaults for any missing fields."""
    if not rules_yaml or not rules_yaml.strip():
        return _default_config(repo_id)

    doc = yaml.safe_load(rules_yaml) or {}

    rules: list[Rule] = []
    for entry in doc.get("rules", []):
        rules.append(
            Rule(
                id=str(entry["id"]),
                pattern=str(entry["pattern"]),
                description=str(entry.get("description", "")),
                languages=[str(lang) for lang in entry.get("languages", [])],
                severity=str(entry.get("severity", "warning")),
            )
        )

    return RepoConfig(
        repo_id=repo_id,
        rules=rules,
        ignore=list(doc.get("ignore", [])),
        severity_threshold=str(doc.get("severity_threshold", "warning")),
    )


def _default_config(repo_id: str) -> RepoConfig:
    return RepoConfig(repo_id=repo_id)


async def load_repo_config(pool: asyncpg.Pool, repo_id: str) -> RepoConfig:
    """Fetch repo config from DB; returns default config when none is stored."""
    row = await pool.fetchrow(
        "SELECT rules_yaml FROM repo_config WHERE repo_id = $1",
        repo_id,
    )
    if row is None or not row["rules_yaml"]:
        logger.debug("no custom rules for repo=%s; using defaults", repo_id)
        return _default_config(repo_id)

    try:
        config = parse_rules_yaml(repo_id, row["rules_yaml"])
        logger.info("loaded %d rules for repo=%s", len(config.rules), repo_id)
        return config
    except Exception as exc:
        logger.warning("failed to parse rules for repo=%s (%s); using defaults", repo_id, exc)
        return _default_config(repo_id)
