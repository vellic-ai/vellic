"""Front-matter schema validation for prompt DSL files."""

from __future__ import annotations

from typing import Any

from .models import PromptFrontmatter

_VALID_TRIGGER_PREFIXES = ("pr.", "push.", "schedule.")
_KNOWN_KEYS = frozenset({"scope", "triggers", "priority", "inherits", "variables"})


class PromptValidationError(ValueError):
    """Raised when a prompt file's front-matter fails validation."""


def validate_frontmatter(raw: dict[str, Any], source_hint: str = "") -> PromptFrontmatter:
    loc = f" in {source_hint!r}" if source_hint else ""

    unknown = set(raw) - _KNOWN_KEYS
    if unknown:
        raise PromptValidationError(
            f"Unknown front-matter keys{loc}: {sorted(unknown)}. "
            f"Allowed: {sorted(_KNOWN_KEYS)}"
        )

    scope_raw = raw.get("scope", [])
    if isinstance(scope_raw, str):
        scope_raw = [scope_raw]
    if not isinstance(scope_raw, list):
        raise PromptValidationError(f"'scope' must be a string or list{loc}")
    scope = [str(s) for s in scope_raw]

    triggers_raw = raw.get("triggers", [])
    if isinstance(triggers_raw, str):
        triggers_raw = [triggers_raw]
    if not isinstance(triggers_raw, list):
        raise PromptValidationError(f"'triggers' must be a string or list{loc}")
    triggers = [str(t) for t in triggers_raw]
    for t in triggers:
        if not any(t.startswith(p) for p in _VALID_TRIGGER_PREFIXES):
            raise PromptValidationError(
                f"Invalid trigger {t!r}{loc}. Must start with one of: "
                + ", ".join(_VALID_TRIGGER_PREFIXES)
            )

    priority_raw = raw.get("priority", 0)
    try:
        priority = int(priority_raw)
    except (TypeError, ValueError):
        raise PromptValidationError(f"'priority' must be an integer{loc}") from None

    inherits_raw = raw.get("inherits")
    if inherits_raw is not None and not isinstance(inherits_raw, str):
        raise PromptValidationError(f"'inherits' must be a string{loc}")
    inherits = inherits_raw if inherits_raw else None

    variables_raw = raw.get("variables", {})
    if not isinstance(variables_raw, dict):
        raise PromptValidationError(f"'variables' must be a mapping{loc}")
    variables: dict[str, str] = {}
    for k, v in variables_raw.items():
        if not isinstance(k, str):
            raise PromptValidationError(f"Variable key {k!r} must be a string{loc}")
        variables[str(k)] = str(v)

    return PromptFrontmatter(
        scope=scope,
        triggers=triggers,
        priority=priority,
        inherits=inherits,
        variables=variables,
    )
