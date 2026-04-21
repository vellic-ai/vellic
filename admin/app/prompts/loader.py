"""Preset loader for admin service.

Reads preset .md files from VELLIC_PRESETS_DIR env var (set in Docker to
/app/presets, which is populated from worker/app/prompts/presets/ at build
time). Falls back to the sibling worker directory for local dev.
"""

from __future__ import annotations

import os
from pathlib import Path

from .models import PromptFile
from .parser import load_prompts_from_dir, parse_prompt_content


def _presets_dir() -> Path:
    d = os.getenv("VELLIC_PRESETS_DIR", "")
    if d:
        return Path(d)
    # Local dev fallback: monorepo sibling path
    return Path(__file__).parents[4] / "worker" / "app" / "prompts" / "presets"


def list_presets() -> list[str]:
    d = _presets_dir()
    if not d.is_dir():
        return []
    return sorted(p.stem for p in d.glob("*.md"))


def load_preset(name: str) -> PromptFile:
    d = _presets_dir()
    preset_path = d / f"{name}.md"
    if not preset_path.exists():
        available = ", ".join(list_presets())
        raise ValueError(f"Unknown preset {name!r}. Available: {available}")
    content = preset_path.read_text(encoding="utf-8")
    return parse_prompt_content(content, name=name, path=str(preset_path), source="preset")


def load_all_presets() -> list[PromptFile]:
    return load_prompts_from_dir(_presets_dir(), source="preset")
