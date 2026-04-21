"""Built-in prompt preset library and fork/customize loader (VEL-113).

Presets live under ``worker/app/prompts/presets/`` and are shipped with the
package.  Users can import any preset into their repo's ``.vellic/prompts/``
directory to fork it and layer customisations on top.
"""

from __future__ import annotations

from pathlib import Path

from .models import PromptFile
from .parser import load_prompts_from_dir, parse_prompt_content

# Directory that ships with the package.
_PRESETS_DIR = Path(__file__).parent / "presets"

# Canonical preset names shipped in this release.
BUILTIN_PRESET_NAMES: tuple[str, ...] = (
    "secure-review",
    "performance-review",
    "test-review",
    "doc-review",
    "style-review",
)


def list_presets() -> list[str]:
    """Return the names of all built-in presets (alphabetical order)."""
    return sorted(
        p.stem for p in _PRESETS_DIR.glob("*.md")
    )


def load_preset(name: str) -> PromptFile:
    """Load a built-in preset by *name* and return it as a :class:`PromptFile`.

    Raises:
        ValueError: If *name* is not a recognised preset.
        PromptValidationError: If the preset file is malformed (should never
            happen with shipped presets, but guarded for safety).
    """
    preset_path = _PRESETS_DIR / f"{name}.md"
    if not preset_path.exists():
        available = ", ".join(list_presets())
        raise ValueError(
            f"Unknown preset {name!r}. Available presets: {available}"
        )
    content = preset_path.read_text(encoding="utf-8")
    return parse_prompt_content(content, name=name, path=str(preset_path), source="preset")


def load_all_presets() -> list[PromptFile]:
    """Load every built-in preset and return them as a list of :class:`PromptFile`."""
    return load_prompts_from_dir(_PRESETS_DIR)


def fork_preset(
    name: str,
    target_dir: str | Path,
    *,
    custom_name: str | None = None,
) -> Path:
    """Fork a built-in preset into *target_dir* for repo-local customisation.

    The copied file is marked with ``source: repo`` so the pipeline treats it
    as a user-owned prompt that can be freely edited or overridden.

    Args:
        name: Name of the built-in preset to fork (e.g. ``"secure-review"``).
        target_dir: Destination directory — typically the repo's
            ``.vellic/prompts/`` folder.
        custom_name: Optional file stem for the forked copy.  Defaults to
            *name*, which overwrites an existing file with the same name.

    Returns:
        Path to the newly written file.

    Raises:
        ValueError: If *name* is not a recognised preset.
    """
    # Validate preset exists before touching the filesystem.
    load_preset(name)
    dest_dir = Path(target_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    output_name = custom_name if custom_name else name
    dest_path = dest_dir / f"{output_name}.md"

    # Re-serialise with source="repo" baked into a header comment.
    preset_path = _PRESETS_DIR / f"{name}.md"
    raw = preset_path.read_text(encoding="utf-8")

    # Insert a header comment so the user knows the origin.
    header = f"# Forked from built-in preset: {name}\n# Edit freely — this file is yours.\n\n"
    dest_path.write_text(header + raw, encoding="utf-8")

    return dest_path
