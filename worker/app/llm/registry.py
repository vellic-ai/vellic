import logging
from typing import Any

from vellic_flags import by_key

logger = logging.getLogger("worker.llm.registry")

_REGISTRY: dict[str, type] = {}

# Map provider name → feature flag key
_PROVIDER_FLAGS: dict[str, str] = {
    "openai": "llm.openai",
    "anthropic": "llm.anthropic",
    "ollama": "llm.ollama",
    "vllm": "llm.vllm",
}


def _flag_enabled(key: str) -> bool:
    flag = by_key(key)
    if flag is None:
        return True  # unknown flags default to enabled
    env = flag.read_env()
    return env if env is not None else flag.default


def register(name: str):
    def decorator(cls: type) -> type:
        _REGISTRY[name] = cls
        return cls

    return decorator


def build_provider(name: str, **kwargs: Any) -> Any:
    flag_key = _PROVIDER_FLAGS.get(name)
    if flag_key and not _flag_enabled(flag_key):
        raise ValueError(f"LLM provider {name!r} is disabled by feature flag {flag_key!r}")
    try:
        cls = _REGISTRY[name]
    except KeyError:
        available = sorted(_REGISTRY)
        raise ValueError(f"Unknown LLM provider: {name!r}. Available: {available}") from None
    logger.info("initializing LLM provider: %s", name)
    return cls(**kwargs)
