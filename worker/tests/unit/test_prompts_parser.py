"""Unit tests for the prompt DSL parser and schema validator (VEL-109, VEL-110)."""

import textwrap

import pytest

from app.prompts.parser import load_prompts_from_dir, parse_prompt_content
from app.prompts.schema import PromptValidationError, validate_frontmatter


# ---------------------------------------------------------------------------
# validate_frontmatter
# ---------------------------------------------------------------------------


def test_validate_empty_frontmatter_returns_defaults():
    fm = validate_frontmatter({})
    assert fm.scope == []
    assert fm.triggers == []
    assert fm.priority == 0
    assert fm.inherits is None
    assert fm.variables == {}


def test_validate_full_frontmatter():
    raw = {
        "scope": ["api/**", "frontend/**"],
        "triggers": ["pr.opened", "pr.synchronize"],
        "priority": 10,
        "inherits": "base",
        "variables": {"tone": "strict"},
    }
    fm = validate_frontmatter(raw)
    assert fm.scope == ["api/**", "frontend/**"]
    assert fm.triggers == ["pr.opened", "pr.synchronize"]
    assert fm.priority == 10
    assert fm.inherits == "base"
    assert fm.variables == {"tone": "strict"}


def test_validate_scope_as_string_coerced_to_list():
    fm = validate_frontmatter({"scope": "api/**"})
    assert fm.scope == ["api/**"]


def test_validate_unknown_key_raises():
    with pytest.raises(PromptValidationError, match="Unknown front-matter keys"):
        validate_frontmatter({"bogus_key": "value"})


def test_validate_invalid_priority_raises():
    with pytest.raises(PromptValidationError, match="'priority' must be an integer"):
        validate_frontmatter({"priority": "high"})


def test_validate_invalid_trigger_prefix_raises():
    with pytest.raises(PromptValidationError, match="Invalid trigger"):
        validate_frontmatter({"triggers": ["unknown.event"]})


def test_validate_variables_non_dict_raises():
    with pytest.raises(PromptValidationError, match="'variables' must be a mapping"):
        validate_frontmatter({"variables": "not-a-dict"})


def test_validate_inherits_non_string_raises():
    with pytest.raises(PromptValidationError, match="'inherits' must be a string"):
        validate_frontmatter({"inherits": 123})


# ---------------------------------------------------------------------------
# parse_prompt_content
# ---------------------------------------------------------------------------

_VALID_CONTENT = textwrap.dedent("""\
    ---
    scope: api/**
    priority: 5
    ---
    Review for security issues in {{ diff }}.
""")

_EMPTY_FRONTMATTER_CONTENT = textwrap.dedent("""\
    ---
    ---
    Just a body with no front-matter fields.
""")


def test_parse_valid_content():
    pf = parse_prompt_content(_VALID_CONTENT, name="security")
    assert pf.name == "security"
    assert pf.source == "repo"
    assert pf.frontmatter.scope == ["api/**"]
    assert pf.frontmatter.priority == 5
    assert "{{ diff }}" in pf.body


def test_parse_empty_frontmatter():
    pf = parse_prompt_content(_EMPTY_FRONTMATTER_CONTENT, name="plain")
    assert pf.frontmatter.scope == []
    assert pf.frontmatter.priority == 0
    assert "Just a body" in pf.body


def test_parse_missing_opening_delimiter_raises():
    with pytest.raises(PromptValidationError, match="must start with '---'"):
        parse_prompt_content("no delimiter here\nbody", name="bad")


def test_parse_missing_closing_delimiter_raises():
    with pytest.raises(PromptValidationError, match="no closing '---'"):
        parse_prompt_content("---\nscope: api/**\n", name="bad")


def test_parse_invalid_yaml_raises():
    content = "---\n: bad: yaml: [\n---\nbody"
    with pytest.raises(PromptValidationError, match="YAML parse error"):
        parse_prompt_content(content, name="bad")


def test_parse_yaml_non_mapping_raises():
    content = "---\n- list item\n---\nbody"
    with pytest.raises(PromptValidationError, match="must be a YAML mapping"):
        parse_prompt_content(content, name="bad")


# ---------------------------------------------------------------------------
# load_prompts_from_dir
# ---------------------------------------------------------------------------


def test_load_prompts_from_dir(tmp_path):
    (tmp_path / "alpha.md").write_text(textwrap.dedent("""\
        ---
        priority: 1
        ---
        Alpha body
    """))
    (tmp_path / "beta.md").write_text(textwrap.dedent("""\
        ---
        scope: frontend/**
        ---
        Beta body
    """))
    (tmp_path / "not_a_prompt.txt").write_text("ignored")

    prompts = load_prompts_from_dir(tmp_path)
    assert len(prompts) == 2
    names = {p.name for p in prompts}
    assert names == {"alpha", "beta"}


def test_load_prompts_nonexistent_dir_returns_empty(tmp_path):
    result = load_prompts_from_dir(tmp_path / "does_not_exist")
    assert result == []


def test_load_prompts_invalid_file_raises(tmp_path):
    (tmp_path / "bad.md").write_text("no front-matter here")
    with pytest.raises(PromptValidationError):
        load_prompts_from_dir(tmp_path)
