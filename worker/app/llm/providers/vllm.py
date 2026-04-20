from ..registry import register


@register("vllm")
class VLLMProvider:
    def __init__(self, **_: object) -> None:
        pass

    async def complete(self, prompt: str, *, max_tokens: int) -> str:
        raise NotImplementedError(
            "vLLM provider is not yet implemented. "
            "Deploy a vLLM-compatible server and implement this adapter, "
            "or set LLM_PROVIDER=ollama for local inference."
        )

    async def health(self) -> bool:
        return False
