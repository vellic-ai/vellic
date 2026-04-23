import logging

import httpx

from ..registry import register

logger = logging.getLogger("worker.llm.openai")

_CLOSED_LOOP_WARNING = (
    "⚠️  External LLM provider enabled. "
    "PR diff content will leave your infrastructure."
)

_API_BASE = "https://api.openai.com"


@register("openai")
class OpenAIProvider:
    def __init__(self, api_key: str, model: str = "gpt-4o", **_: object) -> None:
        logger.warning(_CLOSED_LOOP_WARNING)
        if not api_key:
            raise ValueError(
                "OpenAI provider requires an API key. "
                "Set one in the Admin UI (Settings → LLM Provider → API Key)."
            )
        self._model = model
        self._client = httpx.AsyncClient(
            base_url=_API_BASE,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=120.0,
        )
        logger.info("OpenAI provider configured: model=%s", model)

    async def complete(self, prompt: str, *, max_tokens: int) -> str:
        resp = await self._client.post(
            "/v1/chat/completions",
            json={
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    async def health(self) -> bool:
        try:
            resp = await self._client.get("/v1/models", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False
