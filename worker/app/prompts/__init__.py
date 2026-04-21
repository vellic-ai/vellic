"""Prompt DSL — file-based customisation of the AI reviewer."""

from .context_resolver import build_prompt_context, extract_symbols_from_diff, fetch_prev_reviews
from .inheritance import CircularInheritanceError, cascade_merge, resolve_all, resolve_single
from .models import PromptContext, PromptFile, PromptFrontmatter, ResolvedPrompt
from .parser import load_prompts_from_dir, parse_prompt_content
from .renderer import build_resolved_prompt, render_prompt
from .schema import PromptValidationError, validate_frontmatter

__all__ = [
    "CircularInheritanceError",
    "PromptContext",
    "PromptFile",
    "PromptFrontmatter",
    "PromptValidationError",
    "ResolvedPrompt",
    "build_prompt_context",
    "build_resolved_prompt",
    "cascade_merge",
    "extract_symbols_from_diff",
    "fetch_prev_reviews",
    "load_prompts_from_dir",
    "parse_prompt_content",
    "render_prompt",
    "resolve_all",
    "resolve_single",
    "validate_frontmatter",
]
