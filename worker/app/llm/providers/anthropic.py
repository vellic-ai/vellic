import logging

import httpx

from ..registry import register

logger = logging.getLogger("worker.llm.anthropic")

_CLOSED_LOOP_WARNING = (
    "⚠️  External LLM provider enabled. "
    "PR diff content will leave your infrastructure."
)

_API_BASE = "https://api.anthropic.com"
_ANTHROPIC_VERSION = "2023-06-01"


@register("anthropic")
class AnthropicProvider:
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022", **_: object) -> None:
        logger.warning(_CLOSED_LOOP_WARNING)
        if not api_key:
            raise ValueError("Anthropic provider requires LLM_API_KEY to be set.")
        self._model = model
        self._client = httpx.AsyncClient(
            base_url=_API_BASE,
            headers={
                "x-api-key": api_key,
                "anthropic-version": _ANTHROPIC_VERSION,
            },
            timeout=120.0,
        )
        logger.info("Anthropic provider configured: model=%s", model)

    async def complete(self, prompt: str, *, max_tokens: int) -> str:
        resp = await self._client.post(
            "/v1/messages",
            json={
                "model": self._model,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]

    async def health(self) -> bool:
        try:
            resp = await self._client.get("/v1/models", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False
