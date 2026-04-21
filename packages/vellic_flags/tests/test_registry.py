"""Tests for the vellic_flags typed flag catalog."""

import os

import pytest

from vellic_flags import (
    CATALOG,
    CostImpact,
    FlagCategory,
    FlagDef,
    FlagScope,
    by_key,
    env_var,
)


# ---------------------------------------------------------------------------
# Structural / catalog invariants
# ---------------------------------------------------------------------------

def test_catalog_is_non_empty():
    assert len(CATALOG) > 0


def test_all_keys_are_unique():
    keys = [f.key for f in CATALOG]
    assert len(keys) == len(set(keys)), "Duplicate flag keys found"


def test_all_flag_keys_follow_dot_convention():
    for flag in CATALOG:
        parts = flag.key.split(".")
        assert len(parts) >= 2, f"{flag.key!r} has no category prefix"
        assert all(p for p in parts), f"{flag.key!r} has empty segment"


def test_flag_category_matches_key_prefix():
    """The first segment of the key must match the category enum value."""
    for flag in CATALOG:
        prefix = flag.key.split(".")[0]
        assert prefix == flag.category.value, (
            f"{flag.key!r}: key prefix {prefix!r} != category {flag.category.value!r}"
        )


def test_required_flags_exist():
    """Every key listed in `requires` must itself be in the catalog."""
    catalog_keys = {f.key for f in CATALOG}
    for flag in CATALOG:
        for dep in flag.requires:
            assert dep in catalog_keys, (
                f"{flag.key!r} requires unknown flag {dep!r}"
            )


def test_all_flags_are_frozen():
    flag = CATALOG[0]
    with pytest.raises((AttributeError, TypeError)):
        flag.default = not flag.default  # type: ignore[misc]


# ---------------------------------------------------------------------------
# FlagDef helpers
# ---------------------------------------------------------------------------

def test_env_var_name():
    flag = by_key("vcs.github")
    assert flag is not None
    assert flag.env_var() == "VELLIC_FEATURE_VCS_GITHUB"


def test_env_var_helper_function():
    assert env_var("pipeline.llm_analysis") == "VELLIC_FEATURE_PIPELINE_LLM_ANALYSIS"


def test_by_key_returns_none_for_unknown():
    assert by_key("does.not.exist") is None


def test_by_key_returns_correct_flag():
    flag = by_key("llm.openai")
    assert flag is not None
    assert flag.name == "OpenAI"
    assert flag.category == FlagCategory.LLM
    assert flag.default is True


# ---------------------------------------------------------------------------
# ENV override read
# ---------------------------------------------------------------------------

def test_read_env_returns_none_when_unset():
    flag = by_key("vcs.github")
    assert flag is not None
    os.environ.pop(flag.env_var(), None)
    assert flag.read_env() is None


def test_read_env_true_variants(monkeypatch):
    flag = by_key("vcs.bitbucket")
    assert flag is not None
    for val in ("1", "true", "True", "TRUE", "yes", "YES"):
        monkeypatch.setenv(flag.env_var(), val)
        assert flag.read_env() is True, f"Expected True for ENV={val!r}"


def test_read_env_false_variants(monkeypatch):
    flag = by_key("vcs.github")
    assert flag is not None
    for val in ("0", "false", "False", "FALSE", "no", "NO", "off"):
        monkeypatch.setenv(flag.env_var(), val)
        assert flag.read_env() is False, f"Expected False for ENV={val!r}"


# ---------------------------------------------------------------------------
# Known-flag spot-checks
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("key,expected_default", [
    ("vcs.github", True),
    ("vcs.gitlab", True),
    ("vcs.bitbucket", False),
    ("vcs.gitea", False),
    ("llm.openai", True),
    ("llm.anthropic", True),
    ("llm.vllm", False),
    ("pipeline.diff", True),
    ("pipeline.llm_analysis", True),
    ("pipeline.security_scan", False),
    ("ast.python", True),
    ("ast.typescript", True),
    ("ast.go", False),
    ("ast.rust", False),
    ("vector.qdrant", False),
    ("platform.multi_tenant", False),
    ("platform.prompt_dsl", False),
])
def test_known_flag_defaults(key: str, expected_default: bool):
    flag = by_key(key)
    assert flag is not None, f"Flag {key!r} not found in catalog"
    assert flag.default == expected_default


def test_ast_flags_require_pipeline_context():
    ast_flags = [f for f in CATALOG if f.category == FlagCategory.AST]
    for flag in ast_flags:
        assert "pipeline.context" in flag.requires, (
            f"AST flag {flag.key!r} should require pipeline.context"
        )


def test_vector_flags_require_pipeline_context():
    vector_flags = [f for f in CATALOG if f.category == FlagCategory.VECTOR]
    for flag in vector_flags:
        assert "pipeline.context" in flag.requires, (
            f"Vector flag {flag.key!r} should require pipeline.context"
        )


def test_llm_flags_have_cost_impact():
    llm_flags = [f for f in CATALOG if f.category == FlagCategory.LLM]
    for flag in llm_flags:
        assert flag.cost_impact != CostImpact.NONE, (
            f"LLM flag {flag.key!r} should have non-zero cost_impact"
        )


def test_platform_flags_are_global_or_repo_scoped():
    platform_flags = [f for f in CATALOG if f.category == FlagCategory.PLATFORM]
    for flag in platform_flags:
        assert flag.scope in (FlagScope.GLOBAL, FlagScope.REPO), (
            f"Platform flag {flag.key!r} has unexpected scope {flag.scope}"
        )
