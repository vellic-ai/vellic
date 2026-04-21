"""Prompt DSL — file-based customisation of the AI reviewer."""

from .context_resolver import build_prompt_context, extract_symbols_from_diff, fetch_prev_reviews
from .inheritance import CircularInheritanceError, cascade_merge, resolve_all, resolve_single
from .models import PromptContext, PromptFile, PromptFrontmatter, ResolvedPrompt
from .parser import load_prompts_from_dir, parse_prompt_content
from .preset_loader import (
    BUILTIN_PRESET_NAMES,
    fork_preset,
    list_presets,
    load_all_presets,
    load_preset,
)
from .renderer import build_resolved_prompt, render_prompt
from .repo_loader import load_repo_prompts, load_repo_prompts_sync
from .schema import PromptValidationError, validate_frontmatter
from .store import delete_override, get_override, list_overrides, upsert_override

__all__ = [
    "BUILTIN_PRESET_NAMES",
    "CircularInheritanceError",
    "PromptContext",
    "PromptFile",
    "PromptFrontmatter",
    "PromptValidationError",
    "ResolvedPrompt",
    "build_prompt_context",
    "build_resolved_prompt",
    "cascade_merge",
    "delete_override",
    "extract_symbols_from_diff",
    "fetch_prev_reviews",
    "fork_preset",
    "get_override",
    "list_overrides",
    "list_presets",
    "load_all_presets",
    "load_preset",
    "load_prompts_from_dir",
    "load_repo_prompts",
    "load_repo_prompts_sync",
    "parse_prompt_content",
    "render_prompt",
    "resolve_all",
    "resolve_single",
    "upsert_override",
    "validate_frontmatter",
]
