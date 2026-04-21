from __future__ import annotations

import json
import logging
import re

from ..context.ast.models import ASTContext
from ..llm.protocol import LLMProvider
from .models import AnalysisResult, DiffChunk, PRContext, ReviewComment

logger = logging.getLogger("worker.pipeline.llm_analyzer")

_INSTRUCTIONS = """\
You are a precise code reviewer. Analyze the PR diff and return ONLY valid JSON \
— no prose, no markdown fences.

Required JSON schema:
{
  "comments": [
    {
      "file": "<path>",
      "line": <int>,
      "body": "<specific actionable feedback>",
      "confidence": <0.0-1.0>,
      "rationale": "<why this matters>"
    }
  ],
  "summary": "<overall PR assessment, 1-3 sentences>",
  "generic_ratio": <fraction of generic/low-value comments, 0.0-1.0>
}

Rules:
- Only include comments that are specific, actionable, and anchored to a file+line.
- Return an empty comments array when the diff looks correct.
- generic_ratio must reflect how many of your comments are vague or boilerplate.
"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise ValueError(f"No JSON object found in LLM output: {text[:300]!r}")


def _format_symbols(ast_ctx: ASTContext) -> str:
    if not ast_ctx.symbols:
        return ""
    lines = ["Symbols changed:"]
    for sym in ast_ctx.symbols:
        entry = f"  - {sym.kind} `{sym.name}`"
        if sym.parent:
            entry += f" (in `{sym.parent}`)"
        if sym.signature:
            entry += f" — `{sym.signature}`"
        if sym.docstring:
            entry += f"\n    doc: {sym.docstring[:200]}"
        lines.append(entry)
    return "\n".join(lines)


def _build_prompt(
    context: PRContext,
    chunks: list[DiffChunk],
    ast_contexts: dict[str, ASTContext] | None = None,
    custom_instructions: str | None = None,
) -> str:
    parts = [
        custom_instructions if custom_instructions is not None else _INSTRUCTIONS,
        "",
        f"PR: {context.title}",
        f"Repo: {context.repo}   Base: {context.base_branch}",
    ]
    if context.body:
        parts.append(f"Description: {context.body[:800]}")
    parts.append("")
    parts.append("## Diff")

    for chunk in chunks:
        parts.append(f"\n### {chunk.filename}")
        parts.append("```diff")
        parts.append(chunk.patch)
        parts.append("```")
        if ast_contexts:
            ast_ctx = ast_contexts.get(chunk.filename)
            if ast_ctx and ast_ctx.symbols:
                parts.append(_format_symbols(ast_ctx))

    parts.append("\nReturn the JSON analysis now.")
    return "\n".join(parts)


async def analyze(
    context: PRContext,
    chunks: list[DiffChunk],
    llm: LLMProvider,
    max_tokens: int = 2048,
    ast_contexts: dict[str, ASTContext] | None = None,
    custom_instructions: str | None = None,
) -> AnalysisResult:
    if not chunks:
        logger.info("no reviewable diff chunks for %s#%d", context.repo, context.pr_number)
        return AnalysisResult(comments=[], summary="No reviewable diff found.", generic_ratio=0.0)

    prompt = _build_prompt(context, chunks, ast_contexts=ast_contexts, custom_instructions=custom_instructions)
    raw = await llm.complete(prompt, max_tokens=max_tokens)
    logger.debug("LLM raw response length=%d", len(raw))

    try:
        data = _extract_json(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("LLM JSON parse failed (%s); returning empty analysis", exc)
        return AnalysisResult(comments=[], summary=raw[:500], generic_ratio=1.0)

    comments = [
        ReviewComment(
            file=c.get("file", ""),
            line=int(c.get("line", 0)),
            body=c.get("body", ""),
            confidence=max(0.0, min(1.0, float(c.get("confidence", 0.5)))),
            rationale=c.get("rationale", ""),
        )
        for c in data.get("comments", [])
        if isinstance(c, dict)
    ]

    return AnalysisResult(
        comments=comments,
        summary=str(data.get("summary", "")),
        generic_ratio=max(0.0, min(1.0, float(data.get("generic_ratio", 0.0)))),
    )
