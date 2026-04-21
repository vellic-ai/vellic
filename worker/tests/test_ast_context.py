"""Tests for worker/app/context/ast/* — runs without tree-sitter installed
(graceful-degradation path) and with it when available."""
from __future__ import annotations

import pytest

from worker.app.context.ast.enricher import ASTEnricher, _extract_source_from_patch, _changed_line_numbers
from worker.app.context.ast.models import ASTContext, SymbolInfo
from worker.app.context.ast.registry import get_parser
from worker.app.pipeline.models import DiffChunk


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_chunk(filename: str, patch: str) -> DiffChunk:
    return DiffChunk(filename=filename, patch_lines=patch.splitlines())


# ---------------------------------------------------------------------------
# patch utilities
# ---------------------------------------------------------------------------

SIMPLE_PATCH = """\
@@ -1,3 +1,5 @@
 def foo():
+    x = 1
+    return x
 pass
"""


def test_extract_source_preserves_new_lines():
    src, line_nums = _extract_source_from_patch(SIMPLE_PATCH.splitlines())
    assert "x = 1" in src
    assert "return x" in src


def test_changed_line_numbers():
    changed = _changed_line_numbers(SIMPLE_PATCH.splitlines())
    assert len(changed) == 2
    assert changed[0] == 2
    assert changed[1] == 3


def test_extract_source_no_hunk():
    src, nums = _extract_source_from_patch(["+hello", "+world"])
    assert "hello" in src
    assert "world" in src


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------

def test_registry_python():
    p = get_parser("foo.py")
    assert p is not None
    assert p.language == "python"


def test_registry_typescript():
    p = get_parser("bar.ts")
    assert p is not None
    assert p.language == "typescript"


def test_registry_tsx():
    p = get_parser("comp.tsx")
    assert p is not None
    assert p.language == "tsx"


def test_registry_javascript():
    p = get_parser("index.js")
    assert p is not None
    assert p.language == "javascript"


def test_registry_go():
    p = get_parser("main.go")
    assert p is not None
    assert p.language == "go"


def test_registry_rust():
    p = get_parser("lib.rs")
    assert p is not None
    assert p.language == "rust"


def test_registry_unknown():
    assert get_parser("data.csv") is None
    assert get_parser("Makefile") is None


# ---------------------------------------------------------------------------
# ASTContext.symbols_for_lines
# ---------------------------------------------------------------------------

def test_symbols_for_lines_hit():
    ctx = ASTContext(
        filename="a.py",
        language="python",
        symbols=[
            SymbolInfo(name="foo", kind="function", start_line=1, end_line=10),
            SymbolInfo(name="bar", kind="function", start_line=15, end_line=25),
        ],
    )
    result = ctx.symbols_for_lines([5])
    assert len(result) == 1
    assert result[0].name == "foo"


def test_symbols_for_lines_miss():
    ctx = ASTContext(
        filename="a.py",
        language="python",
        symbols=[SymbolInfo(name="foo", kind="function", start_line=1, end_line=5)],
    )
    assert ctx.symbols_for_lines([20]) == []


def test_symbols_for_lines_dedup():
    ctx = ASTContext(
        filename="a.py",
        language="python",
        symbols=[SymbolInfo(name="foo", kind="function", start_line=1, end_line=10)],
    )
    result = ctx.symbols_for_lines([2, 3, 4])
    assert len(result) == 1


# ---------------------------------------------------------------------------
# ASTEnricher — unsupported file type
# ---------------------------------------------------------------------------

def test_enricher_unsupported_file():
    enricher = ASTEnricher()
    chunk = _make_chunk("data.csv", "+a,b,c\n")
    ctx = enricher.enrich(chunk)
    assert ctx.language == "unknown"
    assert ctx.symbols == []


def test_enricher_all_returns_dict():
    enricher = ASTEnricher()
    chunks = [_make_chunk("a.py", SIMPLE_PATCH), _make_chunk("b.csv", "+x\n")]
    result = enricher.enrich_all(chunks)
    assert set(result.keys()) == {"a.py", "b.csv"}


# ---------------------------------------------------------------------------
# Python parser (skipped gracefully if tree-sitter-python not installed)
# ---------------------------------------------------------------------------

def _ts_python_available() -> bool:
    try:
        import tree_sitter_python  # noqa: F401
        return True
    except ImportError:
        return False


@pytest.mark.skipif(not _ts_python_available(), reason="tree-sitter-python not installed")
def test_python_parser_functions():
    from worker.app.context.ast.python_parser import PythonASTProvider

    src = '''\
def greet(name: str) -> str:
    """Say hello."""
    return f"Hello {name}"


class Greeter:
    def __init__(self):
        pass

    def greet(self, name: str) -> str:
        return f"Hi {name}"
'''
    provider = PythonASTProvider()
    ctx = provider.parse("greet.py", src)
    assert ctx.language == "python"
    assert ctx.parse_error == ""
    names = {s.name for s in ctx.symbols}
    assert "greet" in names
    assert "Greeter" in names
    fn = next(s for s in ctx.symbols if s.name == "greet" and s.kind == "function")
    assert "greet(name" in fn.signature
    assert "Say hello" in fn.docstring


@pytest.mark.skipif(not _ts_python_available(), reason="tree-sitter-python not installed")
def test_python_enricher_finds_symbols_in_diff():
    enricher = ASTEnricher()
    patch = """\
@@ -1,6 +1,9 @@
 def old():
     pass
+
+def new_func(x: int) -> int:
+    return x * 2
"""
    chunk = _make_chunk("math.py", patch)
    ctx = enricher.enrich(chunk)
    assert ctx.language == "python"
    names = {s.name for s in ctx.symbols}
    assert "new_func" in names
