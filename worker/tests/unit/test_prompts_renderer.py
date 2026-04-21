"""Unit tests for the prompt DSL renderer (VEL-109)."""

import textwrap

from app.prompts.models import PromptContext, PromptFrontmatter
from app.prompts.parser import parse_prompt_content
from app.prompts.renderer import build_resolved_prompt, render_body, render_prompt


def test_render_body_substitutes_known_vars():
    body = "Repo: {{ repo }}, Branch: {{ base_branch }}"
    result = render_body(body, {"repo": "acme/api", "base_branch": "main"})
    assert result == "Repo: acme/api, Branch: main"


def test_render_body_unknown_var_becomes_empty():
    result = render_body("Hello {{ unknown_var }}!", {"known": "value"})
    assert result == "Hello !"


def test_render_body_whitespace_in_placeholder():
    result = render_body("{{  repo  }}", {"repo": "acme/api"})
    assert result == "acme/api"


def test_render_body_no_placeholders():
    result = render_body("Static text only.", {})
    assert result == "Static text only."


def _make_prompt(body: str, variables: dict | None = None):
    content = textwrap.dedent(f"""\
        ---
        priority: 0
        ---
        {body}
    """)
    pf = parse_prompt_content(content, name="test")
    if variables:
        pf.frontmatter.variables.update(variables)
    return pf


def test_render_prompt_uses_context_vars():
    pf = _make_prompt("Reviewing {{ pr_title }} on {{ repo }}")
    ctx = PromptContext(pr_title="Fix login", repo="acme/api")
    result = render_prompt(pf, ctx)
    assert "Fix login" in result
    assert "acme/api" in result


def test_render_prompt_frontmatter_variables_override_context():
    pf = _make_prompt("Tone: {{ tone }}", variables={"tone": "strict"})
    ctx = PromptContext(extra={"tone": "relaxed"})
    # frontmatter.variables win over context.extra
    result = render_prompt(pf, ctx)
    assert "strict" in result


def test_render_prompt_context_extra_available():
    pf = _make_prompt("Custom: {{ custom_field }}")
    ctx = PromptContext(extra={"custom_field": "hello"})
    result = render_prompt(pf, ctx)
    assert "hello" in result


def test_build_resolved_prompt_joins_multiple():
    p1 = _make_prompt("First part.")
    p2 = _make_prompt("Second part.")
    ctx = PromptContext()
    resolved = build_resolved_prompt([p1, p2], ctx)
    assert "First part." in resolved.body
    assert "Second part." in resolved.body
    assert resolved.sources == ["test", "test"]


def test_build_resolved_prompt_skips_empty_bodies():
    p1 = _make_prompt("Real content here.")
    p2 = _make_prompt("{{ empty_var }}")  # renders to "" → stripped → skipped
    ctx = PromptContext()
    resolved = build_resolved_prompt([p1, p2], ctx)
    assert resolved.sources == ["test"]
    assert "Real content here." in resolved.body


def test_build_resolved_prompt_empty_list():
    resolved = build_resolved_prompt([], PromptContext())
    assert resolved.body == ""
    assert resolved.sources == []
