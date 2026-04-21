from __future__ import annotations

import logging

from .models import ASTContext, SymbolInfo
from .provider import ASTProvider

logger = logging.getLogger("worker.context.ast.rust")

try:
    import tree_sitter_rust as _tsrust
    from tree_sitter import Language, Node, Parser

    _LANGUAGE = Language(_tsrust.language())
    _PARSER = Parser(_LANGUAGE)
    _AVAILABLE = True
except Exception as exc:  # pragma: no cover
    _AVAILABLE = False
    logger.debug("tree-sitter-rust unavailable: %s", exc)


def _text(node: "Node", src: bytes) -> str:
    return src[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _extract_rust_symbols(node: "Node", src: bytes, parent_name: str = "") -> list[SymbolInfo]:
    symbols: list[SymbolInfo] = []
    for child in node.children:
        if child.type == "function_item":
            name_node = child.child_by_field_name("name")
            name = _text(name_node, src) if name_node else "<unknown>"
            sig = _text(child, src).split("{")[0].strip()[:120]
            symbols.append(SymbolInfo(
                name=name, kind="method" if parent_name else "function",
                signature=sig,
                start_line=child.start_point[0] + 1, end_line=child.end_point[0] + 1,
                parent=parent_name,
            ))
            symbols.extend(_extract_rust_symbols(child, src, parent_name=name))

        elif child.type in ("struct_item", "enum_item", "trait_item", "impl_item"):
            name_node = child.child_by_field_name("name")
            name = _text(name_node, src) if name_node else "<unknown>"
            kind_map = {"struct_item": "class", "enum_item": "class", "trait_item": "class", "impl_item": "class"}
            symbols.append(SymbolInfo(
                name=name, kind=kind_map.get(child.type, "class"),
                signature=_text(child, src).split("{")[0].strip()[:120],
                start_line=child.start_point[0] + 1, end_line=child.end_point[0] + 1,
                parent=parent_name,
            ))
            symbols.extend(_extract_rust_symbols(child, src, parent_name=name))

        else:
            symbols.extend(_extract_rust_symbols(child, src, parent_name=parent_name))

    return symbols


class RustASTProvider(ASTProvider):
    language = "rust"
    file_extensions = (".rs",)

    def parse(self, filename: str, source: str) -> ASTContext:
        if not _AVAILABLE:
            return ASTContext(filename=filename, language="rust", parse_error="tree-sitter-rust not installed")
        src = source.encode("utf-8")
        try:
            tree = _PARSER.parse(src)
            symbols = _extract_rust_symbols(tree.root_node, src)
        except Exception as exc:
            return ASTContext(filename=filename, language="rust", parse_error=str(exc))
        return ASTContext(filename=filename, language="rust", symbols=symbols)
