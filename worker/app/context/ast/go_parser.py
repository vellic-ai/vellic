from __future__ import annotations

import logging

from .models import ASTContext, SymbolInfo
from .provider import ASTProvider

logger = logging.getLogger("worker.context.ast.go")

try:
    import tree_sitter_go as _tsgo
    from tree_sitter import Language, Node, Parser

    _LANGUAGE = Language(_tsgo.language())
    _PARSER = Parser(_LANGUAGE)
    _AVAILABLE = True
except Exception as exc:  # pragma: no cover
    _AVAILABLE = False
    logger.debug("tree-sitter-go unavailable: %s", exc)


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _extract_go_symbols(node: Node, src: bytes, parent_name: str = "") -> list[SymbolInfo]:
    symbols: list[SymbolInfo] = []
    for child in node.children:
        if child.type == "function_declaration":
            name_node = child.child_by_field_name("name")
            name = _text(name_node, src) if name_node else "<unknown>"
            sig = _text(child, src).split("{")[0].strip()[:120]
            symbols.append(SymbolInfo(
                name=name, kind="function", signature=sig,
                start_line=child.start_point[0] + 1, end_line=child.end_point[0] + 1,
                parent=parent_name,
            ))
            symbols.extend(_extract_go_symbols(child, src, parent_name=name))

        elif child.type == "method_declaration":
            name_node = child.child_by_field_name("name")
            recv_node = child.child_by_field_name("receiver")
            name = _text(name_node, src) if name_node else "<unknown>"
            recv = _text(recv_node, src).strip("() ") if recv_node else ""
            sig = _text(child, src).split("{")[0].strip()[:120]
            symbols.append(SymbolInfo(
                name=name, kind="method", signature=sig,
                start_line=child.start_point[0] + 1, end_line=child.end_point[0] + 1,
                parent=recv,
            ))
            symbols.extend(_extract_go_symbols(child, src, parent_name=name))

        elif child.type == "type_declaration":
            for spec in child.children:
                if spec.type == "type_spec":
                    name_node = spec.child_by_field_name("name")
                    if name_node:
                        name = _text(name_node, src)
                        symbols.append(SymbolInfo(
                            name=name, kind="class", signature=f"type {name}",
                            start_line=spec.start_point[0] + 1, end_line=spec.end_point[0] + 1,
                        ))
        else:
            symbols.extend(_extract_go_symbols(child, src, parent_name=parent_name))

    return symbols


class GoASTProvider(ASTProvider):
    language = "go"
    file_extensions = (".go",)

    def parse(self, filename: str, source: str) -> ASTContext:
        if not _AVAILABLE:
            return ASTContext(filename=filename, language="go",
                              parse_error="tree-sitter-go not installed")
        src = source.encode("utf-8")
        try:
            tree = _PARSER.parse(src)
            symbols = _extract_go_symbols(tree.root_node, src)
        except Exception as exc:
            return ASTContext(filename=filename, language="go", parse_error=str(exc))
        return ASTContext(filename=filename, language="go", symbols=symbols)
