"""Unit tests for the rules engine: models, loader (parse), and evaluator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.pipeline.models import DiffChunk
from app.rules.evaluator import evaluate_rules, _file_matches_languages, _file_is_ignored
from app.rules.loader import parse_rules_yaml, load_repo_config
from app.rules.models import RepoConfig, Rule, RuleViolation


# ---------------------------------------------------------------------------
# parse_rules_yaml
# ---------------------------------------------------------------------------

def test_parse_empty_yaml_returns_default():
    config = parse_rules_yaml("org/repo", "")
    assert config.repo_id == "org/repo"
    assert config.rules == []
    assert config.ignore == []
    assert config.severity_threshold == "warning"


def test_parse_rules_yaml_basic():
    yaml_str = """\
rules:
  - id: no_print
    pattern: "print("
    description: No print statements
    languages: [python]
    severity: warning
severity_threshold: info
"""
    config = parse_rules_yaml("org/repo", yaml_str)
    assert len(config.rules) == 1
    rule = config.rules[0]
    assert rule.id == "no_print"
    assert rule.pattern == "print("
    assert rule.description == "No print statements"
    assert rule.languages == ["python"]
    assert rule.severity == "warning"
    assert config.severity_threshold == "info"


def test_parse_rules_yaml_ignore_patterns():
    yaml_str = """\
rules: []
ignore:
  - "tests/**"
  - "*.md"
"""
    config = parse_rules_yaml("org/repo", yaml_str)
    assert config.ignore == ["tests/**", "*.md"]


def test_parse_rules_yaml_defaults_severity():
    yaml_str = """\
rules:
  - id: todo_check
    pattern: "TODO:"
