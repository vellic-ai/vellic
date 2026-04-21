from abc import ABC, abstractmethod

from .models import ASTContext


class ASTProvider(ABC):
    """Parse source text and extract symbol information."""

    @property
    @abstractmethod
    def language(self) -> str:
        """Canonical language name (e.g. 'python', 'typescript')."""

    @property
    @abstractmethod
    def file_extensions(self) -> tuple[str, ...]:
        """File extensions this provider handles (e.g. ('.py',))."""

    @abstractmethod
    def parse(self, filename: str, source: str) -> ASTContext:
        """Parse *source* and return an ASTContext with symbols populated."""
