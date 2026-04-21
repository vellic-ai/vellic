from dataclasses import dataclass, field


@dataclass
class SymbolInfo:
    name: str
    kind: str  # "function" | "method" | "class" | "module"
    signature: str = ""
    docstring: str = ""
    start_line: int = 0
    end_line: int = 0
    parent: str = ""  # enclosing class name if applicable


@dataclass
class ASTContext:
    filename: str
    language: str
    symbols: list[SymbolInfo] = field(default_factory=list)
    parse_error: str = ""

    def symbols_for_lines(self, lines: list[int]) -> list[SymbolInfo]:
        """Return symbols whose body contains any of the given 1-based line numbers."""
        result: list[SymbolInfo] = []
        seen: set[tuple[str, str]] = set()
        for sym in self.symbols:
            if sym.start_line == 0:
                continue
            for ln in lines:
                if sym.start_line <= ln <= sym.end_line and (sym.name, sym.parent) not in seen:
                    result.append(sym)
                    seen.add((sym.name, sym.parent))
                    break
        return result
