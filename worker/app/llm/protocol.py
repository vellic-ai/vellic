from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    async def complete(self, prompt: str, *, max_tokens: int) -> str: ...
    async def health(self) -> bool: ...
