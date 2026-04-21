"""Jinja-like template renderer for prompt bodies."""

from __future__ import annotations

import re

from .models import PromptContext, PromptFile, ResolvedPrompt

_VAR_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")
_UNDEFINED_SENTINEL = ""


def render_body(body: str, variables: dict[str, str]) -> str:
    def _sub(m: re.Match) -> str:
        return variables.get(m.group(1), _UNDEFINED_SENTINEL)

    return _VAR_RE.sub(_sub, body)


def render_prompt(prompt: PromptFile, context: PromptContext) -> str:
    ctx_vars = context.as_dict()
    merged = {**ctx_vars, **prompt.frontmatter.variables}
    return render_body(prompt.body, merged)


def build_resolved_prompt(prompts: list[PromptFile], context: PromptContext) -> ResolvedPrompt:
    parts: list[str] = []
    sources: list[str] = []
    for p in prompts:
        rendered = render_prompt(p, context)
        if rendered.strip():
            parts.append(rendered.strip())
            sources.append(p.name)
    body = "\n\n".join(parts)
    return ResolvedPrompt(body=body, sources=sources)