"""
    config = parse_rules_yaml("org/repo", yaml_str)
    assert config.rules[0].severity == "warning"
    assert config.rules[0].languages == []


# ---------------------------------------------------------------------------
# _file_matches_languages
# ---------------------------------------------------------------------------

def test_language_filter_empty_matches_all():
    assert _file_matches_languages("app.py", []) is True
    assert _file_matches_languages("main.go", []) is True


def test_language_filter_python():
    assert _file_matches_languages("app.py", ["python"]) is True
    assert _file_matches_languages("app.js", ["python"]) is False


def test_language_filter_typescript():
    assert _file_matches_languages("component.tsx", ["typescript"]) is True
    assert _file_matches_languages("component.ts", ["typescript"]) is True
    assert _file_matches_languages("component.js", ["typescript"]) is False


def test_language_filter_multiple():
    assert _file_matches_languages("app.py", ["python", "go"]) is True
    assert _file_matches_languages("main.go", ["python", "go"]) is True
    assert _file_matches_languages("style.css", ["python", "go"]) is False


# ---------------------------------------------------------------------------
# _file_is_ignored
# ---------------------------------------------------------------------------

def test_ignored_glob():
    assert _file_is_ignored("tests/test_foo.py", ["tests/**"]) is True
    assert _file_is_ignored("app/main.py", ["tests/**"]) is False


def test_ignored_extension_glob():
    assert _file_is_ignored("README.md", ["*.md"]) is True
    assert _file_is_ignored("README.txt", ["*.md"]) is False


# ---------------------------------------------------------------------------
# evaluate_rules — core scenarios
# ---------------------------------------------------------------------------

def _make_config(pattern: str, severity: str = "warning", languages: list | None = None, ignore: list | None = None) -> RepoConfig:
    return RepoConfig(
        repo_id="org/repo",
        rules=[Rule(id="test_rule", pattern=pattern, languages=languages or [], severity=severity)],
        ignore=ignore or [],
        severity_threshold="info",
    )


def test_evaluate_no_rules_returns_empty():
    config = RepoConfig(repo_id="org/repo")
    chunks = [DiffChunk("app.py", ["+print('hello')"])]
    assert evaluate_rules(config, chunks) == []


def test_evaluate_detects_pattern_in_added_line():
    config = _make_config(pattern=r"print\(")
    chunks = [DiffChunk("app.py", ["+print('hello')"])]
    violations = evaluate_rules(config, chunks)
    assert len(violations) == 1
    assert violations[0].rule_id == "test_rule"
    assert violations[0].file == "app.py"


def test_evaluate_ignores_removed_lines():
    config = _make_config(pattern=r"print\(")
    chunks = [DiffChunk("app.py", ["-print('old')"])]
    assert evaluate_rules(config, chunks) == []


def test_evaluate_ignores_context_lines():
    config = _make_config(pattern=r"print\(")
    chunks = [DiffChunk("app.py", [" print('context')"])]
    assert evaluate_rules(config, chunks) == []


def test_evaluate_ignores_diff_header():
    config = _make_config(pattern=r"print\(")
    chunks = [DiffChunk("app.py", ["+++ b/app.py", "+print('x')"])]
    violations = evaluate_rules(config, chunks)
    assert len(violations) == 1


def test_evaluate_language_filter_skips_non_matching():
    config = _make_config(pattern=r"print\(", languages=["python"])
    chunks = [DiffChunk("app.js", ["+print('hello')"])]
    assert evaluate_rules(config, chunks) == []


def test_evaluate_language_filter_matches_correct_extension():
    config = _make_config(pattern=r"print\(", languages=["python"])
    chunks = [DiffChunk("app.py", ["+print('hello')"])]
    assert len(evaluate_rules(config, chunks)) == 1


def test_evaluate_ignored_file():
    config = _make_config(pattern=r"print\(", ignore=["tests/**"])
    chunks = [DiffChunk("tests/test_app.py", ["+print('hello')"])]
    assert evaluate_rules(config, chunks) == []


def test_evaluate_severity_threshold_filters():
    config = RepoConfig(
        repo_id="org/repo",
        rules=[Rule(id="info_rule", pattern=r"TODO", severity="info")],
        ignore=[],
        severity_threshold="warning",  # info rules should be filtered out
    )
    chunks = [DiffChunk("app.py", ["+# TODO: fix this"])]
    assert evaluate_rules(config, chunks) == []


def test_evaluate_severity_threshold_allows_error():
    config = RepoConfig(
        repo_id="org/repo",
        rules=[Rule(id="cred_rule", pattern=r"password\s*=", severity="error")],
        ignore=[],
        severity_threshold="warning",
    )
    chunks = [DiffChunk("app.py", ['+password = "secret"'])]
    assert len(evaluate_rules(config, chunks)) == 1


def test_evaluate_hunk_header_sets_line_number():
    config = _make_config(pattern=r"TODO")
    chunks = [DiffChunk("app.py", ["@@ -1,3 +10,5 @@", " context", "+# TODO: here"])]
    violations = evaluate_rules(config, chunks)
    assert len(violations) == 1
    assert violations[0].line == 11  # line 10 + 1 context + 1 added


def test_evaluate_multiple_rules_multiple_violations():
    config = RepoConfig(
        repo_id="org/repo",
        rules=[
            Rule(id="no_print", pattern=r"print\(", severity="warning"),
            Rule(id="no_todo", pattern=r"TODO", severity="info"),
        ],
        ignore=[],
        severity_threshold="info",
    )
    chunks = [DiffChunk("app.py", ["+print('x')  # TODO: remove"])]
    violations = evaluate_rules(config, chunks)
    assert len(violations) == 2
    rule_ids = {v.rule_id for v in violations}
    assert rule_ids == {"no_print", "no_todo"}


# ---------------------------------------------------------------------------
# load_repo_config (async, with mocked pool)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_load_repo_config_returns_default_when_no_row():
    pool = MagicMock()
    pool.fetchrow = AsyncMock(return_value=None)
    config = await load_repo_config(pool, "org/repo")
    assert config.repo_id == "org/repo"
    assert config.rules == []


@pytest.mark.asyncio
async def test_load_repo_config_returns_default_when_empty_yaml():
    pool = MagicMock()
    pool.fetchrow = AsyncMock(return_value={"rules_yaml": ""})
    config = await load_repo_config(pool, "org/repo")
    assert config.rules == []


@pytest.mark.asyncio
async def test_load_repo_config_parses_stored_yaml():
    yaml_str = "rules:\n  - id: r1\n    pattern: foo\n"
    pool = MagicMock()
    pool.fetchrow = AsyncMock(return_value={"rules_yaml": yaml_str})
    config = await load_repo_config(pool, "org/repo")
    assert len(config.rules) == 1
    assert config.rules[0].id == "r1"


@pytest.mark.asyncio
async def test_load_repo_config_falls_back_on_invalid_yaml():
    pool = MagicMock()
    pool.fetchrow = AsyncMock(return_value={"rules_yaml": "{ invalid: yaml: ["})
    config = await load_repo_config(pool, "org/repo")
    assert config.rules == []
