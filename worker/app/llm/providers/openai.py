import logging

from ..registry import register

logger = logging.getLogger("worker.llm.openai")

_CLOSED_LOOP_WARNING = (
    "\u26a0\ufe0f  External LLM provider enabled. "
    "PR diff content will leave your infrastructure."
)


@register("openai")
class OpenAIProvider:
    def __init__(self, **_: object) -> None:
        logger.warning(_CLOSED_LOOP_WARNING)

    async def complete(self, prompt: str, *, max_tokens: int) -> str:
        raise NotImplementedError(
            "OpenAI provider stub. "
            "Set LLM_PROVIDER=ollama for local inference, "
            "or implement this adapter with your OpenAI API key."
        )

    async def health(self) -> bool:
        return False
