"""Prompt inheritance resolution and cascading merger (VEL-112).

Supports ``inherits: base`` in front-matter.  When a prompt declares
``inherits``, its parent's body is prepended and its parent's
front-matter fields fill in any unset child values.  Circular chains
are detected and rejected immediately.

``cascade_merge`` sorts an already-resolved list of matching prompts by
priority so that higher-priority entries render first (their instructions
lead the final prompt text).  Variable conflicts are resolved by
``render_prompt`` per-prompt, so each prompt renders with its own variables.
"""

from __future__ import annotations

from .models import PromptFile, PromptFrontmatter


class CircularInheritanceError(ValueError):
    """Raised when a circular inheritance chain is detected."""


def _merge_frontmatters(
    parent: PromptFrontmatter, child: PromptFrontmatter
) -> PromptFrontmatter:
    """Return a new front-matter with child values overriding parent values.

    List fields (``scope``, ``triggers``) fall back to the parent when the
    child leaves them empty.  ``priority`` falls back to the parent when the
    child uses the default of 0.  Variables are deep-merged (child wins per
    key).  ``inherits`` is always ``None`` in the result — it is consumed here.
    """
    return PromptFrontmatter(
        scope=child.scope if child.scope else parent.scope,
        triggers=child.triggers if child.triggers else parent.triggers,
        priority=child.priority if child.priority != 0 else parent.priority,
        inherits=None,
        variables={**parent.variables, **child.variables},
    )


def _merge_bodies(parent_body: str, child_body: str) -> str:
    """Concatenate parent and child bodies with a blank-line separator.

    The parent body always comes first so that inherited instructions act as
    a preamble; the child body appends its specialisation on top.
    """
    parts = [b.strip() for b in (parent_body, child_body) if b.strip()]
    return "\n\n".join(parts)


def resolve_single(
    prompt: PromptFile,
    registry: dict[str, PromptFile],
    _chain: tuple[str, ...] = (),
) -> PromptFile:
    """Resolve *prompt*'s full inheritance chain and return the merged result.

    Args:
        prompt:   The prompt to resolve.
        registry: Name → ``PromptFile`` mapping of all available prompts.
        _chain:   Names already on the current resolution path (cycle guard).

    Raises:
        CircularInheritanceError: If a cycle is detected.
        ValueError: If an inherited prompt name is not in *registry*.
    """
    if prompt.name in _chain:
        cycle = " -> ".join(_chain) + " -> " + prompt.name
        raise CircularInheritanceError(
            f"Circular inheritance detected: {cycle}"
        )

    if prompt.frontmatter.inherits is None:
        return prompt

    parent_name = prompt.frontmatter.inherits
    if parent_name not in registry:
        raise ValueError(
            f"Prompt '{prompt.name}' inherits from unknown prompt '{parent_name}'"
        )

    resolved_parent = resolve_single(
        registry[parent_name], registry, _chain + (prompt.name,)
    )

    merged_fm = _merge_frontmatters(resolved_parent.frontmatter, prompt.frontmatter)
    merged_body = _merge_bodies(resolved_parent.body, prompt.body)

    return PromptFile(
        name=prompt.name,
        path=prompt.path,
        frontmatter=merged_fm,
        body=merged_body,
        source=prompt.source,
    )


def resolve_all(prompts: list[PromptFile]) -> list[PromptFile]:
    """Resolve inheritance for every prompt in *prompts*.

    Builds a name → prompt registry and resolves each prompt's chain.

    Raises:
        CircularInheritanceError: If any cycle is detected.
        ValueError: If any prompt references an unknown parent.
    """
    registry = {p.name: p for p in prompts}
    return [resolve_single(p, registry) for p in prompts]


def cascade_merge(prompts: list[PromptFile]) -> list[PromptFile]:
    """Sort *prompts* by priority, highest first, for cascade rendering.

    ``build_resolved_prompt`` in the renderer will concatenate the resulting
    list in order — placing the most specific (highest-priority) instructions
    at the top of the final prompt.

    When multiple prompts share the same priority, their relative order from
    the input list is preserved (stable sort).
    """
    return sorted(prompts, key=lambda p: p.frontmatter.priority, reverse=True)
