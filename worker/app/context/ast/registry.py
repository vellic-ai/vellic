"""Maps file extensions to ASTProvider instances."""
from __future__ import annotations

import os

from .provider import ASTProvider

_providers: dict[str, ASTProvider] | None = None


def _build_registry() -> dict[str, ASTProvider]:
    registry: dict[str, ASTProvider] = {}

    from .go_parser import GoASTProvider
    from .python_parser import PythonASTProvider
    from .rust_parser import RustASTProvider
    from .ts_parser import JavaScriptASTProvider, TSXASTProvider, TypeScriptASTProvider

    for provider in (
        PythonASTProvider(),
        TypeScriptASTProvider(),
        TSXASTProvider(),
        JavaScriptASTProvider(),
        GoASTProvider(),
        RustASTProvider(),
    ):
        for ext in provider.file_extensions:
            registry[ext] = provider

    return registry


def get_parser(filename: str) -> ASTProvider | None:
    """Return the ASTProvider for *filename*, or None if unsupported."""
    global _providers
    if _providers is None:
        _providers = _build_registry()
    ext = os.path.splitext(filename)[1].lower()
    return _providers.get(ext)
