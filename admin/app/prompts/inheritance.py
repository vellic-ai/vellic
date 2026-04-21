"""Prompt inheritance resolution and cascading merger."""

from __future__ import annotations

from .models import PromptFile, PromptFrontmatter


class CircularInheritanceError(ValueError):
    """Raised when a circular inheritance chain is detected."""


def _merge_frontmatters(
    parent: PromptFrontmatter, child: PromptFrontmatter
) -> PromptFrontmatter:
    return PromptFrontmatter(
        scope=child.scope if child.scope else parent.scope,
        triggers=child.triggers if child.triggers else parent.triggers,
        priority=child.priority if child.priority != 0 else parent.priority,
        inherits=None,
        variables={**parent.variables, **child.variables},
    )


def _merge_bodies(parent_body: str, child_body: str) -> str:
    parts = [b.strip() for b in (parent_body, child_body) if b.strip()]
    return "\n\n".join(parts)


def resolve_single(
    prompt: PromptFile,
    registry: dict[str, PromptFile],
    _chain: tuple[str, ...] = (),
) -> PromptFile:
    if prompt.name in _chain:
        cycle = " -> ".join(_chain) + " -> " + prompt.name
        raise CircularInheritanceError(f"Circular inheritance detected: {cycle}")

    if prompt.frontmatter.inherits is None:
        return prompt

    parent_name = prompt.frontmatter.inherits
    if parent_name not in registry:
        raise ValueError(
            f"Prompt '{prompt.name}' inherits from unknown prompt '{parent_name}'"
        )

    resolved_parent = resolve_single(registry[parent_name], registry, _chain + (prompt.name,))
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
    registry = {p.name: p for p in prompts}
    return [resolve_single(p, registry) for p in prompts]


def cascade_merge(prompts: list[PromptFile]) -> list[PromptFile]:
    return sorted(prompts, key=lambda p: p.frontmatter.priority, reverse=True)
