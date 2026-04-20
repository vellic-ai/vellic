import logging

import httpx

from ..registry import register

logger = logging.getLogger("worker.llm.ollama")


@register("ollama")
class OllamaProvider:
    def __init__(self, base_url: str, model: str, **_: object) -> None:
        self._model = model
        self._client = httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=120.0)
        logger.info("Ollama provider configured: base_url=%s model=%s", base_url, model)

    async def complete(self, prompt: str, *, max_tokens: int) -> str:
        resp = await self._client.post(
            "/api/generate",
            json={
                "model": self._model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": max_tokens},
            },
        )
        resp.raise_for_status()
        return resp.json()["response"]

    async def health(self) -> bool:
        try:
            resp = await self._client.get("/api/tags", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False
