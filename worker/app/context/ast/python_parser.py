from __future__ import annotations

import logging

from .models import ASTContext, SymbolInfo
from .provider import ASTProvider

logger = logging.getLogger("worker.context.ast.python")

try:
    import tree_sitter_python as _tspy
    from tree_sitter import Language, Node, Parser

    _LANGUAGE = Language(_tspy.language())
    _PARSER = Parser(_LANGUAGE)
    _AVAILABLE = True
except Exception as exc:  # pragma: no cover
    _AVAILABLE = False
    logger.debug("tree-sitter-python unavailable: %s", exc)


def _text(node: Node, source_bytes: bytes) -> str:
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _get_docstring(node: Node, source_bytes: bytes) -> str:
    """Return the first string literal child of a function/class body, if any."""
    for child in node.children:
        if child.type == "block":
            for stmt in child.children:
                if stmt.type == "expression_statement":
                    for expr in stmt.children:
                        if expr.type == "string":
                            raw = _text(expr, source_bytes).strip("\"' \t\n")
                            return raw[:500]
    return ""


def _extract_symbols(
    node: Node,
    source_bytes: bytes,
    parent_name: str = "",
) -> list[SymbolInfo]:
    symbols: list[SymbolInfo] = []

    for child in node.children:
        if child.type in ("function_definition", "async_function_definition"):
            name_node = child.child_by_field_name("name")
            params_node = child.child_by_field_name("parameters")
            name = _text(name_node, source_bytes) if name_node else "<unknown>"
            params = _text(params_node, source_bytes) if params_node else "()"
            sig = f"def {name}{params}"
            doc = _get_docstring(child, source_bytes)
            sym = SymbolInfo(
                name=name,
                kind="method" if parent_name else "function",
                signature=sig,
                docstring=doc,
                start_line=child.start_point[0] + 1,
                end_line=child.end_point[0] + 1,
                parent=parent_name,
            )
            symbols.append(sym)
            symbols.extend(_extract_symbols(child, source_bytes, parent_name=name))

        elif child.type == "class_definition":
            name_node = child.child_by_field_name("name")
            name = _text(name_node, source_bytes) if name_node else "<unknown>"
            doc = _get_docstring(child, source_bytes)
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
            symbols.extend(_extract_symbols(child, source_bytes, parent_name=name))

        else:
            symbols.extend(_extract_symbols(child, source_bytes, parent_name=parent_name))

    return symbols


class PythonASTProvider(ASTProvider):
    language = "python"
    file_extensions = (".py",)

    def parse(self, filename: str, source: str) -> ASTContext:
        if not _AVAILABLE:
            return ASTContext(filename=filename, language="python",
                              parse_error="tree-sitter-python not installed")

        source_bytes = source.encode("utf-8")
        try:
            tree = _PARSER.parse(source_bytes)
            symbols = _extract_symbols(tree.root_node, source_bytes)
        except Exception as exc:
            logger.warning("parse error %s: %s", filename, exc)
            return ASTContext(filename=filename, language="python", parse_error=str(exc))

        return ASTContext(filename=filename, language="python", symbols=symbols)
