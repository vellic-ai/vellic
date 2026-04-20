import logging

from ..registry import register

logger = logging.getLogger("worker.llm.anthropic")

_CLOSED_LOOP_WARNING = (
    "\u26a0\ufe0f  External LLM provider enabled. "
    "PR diff content will leave your infrastructure."
)


@register("anthropic")
class AnthropicProvider:
    def __init__(self, **_: object) -> None:
        logger.warning(_CLOSED_LOOP_WARNING)

    async def complete(self, prompt: str, *, max_tokens: int) -> str:
        raise NotImplementedError(
            "Anthropic provider stub. "
            "Set LLM_PROVIDER=ollama for local inference, "
            "or implement this adapter with your Anthropic API key."
        )

    async def health(self) -> bool:
        return False
