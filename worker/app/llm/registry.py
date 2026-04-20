import logging
from typing import Any

logger = logging.getLogger("worker.llm.registry")

_REGISTRY: dict[str, type] = {}


def register(name: str):
    def decorator(cls: type) -> type:
        _REGISTRY[name] = cls
        return cls

    return decorator


def build_provider(name: str, **kwargs: Any) -> Any:
    try:
        cls = _REGISTRY[name]
    except KeyError:
        available = sorted(_REGISTRY)
        raise ValueError(f"Unknown LLM provider: {name!r}. Available: {available}")
    logger.info("initializing LLM provider: %s", name)
    return cls(**kwargs)
