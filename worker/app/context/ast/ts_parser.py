"""TypeScript / JavaScript AST provider using tree-sitter."""
from __future__ import annotations

import logging

from .models import ASTContext, SymbolInfo
from .provider import ASTProvider

logger = logging.getLogger("worker.context.ast.typescript")

try:
    import tree_sitter_typescript as _tsts
    from tree_sitter import Language, Node, Parser

    _TS_LANGUAGE = Language(_tsts.language_typescript())
    _TS_PARSER = Parser(_TS_LANGUAGE)
    _TSX_LANGUAGE = Language(_tsts.language_tsx())
    _TSX_PARSER = Parser(_TSX_LANGUAGE)
    _TS_AVAILABLE = True
except Exception as exc:  # pragma: no cover
    _TS_AVAILABLE = False
    logger.debug("tree-sitter-typescript unavailable: %s", exc)

try:
    import tree_sitter_javascript as _tsjs
    from tree_sitter import Language, Parser  # noqa: F811

    _JS_LANGUAGE = Language(_tsjs.language())
    _JS_PARSER = Parser(_JS_LANGUAGE)
    _JS_AVAILABLE = True
except Exception as exc:  # pragma: no cover
    _JS_AVAILABLE = False
    logger.debug("tree-sitter-javascript unavailable: %s", exc)


_FUNC_TYPES = {
    "function_declaration",
    "function_expression",
    "arrow_function",
    "method_definition",
    "generator_function_declaration",
}

_CLASS_TYPES = {
    "class_declaration",
    "class_expression",
}


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _get_js_docstring(node: Node, src: bytes) -> str:
    prev = node.prev_sibling
    if prev and prev.type == "comment":
        raw = _text(prev, src)
        if raw.startswith("/**") or raw.startswith("//"):
            return raw.lstrip("/ *\n").rstrip("/ *\n")[:500]
    return ""


def _extract_js_symbols(
    node: Node,
    src: bytes,
    parent_name: str = "",
) -> list[SymbolInfo]:
    symbols: list[SymbolInfo] = []

    for child in node.children:
        if child.type in _FUNC_TYPES:
            name_node = child.child_by_field_name("name")
            name = _text(name_node, src) if name_node else "<anonymous>"
            doc = _get_js_docstring(child, src)
            sym = SymbolInfo(
                name=name,
                kind="method" if parent_name else "function",
                signature=_text(child, src).split("{")[0].strip()[:120],
                docstring=doc,
                start_line=child.start_point[0] + 1,
                end_line=child.end_point[0] + 1,
                parent=parent_name,
            )
            symbols.append(sym)
            symbols.extend(_extract_js_symbols(child, src, parent_name=name))

        elif child.type in _CLASS_TYPES:
            name_node = child.child_by_field_name("name")
            name = _text(name_node, src) if name_node else "<anonymous>"
            doc = _get_js_docstring(child, src)
            sym = SymbolInfo(
                name=name,
                kind="class",
                signature=f"class {name}",
                docstring=doc,
                start_line=child.start_point[0] + 1,
                end_line=child.end_point[0] + 1,
                parent=parent_name,
            )
            symbols.append(sym)
            symbols.extend(_extract_js_symbols(child, src, parent_name=name))

        else:
            symbols.extend(_extract_js_symbols(child, src, parent_name=parent_name))

    return symbols


class TypeScriptASTProvider(ASTProvider):
    language = "typescript"
    file_extensions = (".ts",)

    def parse(self, filename: str, source: str) -> ASTContext:
        if not _TS_AVAILABLE:
            return ASTContext(filename=filename, language="typescript",
                              parse_error="tree-sitter-typescript not installed")
        src = source.encode("utf-8")
        try:
            tree = _TS_PARSER.parse(src)
            symbols = _extract_js_symbols(tree.root_node, src)
        except Exception as exc:
            return ASTContext(filename=filename, language="typescript", parse_error=str(exc))
        return ASTContext(filename=filename, language="typescript", symbols=symbols)


class TSXASTProvider(ASTProvider):
    language = "tsx"
    file_extensions = (".tsx",)

    def parse(self, filename: str, source: str) -> ASTContext:
        if not _TS_AVAILABLE:
            return ASTContext(filename=filename, language="tsx",
                              parse_error="tree-sitter-typescript not installed")
        src = source.encode("utf-8")
        try:
            tree = _TSX_PARSER.parse(src)
            symbols = _extract_js_symbols(tree.root_node, src)
        except Exception as exc:
            return ASTContext(filename=filename, language="tsx", parse_error=str(exc))
        return ASTContext(filename=filename, language="tsx", symbols=symbols)


class JavaScriptASTProvider(ASTProvider):
    language = "javascript"
    file_extensions = (".js", ".mjs", ".cjs", ".jsx")

    def parse(self, filename: str, source: str) -> ASTContext:
        if not _JS_AVAILABLE:
            return ASTContext(filename=filename, language="javascript",
                              parse_error="tree-sitter-javascript not installed")
        src = source.encode("utf-8")
        try:
            tree = _JS_PARSER.parse(src)
            symbols = _extract_js_symbols(tree.root_node, src)
        except Exception as exc:
            return ASTContext(filename=filename, language="javascript", parse_error=str(exc))
        return ASTContext(filename=filename, language="javascript", symbols=symbols)
