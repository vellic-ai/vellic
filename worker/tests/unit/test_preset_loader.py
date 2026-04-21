"""Tests for the built-in prompt preset library (VEL-113)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.prompts.models import PromptFile
from app.prompts.preset_loader import (
    BUILTIN_PRESET_NAMES,
    fork_preset,
    list_presets,
    load_all_presets,
    load_preset,
)

# ---------------------------------------------------------------------------
# list_presets
# ---------------------------------------------------------------------------


def test_list_presets_returns_all_builtins():
    names = list_presets()
    assert set(names) == set(BUILTIN_PRESET_NAMES)


def test_list_presets_is_sorted():
    names = list_presets()
    assert names == sorted(names)


# ---------------------------------------------------------------------------
# load_preset
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", BUILTIN_PRESET_NAMES)
def test_load_preset_valid(name: str):
    prompt = load_preset(name)
    assert isinstance(prompt, PromptFile)
    assert prompt.name == name
    assert prompt.source == "preset"
    assert prompt.body.strip()


@pytest.mark.parametrize("name", BUILTIN_PRESET_NAMES)
def test_load_preset_frontmatter_valid(name: str):
    prompt = load_preset(name)
    fm = prompt.frontmatter
    assert isinstance(fm.priority, int)
    assert isinstance(fm.scope, list)
    assert isinstance(fm.triggers, list)


def test_load_preset_unknown_raises():
    with pytest.raises(ValueError, match="Unknown preset"):
        load_preset("does-not-exist")


def test_load_preset_unknown_lists_available():
    with pytest.raises(ValueError, match="secure-review"):
        load_preset("does-not-exist")


# ---------------------------------------------------------------------------
# load_all_presets
# ---------------------------------------------------------------------------


def test_load_all_presets_count():
    presets = load_all_presets()
    assert len(presets) == len(BUILTIN_PRESET_NAMES)


def test_load_all_presets_all_are_prompt_files():
    for p in load_all_presets():
        assert isinstance(p, PromptFile)


# ---------------------------------------------------------------------------
# fork_preset
# ---------------------------------------------------------------------------


def test_fork_preset_creates_file(tmp_path: Path):
    dest = fork_preset("secure-review", tmp_path)
    assert dest.exists()
    assert dest.name == "secure-review.md"


def test_fork_preset_custom_name(tmp_path: Path):
    dest = fork_preset("secure-review", tmp_path, custom_name="my-security")
    assert dest.name == "my-security.md"


def test_fork_preset_creates_target_dir(tmp_path: Path):
    nested = tmp_path / "a" / "b" / "c"
    fork_preset("doc-review", nested)
    assert nested.is_dir()


def test_fork_preset_content_is_parseable(tmp_path: Path):
    dest = fork_preset("style-review", tmp_path)
    from app.prompts.parser import parse_prompt_content

    content = dest.read_text(encoding="utf-8")
    # Skip the header comment lines before the front-matter delimiter.
    # The header comment starts with '#'; strip it off to get a valid DSL file.
    lines = content.splitlines(keepends=True)
    body_lines = [line for line in lines if not line.startswith("#")]
    trimmed = "".join(body_lines).lstrip("\n")
    prompt = parse_prompt_content(trimmed, name="style-review")
    assert prompt.body.strip()


def test_fork_preset_unknown_raises(tmp_path: Path):
    with pytest.raises(ValueError, match="Unknown preset"):
        fork_preset("not-a-preset", tmp_path)


def test_fork_preset_header_mentions_origin(tmp_path: Path):
    dest = fork_preset("test-review", tmp_path)
    content = dest.read_text(encoding="utf-8")
    assert "test-review" in content
    assert "Forked from built-in preset" in content
